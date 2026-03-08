"""
Sporisk formula — the Gpot × Erisk × 100 index from sporisk.vercel.app
All inputs must be normalized to [0, 1] before calling.
"""

# Min/max ranges derived from your 2020–2026 Central Valley dataset
NORM_RANGES = {
    "sm":     (0.03, 0.45),   # soil moisture m³/m³
    "tmax":   (5.0,  45.0),   # °C
    "precip": (0.0,  200.0),  # mm monthly total
    "pm10":   (0.0,  150.0),  # µg/m³
    "wind":   (0.0,  60.0),   # km/h
}

def _norm(val, lo, hi):
    if val is None:
        return 0.5   # impute midpoint if missing
    return max(0.0, min(1.0, (val - lo) / (hi - lo)))

def compute_sporisk(sm_lag6, t_lag6, p_lag18mo,
                    pm10_1mo, sm_now, wind, tmax):
    """
    Returns dict with gpot, erisk, risk_score (0–100), and tier label.
    All raw inputs in original units; normalization happens here.
    """
    # Normalize each variable
    sm6n   = _norm(sm_lag6,  *NORM_RANGES["sm"])
    t6n    = _norm(t_lag6,   *NORM_RANGES["tmax"])
    p18n   = _norm(p_lag18mo,*NORM_RANGES["precip"])
    pm10n  = _norm(pm10_1mo, *NORM_RANGES["pm10"])
    sm_now_n = _norm(sm_now, *NORM_RANGES["sm"])
    windn  = _norm(wind,     *NORM_RANGES["wind"])
    tmaxn  = _norm(tmax,     *NORM_RANGES["tmax"])

    gpot  = 0.35*sm6n + 0.20*t6n + 0.30*p18n
    erisk = 0.25*pm10n + 0.15*(1 - sm_now_n) + 0.05*windn + 0.20*tmaxn

    score = round(gpot * erisk * 100, 2)

    if score < 3:      tier = "Low"
    elif score < 8:    tier = "Moderate"
    elif score < 15:   tier = "High"
    else:              tier = "Very High"

    return {
        "risk_score":  score,
        "gpot":        round(gpot, 4),
        "erisk":       round(erisk, 4),
        "risk_level":  tier,
    }