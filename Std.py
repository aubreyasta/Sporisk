"""
SporaSync — Standardizer (Step 4)
===================================
Reads the 3 raw CSVs from scrape.py:
  data/weather.csv        — precip_mm, soil_moisture_m3m3, wind_speed_kmh  (daily)
  data/air_quality.csv    — pm10_ugm3                                       (daily)
  data/cases.csv          — case_count                                      (annual)

Outputs:
  data/sporasync_master.csv

Formula (from ecological/epidemiological research):
─────────────────────────────────────────────────────
  Step 1 — Growth Potential (G_pot):
    G_pot = 0.35·SM_lag6mo + 0.20·Tmax_lag6mo + 0.45·Precip_lag1.5y

  Step 2 — Exposure Risk (E_risk):
    E_risk = 0.385·PM10_lag1mo + 0.308·Tmax_lag1mo + 0.231·(1−SM_current) + 0.077·Wind

  Step 3 — Final Score (multiplicative):
    Risk = G_pot × E_risk × 100   (0–100 scale)

    Multiplicative because: high fungal growth with no dispersal = no cases,
    and high wind/dust with no fungal biomass = no cases either.

Weights source: Table 3 MNBR Adjusted Incidence Rate Ratios
  SM_lag 35% | Tmax 20% | Precip_1.5y 45% (growth)
  PM10 25%   | Tmax 20% | Soil Aridity 15% | Wind 5% (dispersal, renormed to 1.0)

Usage:
    python standardize.py
"""

import pandas as pd
import numpy as np
import os
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR    = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "sporasync_master.csv")
START_DATE  = "2020-01-01"
END_DATE    = date.today().isoformat()

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
# WEIGHTS  (Table 3, re-normalized within each phase to sum to 1.0)
# ─────────────────────────────────────────────────────────────────────────────

W_G = {
    "sm_lag6mo":      0.35,
    "tmax_lag6mo":    0.20,
    "precip_lag1p5y": 0.45,
}

_e_raw = {"pm10_lag1mo": 25, "tmax_lag1mo": 20, "soil_aridity": 15, "wind_current": 5}
_e_sum = sum(_e_raw.values())
W_E = {k: round(v / _e_sum, 4) for k, v in _e_raw.items()}
# → pm10≈0.3846, tmax≈0.3077, aridity≈0.2308, wind≈0.0769

# ─────────────────────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────────────────────

def load_inputs():
    print("\n━━ Loading raw CSVs ━━")
    weather = pd.read_csv(os.path.join(DATA_DIR, "weather.csv"),     parse_dates=["date"])
    aq      = pd.read_csv(os.path.join(DATA_DIR, "air_quality.csv"), parse_dates=["date"])
    cases   = pd.read_csv(os.path.join(DATA_DIR, "cases.csv"))
    print(f"  weather.csv     → {len(weather):,} rows")
    print(f"  air_quality.csv → {len(aq):,} rows")
    print(f"  cases.csv       → {len(cases):,} rows")
    return weather, aq, cases


# ─────────────────────────────────────────────────────────────────────────────
# MERGE onto full date × county spine
# ─────────────────────────────────────────────────────────────────────────────

def build_master(weather, aq, cases):
    print("\n━━ Merging onto date × county spine ━━")

    spine = pd.MultiIndex.from_product(
        [pd.date_range(START_DATE, END_DATE, freq="D"), list(COUNTIES.keys())],
        names=["date", "county"]
    ).to_frame(index=False)

    meta = pd.DataFrame([
        {"county": c, "lat": v["lat"], "lon": v["lon"], "fips": v["fips"]}
        for c, v in COUNTIES.items()
    ])

    master = spine.merge(meta,    on="county",          how="left")
    master = master.merge(weather, on=["date","county"], how="left")
    master = master.merge(aq,      on=["date","county"], how="left")

    # Fill PM10 gaps forward/back within each county
    master["pm10_ugm3"] = (
        master.groupby("county")["pm10_ugm3"]
        .transform(lambda s: s.ffill().bfill())
    )

    # Cases: annual → daily (fan out by year)
    cases["year"]  = cases["year"].astype(int)
    master["year"] = master["date"].dt.year
    master = master.merge(
        cases[["county", "year", "case_count", "cases_source"]],
        on=["county", "year"], how="left"
    )
    master.drop(columns=["year"], inplace=True)
    master["case_count"]   = master["case_count"].fillna(0)
    master["cases_source"] = master["cases_source"].fillna("unknown")

    print(f"  → Merged shape: {master.shape}")
    return master


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE ENGINEERING — all lag features the formula needs
# ─────────────────────────────────────────────────────────────────────────────

def engineer_features(df):
    print("\n━━ Engineering lag features ━━")
    frames = []

    for county, grp in df.groupby("county"):
        g = grp.sort_values("date").copy()

        # ── Seasonal temperature proxy ────────────────────────────────────
        # Open-Meteo temp not in our scrape; derive from day-of-year sine wave
        # calibrated to CA Central Valley (8°C winter → 40°C summer peak ~Jul 15)
        doy = g["date"].dt.dayofyear
        g["tmax_approx_c"] = 24 + 16 * np.sin(2 * np.pi * (doy - 80) / 365)

        # ── GROWTH PHASE LAGS ─────────────────────────────────────────────

        # SM_lag6mo: mean soil moisture 6–9 months ago (centred at 7.5 mo = 225 days)
        g["sm_lag6mo"] = (
            g["soil_moisture_m3m3"]
            .shift(225)
            .rolling(window=90, min_periods=30)
            .mean()
        )

        # Tmax_lag6mo: mean max temp 6 months ago
        g["tmax_lag6mo"] = (
            g["tmax_approx_c"]
            .shift(180)
            .rolling(window=60, min_periods=20)
            .mean()
        )

        # Precip_lag1.5y: total precip over 90 days centred ~18 months ago
        # This is the dominant predictor of incidence peaks per the paper
        g["precip_lag1p5y"] = (
            g["precip_mm"]
            .shift(540)
            .rolling(window=90, min_periods=30)
            .sum()
        )

        # ── DISPERSAL PHASE LAGS ──────────────────────────────────────────

        # PM10_lag1mo: 30-day mean PM10 (proxy for spores already airborne)
        g["pm10_lag1mo"] = (
            g["pm10_ugm3"]
            .rolling(window=30, min_periods=10)
            .mean()
        )

        # Tmax_lag1mo: mean max temp 1 month ago (arthroconidia maturation trigger)
        g["tmax_lag1mo"] = (
            g["tmax_approx_c"]
            .shift(30)
            .rolling(window=30, min_periods=10)
            .mean()
        )

        # Wind and soil moisture current — no lag, used as-is after normalization

        frames.append(g)

    result = pd.concat(frames, ignore_index=True)

    lag_cols = ["sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y", "pm10_lag1mo", "tmax_lag1mo"]
    print(f"  Null counts after feature engineering:")
    for c in lag_cols:
        print(f"    {c:25s}: {result[c].isnull().sum():,} nulls")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FILL NULLS — county median
# ─────────────────────────────────────────────────────────────────────────────

def fill_nulls(df):
    print("\n━━ Filling nulls with county median ━━")
    cols = [
        "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh", "pm10_ugm3",
        "sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y", "pm10_lag1mo", "tmax_lag1mo",
    ]
    for col in cols:
        if col not in df.columns:
            continue
        n = df[col].isnull().sum()
        if n:
            df[col] = df.groupby("county")[col].transform(
                lambda s: s.fillna(s.median())
            )
            print(f"  {col:25s}: filled {n:,} nulls")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZE — z-score (analytics) + min-max [0,1] (formula inputs)
# ─────────────────────────────────────────────────────────────────────────────

def zscore(s):
    std = s.std()
    return pd.Series(0.0, index=s.index) if std == 0 else (s - s.mean()) / std

def minmax(s):
    mn, mx = s.min(), s.max()
    return pd.Series(0.0, index=s.index) if mx == mn else (s - mn) / (mx - mn)

def normalize(df):
    print("\n━━ Normalizing ━━")
    raw_cols = [
        "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh", "pm10_ugm3",
        "sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y",
        "pm10_lag1mo", "tmax_lag1mo", "case_count",
    ]
    for col in raw_cols:
        if col not in df.columns:
            continue
        df[f"z_{col}"] = zscore(df[col]).round(4)
        df[f"n_{col}"] = minmax(df[col]).round(4)
        print(f"  {col}")

    # Soil aridity = 1 − n_soil_moisture (aerosolization potential)
    df["n_soil_aridity"] = (1 - df["n_soil_moisture_m3m3"]).round(4)
    print(f"  n_soil_aridity = 1 − n_soil_moisture_m3m3  ✓")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# RISK FORMULA — G_pot × E_risk  (bifurcated, multiplicative)
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk(df):
    print("\n━━ Computing Risk Index ━━")
    print(f"  G_pot  = {W_G['sm_lag6mo']}·SM_lag6mo + {W_G['tmax_lag6mo']}·Tmax_lag6mo + {W_G['precip_lag1p5y']}·Precip_lag1.5y")
    print(f"  E_risk = {W_E['pm10_lag1mo']:.4f}·PM10_lag1mo + {W_E['tmax_lag1mo']:.4f}·Tmax_lag1mo + {W_E['soil_aridity']:.4f}·SoilAridity + {W_E['wind_current']:.4f}·Wind")
    print(f"  Risk   = G_pot × E_risk × 100")

    df["G_pot"] = (
        W_G["sm_lag6mo"]      * df["n_sm_lag6mo"]      +
        W_G["tmax_lag6mo"]    * df["n_tmax_lag6mo"]    +
        W_G["precip_lag1p5y"] * df["n_precip_lag1p5y"]
    ).clip(0, 1).round(4)

    df["E_risk"] = (
        W_E["pm10_lag1mo"]  * df["n_pm10_lag1mo"]    +
        W_E["tmax_lag1mo"]  * df["n_tmax_lag1mo"]    +
        W_E["soil_aridity"] * df["n_soil_aridity"]   +
        W_E["wind_current"] * df["n_wind_speed_kmh"]
    ).clip(0, 1).round(4)

    df["risk_score"] = (df["G_pot"] * df["E_risk"] * 100).round(1)

    bins   = [-0.1, 25, 50, 75, 100]
    labels = ["Low", "Moderate", "High", "Very High"]
    df["risk_level"] = pd.cut(df["risk_score"], bins=bins, labels=labels).astype(str)
    df["risk_color"] = df["risk_level"].map({
        "Low": "green", "Moderate": "yellow",
        "High": "orange", "Very High": "red"
    })

    print(f"\n  Risk score summary:")
    print(df["risk_score"].describe().round(2).to_string())
    print(f"\n  Risk level distribution:")
    print(df["risk_level"].value_counts().to_string())
    return df


# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_ORDER = [
    # Identity
    "date", "county", "fips", "lat", "lon",
    # Raw inputs
    "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh", "pm10_ugm3",
    "case_count", "cases_source",
    # Engineered features (raw)
    "tmax_approx_c",
    "sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y",
    "pm10_lag1mo", "tmax_lag1mo",
    # Normalized [0,1] — formula inputs
    "n_sm_lag6mo", "n_tmax_lag6mo", "n_precip_lag1p5y",
    "n_pm10_lag1mo", "n_tmax_lag1mo",
    "n_soil_moisture_m3m3", "n_soil_aridity",
    "n_wind_speed_kmh", "n_pm10_ugm3", "n_case_count",
    # Z-scores — analytics
    "z_sm_lag6mo", "z_tmax_lag6mo", "z_precip_lag1p5y",
    "z_pm10_lag1mo", "z_wind_speed_kmh",
    "z_soil_moisture_m3m3", "z_pm10_ugm3", "z_case_count",
    # Risk output — what Beta uses
    "G_pot", "E_risk", "risk_score", "risk_level", "risk_color",
]


def save(df):
    print("\n━━ Saving ━━")
    extras = [c for c in df.columns if c not in COLUMN_ORDER]
    cols   = [c for c in COLUMN_ORDER if c in df.columns] + extras
    df     = df[cols].sort_values(["county", "date"]).reset_index(drop=True)
    df.to_csv(OUTPUT_FILE, index=False, date_format="%Y-%m-%d")
    mb = os.path.getsize(OUTPUT_FILE) / 1_048_576
    print(f"  ✅ Saved → {OUTPUT_FILE}")
    print(f"     {len(df):,} rows × {len(df.columns)} columns  ({mb:.1f} MB)")
    print(f"\n  Columns Beta needs:")
    for c in ["G_pot", "E_risk", "risk_score", "risk_level", "risk_color"]:
        print(f"    {c}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("  SporaSync Standardizer — Bifurcated Risk Formula")
    print(f"  Input:  {DATA_DIR}/weather.csv, air_quality.csv, cases.csv")
    print(f"  Output: {OUTPUT_FILE}")
    print("=" * 60)

    weather, aq, cases = load_inputs()
    master = build_master(weather, aq, cases)
    master = engineer_features(master)
    master = fill_nulls(master)
    master = normalize(master)
    master = compute_risk(master)
    save(master)

    print("\n✅ Done. Hand sporasync_master.csv to Beta.")
    print("\n   Formula recap:")
    print("   G_pot  = 0.35·SM_lag6mo + 0.20·Tmax_lag6mo + 0.45·Precip_lag1.5y")
    print("   E_risk = 0.385·PM10_lag1mo + 0.308·Tmax_lag1mo + 0.231·SoilAridity + 0.077·Wind")
    print("   Risk   = G_pot × E_risk × 100")


if __name__ == "__main__":
    run()