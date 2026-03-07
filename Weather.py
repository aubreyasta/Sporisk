"""
SporaSync — Scraper (Steps 1, 2, 3 only)
==========================================
Pulls raw data from Open-Meteo, EPA AQS, and CDPH.
Saves three clean CSVs to the data/ folder:
  data/weather.csv
  data/air_quality.csv
  data/cases.csv

Usage:
    pip install requests pandas numpy
    python scrape.py
"""

import requests
import pandas as pd
import numpy as np
import time
import os
import zipfile
import io
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

START_DATE  = "2020-01-01"
END_DATE    = date.today().isoformat()
OUTPUT_DIR  = "data"

COUNTIES = {
    "Fresno":      {"lat": 36.7378, "lon": -119.7871, "fips": "06019"},
    "Tulare":      {"lat": 36.2077, "lon": -119.0539, "fips": "06107"},
    "Kings":       {"lat": 36.0748, "lon": -119.8154, "fips": "06031"},
    "Kern":        {"lat": 35.3433, "lon": -118.7279, "fips": "06029"},
    "Merced":      {"lat": 37.1913, "lon": -120.7151, "fips": "06047"},
    "Madera":      {"lat": 37.2180, "lon": -119.7573, "fips": "06039"},
    "San Joaquin": {"lat": 37.9317, "lon": -121.2717, "fips": "06077"},
    "Stanislaus":  {"lat": 37.5591, "lon": -120.9982, "fips": "06099"},
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get(url, params=None, timeout=60):
    """GET with 3 retries. Returns parsed JSON or None."""
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:
                print(f"FAILED ({e})")
                return None
            time.sleep(2 ** attempt)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — OPEN-METEO: precip, soil moisture, wind
# ─────────────────────────────────────────────────────────────────────────────

def fetch_weather(county, lat, lon):
    base = "https://archive-api.open-meteo.com/v1/archive"
    shared = {
        "latitude": lat, "longitude": lon,
        "start_date": START_DATE, "end_date": END_DATE,
        "timezone": "America/Los_Angeles",
    }

    print(f"  {county}...", end=" ", flush=True)

    # Call 1: daily precip + wind
    data = _get(base, {**shared, "daily": ["precipitation_sum", "wind_speed_10m_max"]})
    if data is None:
        return pd.DataFrame()
    d = data["daily"]
    df = pd.DataFrame({
        "date":           d["time"],
        "county":         county,
        "precip_mm":      d["precipitation_sum"],
        "wind_speed_kmh": d["wind_speed_10m_max"],
    })
    df["date"] = pd.to_datetime(df["date"])

    # Call 2: hourly soil moisture → daily mean
    time.sleep(0.4)
    hdata = _get(base, {**shared, "hourly": ["soil_moisture_0_to_7cm"]})
    if hdata is not None:
        h = hdata["hourly"]
        dh = pd.DataFrame({"datetime": h["time"], "soil": h["soil_moisture_0_to_7cm"]})
        dh["date"] = pd.to_datetime(dh["datetime"]).dt.normalize()
        soil = dh.groupby("date")["soil"].mean().reset_index()
        soil.columns = ["date", "soil_moisture_m3m3"]
        df = df.merge(soil, on="date", how="left")
    else:
        df["soil_moisture_m3m3"] = np.nan

    print(f"{len(df)} rows")
    time.sleep(0.3)
    return df[["date", "county", "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh"]]


def collect_weather():
    print("\n━━ STEP 1: Open-Meteo Weather ━━")
    frames = [fetch_weather(c, v["lat"], v["lon"]) for c, v in COUNTIES.items()]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    path = os.path.join(OUTPUT_DIR, "weather.csv")
    df.to_csv(path, index=False, date_format="%Y-%m-%d")
    print(f"  ✅ Saved → {path}  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — EPA AQS BULK: PM10
# ─────────────────────────────────────────────────────────────────────────────

def collect_air_quality():
    print("\n━━ STEP 2: EPA AQS Bulk PM10 (no key needed) ━━")

    fips_to_county = {v["fips"][2:]: c for c, v in COUNTIES.items()}
    ca_fips        = set(fips_to_county.keys())
    years          = range(int(START_DATE[:4]), date.today().year + 1)
    all_rows       = []

    for year in years:
        url = f"https://aqs.epa.gov/aqsweb/airdata/daily_81102_{year}.zip"
        print(f"  {year}...", end=" ", flush=True)
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
                (df_year["State Code"]     == "06") &
                (df_year["County Code"].isin(ca_fips)) &
                (df_year["Parameter Code"] == "81102")
            ].copy()
            df_year["county"]    = df_year["County Code"].map(fips_to_county)
            df_year["date"]      = pd.to_datetime(df_year["Date Local"])
            df_year["pm10_ugm3"] = pd.to_numeric(df_year["Arithmetic Mean"], errors="coerce")
            df_year = df_year.dropna(subset=["pm10_ugm3"])
            df_year = df_year[df_year["pm10_ugm3"].between(0, 1500)]
            all_rows.append(df_year[["date", "county", "pm10_ugm3"]])
            print(f"{len(df_year)} rows")
        except Exception as e:
            print(f"FAILED ({e})")
        time.sleep(0.5)

    if not all_rows:
        print("  ⚠ No data retrieved.")
        return pd.DataFrame(columns=["date", "county", "pm10_ugm3"])

    df = (
        pd.concat(all_rows, ignore_index=True)
        .groupby(["date", "county"])["pm10_ugm3"]
        .mean()
        .reset_index()
    )
    path = os.path.join(OUTPUT_DIR, "air_quality.csv")
    df.to_csv(path, index=False, date_format="%Y-%m-%d")
    print(f"  ✅ Saved → {path}  ({len(df):,} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — CDPH: Valley Fever case counts
# ─────────────────────────────────────────────────────────────────────────────
# No public API. Drop the real CDPH CSV export at data/cdph_valley_fever.csv
# with columns: county, year, case_count
# Otherwise the synthetic fallback is used automatically.
# ─────────────────────────────────────────────────────────────────────────────

SYNTHETIC_CASES = {
    "Fresno":      {2020: 1420, 2021: 1580, 2022: 1350, 2023: 1900, 2024: 2100},
    "Kern":        {2020: 980,  2021: 1100, 2022: 920,  2023: 1400, 2024: 1650},
    "Tulare":      {2020: 610,  2021: 680,  2022: 590,  2023: 830,  2024: 940},
    "Kings":       {2020: 210,  2021: 240,  2022: 200,  2023: 310,  2024: 360},
    "Merced":      {2020: 180,  2021: 200,  2022: 170,  2023: 260,  2024: 310},
    "Madera":      {2020: 150,  2021: 170,  2022: 145,  2023: 220,  2024: 265},
    "San Joaquin": {2020: 120,  2021: 135,  2022: 110,  2023: 175,  2024: 200},
    "Stanislaus":  {2020: 95,   2021: 108,  2022: 90,   2023: 140,  2024: 165},
}


def collect_cases():
    print("\n━━ STEP 3: CDPH Valley Fever Cases ━━")
    cdph_path = os.path.join(OUTPUT_DIR, "cdph_valley_fever.csv")

    if os.path.exists(cdph_path):
        print(f"  Loading real CDPH data from {cdph_path}")
        df = pd.read_csv(cdph_path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["cases_source"] = "cdph_official"
    else:
        print(f"  ⚠ {cdph_path} not found — using synthetic fallback.")
        rows = [
            {"county": county, "year": year, "case_count": count}
            for county, years in SYNTHETIC_CASES.items()
            for year, count in years.items()
        ]
        df = pd.DataFrame(rows)
        df["cases_source"] = "synthetic"

    df["county"] = df["county"].str.strip().str.title()
    df = df[["county", "year", "case_count", "cases_source"]]

    path = os.path.join(OUTPUT_DIR, "cases.csv")
    df.to_csv(path, index=False)
    print(f"  ✅ Saved → {path}  ({len(df)} rows)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("  SporaSync Scraper — Steps 1, 2, 3")
    print(f"  Date range: {START_DATE} → {END_DATE}")
    print(f"  Counties:   {len(COUNTIES)}")
    print("=" * 60)

    collect_weather()
    collect_air_quality()
    collect_cases()

    print("\n✅ All raw data saved to data/")
    print("   weather.csv     — precip, soil moisture, wind (daily per county)")
    print("   air_quality.csv — PM10 µg/m³ (daily per county)")
    print("   cases.csv       — Valley Fever case counts (annual per county)")


if __name__ == "__main__":
    run()