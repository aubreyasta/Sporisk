import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components

from data.mock_data import CENTRAL_VALLEY_COUNTIES, get_county_data
from utils.location import get_user_location
from utils.geo import find_county_for_point
from utils.map_builder import build_map
from utils.risk_colors import risk_level

st.set_page_config(page_title="CV Dust Risk", layout="wide", initial_sidebar_state="collapsed")

# ── Session ───────────────────────────────────────────────────────
if "county" not in st.session_state:
    lat, lon = get_user_location()
    detected = find_county_for_point(lat, lon)
    st.session_state.county = (
        detected if detected in CENTRAL_VALLEY_COUNTIES
        else CENTRAL_VALLEY_COUNTIES[0]
    )
if "active_metric" not in st.session_state:
    st.session_state.active_metric = None
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Ask me about dust risk in your area."}
    ]

# ── Handle metric click from query params ─────────────────────────
qp = st.query_params
if "metric" in qp:
    clicked = qp["metric"]
    st.query_params.clear()
    st.session_state.active_metric = None if clicked == st.session_state.active_metric else clicked
    st.rerun()

county        = st.session_state.county
data          = get_county_data(county) or {}
risk          = data.get("risk_index")
level, _      = risk_level(risk)
active_metric = st.session_state.active_metric

# ── Risk card colors (full card background) ───────────────────────
def card_colors(r):
    if r is None:   return "#2a2a2a", "#e0e0e0"
    if r < 20:      return "#1a4731", "#d0ffe0"
    elif r < 40:    return "#1e5c38", "#c8ffd4"
    elif r < 60:    return "#6b3a00", "#ffe8a0"
    elif r < 80:    return "#6b1010", "#ffe0e0"
    else:           return "#3c000c", "#ffd0d0"

card_bg, card_text = card_colors(risk)
risk_str = str(int(round(risk))) if risk is not None else "--"

# ── CSS ───────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background: #f0ede8 !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #1a1614 !important;
}}
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeader"],
section[data-testid="stSidebar"] {{ display: none !important; }}

.block-container {{ padding: 0 !important; max-width: 100% !important; }}
[data-testid="stVerticalBlock"] {{ gap: 0 !important; padding: 0 !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border: none !important; border-radius: 0 !important; }}
[data-testid="stHorizontalBlock"] {{ gap: 0 !important; padding: 0 !important; }}
[data-testid="stColumn"] {{ padding: 0 !important; }}

/* ── Float risk card over the st_folium map ──
   st_folium renders as: stVerticalBlock > stVerticalBlockBorderWrapper > stCustomComponentV1
   We make the outermost stVerticalBlock relative, then absolutely place
   the .risk-card-overlay which is rendered as the very next sibling element.
   The card sits on top via negative margin pulling it up into the map area. ── */

/* The stVerticalBlock that directly contains the map component gets position:relative */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:has(
  [data-testid="stCustomComponentV1"]
) {{
    position: static !important;
}}

/* Pull the card UP into the map using negative top margin, z-index over iframe */
.risk-card-overlay {{
    position: relative;
    z-index: 9999;
    margin-top: -254px;    /* pull up almost full map height */
    margin-right: 14px;
    margin-bottom: 240px;  /* restore space so content below isn't eaten */
    float: right;
    clear: right;
    width: 118px;
    background: {card_bg};
    border-radius: 14px;
    padding: 12px 14px 13px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.38);
    border: 1.5px solid rgba(255,255,255,0.13);
    pointer-events: none;
    font-family: 'DM Sans', -apple-system, sans-serif;
}}
.rc-county {{
    font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
    text-transform: uppercase; color: {card_text}; opacity: 0.72;
    margin-bottom: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.rc-number {{
    font-size: 50px; font-weight: 500; line-height: 1; letter-spacing: -3px;
    font-family: 'DM Mono', 'Courier New', monospace; color: {card_text};
}}
.rc-level {{
    font-size: 10px; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: {card_text}; opacity: 0.82; margin-top: 3px;
}}

/* ── County selectbox — visible below map ── */
[data-testid="stSelectbox"] label {{ display: none !important; }}
[data-testid="stSelectbox"] {{ margin: 8px 16px 8px !important; }}
[data-testid="stSelectbox"] > div > div {{
    background: #fff !important;
    border: 1px solid #d0cbc2 !important;
    border-radius: 8px !important;
    min-height: 30px !important;
    font-size: 12px !important;
    color: #1a1614 !important;
    box-shadow: none !important;
}}

/* ── Stats grid cards ── */
[data-testid="stIFrame"] iframe {{ border: none !important; display: block !important; }}

/* ── Chat ── */
[data-testid="stChatMessageContainer"],
[data-testid="stChatMessage"] {{
    background: rgba(255,255,255,0.7) !important;
    border: 1px solid rgba(212,207,200,0.6) !important;
    border-radius: 8px !important;
    margin: 3px 10px !important;
    padding: 6px 10px !important;
    font-size: 12px !important;
    color: #1a1614 !important;
}}
.stChatMessage {{ background: transparent !important; }}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessageContainer"] p,
[data-testid="stMarkdownContainer"] p {{ color: #1a1614 !important; }}
[data-testid="stBottom"] {{
    background: #e8e4de !important;
    border-top: 1px solid #d4cfc8 !important;
}}
[data-testid="stChatInput"] > div {{
    background: #fff !important;
    border: 1px solid #d0cbc2 !important;
    border-radius: 8px !important;
}}
[data-testid="stChatInput"] textarea {{
    color: #1a1614 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{ color: #a09880 !important; }}
[data-testid="stBaseButton-secondary"] {{
    background: rgba(160,144,128,0.15) !important;
    border: 1px solid rgba(160,144,128,0.35) !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    color: #4a4438 !important;
    font-size: 11px !important;
    height: 26px !important; min-height: 26px !important;
    padding: 0 8px !important;
}}
</style>
""", unsafe_allow_html=True)

# ── MAP + FLOATING RISK CARD (single components.html container) ───
# Embedding both in one call gives us a real position:relative root
# we fully control — the only bulletproof way to float over a folium map.
m = build_map(active_county=county)
map_html = m._repr_html_()

# Render map with st_folium (tiles + circles work correctly)
try:
    from streamlit_folium import st_folium
    st_folium(m, width="100%", height=264, key="cv_map", returned_objects=[])
except Exception:
    components.html(m._repr_html_(), height=264, scrolling=False)

# Risk card floats over the map using CSS fixed positioning anchored
# to the viewport top-right. We use a sentinel div to know where
# the map is, then position relative to it via the stVerticalBlock parent.
st.markdown(
    f'<div class="risk-card-overlay">'
    f'<div class="rc-county">{county}</div>'
    f'<div class="rc-number">{risk_str}</div>'
    f'<div class="rc-level">{level}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:1px;background:#d4cfc8;"></div>', unsafe_allow_html=True)

# ── COUNTY PICKER ─────────────────────────────────────────────────
chosen = st.selectbox(
    "County", CENTRAL_VALLEY_COUNTIES,
    index=CENTRAL_VALLEY_COUNTIES.index(county),
    key="county_picker", label_visibility="collapsed",
)
if chosen != county:
    st.session_state.county = chosen
    st.session_state.active_metric = None
    st.rerun()

st.markdown('<div style="height:1px;background:#d4cfc8;"></div>', unsafe_allow_html=True)

# ── STATS GRID ────────────────────────────────────────────────────
def fmt(key):
    v = data.get(key)
    if v is None: return "—"
    return f"{v*100:.1f}" if key == "soil_moisture" else f"{float(v):.1f}"

METRICS = [
    ("pm10",          "PM 10",      fmt("pm10"),          "µg/m³"),
    ("wind_speed",    "Wind",       fmt("wind_speed"),    "m/s"),
    ("soil_moisture", "Soil Moist", fmt("soil_moisture"), "%"),
    ("precipitation", "Precip",     fmt("precipitation"), "mm"),
]

cards_html = ""
for key, label, value, unit in METRICS:
    active = active_metric == key
    bg     = "#f0ece5" if active else "#ffffff"
    border = "2px solid #7a6e5f" if active else "1px solid #d4cfc8"
    shadow = "0 0 0 3px rgba(122,110,95,0.12)" if active else "none"
    cards_html += f"""
    <div class="card" onclick="sendMetric('{key}')"
         style="background:{bg};border:{border};box-shadow:{shadow};">
      <div class="card-label">{label}</div>
      <div class="card-value">{value}</div>
      <div class="card-unit">{unit}</div>
    </div>"""

grid_html = f"""<!DOCTYPE html><html><head>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&family=DM+Mono:wght@400;500&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #eae6e0; padding: 12px 16px 8px; font-family: 'DM Sans', sans-serif; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .card {{
    border-radius: 10px; padding: 14px 14px 12px;
    cursor: pointer; transition: border-color 0.12s; user-select: none;
  }}
  .card:hover {{ border-color: #a09880 !important; }}
  .card-label {{
    font-size: 10px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8a8070; margin-bottom: 6px;
  }}
  .card-value {{
    font-size: 24px; font-weight: 600; color: #1a1614;
    font-family: 'DM Mono', monospace; letter-spacing: -1px; line-height: 1;
  }}
  .card-unit {{
    font-size: 10px; color: #a09880;
    font-family: 'DM Mono', monospace; margin-top: 3px;
  }}
</style></head><body>
  <div class="grid">{cards_html}</div>
  <script>
    function sendMetric(key) {{
      var url = new URL(window.parent.location.href);
      url.searchParams.set('metric', key);
      window.parent.location.href = url.toString();
    }}
  </script>
</body></html>"""

components.html(grid_html, height=170, scrolling=False)

# ── CHART PANEL ───────────────────────────────────────────────────
if active_metric:
    LABELS = {
        "pm10":          ("PM 10",      "µg/m³"),
        "wind_speed":    ("Wind",       "m/s"),
        "soil_moisture": ("Soil Moist", "%"),
        "precipitation": ("Precip",     "mm"),
    }
    lbl, unit = LABELS.get(active_metric, (active_metric, ""))
    st.markdown(
        f'<div style="margin:0 16px 10px;background:#fff;border:1px solid #d4cfc8;'
        f'border-radius:10px;overflow:hidden;">'
        f'<div style="padding:10px 14px;font-size:12px;font-weight:600;color:#4a4438;'
        f'border-bottom:1px solid #e8e4dc;background:#faf8f5;">{lbl} — {county} County</div>'
        f'<div style="padding:20px 14px;font-size:11px;color:#a09880;'
        f'font-family:DM Mono,monospace;">'
        f'Wire up: get_metric_history("{county}", "{active_metric}")'
        f'</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<div style="height:1px;background:#d4cfc8;"></div>', unsafe_allow_html=True)

# ── CHAT ──────────────────────────────────────────────────────────
col_t, col_b = st.columns([6, 1])
with col_t:
    st.markdown(
        '<div style="padding:8px 16px;font-size:12px;font-weight:600;color:#4a4438;'
        'letter-spacing:0.04em;background:#e4e0da;border-bottom:1px solid #d4cfc8;">'
        'AI Assistant</div>',
        unsafe_allow_html=True,
    )
with col_b:
    if st.button("▲" if st.session_state.chat_open else "▼", key="chat_toggle"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

if st.session_state.chat_open:
    with st.container(height=150, border=False):
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    if prompt := st.chat_input("Ask about dust risk…", key="chat_input"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        import random as _r
        st.session_state.messages.append({"role": "assistant", "content": _r.choice([
            "PM10 is elevated due to low soil moisture and recent farm activity.",
            "Southern counties show the highest concentrations today.",
            "Wind patterns suggest conditions ease by evening.",
        ])})
        st.rerun()
