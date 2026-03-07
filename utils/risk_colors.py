from __future__ import annotations

def risk_level(risk_index: float | None) -> tuple[str, str]:
    """Returns (label, color_hex) for a risk index value."""
    if risk_index is None:
        return "Unknown", "#8a8070"
    if risk_index < 20:
        return "None", "#2d7a4f"
    elif risk_index < 40:
        return "Low", "#2d7a4f"
    elif risk_index < 60:
        return "Moderate", "#b07800"
    elif risk_index < 80:
        return "High", "#b03000"
    else:
        return "Critical", "#8b0000"

def risk_fill(risk_index: float | None) -> str:
    _, color = risk_level(risk_index)
    return color

def risk_fill_opacity(risk_index: float | None) -> float:
    if risk_index is None:
        return 0.25
    return 0.25 + (risk_index / 100) * 0.45
