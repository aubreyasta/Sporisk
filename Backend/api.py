"""
SporeRisk — FastAPI Backend
============================
Serves Valley Fever risk data, AI-generated summaries,
historical data, forecasts, and health resource lookups.

Endpoints:
  GET  /risk?lat=&lon=           → current risk index + stats for auto-detected county
  GET  /risk/{county}            → risk index + stats for a specific county
  GET  /counties                 → list all counties with latest risk
  GET  /history/{county}         → historical risk data (monthly)
  GET  /forecast/{county}        → 4-6 month ahead TGCN + baseline predictions
  POST /chat                     → Gemini-powered chatbot (health advice, resources)
  GET  /summary/{county}         → AI-generated plain-English risk summary

Run:
  export GEMINI_API_KEY="your-key-here"
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
import os
import json
import uuid
from datetime import datetime, date

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PSYCOPG2 = True
except ImportError:
    _HAS_PSYCOPG2 = False

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ─────────────────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SporeRisk API",
    description="Valley Fever risk prediction for California's Central Valley",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else [
    "https://sporisk-main.vercel.app",
    "https://sporisk.vercel.app",
    "http://localhost:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# County metadata (centroids + FIPS)
COUNTY_META = {
    "Fresno":      {"fips": "06019", "lat": 36.7378, "lon": -119.7871},
    "Kern":        {"fips": "06029", "lat": 35.3433, "lon": -118.7279},
    "Kings":       {"fips": "06031", "lat": 36.0748, "lon": -119.8154},
    "Madera":      {"fips": "06039", "lat": 37.2180, "lon": -119.7573},
    "Merced":      {"fips": "06047", "lat": 37.1913, "lon": -120.7151},
    "San Joaquin": {"fips": "06077", "lat": 37.9317, "lon": -121.2717},
    "Stanislaus":  {"fips": "06099", "lat": 37.5591, "lon": -120.9982},
    "Tulare":      {"fips": "06107", "lat": 36.2077, "lon": -119.0539},
}

# Rough bounding boxes for county detection from lat/lon
# (good enough for hackathon — production would use shapefiles)
COUNTY_BOUNDS = {
    "Kern":        {"lat_min": 34.79, "lat_max": 35.79, "lon_min": -119.95, "lon_max": -117.63},
    "Tulare":      {"lat_min": 35.79, "lat_max": 36.45, "lon_min": -119.55, "lon_max": -118.30},
    "Kings":       {"lat_min": 35.80, "lat_max": 36.32, "lon_min": -120.19, "lon_max": -119.47},
    "Fresno":      {"lat_min": 36.32, "lat_max": 37.12, "lon_min": -120.65, "lon_max": -118.36},
    "Madera":      {"lat_min": 36.96, "lat_max": 37.49, "lon_min": -120.30, "lon_max": -119.02},
    "Merced":      {"lat_min": 36.97, "lat_max": 37.63, "lon_min": -121.23, "lon_max": -120.05},
    "Stanislaus":  {"lat_min": 37.39, "lat_max": 37.77, "lon_min": -121.40, "lon_max": -120.65},
    "San Joaquin": {"lat_min": 37.63, "lat_max": 38.30, "lon_min": -121.58, "lon_max": -120.92},
}


def load_baseline():
    path = os.path.join(DATA_DIR, "baseline_predictions.csv")
    df = pd.read_csv(path)
    return df


def load_tgcn():
    path = os.path.join(DATA_DIR, "tgcn_predictions.csv")
    df = pd.read_csv(path)
    return df


def load_env_data():
    """Load and merge weather + air quality historical data."""
    # Look in backend/data/ first, then fall back to ../data/
    data_dir = os.path.join(DATA_DIR, "data")
    if not os.path.isdir(data_dir):
        data_dir = os.path.join(os.path.dirname(DATA_DIR), "data")

    weather_path = os.path.join(data_dir, "weather.csv")
    aq_path = os.path.join(data_dir, "air_quality.csv")

    try:
        weather = pd.read_csv(weather_path, parse_dates=["date"])
        weather["year"] = weather["date"].dt.year
        weather["month"] = weather["date"].dt.month

        aq = pd.read_csv(aq_path, parse_dates=["date"])
        aq["year"] = aq["date"].dt.year
        aq["month"] = aq["date"].dt.month

        # Monthly averages
        weather_monthly = weather.groupby(["county", "year", "month"]).agg(
            precip_mm=("precip_mm", "sum"),
            soil_moisture=("soil_moisture_m3m3", "mean"),
            wind_speed=("wind_speed_kmh", "mean"),
        ).reset_index()

        aq_monthly = aq.groupby(["county", "year", "month"]).agg(
            pm10=("pm10_ugm3", "mean"),
        ).reset_index()

        merged = weather_monthly.merge(aq_monthly, on=["county", "year", "month"], how="left")
        return merged
    except Exception as e:
        print(f"  Env data load warning: {e}")
        return pd.DataFrame()


def get_db_conn():
    """Get a psycopg2 connection, or None if unavailable."""
    if not _HAS_PSYCOPG2 or not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"DB connection error: {e}")
        return None


# Load on startup
baseline_df = load_baseline()
tgcn_df = load_tgcn()
env_df = load_env_data()


def detect_county(lat: float, lon: float) -> Optional[str]:
    """Find which county a lat/lon falls in using bounding boxes."""
    for county, bounds in COUNTY_BOUNDS.items():
        if (bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lon_min"] <= lon <= bounds["lon_max"]):
            return county

    # Fallback: nearest county centroid
    min_dist = float("inf")
    nearest = None
    for county, meta in COUNTY_META.items():
        dist = (lat - meta["lat"])**2 + (lon - meta["lon"])**2
        if dist < min_dist:
            min_dist = dist
            nearest = county
    return nearest


def get_latest_risk(county: str) -> dict:
    """Get the most recent risk data for a county."""
    county_data = baseline_df[baseline_df["county"] == county].copy()
    if county_data.empty:
        return None

    # Get the latest month with data
    county_data = county_data.sort_values(["year", "month"], ascending=False)
    latest = county_data.iloc[0]

    # risk_score is now the continuous 0–100 Sporisk index (Gpot × Erisk × 100).
    # gpot and erisk are the two biological phase scores (each 0–1).
    # predicted_risk is the tier label derived from risk_score.
    # Guard against old CSV that doesn't yet have sporisk columns
    _has_sporisk = "gpot" in baseline_df.columns and "erisk" in baseline_df.columns

    raw_score = latest.get("risk_score") if "risk_score" in latest.index else None
    risk_score = float(raw_score) if raw_score is not None and not (isinstance(raw_score, float) and np.isnan(raw_score)) else None

    gpot  = float(latest["gpot"])  if _has_sporisk and not np.isnan(float(latest["gpot"]))  else None
    erisk = float(latest["erisk"]) if _has_sporisk and not np.isnan(float(latest["erisk"])) else None

    # If old CSV, fall back to legacy integer-based risk_score so API still responds
    if risk_score is None and "predicted_risk" in latest.index:
        risk_score = {"Low": 1.0, "Moderate": 2.0, "High": 3.0, "Very High": 4.0}.get(str(latest["predicted_risk"]))

    return {
        "county": county,
        "fips": COUNTY_META[county]["fips"],
        "lat": COUNTY_META[county]["lat"],
        "lon": COUNTY_META[county]["lon"],
        "year": int(latest["year"]),
        "month": int(latest["month"]),
        "risk_level": latest["predicted_risk"],
        "risk_score": round(risk_score, 2) if risk_score is not None else None,
        "gpot":  round(gpot,  4) if gpot  is not None else None,
        "erisk": round(erisk, 4) if erisk is not None else None,
        "predicted_cases": round(float(latest["predicted_cases"]), 1),
        "monthly_cases": round(float(latest["monthly_cases"]), 1),
    }


def get_environmental_stats(county: str) -> dict:
    """
    Fetch current-ish environmental stats from Open-Meteo.
    Falls back to static estimates if API is unavailable.
    """
    meta = COUNTY_META.get(county)
    if not meta:
        return {}

    # Try fetching live data from Open-Meteo (same source as scraper)
    try:
        import requests
        lat, lon = meta["lat"], meta["lon"]

        # Current weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "wind_speed_10m", "precipitation"],
            "daily": ["temperature_2m_max", "precipitation_sum", "wind_speed_10m_max"],
            "timezone": "America/Los_Angeles",
            "forecast_days": 7,
        }
        wr = requests.get(weather_url, params=weather_params, timeout=10).json()

        current = wr.get("current", {})
        daily = wr.get("daily", {})

        # Air quality (PM10)
        aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        aqi_params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["pm10"],
            "timezone": "America/Los_Angeles",
        }
        ar = requests.get(aqi_url, params=aqi_params, timeout=10).json()
        pm10 = ar.get("current", {}).get("pm10")

        return {
            "temperature_c": current.get("temperature_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "temp_max_c": daily.get("temperature_2m_max", [None])[0],
            "wind_max_kmh": daily.get("wind_speed_10m_max", [None])[0],
            "precip_daily_mm": daily.get("precipitation_sum", [None])[0],
            "precip_week_mm": round(sum(x for x in daily.get("precipitation_sum", []) if x is not None), 1),
            "pm10_ugm3": pm10,
            "source": "open-meteo (live)",
            "timestamp": current.get("time"),
        }
    except Exception as e:
        # Fallback: return None stats so frontend knows data is unavailable
        return {
            "temperature_c": None,
            "wind_speed_kmh": None,
            "precipitation_mm": None,
            "pm10_ugm3": None,
            "source": "unavailable",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Toggle this to False to disable all Gemini calls (e.g. when quota is exhausted) ──
GEMINI_ENABLED = True


def get_gemini_client(with_search=False):
    """
    Initialize Gemini client using the new google-genai SDK (google-generativeai is deprecated).
    Returns a callable (prompt str → response str) or None if unavailable.
    """
    if not GEMINI_ENABLED or not GEMINI_API_KEY:
        return None
    try:
        from google import genai as google_genai
        from google.genai import types as genai_types

        client = google_genai.Client(api_key=GEMINI_API_KEY)

        def call(prompt: str) -> str:
            """Send a prompt, return text. Handles search grounding transparently."""
            config_kwargs = {}
            if with_search:
                config_kwargs["tools"] = [genai_types.Tool(
                    google_search=genai_types.GoogleSearch()
                )]
            cfg = genai_types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
            kwargs = {"model": "gemini-2.0-flash", "contents": prompt}
            if cfg:
                kwargs["config"] = cfg
            resp = client.models.generate_content(**kwargs)
            return resp.text

        # Attach client ref so callers can inspect grounding metadata if needed
        call._client = client
        return call

    except ImportError:
        # Fall back to old SDK if new one not installed
        try:
            import google.generativeai as genai_old
            genai_old.configure(api_key=GEMINI_API_KEY)
            model = genai_old.GenerativeModel("gemini-2.0-flash")
            def call_old(prompt: str) -> str:
                return model.generate_content(prompt).text
            return call_old
        except Exception as e2:
            print(f"Gemini init error (fallback): {e2}")
            return None
    except Exception as e:
        print(f"Gemini init error: {e}")
        return None


def generate_risk_summary(county: str, risk_data: dict, env_stats: dict) -> dict:
    """
    Generate risk summary bullets + actionable advice.
    Tone adapts: calm for low risk, urgent/alarming for high risk.
    Returns: {"bullets": [...], "advice": [...]}
    """
    model = get_gemini_client()
    risk_level = risk_data.get("risk_level", "Unknown")
    risk_score = risk_data.get("risk_score")   # 0–100 continuous Sporisk index
    gpot       = risk_data.get("gpot")
    erisk      = risk_data.get("erisk")

    # High threshold: score >= 8 (Moderate+) → elevated; >= 15 (High+) → urgent
    is_high = (risk_score is not None and risk_score >= 8) or risk_level in ("High", "Very High")

    score_display = f"{risk_score:.1f}/100" if risk_score is not None else "N/A"
    component_display = ""
    if gpot is not None and erisk is not None:
        component_display = f" (Growth potential: {gpot:.2f}, Dispersal risk: {erisk:.2f})"

    if model:
        if is_high:
            tone_instruction = (
                "Use URGENT, alarming language. This is a serious public health situation. "
                "Make the user understand they need to take action RIGHT NOW. "
                "Use phrases like 'Dangerous conditions', 'Take immediate precautions', 'Risk is critically elevated'. "
                "Include 2-3 specific actionable advice items (wear N95 mask outdoors, avoid dusty areas, see a doctor if you have symptoms)."
            )
        else:
            tone_instruction = (
                "Use calm, reassuring language. Conditions are manageable. "
                "Be informative but not alarming. "
                "Brief mention of standard precautions is fine."
            )

        prompt = f"""You are SporeRisk, a Valley Fever risk advisor for California's Central Valley.

{tone_instruction}

County: {county}
Risk Level: {risk_level} (Sporisk score: {score_display}{component_display})
  - Growth Potential (Gpot): how favorable recent soil/rain conditions were for fungal growth (0–1)
  - Dispersal Risk (Erisk): how favorable current conditions are for spores becoming airborne (0–1)
  - Final score = Gpot × Erisk × 100
Temperature: {env_stats.get('temperature_c', 'N/A')}°C
Wind Speed: {env_stats.get('wind_speed_kmh', 'N/A')} km/h
Precipitation: {env_stats.get('precipitation_mm', 'N/A')} mm
PM10 Dust: {env_stats.get('pm10_ugm3', 'N/A')} µg/m³

Return a JSON object with exactly two keys:
- "bullets": array of 3-4 strings explaining WHY the risk is at this level, referencing Gpot/Erisk if helpful
- "advice": array of 2-4 strings with specific actionable steps for residents

No markdown. Example format:
{{"bullets": ["Soil is critically dry...", "PM10 levels are elevated...", "Growth potential of 0.44 means last season's rain fed significant fungal biomass..."], "advice": ["Wear N95 mask outdoors", "Avoid agricultural areas today"]}}
"""
        try:
            text = model(prompt).strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "bullets" in parsed:
                return parsed
            if isinstance(parsed, list):
                return {"bullets": parsed, "advice": []}
        except Exception as e:
            print(f"Gemini summary error: {e}")

    # Fallback: rule-based summaries
    bullets = []
    advice = []
    risk = risk_data.get("risk_level", "Unknown")

    wind = env_stats.get("wind_speed_kmh")
    pm10 = env_stats.get("pm10_ugm3")
    temp = env_stats.get("temperature_c")
    precip = env_stats.get("precipitation_mm")

    if wind and wind > 20:
        bullets.append(f"Wind speeds are elevated at {wind:.0f} km/h, increasing dust and spore dispersal")
    elif wind and wind < 10:
        bullets.append(f"Wind is calm at {wind:.0f} km/h, limiting airborne spore spread")

    if pm10 and pm10 > 50:
        bullets.append(f"PM10 dust levels are dangerously high ({pm10:.0f} µg/m³) — active soil disturbance detected")
    elif pm10 and pm10 < 20:
        bullets.append(f"Dust levels are low ({pm10:.0f} µg/m³), reducing airborne exposure risk")

    if temp and temp > 35:
        bullets.append(f"Extreme heat ({temp:.0f}°C) is critically drying soil and releasing fungal spores")
    elif temp and temp > 25:
        bullets.append(f"Warm conditions ({temp:.0f}°C) are within the optimal range for Cocci growth cycles")

    if precip is not None and precip > 5:
        bullets.append("Recent rainfall may temporarily suppress dust but feeds future fungal biomass growth")
    elif precip is not None and precip == 0:
        bullets.append("Zero precipitation — dangerously dry soil conditions accelerate spore release")

    if risk == "Very High":
        bullets.append(f"⚠️ CRITICAL: {risk_level} risk detected — conditions are dangerous for outdoor exposure")
        advice = [
            "Wear an N95 or P100 respirator for ALL outdoor activities",
            "Avoid agricultural fields, construction sites, and disturbed soil entirely",
            "See a doctor immediately if you develop cough, fever, or chest pain",
            "Keep windows and car vents closed — use recirculation mode",
        ]
    elif risk == "High":
        bullets.append(f"Elevated risk detected — outdoor workers and immunocompromised individuals are especially vulnerable")
        advice = [
            "Wear an N95 mask during outdoor activities, especially near farms or construction",
            "Reduce time outdoors during windy or dusty conditions",
            "Monitor for symptoms: cough, fever, fatigue lasting more than a week",
        ]
    elif risk == "Moderate":
        advice = [
            "Standard precautions recommended for outdoor workers",
            "Wear a dust mask if working with soil",
        ]
    else:
        advice = ["Conditions are manageable — standard hygiene and outdoor awareness is sufficient"]

    if not bullets:
        bullets = ["Current conditions are within typical seasonal range for this area"]

    return {"bullets": bullets, "advice": advice}


# ─────────────────────────────────────────────────────────────────────────────
# CHAT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    county: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "SporeRisk API",
        "version": "1.0.0",
        "description": "Valley Fever risk prediction for California's Central Valley",
        "counties": list(COUNTY_META.keys()),
        "endpoints": ["/risk", "/risk/{county}", "/counties", "/history/{county}",
                       "/forecast/{county}", "/summary/{county}", "/chat"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "counties": len(COUNTY_META), "baseline_rows": len(baseline_df)}


@app.get("/risk")
def get_risk_by_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Auto-detect county from lat/lon and return current risk."""
    county = detect_county(lat, lon)
    if not county:
        raise HTTPException(404, "Location not within tracked Central Valley counties")

    risk = get_latest_risk(county)
    env = get_environmental_stats(county)
    summary_data = generate_risk_summary(county, risk, env)

    return {
        "detected_county": county,
        "risk": risk,
        "risk_level": risk.get("risk_level") if risk else None,
        # risk_score is now the 0–100 continuous Sporisk index (Gpot × Erisk × 100)
        "risk_score": risk.get("risk_score") if risk else None,
        "gpot":  risk.get("gpot")  if risk else None,
        "erisk": risk.get("erisk") if risk else None,
        "environment": env,
        "summary": summary_data.get("bullets", []),
        "advice": summary_data.get("advice", []),
    }


@app.get("/risk/{county}")
def get_risk_by_county(county: str):
    """Get current risk for a specific county."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found. Available: {list(COUNTY_META.keys())}")

    risk = get_latest_risk(county_name)
    env = get_environmental_stats(county_name)
    summary_data = generate_risk_summary(county_name, risk, env)

    return {
        "county": county_name,
        "risk_level": risk.get("risk_level") if risk else None,
        # risk_score is now the 0–100 continuous Sporisk index (Gpot × Erisk × 100)
        "risk_score": risk.get("risk_score") if risk else None,
        "gpot":  risk.get("gpot")  if risk else None,
        "erisk": risk.get("erisk") if risk else None,
        "environment": env,
        "summary": summary_data.get("bullets", []),
        "advice": summary_data.get("advice", []),
    }


@app.get("/counties")
def list_counties():
    """List all counties with their latest risk levels."""
    results = []
    for county in COUNTY_META:
        risk = get_latest_risk(county)
        if risk:
            results.append(risk)
    return {"counties": results}


@app.get("/history/{county}")
def get_history(
    county: str,
    start_year: int = Query(2021, description="Start year"),
    end_year: int = Query(2026, description="End year"),
):
    """Get monthly historical risk data for a county."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    data = baseline_df[
        (baseline_df["county"] == county_name) &
        (baseline_df["year"] >= start_year) &
        (baseline_df["year"] <= end_year)
    ].sort_values(["year", "month"])

    score_map = {"Low": 1, "Moderate": 2, "High": 3, "Very High": 4}  # kept for legacy compat
    records = []
    for _, row in data.iterrows():
        risk_lvl = str(row["predicted_risk"]) if row["predicted_risk"] else "Low"
        # Use the continuous Sporisk score if available, fall back to legacy integer
        raw_score = row.get("risk_score")
        if raw_score is not None and not (isinstance(raw_score, float) and np.isnan(raw_score)):
            out_score = round(float(raw_score), 2)
        else:
            out_score = score_map.get(risk_lvl, 1)  # legacy fallback

        records.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "monthly_cases": round(float(row["monthly_cases"]), 1),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "predicted_risk": risk_lvl,
            "risk_score": out_score,
            "gpot":  round(float(row["gpot"]),  4) if "gpot"  in row and not np.isnan(float(row["gpot"]  or 0)) else None,
            "erisk": round(float(row["erisk"]), 4) if "erisk" in row and not np.isnan(float(row["erisk"] or 0)) else None,
        })

    return {
        "county": county_name,
        "start_year": start_year,
        "end_year": end_year,
        "records": records,
    }


@app.get("/forecast/{county}")
def get_forecast(county: str):
    """
    Get forward-looking predictions: baseline (Random Forest) + TGCN.
    Returns months where actual_cases = 0 (future) or the latest predictions.
    """
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    # Baseline forecast: months in 2025-2026 (future relative to most case data)
    now = datetime.now()
    future = baseline_df[
        (baseline_df["county"] == county_name) &
        ((baseline_df["year"] > now.year) |
         ((baseline_df["year"] == now.year) & (baseline_df["month"] >= now.month)))
    ].sort_values(["year", "month"])

    # If no future data, grab the last 6 months of predictions
    if future.empty:
        future = baseline_df[
            baseline_df["county"] == county_name
        ].sort_values(["year", "month"]).tail(6)

    baseline_forecast = []
    for _, row in future.iterrows():
        raw_score = row.get("risk_score")
        score = round(float(raw_score), 2) if raw_score is not None and not np.isnan(float(raw_score or 0)) else None
        baseline_forecast.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "risk_level": row["predicted_risk"],
            # Sporisk index: Gpot × Erisk × 100 (environmental formula)
            "risk_score": score,
            "gpot":  round(float(row["gpot"]),  4) if "gpot"  in row.index and not np.isnan(float(row.get("gpot")  or 0)) else None,
            "erisk": round(float(row["erisk"]), 4) if "erisk" in row.index and not np.isnan(float(row.get("erisk") or 0)) else None,
            "score_method": "gpot_erisk",   # full Sporisk formula
            "model": "random_forest",
        })

    # TGCN predictions — risk_score here is case-percentile derived (NOT Gpot×Erisk)
    # score_method field marks the distinction clearly
    tgcn_data = tgcn_df[tgcn_df["county"] == county_name].sort_values("test_sample")
    tgcn_forecast = []
    for _, row in tgcn_data.iterrows():
        raw_score = row.get("risk_score")
        score = round(float(raw_score), 2) if raw_score is not None and not np.isnan(float(raw_score or 0)) else None
        tgcn_forecast.append({
            "test_sample": int(row["test_sample"]),
            "actual_cases": round(float(row["actual_cases"]), 1),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "residual": round(float(row["residual"]), 1),
            # risk_score is case-count → percentile mapped to 0-100 scale
            # so it can be shown on the same chart as baseline risk_score
            "risk_score": score,
            "risk_level": str(row["predicted_risk"]) if "predicted_risk" in row.index else None,
            "score_method": str(row.get("score_method", "case_percentile")),
            "model": "tgcn",
        })

    return {
        "county": county_name,
        "baseline_forecast": baseline_forecast,
        "tgcn_forecast": tgcn_forecast,
        "score_methods": {
            "random_forest": "Gpot × Erisk × 100 (environmental formula, sporisk.vercel.app)",
            "tgcn": "Case-count percentile mapped to 0-100 (T-GCN predicts cases, not environment)",
        },
    }


@app.get("/summary/{county}")
def get_ai_summary(county: str):
    """Get AI-generated plain-English risk summary (Apple notification style)."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    risk = get_latest_risk(county_name)
    env = get_environmental_stats(county_name)
    summary_data = generate_risk_summary(county_name, risk, env)

    return {
        "county": county_name,
        "risk_level": risk.get("risk_level"),
        "risk_score": risk.get("risk_score"),
        "gpot":  risk.get("gpot"),
        "erisk": risk.get("erisk"),
        "summary_bullets": summary_data.get("bullets", []),
        "advice": summary_data.get("advice", []),
        "environment": env,
        "generated_at": datetime.now().isoformat(),
        "ai_powered": bool(GEMINI_API_KEY),
    }


@app.get("/insights/{county}")
def get_historical_insights(county: str):
    """
    Generate Gemini-powered historical pattern analysis with environmental context.
    Explains WHY risk is at current level using specific data (precipitation deficits, soil moisture, etc.)
    """
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    data = baseline_df[baseline_df["county"] == county_name].sort_values(["year", "month"])
    MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    # Build yearly summary
    yearly_rows = []
    for yr, grp in data.groupby("year"):
        avg_c = grp["monthly_cases"].mean()
        max_c = grp["monthly_cases"].max()
        high_risk = int((grp["risk_score"] >= 8).sum()) if "risk_score" in grp.columns else 0
        yearly_rows.append(f"  {int(yr)}: avg {avg_c:.0f} cases/mo, peak {max_c:.0f}, high-risk months: {high_risk}")

    yearly_summary = "\n".join(yearly_rows)

    peak_month_idx = data["monthly_cases"].idxmax()
    peak_row = data.loc[peak_month_idx]
    peak_month_name = MONTH_NAMES[int(peak_row["month"]) - 1]

    # Build environmental anomaly context from historical env data
    env_context = ""
    if not env_df.empty:
        county_env = env_df[env_df["county"] == county_name].sort_values(["year", "month"])
        if not county_env.empty:
            # Last 6 months vs historical average
            recent_6 = county_env.tail(6)
            hist_avg_precip = county_env["precip_mm"].mean()
            recent_avg_precip = recent_6["precip_mm"].mean()
            hist_avg_soil = county_env["soil_moisture"].mean()
            recent_avg_soil = recent_6["soil_moisture"].mean()
            hist_avg_pm10 = county_env["pm10"].mean() if "pm10" in county_env.columns else None
            recent_avg_pm10 = recent_6["pm10"].mean() if "pm10" in recent_6.columns else None

            precip_anomaly = ((recent_avg_precip - hist_avg_precip) / max(hist_avg_precip, 0.1)) * 100
            soil_anomaly = ((recent_avg_soil - hist_avg_soil) / max(hist_avg_soil, 0.001)) * 100

            env_context = f"""
Recent 6-month environmental conditions vs historical averages:
- Precipitation: {recent_avg_precip:.1f} mm/mo (historical avg: {hist_avg_precip:.1f} mm/mo, {precip_anomaly:+.0f}% anomaly)
- Soil moisture: {recent_avg_soil:.4f} m³/m³ (historical avg: {hist_avg_soil:.4f}, {soil_anomaly:+.0f}% anomaly)"""
            if hist_avg_pm10 is not None:
                pm10_anomaly = ((recent_avg_pm10 - hist_avg_pm10) / max(hist_avg_pm10, 0.1)) * 100
                env_context += f"\n- PM10 dust: {recent_avg_pm10:.0f} µg/m³ (historical avg: {hist_avg_pm10:.0f}, {pm10_anomaly:+.0f}% anomaly)"

    model = get_gemini_client()

    if model:
        prompt = f"""You are SporeRisk, analyzing Valley Fever risk data for {county_name} County, California.

Historical case data by year:
{yearly_summary}

Peak single month: {peak_month_name} {int(peak_row["year"])} with {peak_row["monthly_cases"]:.0f} actual cases.
{env_context}

The model uses county-relative risk thresholds — High/Very High means the predicted risk is in the top 25%
of what this specific county typically sees historically.

Generate 4-5 concise, data-driven bullet points that:
1. Explain WHY risk is currently at this level using specific numbers from the environmental data above
2. Identify the seasonal pattern (which months/season are riskiest and why)
3. Note any significant environmental anomalies (e.g., precipitation is X% below average, soil is critically dry)
4. Give a practical, specific warning for residents based on actual conditions
5. Mention year-over-year case trends if notable

Be SPECIFIC — reference actual numbers. Don't be generic.
Example of good insight: "Kern has been running 42% below average precipitation for the past 6 months, creating critically dry soil conditions that are a primary driver of the current Very High risk."

Respond ONLY with a JSON array of strings. No markdown.
"""
        try:
            text = model(prompt).strip().replace("```json", "").replace("```", "").strip()
            insights = json.loads(text)
            return {
                "county": county_name,
                "insights": insights,
                "ai_powered": True,
                "env_context_used": bool(env_context),
            }
        except Exception as e:
            print(f"Gemini insights error: {e}")

    # Rule-based fallback
    avg_2022 = data[data["year"] == 2022]["monthly_cases"].mean()
    avg_2024 = data[data["year"] == 2024]["monthly_cases"].mean() if 2024 in data["year"].values else avg_2022
    peak_months = data.groupby("month")["monthly_cases"].mean()
    peak_m = peak_months.idxmax()
    peak_m_name = MONTH_NAMES[peak_m - 1]

    insights = [
        f"Historically, {county_name} sees peak Valley Fever risk around {peak_m_name} due to dry summer conditions.",
        f"The 2021–2026 dataset shows cases averaging {data['monthly_cases'].mean():.0f}/month for this county.",
        f"Year-over-year trend: 2022 averaged {avg_2022:.0f} cases/month vs 2024's {avg_2024:.0f} — a {'significant increase' if avg_2024 > avg_2022 * 1.2 else 'similar level'}.",
    ]
    return {
        "county": county_name,
        "insights": insights,
        "ai_powered": False,
    }


@app.get("/env-history/{county}")
def get_env_history(
    county: str,
    months: int = Query(24, description="Number of months of history to return"),
):
    """Get monthly environmental history (precip, soil moisture, PM10, wind) for a county."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    if env_df.empty:
        return {"county": county_name, "records": []}

    county_env = env_df[env_df["county"] == county_name].sort_values(["year", "month"]).tail(months)

    # Merge in risk_score from baseline predictions
    # Only select columns that exist — old CSVs lack gpot/erisk until model_baseline.py is re-run
    _bl_want = ["year", "month", "predicted_risk", "risk_score", "gpot", "erisk"]
    _bl_cols = [c for c in _bl_want if c in baseline_df.columns]
    baseline_county = baseline_df[baseline_df["county"] == county_name][_bl_cols]

    records = []
    for _, row in county_env.iterrows():
        yr, mo = int(row["year"]), int(row["month"])
        bl_match = baseline_county[(baseline_county["year"] == yr) & (baseline_county["month"] == mo)]

        risk_score = None
        gpot_val   = None
        erisk_val  = None
        if not bl_match.empty:
            raw = bl_match["risk_score"].iloc[0]
            risk_score = round(float(raw), 2) if raw is not None and not np.isnan(float(raw)) else None
            if "gpot" in bl_match.columns:
                g = bl_match["gpot"].iloc[0]
                gpot_val = round(float(g), 4) if g is not None and not np.isnan(float(g)) else None
            if "erisk" in bl_match.columns:
                e = bl_match["erisk"].iloc[0]
                erisk_val = round(float(e), 4) if e is not None and not np.isnan(float(e)) else None

        records.append({
            "year": yr,
            "month": mo,
            "label": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][mo-1]}'{str(yr)[2:]}",
            "precip_mm": round(float(row["precip_mm"]), 2) if pd.notna(row["precip_mm"]) else None,
            "soil_moisture": round(float(row["soil_moisture"]), 4) if pd.notna(row["soil_moisture"]) else None,
            "wind_speed": round(float(row["wind_speed"]), 1) if pd.notna(row["wind_speed"]) else None,
            "pm10": round(float(row["pm10"]), 1) if "pm10" in row and pd.notna(row["pm10"]) else None,
            "risk_score": risk_score,   # 0–100 continuous
            "gpot":  gpot_val,
            "erisk": erisk_val,
        })

    return {"county": county_name, "records": records}


@app.get("/clinics/{county}")
def get_clinics(county: str):
    """Get healthcare clinics and hospitals for a county."""
    from clinics import get_clinics_for_county
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)
    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")
    return {"county": county_name, "clinics": get_clinics_for_county(county_name)}


@app.get("/clinics")
def get_all_clinics_endpoint():
    """Get all clinics across all counties."""
    from clinics import get_all_clinics
    return {"clinics": get_all_clinics(), "total": len(get_all_clinics())}


@app.get("/vulnerable-zones/{county}")
def get_vulnerable_zones(county: str):
    """Get vulnerable population zones for a county (farmworker housing, schools, worksites)."""
    from vulnerable_zones import get_zones_for_county
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    zones = get_zones_for_county(county_name)
    return {"county": county_name, "zones": zones, "count": len(zones)}


@app.get("/vulnerable-zones")
def get_all_vulnerable_zones():
    """Get all vulnerable population zones across all counties."""
    from vulnerable_zones import get_all_zones
    all_zones = get_all_zones()
    all_flat = []
    for county, zones in all_zones.items():
        for z in zones:
            all_flat.append({**z, "county": county})
    return {"zones": all_flat, "total": len(all_flat)}


class DustReportRequest(BaseModel):
    county: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    severity: int = 2
    description: Optional[str] = ""
    reporter_id: Optional[str] = None


@app.post("/report/dust")
def submit_dust_report(req: DustReportRequest):
    """Submit a community dust storm report."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = req.county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized, req.county)

    reporter_id = req.reporter_id or str(uuid.uuid4())
    badge_awarded = False

    conn = get_db_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dust_reports (county, lat, lon, severity, description, reporter_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (county_name, req.lat, req.lon, max(1, min(3, req.severity)), req.description, reporter_id)
                )
                report_id = cur.fetchone()[0]

                # Update badge count
                cur.execute("""
                    INSERT INTO user_badges (reporter_id, badge_count, last_report_at)
                    VALUES (%s, 1, NOW())
                    ON CONFLICT (reporter_id) DO UPDATE
                    SET badge_count = user_badges.badge_count + 1,
                        last_report_at = NOW()
                    RETURNING badge_count
                """, (reporter_id,))
                badge_count = cur.fetchone()[0]

                if badge_count >= 3 and badge_count - 1 < 3:
                    badge_awarded = True
                    cur.execute("UPDATE user_badges SET community_shield = TRUE WHERE reporter_id = %s", (reporter_id,))

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Report insert error: {e}")
            report_id = str(uuid.uuid4())
        finally:
            conn.close()
    else:
        report_id = str(uuid.uuid4())

    return {
        "success": True,
        "report_id": report_id,
        "reporter_id": reporter_id,
        "badge_awarded": badge_awarded,
        "message": "Community Shield badge earned! Thank you for protecting your community." if badge_awarded else "Report submitted. Thank you for keeping your community safe.",
    }


@app.get("/reports/{county}")
def get_county_reports(county: str, hours: int = Query(24, description="Hours of history")):
    """Get recent community dust storm reports for a county."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found")

    conn = get_db_conn()
    if not conn:
        return {"county": county_name, "reports": [], "count": 0}

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, severity, description, created_at
                FROM dust_reports
                WHERE county = %s AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC
                LIMIT 20
            """, (county_name, hours))
            reports = [dict(r) for r in cur.fetchall()]
            for r in reports:
                if r.get("created_at"):
                    r["created_at"] = r["created_at"].isoformat()
    except Exception as e:
        print(f"Reports fetch error: {e}")
        reports = []
    finally:
        conn.close()

    return {"county": county_name, "reports": reports, "count": len(reports)}


class SmsSubscribeRequest(BaseModel):
    phone: str
    county: str
    language: str = "english"


SMS_TEMPLATES = {
    "english": "⚠️ SporeRisk Alert: {risk_level} Valley Fever risk in {county} County. {advice} Stay safe.",
    "spanish": "⚠️ Alerta SporeRisk: Riesgo {risk_level} de Fiebre del Valle en el Condado de {county}. {advice} Cuídese.",
    "hmong": "⚠️ SporeRisk Ceeb Toom: Kab Mob Valley Fever pheej hmoo {risk_level} hauv {county} Cheeb Tsam. {advice}",
    "punjabi": "⚠️ SporeRisk ਚੇਤਾਵਨੀ: {county} ਕਾਉਂਟੀ ਵਿੱਚ {risk_level} ਵੈਲੀ ਫੀਵਰ ਖਤਰਾ। {advice}",
}


@app.post("/alerts/subscribe")
def subscribe_alerts(req: SmsSubscribeRequest):
    """Subscribe to SMS risk alerts for a county."""
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = req.county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized, req.county)

    lang = req.language.lower()
    if lang not in SMS_TEMPLATES:
        lang = "english"

    conn = get_db_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sms_subscriptions (phone, county, language)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (phone, county) DO UPDATE SET language = EXCLUDED.language
                """, (req.phone, county_name, lang))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"SMS subscribe error: {e}")
        finally:
            conn.close()

    lang_names = {"english": "English", "spanish": "Spanish / Español", "hmong": "Hmong", "punjabi": "Punjabi / ਪੰਜਾਬੀ"}
    return {
        "success": True,
        "county": county_name,
        "language": lang_names.get(lang, lang),
        "message": f"Subscribed! You'll receive {lang_names.get(lang, lang)} alerts when risk in {county_name} County reaches High or Very High.",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Gemini-powered chatbot for health advice, nearby resources,
    and Valley Fever questions. Uses Google Search grounding for
    real-time local healthcare provider lookups.
    """
    # Resolve county context
    county = req.county
    if not county and req.lat and req.lon:
        county = detect_county(req.lat, req.lon)

    # Build context
    risk_context = ""
    if county:
        risk = get_latest_risk(county)
        env = get_environmental_stats(county)
        risk_context = f"""
Current context for {county} County:
- Risk Level: {risk.get('risk_level', 'Unknown') if risk else 'Unknown'}
- Predicted Monthly Cases: {risk.get('predicted_cases', 'N/A') if risk else 'N/A'}
- Temperature: {env.get('temperature_c', 'N/A')}C
- Wind: {env.get('wind_speed_kmh', 'N/A')} km/h
- PM10: {env.get('pm10_ugm3', 'N/A')} ug/m3
"""

    # Detect if this is a healthcare/location query that benefits from live search
    msg_lower = req.message.lower()
    needs_search = any(w in msg_lower for w in [
        "pharmacy", "drugstore", "clinic", "hospital", "doctor",
        "antifungal", "fluconazole", "medication", "prescription",
        "nearest", "closest", "nearby", "where can i", "find a",
        "healthcare", "urgent care", "emergency", "ER",
    ])

    # Use search-grounded model for healthcare queries, regular for others
    model = get_gemini_client(with_search=needs_search)

    if not model:
        return _fallback_chat(req.message, county)

    county_location = ""
    if county:
        meta = COUNTY_META.get(county, {})
        county_location = f"The user is in {county} County, California (lat: {meta.get('lat')}, lon: {meta.get('lon')}). "

    if needs_search:
        system_prompt = f"""You are SporeRisk Health Assistant, built at UC Merced for HackMerced.

{county_location}

The user is asking about healthcare resources related to Valley Fever (Coccidioidomycosis).

USE GOOGLE SEARCH to find REAL, SPECIFIC healthcare providers near the user's location. Include:
- Actual pharmacy/clinic/hospital names
- Real addresses and phone numbers when available
- Whether they are currently open if possible
- Distance or general proximity to the user's county

{risk_context}

IMPORTANT GUIDELINES:
- Search for real providers in {county + ' County, California' if county else 'the Central Valley, California'}
- For antifungal medications (fluconazole, itraconazole), remind users they need a prescription
- Always recommend consulting a healthcare provider for medical decisions
- Prioritize community health centers and county health departments for uninsured patients
- Be concise and actionable — users are on mobile
- Respond in a warm, community-focused tone aligned with CITRIS values of equitable access

Keep responses under 250 words. Be specific with names and addresses."""
    else:
        system_prompt = f"""You are SporeRisk Health Assistant, an AI advisor for Valley Fever 
(Coccidioidomycosis) in California's Central Valley. You were built at UC Merced for HackMerced.

Your role:
1. Answer questions about Valley Fever symptoms, prevention, and treatment
2. Suggest nearby healthcare resources (clinics, pharmacies, hospitals) in the Central Valley
3. Provide actionable safety advice based on current risk conditions
4. Explain risk data in plain, accessible language

{risk_context}

GUIDELINES:
- Be concise and actionable — users are on mobile
- Always recommend consulting a healthcare provider for medical decisions
- For high-risk situations, emphasize N95 masks, avoiding soil disturbance, 
  staying indoors during dust storms
- If asked about antifungal medication, mention fluconazole/itraconazole are 
  standard treatments but MUST be prescribed by a doctor
- Respond in a warm, community-focused tone aligned with CITRIS values of 
  equitable access to health technology

Keep responses under 200 words. Be direct and helpful."""

    try:
        reply_text = model(f"{system_prompt}\n\nUser question: {req.message}")

        sources = ["SporeRisk prediction model"]
        if needs_search:
            sources.append("Google Search (live healthcare data)")
        else:
            sources.append("Open-Meteo environmental data")

        return ChatResponse(
            reply=reply_text,
            sources=sources,
        )
    except Exception as e:
        print(f"Gemini chat error: {e}")
        return _fallback_chat(req.message, county, error=str(e))


def _fallback_chat(message: str, county: Optional[str] = None, error: str = "") -> ChatResponse:
    """Rule-based fallback when Gemini is unavailable."""
    msg = message.lower()
    sources = ["SporeRisk knowledge base"]

    if any(w in msg for w in ["pharmacy", "drugstore", "antifungal", "fluconazole", "medication"]):
        reply = (
            f"For antifungal medications in the Central Valley, you'll need a prescription from a doctor. "
            f"Common options include fluconazole and itraconazole. "
            f"Visit your nearest urgent care, or check these pharmacies:\n"
            f"• CVS Pharmacy — multiple Central Valley locations\n"
            f"• Walgreens — available in most cities\n"
            f"• Costco Pharmacy — often has lower prescription prices\n"
            f"• Your county health department may offer low-cost options\n\n"
            f"If you're experiencing symptoms (cough, fever, fatigue, rash), see a doctor promptly."
        )
    elif any(w in msg for w in ["mask", "protect", "prevention", "safe", "what should i do"]):
        reply = (
            f"To reduce your Valley Fever risk:\n"
            f"• Wear an N95 mask during dusty conditions or outdoor work\n"
            f"• Avoid areas with soil disturbance (construction, farming, off-roading)\n"
            f"• Keep car windows closed during dust storms\n"
            f"• Use HEPA air filters indoors\n"
            f"• Wet soil before digging to reduce dust\n"
        )
        if county:
            risk = get_latest_risk(county)
            if risk and risk.get("risk_level") in ("High", "Very High"):
                reply += f"\n⚠️ {county} County is currently at {risk['risk_level']} risk — extra caution advised."
    elif any(w in msg for w in ["symptom", "sick", "cough", "fever"]):
        reply = (
            "Common Valley Fever symptoms include:\n"
            "• Cough (can last weeks)\n"
            "• Fever and chills\n"
            "• Fatigue and body aches\n"
            "• Chest pain\n"
            "• Rash on legs or upper body\n\n"
            "Most cases resolve on their own, but see a doctor if symptoms persist "
            "beyond 1-2 weeks or if you're immunocompromised. Early diagnosis matters."
        )
    elif any(w in msg for w in ["clinic", "hospital", "doctor", "healthcare"]):
        reply = (
            f"Healthcare options in the Central Valley:\n"
            f"• Community Medical Centers (Fresno) — largest regional provider\n"
            f"• Kern Medical (Bakersfield) — Valley Fever expertise\n"
            f"• Mercy Medical Center (Merced)\n"
            f"• Kaiser Permanente — multiple Valley locations\n"
            f"• County Health Departments offer low-cost testing\n\n"
            f"For urgent symptoms, call 911 or visit your nearest ER."
        )
    else:
        reply = (
            "I'm SporeRisk's health assistant. I can help you with:\n"
            "• Current Valley Fever risk in your area\n"
            "• Finding nearby pharmacies and clinics\n"
            "• Prevention tips and protective measures\n"
            "• Understanding symptoms and when to see a doctor\n\n"
            "What would you like to know?"
        )

    if error:
        reply += f"\n\n(Note: AI-powered responses are temporarily unavailable. Using built-in knowledge.)"

    return ChatResponse(reply=reply, sources=sources)


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/scheduler/status")
def scheduler_status():
    """Check the auto-refresh scheduler's current state."""
    try:
        from scheduler import load_state
        state = load_state()
        return {
            "status": "running",
            "last_pipeline_run": state.get("last_pipeline_run"),
            "last_checks": state.get("last_check", {}),
            "weather_through": state.get("weather_last_date"),
            "air_quality_through": state.get("air_quality_last_date"),
            "cases_through_year": state.get("cases_last_year"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/scheduler/trigger")
def trigger_refresh():
    """Manually trigger a data refresh check cycle."""
    try:
        from scheduler import run_check_cycle
        had_new_data = run_check_cycle()

        # Reload predictions if pipeline ran
        if had_new_data:
            global baseline_df, tgcn_df
            baseline_df = load_baseline()
            tgcn_df = load_tgcn()

        return {
            "triggered": True,
            "new_data_found": had_new_data,
            "predictions_reloaded": had_new_data,
        }
    except Exception as e:
        raise HTTPException(500, f"Refresh failed: {e}")


# Auto-refresh interval (hours). Set to 0 to disable.
AUTO_REFRESH_HOURS = float(os.environ.get("SPORERISK_REFRESH_HOURS", "6"))


@app.on_event("startup")
def startup():
    print(f"SporeRisk API starting...")
    print(f"  Counties loaded: {len(COUNTY_META)}")
    print(f"  Baseline predictions: {len(baseline_df)} rows")
    print(f"  TGCN predictions: {len(tgcn_df)} rows")
    print(f"  Env data: {len(env_df)} monthly records")
    print(f"  Gemini API: {'configured' if GEMINI_API_KEY else 'NOT SET (using fallback)'}")
    print(f"  Database: {'connected' if DATABASE_URL else 'not configured'}")

    # Start auto-refresh scheduler as background thread
    if AUTO_REFRESH_HOURS > 0:
        try:
            from scheduler import start_scheduler
            start_scheduler(interval_hours=AUTO_REFRESH_HOURS)
            print(f"  Auto-refresh: ON (every {AUTO_REFRESH_HOURS}h)")
        except Exception as e:
            print(f"  Auto-refresh: FAILED to start ({e})")
    else:
        print(f"  Auto-refresh: OFF (set SPORERISK_REFRESH_HOURS > 0 to enable)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)