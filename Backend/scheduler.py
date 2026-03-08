"""
SporeRisk — Auto-Refresh Scheduler
====================================
Monitors data sources for new entries and triggers the full pipeline:
  detect new data → scrape → standardize → retrain → update predictions

Data source refresh cadences:
  Open-Meteo (weather):   Daily archive updates, ~2 day lag
  EPA AQS (PM10):         Quarterly bulk file drops (Jan, Apr, Jul, Oct)
  CDPH (cases):           Annual release, typically mid-year for prior year

The scheduler runs as a background thread alongside the FastAPI server,
or standalone via cron / systemd timer.

Usage:
  # As standalone (cron-friendly):
  python scheduler.py --run-once

  # Or import into api.py to run as background thread:
  from scheduler import start_scheduler
  start_scheduler(interval_hours=6)
"""

import os
import json
import time
import hashlib
import logging
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = BASE_DIR / "data"
STATE_FILE = BASE_DIR / "scheduler_state.json"
LOG_FILE = BASE_DIR / "scheduler.log"

# How often to check each source
CHECK_INTERVALS = {
    "weather":     timedelta(hours=12),   # Open-Meteo updates daily
    "air_quality": timedelta(days=7),     # EPA bulk drops quarterly, but check weekly
    "cases":       timedelta(days=30),    # CDPH annual, check monthly
}

COUNTIES = {
    "Fresno":      {"lat": 36.7378, "lon": -119.7871, "fips": "06019"},
    "Kern":        {"lat": 35.3433, "lon": -118.7279, "fips": "06029"},
    "Kings":       {"lat": 36.0748, "lon": -119.8154, "fips": "06031"},
    "Madera":      {"lat": 37.2180, "lon": -119.7573, "fips": "06039"},
    "Merced":      {"lat": 37.1913, "lon": -120.7151, "fips": "06047"},
    "San Joaquin": {"lat": 37.9317, "lon": -121.2717, "fips": "06077"},
    "Stanislaus":  {"lat": 37.5591, "lon": -120.9982, "fips": "06099"},
    "Tulare":      {"lat": 36.2077, "lon": -119.0539, "fips": "06107"},
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("sporerisk.scheduler")


# ─────────────────────────────────────────────────────────────────────────────
# STATE MANAGEMENT — tracks what we've already seen
# ─────────────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load the scheduler's memory of what data it's already processed."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "weather_last_date": None,       # latest date in weather.csv
        "air_quality_last_date": None,   # latest date in air_quality.csv
        "cases_last_year": None,         # latest year in cases.csv
        "last_check": {},                # {source: iso_timestamp}
        "last_pipeline_run": None,       # when we last ran the full pipeline
        "data_hashes": {},               # {filename: sha256} to detect changes
    }


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def file_hash(path: Path) -> Optional[str]:
    """SHA256 of a file's contents for change detection."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# DATA FRESHNESS CHECKS — probe sources without full scrape
# ─────────────────────────────────────────────────────────────────────────────

def check_weather_freshness(state: dict) -> dict:
    """
    Probe Open-Meteo to see if there's newer weather data than what we have.
    Open-Meteo archive typically has a ~2 day lag.
    """
    result = {"source": "weather", "has_new_data": False, "details": {}}

    try:
        # Check one county (Merced) as a canary
        resp = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": 37.1913, "longitude": -120.7151,
                "start_date": (date.today() - timedelta(days=5)).isoformat(),
                "end_date": date.today().isoformat(),
                "daily": "precipitation_sum",
                "timezone": "America/Los_Angeles",
            },
            timeout=15,
        )
        data = resp.json()
        dates = data.get("daily", {}).get("time", [])
        # Filter out dates with null values (not yet available)
        precip = data.get("daily", {}).get("precipitation_sum", [])
        available_dates = [d for d, p in zip(dates, precip) if p is not None]

        if available_dates:
            latest_available = max(available_dates)
            our_latest = state.get("weather_last_date")

            result["details"] = {
                "latest_available": latest_available,
                "our_latest": our_latest,
            }

            if our_latest is None or latest_available > our_latest:
                result["has_new_data"] = True
                result["new_through"] = latest_available
                log.info(f"Weather: new data available through {latest_available} (we have through {our_latest})")
            else:
                log.debug(f"Weather: up to date through {our_latest}")

    except Exception as e:
        log.warning(f"Weather freshness check failed: {e}")
        result["error"] = str(e)

    return result


def check_air_quality_freshness(state: dict) -> dict:
    """
    Check if EPA AQS has published a new yearly PM10 bulk file.
    EPA typically drops files for the prior year in Q1.
    """
    result = {"source": "air_quality", "has_new_data": False, "details": {}}

    try:
        current_year = date.today().year
        # Check if this year's file exists (it wouldn't until ~March)
        url = f"https://aqs.epa.gov/aqsweb/airdata/daily_81102_{current_year}.zip"
        resp = requests.head(url, timeout=15)

        if resp.status_code == 200:
            content_length = resp.headers.get("Content-Length", "0")
            last_modified = resp.headers.get("Last-Modified", "")

            our_latest = state.get("air_quality_last_date")
            result["details"] = {
                "year_available": current_year,
                "file_size": content_length,
                "last_modified": last_modified,
                "our_latest": our_latest,
            }

            # If we don't have data for this year yet, it's new
            if our_latest is None or our_latest < f"{current_year}-01-01":
                result["has_new_data"] = True
                log.info(f"Air quality: {current_year} EPA file available (we have through {our_latest})")
        else:
            # Also check prior year in case we missed it
            prior_year = current_year - 1
            url_prior = f"https://aqs.epa.gov/aqsweb/airdata/daily_81102_{prior_year}.zip"
            resp_prior = requests.head(url_prior, timeout=15)
            if resp_prior.status_code == 200:
                our_latest = state.get("air_quality_last_date")
                if our_latest is None or our_latest < f"{prior_year}-01-01":
                    result["has_new_data"] = True
                    result["details"]["year_available"] = prior_year
                    log.info(f"Air quality: {prior_year} EPA file available")

    except Exception as e:
        log.warning(f"Air quality freshness check failed: {e}")
        result["error"] = str(e)

    return result


def check_cases_freshness(state: dict) -> dict:
    """
    Check if CDPH has released new Valley Fever case data.
    CDPH updates their dashboard periodically — we check for a local
    cdph_valley_fever.csv drop (manual or automated download).
    """
    result = {"source": "cases", "has_new_data": False, "details": {}}

    cdph_path = DATA_DIR / "cdph_valley_fever.csv"

    # Strategy 1: Check if manual CDPH CSV was updated
    if cdph_path.exists():
        current_hash = file_hash(cdph_path)
        stored_hash = state.get("data_hashes", {}).get("cdph_valley_fever.csv")

        if current_hash != stored_hash:
            result["has_new_data"] = True
            result["details"]["reason"] = "cdph_valley_fever.csv modified"
            log.info("Cases: CDPH CSV was updated externally")
            return result

    # Strategy 2: Check if our hardcoded REAL_CASES in scraper.py covers current year
    current_year = date.today().year
    cases_path = DATA_DIR / "cases.csv"
    if cases_path.exists():
        df = pd.read_csv(cases_path)
        max_year = df["year"].max()
        our_latest = state.get("cases_last_year")

        result["details"] = {
            "max_year_in_data": int(max_year),
            "current_year": current_year,
        }

        # Cases typically lag by a year — if it's 2026 and we only have through 2024, that's expected
        # Flag if a new CDPH file appeared or was modified
        if our_latest and int(max_year) > int(our_latest):
            result["has_new_data"] = True
            log.info(f"Cases: new year detected ({max_year} vs stored {our_latest})")
    else:
        result["has_new_data"] = True
        result["details"]["reason"] = "cases.csv missing — needs initial scrape"

    return result


# ─────────────────────────────────────────────────────────────────────────────
# INCREMENTAL SCRAPING — only fetch what's new
# ─────────────────────────────────────────────────────────────────────────────

def incremental_weather_scrape(state: dict) -> bool:
    """
    Scrape only new weather data since our last known date.
    Appends to existing weather.csv instead of full re-scrape.
    """
    log.info("Starting incremental weather scrape...")

    our_latest = state.get("weather_last_date")
    if our_latest:
        start = (pd.to_datetime(our_latest) + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start = "2020-01-01"

    end = date.today().isoformat()

    if start >= end:
        log.info("Weather: already up to date")
        return False

    frames = []
    for county, meta in COUNTIES.items():
        log.info(f"  Fetching weather for {county} ({start} → {end})...")
        try:
            # Daily weather
            resp = requests.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": meta["lat"], "longitude": meta["lon"],
                    "start_date": start, "end_date": end,
                    "daily": ["precipitation_sum", "wind_speed_10m_max", "temperature_2m_max"],
                    "timezone": "America/Los_Angeles",
                },
                timeout=60,
            )
            data = resp.json()
            d = data["daily"]
            df = pd.DataFrame({
                "date": d["time"],
                "county": county,
                "precip_mm": d["precipitation_sum"],
                "wind_speed_kmh": d["wind_speed_10m_max"],
                "tmax_approx_c": d["temperature_2m_max"],
            })
            df["date"] = pd.to_datetime(df["date"])

            # Hourly soil moisture → daily mean
            time.sleep(0.4)
            hresp = requests.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": meta["lat"], "longitude": meta["lon"],
                    "start_date": start, "end_date": end,
                    "hourly": ["soil_moisture_0_to_7cm"],
                    "timezone": "America/Los_Angeles",
                },
                timeout=60,
            )
            hdata = hresp.json()
            h = hdata["hourly"]
            dh = pd.DataFrame({"datetime": h["time"], "soil": h["soil_moisture_0_to_7cm"]})
            dh["date"] = pd.to_datetime(dh["datetime"]).dt.normalize()
            soil = dh.groupby("date")["soil"].mean().reset_index()
            soil.columns = ["date", "soil_moisture_m3m3"]
            df = df.merge(soil, on="date", how="left")

            # Drop rows where all values are null (dates beyond archive availability)
            df = df.dropna(subset=["precip_mm", "wind_speed_kmh", "tmax_approx_c"], how="all")
            frames.append(df)
            log.info(f"    {county}: {len(df)} new rows")
            time.sleep(0.3)

        except Exception as e:
            log.warning(f"    {county}: FAILED ({e})")

    if not frames:
        return False

    new_data = pd.concat(frames, ignore_index=True)
    new_data = new_data[["date", "county", "precip_mm", "soil_moisture_m3m3",
                          "wind_speed_kmh", "tmax_approx_c"]]

    # Append to existing or create new
    weather_path = DATA_DIR / "weather.csv"
    if weather_path.exists():
        existing = pd.read_csv(weather_path, parse_dates=["date"])
        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "county"], keep="last")
        combined = combined.sort_values(["county", "date"]).reset_index(drop=True)
    else:
        combined = new_data

    combined.to_csv(weather_path, index=False, date_format="%Y-%m-%d")
    log.info(f"Weather: saved {len(new_data)} new rows → {weather_path} (total: {len(combined)})")

    # Update state
    latest = combined["date"].max()
    state["weather_last_date"] = latest.strftime("%Y-%m-%d") if pd.notna(latest) else state.get("weather_last_date")

    return True


def incremental_air_quality_scrape(state: dict) -> bool:
    """
    Check for new EPA AQS PM10 yearly zip files.
    Only downloads years we don't already have.
    """
    log.info("Checking for new EPA AQS PM10 data...")
    import zipfile
    import io

    fips_to_county = {v["fips"][2:]: c for c, v in COUNTIES.items()}
    ca_fips = set(fips_to_county.keys())

    aq_path = DATA_DIR / "air_quality.csv"
    if aq_path.exists():
        existing = pd.read_csv(aq_path, parse_dates=["date"])
        existing_years = set(existing["date"].dt.year.unique())
    else:
        existing = pd.DataFrame(columns=["date", "county", "pm10_ugm3"])
        existing_years = set()

    # Check which years might have new data
    current_year = date.today().year
    years_to_check = []
    for y in range(2020, current_year + 1):
        if y not in existing_years or y >= current_year - 1:
            # Always recheck current year and prior year (files get updated)
            years_to_check.append(y)

    if not years_to_check:
        log.info("Air quality: all years up to date")
        return False

    new_rows = []
    fetched_any = False

    for year in years_to_check:
        url = f"https://aqs.epa.gov/aqsweb/airdata/daily_81102_{year}.zip"
        log.info(f"  Fetching PM10 for {year}...")
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df_year = pd.read_csv(f, usecols=[
                        "State Code", "County Code",
                        "Date Local", "Arithmetic Mean", "Parameter Code"
                    ], dtype=str)

            df_year = df_year[
                (df_year["State Code"] == "06") &
                (df_year["County Code"].isin(ca_fips)) &
                (df_year["Parameter Code"] == "81102")
            ].copy()
            df_year["county"] = df_year["County Code"].map(fips_to_county)
            df_year["date"] = pd.to_datetime(df_year["Date Local"])
            df_year["pm10_ugm3"] = pd.to_numeric(df_year["Arithmetic Mean"], errors="coerce")
            df_year = df_year.dropna(subset=["pm10_ugm3"])
            df_year = df_year[df_year["pm10_ugm3"].between(0, 1500)]
            new_rows.append(df_year[["date", "county", "pm10_ugm3"]])
            log.info(f"    {year}: {len(df_year)} rows")
            fetched_any = True
            time.sleep(0.5)

        except Exception as e:
            log.warning(f"    {year}: FAILED ({e})")

    if not fetched_any:
        return False

    new_data = pd.concat(new_rows, ignore_index=True)
    new_data = new_data.groupby(["date", "county"])["pm10_ugm3"].mean().reset_index()

    # Merge with existing (replace years we re-fetched)
    if not existing.empty:
        refetched_years = set(new_data["date"].dt.year.unique())
        existing_keep = existing[~existing["date"].dt.year.isin(refetched_years)]
        combined = pd.concat([existing_keep, new_data], ignore_index=True)
    else:
        combined = new_data

    combined = combined.sort_values(["county", "date"]).reset_index(drop=True)
    combined.to_csv(aq_path, index=False, date_format="%Y-%m-%d")
    log.info(f"Air quality: saved {len(new_data)} rows → {aq_path} (total: {len(combined)})")

    latest = combined["date"].max()
    state["air_quality_last_date"] = latest.strftime("%Y-%m-%d") if pd.notna(latest) else state.get("air_quality_last_date")

    return True


def refresh_cases(state: dict) -> bool:
    """
    Re-run the cases collector from scraper.py.
    This picks up any manually updated cdph_valley_fever.csv
    or uses the hardcoded REAL_CASES fallback.
    """
    log.info("Refreshing case data...")
    try:
        # Import and run the scraper's case collection
        import importlib.util
        spec = importlib.util.spec_from_file_location("scraper", BASE_DIR / "scraper.py")
        scraper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scraper)

        os.makedirs(DATA_DIR, exist_ok=True)
        scraper.collect_cases()

        # Update state
        cases_path = DATA_DIR / "cases.csv"
        if cases_path.exists():
            df = pd.read_csv(cases_path)
            state["cases_last_year"] = int(df["year"].max())
            # Track hash of CDPH file if it exists
            cdph_path = DATA_DIR / "cdph_valley_fever.csv"
            if cdph_path.exists():
                state.setdefault("data_hashes", {})["cdph_valley_fever.csv"] = file_hash(cdph_path)

        log.info("Cases: refreshed successfully")
        return True

    except Exception as e:
        log.error(f"Cases refresh failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE RE-RUN — standardize + retrain + update predictions
# ─────────────────────────────────────────────────────────────────────────────

def run_full_pipeline():
    """
    After new data is scraped, run the full standardization + model pipeline:
      data_collector.py → model_baseline.py → model_tgcn.py
    Then update the prediction CSVs that the API serves.
    """
    log.info("=" * 60)
    log.info("RUNNING FULL PIPELINE: standardize → train → predict")
    log.info("=" * 60)

    try:
        # Step 1: Run data_collector.py (merge + impute + normalize + risk index)
        log.info("Step 1/3: Data standardization...")
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "data_collector", BASE_DIR / "data_collector.py"
        )
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        collector.run()
        log.info("Step 1/3: ✅ Master CSV updated")

        # Step 2: Run model_baseline.py (Random Forest)
        log.info("Step 2/3: Baseline model (Random Forest)...")
        spec = importlib.util.spec_from_file_location(
            "model_baseline", BASE_DIR / "model_baseline.py"
        )
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)

        monthly = baseline.load_and_aggregate(str(DATA_DIR / "sporerisk_master_corrected.csv"))
        monthly = baseline.engineer_features(monthly)
        rf, scaler, features, y_pred, monthly = baseline.train_and_evaluate(monthly)
        baseline.save_predictions(monthly, y_pred, str(DATA_DIR / "baseline_predictions.csv"))
        log.info("Step 2/3: ✅ Baseline predictions updated")

        # Step 3: Run model_tgcn.py (T-GCN)
        log.info("Step 3/3: T-GCN model...")
        spec = importlib.util.spec_from_file_location(
            "model_tgcn", BASE_DIR / "model_tgcn.py"
        )
        tgcn = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tgcn)
        # The TGCN script runs its own main() when loaded
        log.info("Step 3/3: ✅ TGCN predictions updated")

        log.info("=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info("=" * 60)
        return True

    except Exception as e:
        log.error(f"Pipeline failed: {e}", exc_info=True)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCHEDULER LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_check_cycle():
    """
    Single check cycle:
    1. Check each data source for freshness
    2. If new data found, scrape incrementally
    3. If any scraping happened, re-run the full pipeline
    """
    state = load_state()
    now = datetime.now()
    any_new_data = False

    log.info("-" * 40)
    log.info(f"Scheduler check cycle starting at {now.isoformat()}")

    # ── Check weather ──
    last_weather_check = state.get("last_check", {}).get("weather")
    if (last_weather_check is None or
        now - datetime.fromisoformat(last_weather_check) > CHECK_INTERVALS["weather"]):

        freshness = check_weather_freshness(state)
        state.setdefault("last_check", {})["weather"] = now.isoformat()

        if freshness["has_new_data"]:
            if incremental_weather_scrape(state):
                any_new_data = True
    else:
        log.debug("Weather: skipping (checked recently)")

    # ── Check air quality ──
    last_aq_check = state.get("last_check", {}).get("air_quality")
    if (last_aq_check is None or
        now - datetime.fromisoformat(last_aq_check) > CHECK_INTERVALS["air_quality"]):

        freshness = check_air_quality_freshness(state)
        state.setdefault("last_check", {})["air_quality"] = now.isoformat()

        if freshness["has_new_data"]:
            if incremental_air_quality_scrape(state):
                any_new_data = True
    else:
        log.debug("Air quality: skipping (checked recently)")

    # ── Check cases ──
    last_cases_check = state.get("last_check", {}).get("cases")
    if (last_cases_check is None or
        now - datetime.fromisoformat(last_cases_check) > CHECK_INTERVALS["cases"]):

        freshness = check_cases_freshness(state)
        state.setdefault("last_check", {})["cases"] = now.isoformat()

        if freshness["has_new_data"]:
            if refresh_cases(state):
                any_new_data = True
    else:
        log.debug("Cases: skipping (checked recently)")

    # ── Re-run pipeline if we got new data ──
    if any_new_data:
        log.info("New data detected — triggering full pipeline re-run...")
        success = run_full_pipeline()
        if success:
            state["last_pipeline_run"] = now.isoformat()
            log.info("Pipeline completed successfully. Predictions are now up to date.")
        else:
            log.error("Pipeline failed — predictions NOT updated. Will retry next cycle.")
    else:
        log.info("No new data found. Predictions remain current.")

    save_state(state)
    log.info(f"Check cycle complete. Next check in {CHECK_INTERVALS['weather']}.\n")

    return any_new_data


def scheduler_loop(interval_hours: float = 6):
    """Run check cycles on a timer. Meant for background thread."""
    log.info(f"Scheduler started (interval: {interval_hours}h)")

    # Run immediately on start
    try:
        run_check_cycle()
    except Exception as e:
        log.error(f"Initial check cycle failed: {e}", exc_info=True)

    # Then loop
    while True:
        time.sleep(interval_hours * 3600)
        try:
            run_check_cycle()
        except Exception as e:
            log.error(f"Check cycle failed: {e}", exc_info=True)


def start_scheduler(interval_hours: float = 6):
    """
    Start the scheduler as a daemon thread.
    Call this from api.py to run alongside FastAPI.
    """
    t = threading.Thread(
        target=scheduler_loop,
        args=(interval_hours,),
        daemon=True,
        name="sporerisk-scheduler",
    )
    t.start()
    log.info(f"Scheduler thread started (daemon, interval={interval_hours}h)")
    return t


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SporeRisk Auto-Refresh Scheduler")
    parser.add_argument("--run-once", action="store_true",
                        help="Run one check cycle and exit (for cron)")
    parser.add_argument("--force-pipeline", action="store_true",
                        help="Force full pipeline re-run regardless of data freshness")
    parser.add_argument("--interval", type=float, default=6,
                        help="Hours between check cycles (default: 6)")
    parser.add_argument("--status", action="store_true",
                        help="Print current scheduler state and exit")

    args = parser.parse_args()

    if args.status:
        state = load_state()
        print(json.dumps(state, indent=2, default=str))

    elif args.force_pipeline:
        log.info("Forcing full pipeline re-run...")
        # Run all scrapes first
        state = load_state()
        incremental_weather_scrape(state)
        incremental_air_quality_scrape(state)
        refresh_cases(state)
        run_full_pipeline()
        state["last_pipeline_run"] = datetime.now().isoformat()
        save_state(state)

    elif args.run_once:
        run_check_cycle()

    else:
        scheduler_loop(interval_hours=args.interval)
