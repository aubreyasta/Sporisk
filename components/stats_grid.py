"""
Stats grid rendered as a custom component via components.html.
Uses Streamlit.setComponentValue to send clicked metric key back.
No Streamlit buttons = no black squares.
"""
from __future__ import annotations
import streamlit.components.v1 as components


def render_stats_grid(data: dict, active_metric: str | None, height: int = 170) -> str | None:
    """
    Renders a 2x2 HTML grid. Returns the clicked metric key, or None.
    """
    METRICS = [
        ("pm10",          "PM 10",      "pm10",          "µg/m³"),
        ("wind_speed",    "Wind",       "wind_speed",    "m/s"),
        ("soil_moisture", "Soil Moist", "soil_moisture", "%"),
        ("precipitation", "Precip",     "precipitation", "mm"),
    ]

    def fmt(key):
        v = data.get(key)
        if v is None: return "—"
        return f"{v*100:.1f}" if key == "soil_moisture" else f"{float(v):.1f}"

    cards = ""
    for key, label, data_key, unit in METRICS:
        is_active = (active_metric == key)
        bg     = "#f0ece5" if is_active else "#ffffff"
        border = "2px solid #7a6e5f" if is_active else "1px solid #d4cfc8"
        shadow = "0 0 0 3px rgba(122,110,95,0.12)" if is_active else "none"
        cards += f"""
        <div class="card" onclick="clicked('{key}')"
             style="background:{bg};border:{border};box-shadow:{shadow};">
          <div class="card-label">{label}</div>
          <div class="card-value">{fmt(data_key)}</div>
          <div class="card-unit">{unit}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #eae6e0;
    padding: 12px 16px 8px;
    font-family: 'DM Sans', sans-serif;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }}
  .card {{
    border-radius: 10px;
    padding: 14px 14px 12px;
    cursor: pointer;
    transition: border-color 0.12s;
    user-select: none;
  }}
  .card:hover {{ border-color: #a09880 !important; }}
  .card-label {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8a8070;
    margin-bottom: 6px;
  }}
  .card-value {{
    font-size: 24px;
    font-weight: 600;
    color: #1a1614;
    font-family: 'DM Mono', monospace;
    letter-spacing: -1px;
    line-height: 1;
  }}
  .card-unit {{
    font-size: 10px;
    color: #a09880;
    font-family: 'DM Mono', monospace;
    margin-top: 3px;
  }}
</style>
</head>
<body>
  <div class="grid">{cards}</div>
  <script>
    function clicked(key) {{
      // Streamlit's component value protocol
      window.parent.postMessage({{
        type: "streamlit:setComponentValue",
        value: key,
        dataType: "json",
        apiVersion: 1
      }}, "*");
    }}
  </script>
</body>
</html>"""

    result = components.html(html, height=height, scrolling=False)
    return result
