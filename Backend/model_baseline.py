"""
SporeRisk - Model Baseline: Random Forest
==========================================
Aggregates daily data → monthly, trains a Random Forest,
evaluates with cross-validation, and saves predictions.

Run:  python model_baseline.py
Input:  sporerisk_master.csv
Output: baseline_predictions.csv, prints evaluation metrics
"""

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


# ============================================================
# STEP 1: Load and aggregate to monthly
# ============================================================

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load_and_aggregate(csv_path=os.path.join(_DATA, "sporerisk_master_corrected.csv")):
    """
    Takes the daily master CSV and collapses it to monthly rows.
    
    WHY: Case counts are yearly totals repeated daily — training on
    daily rows would mean 365 near-identical targets per county/year.
    Monthly aggregation gives us meaningful weather summaries and
    matches the biological timescale of grow-and-blow.
    """
    print("Loading data...")
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    
    print(f"  Raw: {len(df):,} daily rows across {df['county'].nunique()} counties")
    
    # --- Aggregate daily → monthly ---
    # SUM for precipitation (total rain matters)
    # MEAN for everything else (typical conditions that month)
    monthly = df.groupby(["county", "year", "month"]).agg({
        "fips":                 "first",
        "lat":                  "first",
        "lon":                  "first",
        "precip_mm":            "sum",       # total monthly rainfall
        "soil_moisture_m3m3":   "mean",      # avg soil moisture
        "wind_speed_kmh":       "mean",      # avg wind speed
        "pm10_ugm3":            "mean",      # avg PM10
        "tmax_approx_c":        "mean",      # avg max temp
        "case_count":           "first",     # yearly total (same every day)
    }).reset_index()
    
    print(f"  Monthly: {len(monthly):,} rows ({monthly['county'].nunique()} counties × "
          f"{monthly['year'].nunique()} years)")
    
    # --- Distribute yearly cases into monthly estimates ---
    # Valley Fever has a known seasonal peak: Aug-Nov accounts for ~60% of cases
    # This curve is based on published CDPH seasonal patterns
    SEASONAL_WEIGHTS = {
        1: 0.04, 2: 0.03, 3: 0.04, 4: 0.05, 5: 0.06, 6: 0.07,
        7: 0.08, 8: 0.12, 9: 0.14, 10: 0.15, 11: 0.13, 12: 0.09
    }
    # These sum to 1.0, so yearly_total × weight = estimated monthly cases
    
    monthly["monthly_cases"] = monthly.apply(
        lambda row: row["case_count"] * SEASONAL_WEIGHTS[row["month"]], axis=1
    )
    
    print(f"  Distributed yearly cases into monthly estimates using VF seasonal curve")
    print(f"  Peak months (Aug-Nov) get ~54% of yearly total")
    
    return monthly


# ============================================================
# STEP 2: Engineer features for the Random Forest
# ============================================================

def engineer_features(monthly):
    """
    Creates lag features per county. The Random Forest doesn't understand
    sequences, so we MANUALLY tell it about the past by adding columns
    like "what was soil moisture 6 months ago?"
    
    This is the key difference vs T-GCN — the T-GCN learns these
    temporal relationships on its own from the raw sequences.
    """
    print("\nEngineering lag features...")
    
    # Sort by county then time so shift() works correctly
    monthly = monthly.sort_values(["county", "year", "month"]).reset_index(drop=True)
    
    features_added = []
    
    for county in monthly["county"].unique():
        mask = monthly["county"] == county
        county_df = monthly.loc[mask].copy()
        
        # --- Lag features (shift N months back) ---
        # These encode the "grow and blow" biology:
        
        # Precipitation 3 months ago (short-term growth signal)
        monthly.loc[mask, "precip_lag3"] = county_df["precip_mm"].shift(3)
        
        # Precipitation 6 months ago (main growth window)
        monthly.loc[mask, "precip_lag6"] = county_df["precip_mm"].shift(6)
        
        # Precipitation 18 months ago (multi-year drought/deluge signal)
        monthly.loc[mask, "precip_lag18"] = county_df["precip_mm"].shift(18)
        
        # Soil moisture 6 months ago (was the ground wet during grow phase?)
        monthly.loc[mask, "sm_lag6"] = county_df["soil_moisture_m3m3"].shift(6)
        
        # PM10 1 month ago (were spores already in the air?)
        monthly.loc[mask, "pm10_lag1"] = county_df["pm10_ugm3"].shift(1)
        
        # Max temperature 1 month ago (maturation trigger)
        monthly.loc[mask, "tmax_lag1"] = county_df["tmax_approx_c"].shift(1)
        
        # Max temperature 6 months ago (was it hot during growth phase?)
        monthly.loc[mask, "tmax_lag6"] = county_df["tmax_approx_c"].shift(6)
        
        # --- Rolling averages (sustained conditions) ---
        monthly.loc[mask, "wind_roll3"] = county_df["wind_speed_kmh"].rolling(3).mean()
        monthly.loc[mask, "pm10_roll3"] = county_df["pm10_ugm3"].rolling(3).mean()
        
        # --- Soil aridity (inverse moisture = dispersal potential) ---
        monthly.loc[mask, "soil_aridity"] = 1 - county_df["soil_moisture_m3m3"]
    
    # Drop rows where lag features are NaN (first 18 months per county)
    before = len(monthly)
    monthly = monthly.dropna().reset_index(drop=True)
    print(f"  Added 10 lag/rolling features")
    print(f"  Dropped {before - len(monthly)} rows with NaN lags (first 18 months per county)")
    print(f"  Final dataset: {len(monthly)} rows")
    
    return monthly


# ============================================================
# STEP 3: Train and evaluate Random Forest
# ============================================================

def train_and_evaluate(monthly):
    """
    Trains a Random Forest using Leave-One-County-Out cross-validation.
    
    WHY Leave-One-County-Out? It tests whether the model can predict
    risk for a county it's NEVER seen — proving spatial generalization.
    This is way more impressive to judges than random train/test split.
    """
    print("\n" + "=" * 60)
    print("TRAINING: Random Forest Baseline")
    print("=" * 60)
    
    # --- Define features and target ---
    feature_cols = [
        # Current conditions
        "precip_mm", "soil_moisture_m3m3", "wind_speed_kmh", 
        "pm10_ugm3", "tmax_approx_c", "soil_aridity",
        # Lag features (the grow-and-blow encoding)
        "precip_lag3", "precip_lag6", "precip_lag18",
        "sm_lag6", "pm10_lag1", "tmax_lag1", "tmax_lag6",
        # Rolling features
        "wind_roll3", "pm10_roll3",
        # Time features
        "month"
    ]
    
    target = "monthly_cases"
    
    X = monthly[feature_cols].values
    y = monthly[target].values
    groups = monthly["county"].values  # for leave-one-county-out
    
    # --- Standardize features ---
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"\n  Features: {len(feature_cols)}")
    print(f"  Samples:  {len(X)}")
    print(f"  Target:   monthly estimated cases")
    
    # --- Leave-One-County-Out Cross-Validation ---
    print(f"\n  Cross-validation: Leave-One-County-Out (8 folds)")
    
    logo = LeaveOneGroupOut()
    
    # Random Forest
    rf = RandomForestRegressor(
        n_estimators=200,      # 200 trees in the forest
        max_depth=10,          # prevent overfitting
        min_samples_leaf=3,    # each leaf needs at least 3 samples
        random_state=42,       # reproducible results
        n_jobs=-1              # use all CPU cores
    )
    
    # Get cross-validated predictions (each county predicted by model trained WITHOUT it)
    y_pred_rf = cross_val_predict(rf, X_scaled, y, groups=groups, cv=logo)
    
    # Also train Gradient Boosting for comparison
    gb = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        random_state=42
    )
    y_pred_gb = cross_val_predict(gb, X_scaled, y, groups=groups, cv=logo)
    
    # --- Evaluate both ---
    print("\n  RESULTS (Leave-One-County-Out CV):")
    print("  " + "-" * 50)
    
    for name, y_pred in [("Random Forest", y_pred_rf), ("Gradient Boosting", y_pred_gb)]:
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        print(f"\n  {name}:")
        print(f"    RMSE:  {rmse:.2f} cases/month")
        print(f"    MAE:   {mae:.2f} cases/month")
        print(f"    R²:    {r2:.4f}")
    
    # --- Train final model on ALL data ---
    print("\n  Training final Random Forest on full dataset...")
    rf.fit(X_scaled, y)
    
    # --- Feature importance ---
    importances = pd.DataFrame({
        "feature": feature_cols,
        "importance": rf.feature_importances_
    }).sort_values("importance", ascending=False)
    
    print("\n  FEATURE IMPORTANCE (Top 10):")
    print("  " + "-" * 40)
    for _, row in importances.head(10).iterrows():
        bar = "█" * int(row["importance"] * 50)
        print(f"    {row['feature']:22s} {row['importance']:.4f} {bar}")
    
    return rf, scaler, feature_cols, y_pred_rf, monthly


# ============================================================
# STEP 4: Save predictions
# ============================================================

def save_predictions(monthly, y_pred, output_path="baseline_predictions.csv"):
    """Save the cross-validated predictions alongside actual values."""
    
    results = monthly[["county", "year", "month", "monthly_cases", "lat", "lon"]].copy()
    results["predicted_cases"] = y_pred
    results["residual"] = results["monthly_cases"] - results["predicted_cases"]

    # ----------------------------------------------------------------
    # SPORISK BIOLOGICAL RISK INDEX  (Gpot × Erisk × 100)
    # Formula matches exactly: https://sporisk.vercel.app — Algorithm section
    #
    # Normalization: MinMax using actual min/max observed in the monthly
    # dataset (computed live below), so ranges adapt to the real data
    # rather than hardcoded estimates. Matches data_collector.py approach.
    # ----------------------------------------------------------------

    def _safe(series):
        """Return (min, max) of a Series, ignoring NaN. Returns (0,1) if flat."""
        lo, hi = series.min(), series.max()
        return (lo, hi) if hi > lo else (0.0, 1.0)

    # Compute normalization ranges from the actual monthly data
    sm_range     = _safe(monthly["soil_moisture_m3m3"])
    tmax_range   = _safe(monthly["tmax_approx_c"])
    precip_range = _safe(monthly["precip_mm"])
    pm10_range   = _safe(monthly["pm10_ugm3"])
    wind_range   = _safe(monthly["wind_speed_kmh"])

    # Lag-feature ranges (same physical variable, potentially different range)
    sm6_range    = _safe(monthly["sm_lag6"].dropna())
    tmax6_range  = _safe(monthly["tmax_lag6"].dropna())
    p18_range    = _safe(monthly["precip_lag18"].dropna())
    pm10l_range  = _safe(monthly["pm10_lag1"].dropna())
    tmax1_range  = _safe(monthly["tmax_lag1"].dropna())
    wind3_range  = _safe(monthly["wind_roll3"].dropna())

    print(f"\n  Normalization ranges (from actual data):")
    print(f"    sm_lag6:     {sm6_range[0]:.3f} – {sm6_range[1]:.3f} m³/m³")
    print(f"    tmax_lag6:   {tmax6_range[0]:.1f} – {tmax6_range[1]:.1f} °C")
    print(f"    precip_lag18:{p18_range[0]:.1f} – {p18_range[1]:.1f} mm")
    print(f"    pm10_lag1:   {pm10l_range[0]:.1f} – {pm10l_range[1]:.1f} µg/m³")
    print(f"    wind_roll3:  {wind3_range[0]:.1f} – {wind3_range[1]:.1f} km/h")
    print(f"    sm_now:      {sm_range[0]:.3f} – {sm_range[1]:.3f} m³/m³")
    print(f"    tmax_lag1:   {tmax1_range[0]:.1f} – {tmax1_range[1]:.1f} °C")

    def _norm(val, lo, hi):
        """MinMax normalize to [0,1]. NaN/None → 0.5 (midpoint impute)."""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return 0.5
        return max(0.0, min(1.0, (val - lo) / (hi - lo)))

    def compute_sporisk(row):
        """
        Sporisk formula (sporisk.vercel.app):
          Gpot  = 0.35×SM_lag6 + 0.20×T_lag6 + 0.30×P_lag18
          Erisk = 0.25×PM10_lag1 + 0.15×(1−SM_now) + 0.05×Wind + 0.20×Tmax_lag1
          Score = Gpot × Erisk × 100
        All inputs normalized to [0,1] using actual data min/max.
        """
        # ── Growth Potential ──
        sm6n  = _norm(row.get("sm_lag6"),      *sm6_range)
        t6n   = _norm(row.get("tmax_lag6"),    *tmax6_range)
        p18n  = _norm(row.get("precip_lag18"), *p18_range)

        gpot = 0.35 * sm6n + 0.20 * t6n + 0.30 * p18n

        # ── Exposure Risk ──
        pm10n   = _norm(row.get("pm10_lag1"),          *pm10l_range)
        sm_now  = _norm(row.get("soil_moisture_m3m3"),  *sm_range)
        windn   = _norm(row.get("wind_roll3"),          *wind3_range)
        tmaxn   = _norm(row.get("tmax_lag1"),           *tmax1_range)

        erisk = 0.25 * pm10n + 0.15 * (1 - sm_now) + 0.05 * windn + 0.20 * tmaxn

        score = round(gpot * erisk * 100, 2)

        # Fixed thresholds matching theory page (not quantile-relative)
        if score < 3:    tier = "Low"
        elif score < 8:  tier = "Moderate"
        elif score < 15: tier = "High"
        else:            tier = "Very High"

        return gpot, erisk, score, tier

    gpot_vals, erisk_vals, score_vals, tier_vals = [], [], [], []
    monthly_dict = monthly.to_dict("records")

    for row_dict in monthly_dict:
        gpot, erisk, score, tier = compute_sporisk(row_dict)
        gpot_vals.append(round(gpot, 4))
        erisk_vals.append(round(erisk, 4))
        score_vals.append(score)
        tier_vals.append(tier)

    results["gpot"]          = gpot_vals
    results["erisk"]         = erisk_vals
    results["risk_score"]    = score_vals   # 0–100 continuous (was 1–4 integer)
    results["predicted_risk"] = tier_vals   # "Low"/"Moderate"/"High"/"Very High"
    
    results.to_csv(output_path, index=False)
    print(f"\n  Saved predictions → {output_path}")
    print(f"  Columns: {list(results.columns)}")
    
    # Per-county summary
    print("\n  PER-COUNTY PERFORMANCE:")
    print("  " + "-" * 60)
    print(f"  {'County':15s} {'Avg Actual':>12s} {'Avg Predicted':>14s} {'MAE':>8s}")
    print("  " + "-" * 60)
    
    for county in sorted(results["county"].unique()):
        cm = results[results["county"] == county]
        actual = cm["monthly_cases"].mean()
        predicted = cm["predicted_cases"].mean()
        mae = cm["residual"].abs().mean()
        print(f"  {county:15s} {actual:12.1f} {predicted:14.1f} {mae:8.1f}")
    
    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SPORERISK - Random Forest Baseline")
    print("  Valley Fever Risk Prediction")
    print("=" * 60)
    
    # Load and prepare data
    monthly = load_and_aggregate()
    monthly = engineer_features(monthly)
    
    # Train and evaluate
    rf, scaler, features, y_pred, monthly = train_and_evaluate(monthly)
    
    # Save
    results = save_predictions(monthly, y_pred)
    
    print("\n" + "=" * 60)
    print("  DONE! Your baseline is ready.")
    print("  Next step: model_tgcn.py (LSTM + GNN)")
    print("=" * 60)
