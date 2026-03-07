"""
utils/risk_colors.py
Maps risk index values (0–100) to fill colors for the folium choropleth.
Designed to be swapped out or extended once the backend Risk Index is live.
"""

from dataclasses import dataclass


@dataclass
class RiskLevel:
    label: str
    css_class: str
    fill_color: str   # hex used by folium
    text_color: str


RISK_LEVELS = [
    RiskLevel("None",     "risk-none",     "#1a4731", "#68d391"),
    RiskLevel("Low",      "risk-low",      "#276749", "#9ae6b4"),
    RiskLevel("Moderate", "risk-moderate", "#744210", "#fbd38d"),
    RiskLevel("High",     "risk-high",     "#742a2a", "#fc8181"),
    RiskLevel("Critical", "risk-critical", "#4c0519", "#feb2b2"),
]


def risk_index_to_level(risk_index: float | None) -> RiskLevel:
    """
    Map a 0–100 risk index float to a RiskLevel.
    None / missing data returns the "None" level.
    """
    if risk_index is None:
        return RISK_LEVELS[0]
    if risk_index < 20:
        return RISK_LEVELS[0]
    elif risk_index < 40:
        return RISK_LEVELS[1]
    elif risk_index < 60:
        return RISK_LEVELS[2]
    elif risk_index < 80:
        return RISK_LEVELS[3]
    else:
        return RISK_LEVELS[4]


def risk_index_to_fill(risk_index: float | None) -> str:
    """Convenience: return just the hex fill color."""
    return risk_index_to_level(risk_index).fill_color


def fill_opacity_for_risk(risk_index: float | None) -> float:
    """Higher risk → more opaque fill so it stands out."""
    if risk_index is None:
        return 0.25
    return 0.25 + (risk_index / 100) * 0.45


LEGEND_ITEMS = [
    ("#1a4731", "None   ( 0–19 )"),
    ("#276749", "Low    (20–39)"),
    ("#744210", "Moderate (40–59)"),
    ("#742a2a", "High   (60–79)"),
    ("#4c0519", "Critical (80–100)"),
]
