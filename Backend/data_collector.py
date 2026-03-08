"""
SporeRisk — Data Collector & Standardization Pipeline
======================================================
Merges the three scraper outputs (weather.csv, air_quality.csv, cases.csv)
into a single master CSV ready for model training.

Implements Blueprint §6 Stages 1-5:
  Stage 1: Temporal alignment (daily granularity)
  Stage 2: Missing value imputation
  Stage 3: Outlier clipping
  Stage 4: Lag feature engineering
  Stage 5: Normalization (Z-score + MinMax)
  
Also computes Blueprint §7.1 two-phase risk index:
  G_pot   = Growth Potential (antecedent moisture/temp/precip)
  E_risk  = Exposure Risk (current dust/aridity/wind/temp)
  Risk    = G_pot × E_risk

Usage:
    python Weather.py           # first — scrapes raw data into data/
    python data_collector.py    # then — builds the master CSV

Input:  data/weather.csv, data/air_quality.csv, data/cases.csv
Output: sporerisk_master_corrected.csv
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sporerisk_master_corrected.csv")
# County metadata: FIPS codes and representative coordinates
# (same as Weather.py — coordinates are county centroids)
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


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 0: MERGE — combine the three scraper CSVs into one daily table
# ─────────────────────────────────────────────────────────────────────────────

def merge_sources():
    """
    Joins weather + air quality on (date, county), then attaches
    yearly case counts to every daily row of that county/year.
    """
    print("=" * 70)
    print("  STAGE 0: Merging scraper outputs")
    print("=" * 70)

    # ── Load ──
    weather_path = os.path.join(DATA_DIR, "weather.csv")
    air_path     = os.path.join(DATA_DIR, "air_quality.csv")
    cases_path   = os.path.join(DATA_DIR, "cases.csv")

    weather = pd.read_csv(weather_path, parse_dates=["date"])
    air     = pd.read_csv(air_path,     parse_dates=["date"])
    cases   = pd.read_csv(cases_path)

    print(f"  weather.csv:     {len(weather):>7,} rows")
    print(f"  air_quality.csv: {len(air):>7,} rows")
    print(f"  cases.csv:       {len(cases):>7,} rows")

    # ── Merge weather + air quality on (date, county) ──
    # Left join keeps all weather rows; PM10 may have gaps (not every
    # county has a monitor reporting every day)
    df = weather.merge(air, on=["date", "county"], how="left")

    # ── Attach yearly case counts ──
    # Each daily row gets the annual case_count for its county + year
    df["year"] = df["date"].dt.year
    df = df.merge(cases, on=["county", "year"], how="left")

    # Fill case_count NaN (years with no data, like 2026) with 0
    df["case_count"]  = df["case_count"].fillna(0)
    df["cases_source"] = df["cases_source"].fillna("no_data")

    # ── Attach FIPS, lat, lon from config ──
    df["fips"] = df["county"].map(lambda c: COUNTY_META.get(c, {}).get("fips", ""))
    df["lat"]  = df["county"].map(lambda c: COUNTY_META.get(c, {}).get("lat", np.nan))
    df["lon"]  = df["county"].map(lambda c: COUNTY_META.get(c, {}).get("lon", np.nan))

    # ── Reorder columns ──
    df = df[["date", "county", "fips", "lat", "lon",
             "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
             "pm10_ugm3", "tmax_approx_c",
             "case_count", "cases_source"]].copy()

    df = df.sort_values(["county", "date"]).reset_index(drop=True)
    print(f"\n  Merged: {len(df):,} daily rows × {df['county'].nunique()} counties")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: IMPUTATION — fill gaps in sensor data
# ─────────────────────────────────────────────────────────────────────────────
# (Stage 1 = temporal alignment is handled by merge — already daily)

def impute_missing(df):
    """
    Blueprint §6 Stage 2:
      - Forward fill for slowly-changing vars (soil moisture)
      - Linear interpolation for moderate vars (wind, temp, PM10)
      - Zero fill for precipitation (no data = no rain)
    """
    print("\n" + "=" * 70)
    print("  STAGE 2: Missing value imputation")
    print("=" * 70)

    before = df.isnull().sum()
    print(f"\n  Missing values BEFORE imputation:")
    for col in ["precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
                "pm10_ugm3", "tmax_approx_c"]:
        pct = before[col] / len(df) * 100
        print(f"    {col:25s}: {before[col]:>6,} ({pct:.1f}%)")

    # Apply per-county so we don't bleed across county boundaries
    for county in df["county"].unique():
        mask = df["county"] == county

        # Precipitation: zero fill (no data = no rain)
        df.loc[mask, "precip_mm"] = df.loc[mask, "precip_mm"].fillna(0)

        # Soil moisture: forward fill then backward fill
        # (slowly changing — yesterday's value is best guess)
        df.loc[mask, "soil_moisture_m3m3"] = (
            df.loc[mask, "soil_moisture_m3m3"]
            .ffill()
            .bfill()
        )

        # Wind, temperature, PM10: linear interpolation
        # (moderately changing — draw a line between neighbors)
        for col in ["wind_speed_kmh", "tmax_approx_c", "pm10_ugm3"]:
            df.loc[mask, col] = (
                df.loc[mask, col]
                .interpolate(method="linear", limit_direction="both")
            )

    after = df.isnull().sum()
    print(f"\n  Missing values AFTER imputation:")
    for col in ["precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
                "pm10_ugm3", "tmax_approx_c"]:
        print(f"    {col:25s}: {after[col]:>6,}")

    # Final fallback: if any county has ALL NaN for a variable
    # (e.g. no PM10 monitor at all), fill with cross-county median
    for col in ["pm10_ugm3", "soil_moisture_m3m3", "wind_speed_kmh", "tmax_approx_c"]:
        if df[col].isnull().any():
            median = df[col].median()
            n_fill = df[col].isnull().sum()
            df[col] = df[col].fillna(median)
            print(f"    ⚠ {col}: {n_fill} remaining NaNs filled with cross-county median ({median:.2f})")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3: OUTLIER CLIPPING — cap at physically plausible bounds
# ─────────────────────────────────────────────────────────────────────────────

def clip_outliers(df):
    """
    Blueprint §6 Stage 3:
    Cap values at physical boundaries to remove sensor glitches.
    """
    print("\n" + "=" * 70)
    print("  STAGE 3: Outlier clipping")
    print("=" * 70)

    bounds = {
        # column             min    max     unit
        "precip_mm":         (0,    380),   # ~15 in/day max
        "soil_moisture_m3m3":(0,    0.6),   # volumetric fraction
        "wind_speed_kmh":    (0,    130),   # ~80 mph max
        "pm10_ugm3":         (0,    600),   # EPA extreme AQI
        "tmax_approx_c":     (-15,  55),    # Death Valley record ~57°C
    }

    for col, (lo, hi) in bounds.items():
        n_low  = (df[col] < lo).sum()
        n_high = (df[col] > hi).sum()
        df[col] = df[col].clip(lo, hi)
        if n_low + n_high > 0:
            print(f"  {col:25s}: clipped {n_low} below {lo}, {n_high} above {hi}")

    print("  Done.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4: LAG FEATURE ENGINEERING — encode grow-and-blow biology
# ─────────────────────────────────────────────────────────────────────────────

def engineer_lags(df):
    """
    Blueprint §6 Stage 4 + §7.1:
    Create the lag features that encode the biological lifecycle.

    Growth phase inputs (G_pot):
      sm_lag6mo       — soil moisture 6 months ago (fungal hydration)
      tmax_lag6mo     — max temp 6 months ago (growth-phase heat)
      precip_lag1p5y  — precipitation 1.5 years ago (multi-year cycle)

    Exposure phase inputs (E_risk):
      pm10_lag1mo     — PM10 one month ago (airborne spore proxy)
      tmax_lag1mo     — max temp 1 month ago (maturation trigger)
      (current soil_moisture and wind_speed used directly)
    """
    print("\n" + "=" * 70)
    print("  STAGE 4: Lag feature engineering")
    print("=" * 70)

    df = df.sort_values(["county", "date"]).reset_index(drop=True)

    for county in df["county"].unique():
        mask = df["county"] == county
        c = df.loc[mask]

        # ── G_pot lags (growth phase) ──
        # Soil moisture 6 months ago (~183 days)
        df.loc[mask, "sm_lag6mo"]      = c["soil_moisture_m3m3"].shift(183)
        # Max temperature 6 months ago
        df.loc[mask, "tmax_lag6mo"]    = c["tmax_approx_c"].shift(183)
        # Precipitation 1.5 years ago (~548 days) — multi-year drought/deluge
        df.loc[mask, "precip_lag1p5y"] = c["precip_mm"].shift(548)

        # ── E_risk lags (exposure phase) ──
        # PM10 one month ago (~30 days)
        df.loc[mask, "pm10_lag1mo"]    = c["pm10_ugm3"].shift(30)
        # Max temperature 1 month ago
        df.loc[mask, "tmax_lag1mo"]    = c["tmax_approx_c"].shift(30)

    lag_cols = ["sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y", "pm10_lag1mo", "tmax_lag1mo"]
    n_nan = df[lag_cols].isnull().any(axis=1).sum()
    print(f"  Created 5 lag features: {lag_cols}")
    print(f"  Rows with NaN lags (early dates): {n_nan:,}")
    print(f"  These NaN rows are kept — models handle them during aggregation/windowing")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5: NORMALIZATION — Z-score (preferred) + MinMax (backup)
# ─────────────────────────────────────────────────────────────────────────────

def normalize(df):
    """
    Blueprint §6 Stage 5:
    Z-score is preferred for T-GCN because it preserves distributional
    shape needed by LSTM gates. MinMax included for the risk index formula.
    
    Z = (x - mean) / std
    MinMax = (x - min) / (max - min)
    """
    print("\n" + "=" * 70)
    print("  STAGE 5: Normalization (Z-score + MinMax)")
    print("=" * 70)

    # Columns to normalize
    raw_cols = ["precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
                "pm10_ugm3", "case_count"]
    lag_cols = ["sm_lag6mo", "tmax_lag6mo", "precip_lag1p5y",
                "pm10_lag1mo", "tmax_lag1mo"]
    all_norm = raw_cols + lag_cols

    # ── Z-score normalization ──
    # Preferred for T-GCN (Blueprint §6 Stage 5)
    print("\n  Z-score columns (z_*):")
    for col in all_norm:
        valid = df[col].dropna()
        if len(valid) > 0 and valid.std() > 0:
            df[f"z_{col}"] = (df[col] - valid.mean()) / valid.std()
            print(f"    z_{col:30s}  mean={valid.mean():.3f}  std={valid.std():.3f}")
        else:
            df[f"z_{col}"] = 0.0

    # ── MinMax normalization ──
    # Used for risk index formula (needs 0-1 range)
    print("\n  MinMax columns (n_*):")
    for col in all_norm:
        valid = df[col].dropna()
        if len(valid) > 0:
            vmin, vmax = valid.min(), valid.max()
            if vmax > vmin:
                df[f"n_{col}"] = (df[col] - vmin) / (vmax - vmin)
            else:
                df[f"n_{col}"] = 0.0
            print(f"    n_{col:30s}  min={vmin:.3f}  max={vmax:.3f}")
        else:
            df[f"n_{col}"] = 0.0

    # ── Soil aridity (1 - soil moisture) for E_risk ──
    df["n_soil_aridity"] = 1 - df["n_soil_moisture_m3m3"]

    print(f"\n  Total normalized columns: {len([c for c in df.columns if c.startswith('z_') or c.startswith('n_')])}")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# RISK INDEX — Blueprint §7.1 two-phase formula
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_index(df):
    """
    Blueprint §7.1:
      G_pot  = w1(SM_lag_6mo) + w2(T_lag_6mo) + w3(P_lag_1.5yr)
      E_risk = w4(PM10_1mo) + w5(W_current) + w6(1-SM_current) + w7(T_max_1mo)
      Risk   = G_pot × E_risk
    
    Weights from Research Table 3 (MNBR adjusted incidence rate ratios):
      Soil moisture lag:  35% → β = 1.9
      PM10 1mo:           25% → β = 1.6
      Max temp:           20% → β = 1.9
      Soil aridity:       15% → β = 1.3
      Wind speed:          5% → β = 0.5
    """
    print("\n" + "=" * 70)
    print("  RISK INDEX: Two-phase formula (Blueprint §7.1)")
    print("=" * 70)

    # ── Growth Potential (antecedent conditions) ──
    # Uses normalized lag features (MinMax 0-1 range)
    df["G_pot"] = (
        1.9 * df["n_sm_lag6mo"].fillna(0) +
        1.9 * df["n_tmax_lag6mo"].fillna(0) +
        1.6 * df["n_precip_lag1p5y"].fillna(0)
    )

    # ── Exposure Risk (current dispersal conditions) ──
    df["E_risk"] = (
        1.6 * df["n_pm10_lag1mo"].fillna(0) +
        0.5 * df["n_wind_speed_kmh"].fillna(0) +
        1.3 * df["n_soil_aridity"].fillna(0) +
        1.9 * df["n_tmax_lag1mo"].fillna(0)
    )

    # ── Integrated Risk = G_pot × E_risk ──
    # Multiplicative: high growth + no dispersal = zero human risk
    df["risk_score"] = df["G_pot"] * df["E_risk"]

    # ── Categorize into risk levels ──
    # Thresholds set so distribution roughly matches:
    # ~40% Low, ~30% Moderate, ~20% High, ~10% Very High
    risk_max = df["risk_score"].quantile(0.99)  # avoid outlier-driven thresholds
    if risk_max > 0:
        bins   = [0, risk_max * 0.25, risk_max * 0.50, risk_max * 0.75, float("inf")]
        labels = ["Low", "Moderate", "High", "Very High"]
        colors = {"Low": "green", "Moderate": "yellow", "High": "orange", "Very High": "red"}
        df["risk_level"] = pd.cut(df["risk_score"], bins=bins, labels=labels, include_lowest=True)
        df["risk_color"] = df["risk_level"].map(colors)
    else:
        df["risk_level"] = "Low"
        df["risk_color"] = "green"

    # Print summary
    print(f"\n  G_pot  range: {df['G_pot'].min():.3f} – {df['G_pot'].max():.3f}")
    print(f"  E_risk range: {df['E_risk'].min():.3f} – {df['E_risk'].max():.3f}")
    print(f"  Risk   range: {df['risk_score'].min():.3f} – {df['risk_score'].max():.3f}")
    print(f"\n  Risk level distribution:")
    for level in ["Low", "Moderate", "High", "Very High"]:
        n = (df["risk_level"] == level).sum()
        pct = n / len(df) * 100
        print(f"    {level:12s}: {n:>6,} rows ({pct:.1f}%)")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION — sanity checks before saving
# ─────────────────────────────────────────────────────────────────────────────

def validate(df):
    """Quick sanity checks to catch issues before saving."""
    print("\n" + "=" * 70)
    print("  VALIDATION")
    print("=" * 70)

    issues = []

    # Check county count
    n_counties = df["county"].nunique()
    if n_counties != 8:
        issues.append(f"Expected 8 counties, got {n_counties}")
    else:
        print(f"  Counties: {n_counties} ✓")

    # Check date range
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()} ✓")

    # Check for remaining NaN in critical columns
    critical = ["precip_mm", "soil_moisture_m3m3", "wind_speed_kmh",
                "pm10_ugm3", "tmax_approx_c", "case_count"]
    for col in critical:
        n = df[col].isnull().sum()
        if n > 0:
            issues.append(f"{col} has {n} NaN values")
        else:
            print(f"  {col}: no NaN ✓")

    # Check case count sanity
    for county in sorted(df["county"].unique()):
        for year in [2023, 2024]:
            yearly = df[(df["county"]==county) & (df["date"].dt.year==year)]["case_count"].iloc[0] if len(df[(df["county"]==county) & (df["date"].dt.year==year)]) > 0 else 0
            if yearly == 0 and year <= 2024:
                issues.append(f"{county} {year} has 0 cases — expected real data")

    # Check Kern dominance (it should be the highest)
    kern_2024 = df[(df["county"]=="Kern") & (df["date"].dt.year==2024)]["case_count"].iloc[0]
    if kern_2024 < 3000:
        issues.append(f"Kern 2024 = {kern_2024} — expected ~3990 (corrected CDPH)")
    else:
        print(f"  Kern 2024 cases: {kern_2024:.0f} ✓")

    # Check risk_score = G_pot × E_risk
    sample = df.dropna(subset=["G_pot", "E_risk"]).head(100)
    calc = sample["G_pot"] * sample["E_risk"]
    diff = (sample["risk_score"] - calc).abs().max()
    if diff > 0.01:
        issues.append(f"risk_score ≠ G_pot × E_risk (max diff: {diff:.4f})")
    else:
        print(f"  Risk formula G_pot × E_risk: verified ✓")

    if issues:
        print(f"\n  ⚠ ISSUES FOUND:")
        for i in issues:
            print(f"    - {i}")
    else:
        print(f"\n  ✅ All checks passed!")

    return len(issues) == 0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print("=" * 70)
    print("  SporeRisk — Data Collector & Standardization Pipeline")
    print("  Blueprint §6 Stages 1-5 + §7.1 Risk Index")
    print("=" * 70)

    # Stage 0: Merge scraper outputs
    df = merge_sources()

    # Stage 2: Impute missing values
    df = impute_missing(df)

    # Stage 3: Clip outliers
    df = clip_outliers(df)

    # Stage 4: Engineer lag features
    df = engineer_lags(df)

    # Stage 5: Normalize (Z-score + MinMax)
    df = normalize(df)

    # Risk Index: Two-phase formula
    df = compute_risk_index(df)

    # Validate
    validate(df)

    # Save
    df.to_csv(OUTPUT_CSV, index=False, date_format="%Y-%m-%d")
    print(f"\n{'=' * 70}")
    print(f"  ✅ Saved → {OUTPUT_CSV}")
    print(f"     {len(df):,} rows × {len(df.columns)} columns")
    print(f"     {df['county'].nunique()} counties")
    print(f"     {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"{'=' * 70}")

    # Column summary
    print(f"\n  Column groups:")
    raw    = [c for c in df.columns if not c.startswith(("z_","n_","G_","E_","risk"))]
    z_cols = [c for c in df.columns if c.startswith("z_")]
    n_cols = [c for c in df.columns if c.startswith("n_")]
    r_cols = [c for c in df.columns if c.startswith(("G_","E_","risk"))]
    print(f"    Raw/structural:  {len(raw)} cols — {raw}")
    print(f"    Z-score (z_*):   {len(z_cols)} cols")
    print(f"    MinMax (n_*):    {len(n_cols)} cols")
    print(f"    Risk index:      {len(r_cols)} cols — {r_cols}")

    return df


if __name__ == "__main__":
    run()