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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, date
from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SporeRisk API",
    description="Valley Fever risk prediction for California's Central Valley",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# Load on startup
baseline_df = load_baseline()
tgcn_df = load_tgcn()


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

    return {
        "county": county,
        "fips": COUNTY_META[county]["fips"],
        "lat": COUNTY_META[county]["lat"],
        "lon": COUNTY_META[county]["lon"],
        "year": int(latest["year"]),
        "month": int(latest["month"]),
        "risk_level": latest["predicted_risk"],
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
            "forecast_days": 1,
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


def get_gemini_client():
    """Initialize Gemini client. Returns None if no API key."""
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.0-flash")
    except Exception:
        return None


def generate_risk_summary(county: str, risk_data: dict, env_stats: dict) -> list[str]:
    """
    Generate Apple-notification-style bullet points explaining the risk.
    Falls back to rule-based summaries if Gemini is unavailable.
    """
    model = get_gemini_client()

    if model:
        prompt = f"""You are SporeRisk, a Valley Fever risk advisor for California's Central Valley.
Given the following data for {county} County, generate 3-5 short, plain-English bullet points
explaining WHY the current risk level is what it is. Think Apple notification summary style —
concise, actionable, no jargon.

Risk Level: {risk_data.get('risk_level', 'Unknown')}
Predicted Monthly Cases: {risk_data.get('predicted_cases', 'N/A')}

Current Environmental Conditions:
- Temperature: {env_stats.get('temperature_c', 'N/A')}°C
- Wind Speed: {env_stats.get('wind_speed_kmh', 'N/A')} km/h
- Precipitation: {env_stats.get('precipitation_mm', 'N/A')} mm
- PM10 (dust): {env_stats.get('pm10_ugm3', 'N/A')} µg/m³

Respond ONLY with a JSON array of strings. No markdown, no explanation. Example:
["Wind speeds are elevated, increasing dust dispersal", "Dry soil conditions favor spore release"]
"""
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean potential markdown fencing
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"Gemini summary error: {e}")

    # Fallback: rule-based summaries
    bullets = []
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
        bullets.append(f"PM10 dust levels are high ({pm10:.0f} µg/m³), suggesting active soil disturbance")
    elif pm10 and pm10 < 20:
        bullets.append(f"Dust levels are low ({pm10:.0f} µg/m³), reducing airborne exposure")

    if temp and temp > 35:
        bullets.append(f"High temperatures ({temp:.0f}°C) are drying soil, which can release fungal spores")
    elif temp and temp > 25:
        bullets.append(f"Warm conditions ({temp:.0f}°C) are within the range that supports Cocci growth cycles")

    if precip is not None and precip > 5:
        bullets.append("Recent rainfall may temporarily suppress dust but feeds future fungal growth")
    elif precip is not None and precip == 0:
        bullets.append("No recent rain — dry conditions increase soil cracking and spore exposure")

    if risk in ("High", "Very High"):
        bullets.append("Consider wearing an N95 mask during outdoor activities, especially near construction or agricultural sites")
    elif risk == "Moderate":
        bullets.append("Standard precautions recommended for outdoor workers and immunocompromised individuals")

    return bullets if bullets else ["Current conditions are within typical seasonal range for this area"]


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
    summary = generate_risk_summary(county, risk, env)

    return {
        "detected_county": county,
        "risk": risk,
        "environment": env,
        "summary": summary,
    }


@app.get("/risk/{county}")
def get_risk_by_county(county: str):
    """Get current risk for a specific county."""
    # Normalize county name
    county_map = {c.lower().replace(" ", ""): c for c in COUNTY_META}
    normalized = county.lower().replace(" ", "").replace("_", "")
    county_name = county_map.get(normalized)

    if not county_name:
        raise HTTPException(404, f"County '{county}' not found. Available: {list(COUNTY_META.keys())}")

    risk = get_latest_risk(county_name)
    env = get_environmental_stats(county_name)
    summary = generate_risk_summary(county_name, risk, env)

    return {
        "risk": risk,
        "environment": env,
        "summary": summary,
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

    records = []
    for _, row in data.iterrows():
        records.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "monthly_cases": round(float(row["monthly_cases"]), 1),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "risk_level": row["predicted_risk"],
        })

    return {
        "county": county_name,
        "start_year": start_year,
        "end_year": end_year,
        "data": records,
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
        baseline_forecast.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "risk_level": row["predicted_risk"],
            "model": "random_forest",
        })

    # TGCN predictions for this county
    tgcn_data = tgcn_df[tgcn_df["county"] == county_name].sort_values("test_sample")
    tgcn_forecast = []
    for _, row in tgcn_data.iterrows():
        tgcn_forecast.append({
            "test_sample": int(row["test_sample"]),
            "actual_cases": round(float(row["actual_cases"]), 1),
            "predicted_cases": round(float(row["predicted_cases"]), 1),
            "residual": round(float(row["residual"]), 1),
            "model": "tgcn",
        })

    return {
        "county": county_name,
        "baseline_forecast": baseline_forecast,
        "tgcn_forecast": tgcn_forecast,
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
    summary = generate_risk_summary(county_name, risk, env)

    return {
        "county": county_name,
        "risk_level": risk.get("risk_level"),
        "summary_bullets": summary,
        "environment": env,
        "generated_at": datetime.now().isoformat(),
        "ai_powered": bool(GEMINI_API_KEY),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Gemini-powered chatbot for health advice, nearby resources,
    and Valley Fever questions.
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
- Temperature: {env.get('temperature_c', 'N/A')}°C
- Wind: {env.get('wind_speed_kmh', 'N/A')} km/h
- PM10: {env.get('pm10_ugm3', 'N/A')} µg/m³
"""

    model = get_gemini_client()

    if not model:
        # Fallback: rule-based responses for common queries
        return _fallback_chat(req.message, county)

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
- For pharmacy/clinic questions, suggest well-known Central Valley locations 
  (Community Medical Centers, Kaiser, CVS, Walgreens, county health departments)
- Always recommend consulting a healthcare provider for medical decisions
- For high-risk situations, emphasize N95 masks, avoiding soil disturbance, 
  staying indoors during dust storms
- If asked about antifungal medication, mention fluconazole/itraconazole are 
  standard treatments but MUST be prescribed by a doctor
- Respond in a warm, community-focused tone aligned with CITRIS values of 
  equitable access to health technology

Keep responses under 200 words. Be direct and helpful."""

    try:
        chat_session = model.start_chat(history=[])
        response = model.generate_content(
            f"{system_prompt}\n\nUser question: {req.message}"
        )
        return ChatResponse(
            reply=response.text,
            sources=["SporeRisk prediction model", "Open-Meteo environmental data"],
        )
    except Exception as e:
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
    print(f"  Gemini API: {'configured' if GEMINI_API_KEY else 'NOT SET (using fallback)'}")
    print(f"  Tip: export GEMINI_API_KEY='your-key' to enable AI summaries")

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
