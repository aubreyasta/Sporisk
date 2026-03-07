import sys, os, math, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components

from data.mock_data import CENTRAL_VALLEY_COUNTIES, get_county_data
from utils.location   import get_user_location
from utils.geo        import find_county_for_point
from utils.map_builder import build_map
from utils.risk_colors import risk_level

st.set_page_config(page_title="CV Dust Risk", layout="wide",
                   initial_sidebar_state="collapsed")

# ── Streamlit chrome completely hidden ────────────────────────────
st.markdown("""
<style>
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],[data-testid="stHeader"],
section[data-testid="stSidebar"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}
[data-testid="stVerticalBlock"]{gap:0!important;padding:0!important}
[data-testid="stVerticalBlockBorderWrapper"]{border:none!important;border-radius:0!important}
[data-testid="stIFrame"]>iframe{border:none!important;display:block!important}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────
if "county" not in st.session_state:
    lat, lon = get_user_location()
    det = find_county_for_point(lat, lon)
    st.session_state.county = det if det in CENTRAL_VALLEY_COUNTIES else CENTRAL_VALLEY_COUNTIES[0]
if "metric" not in st.session_state:
    st.session_state.metric = ""          # "" = grid view
if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"assistant",
        "content":"Ask me about dust risk, health precautions, or work recommendations."}]
if "chat_msg" not in st.session_state:
    st.session_state.chat_msg = ""

# ── Query-param actions (from inside the component) ───────────────
qp = st.query_params
action  = qp.get("action",  "")
payload = qp.get("payload", "")
if action:
    st.query_params.clear()
    if action == "county":
        if payload in CENTRAL_VALLEY_COUNTIES:
            st.session_state.county = payload
            st.session_state.metric = ""
    elif action == "metric":
        st.session_state.metric = "" if payload == st.session_state.metric else payload
    elif action == "back":
        st.session_state.metric = ""
    elif action == "chat":
        if payload.strip():
            st.session_state.messages.append({"role":"user","content":payload.strip()})
            county_now = st.session_state.county
            data_now   = get_county_data(county_now) or {}
            risk_now   = data_now.get("risk_index")
            lvl_now, _ = risk_level(risk_now)
            rs_now     = str(int(round(risk_now))) if risk_now else "--"
            replies = [
                f"PM10 is elevated in {county_now}. Wear an N95 for outdoor work over 1 hour.",
                f"Soil moisture is low in {county_now} and winds are picking up — dust will worsen this afternoon.",
                f"Conditions in {county_now} are {lvl_now.lower()} today. Standard PPD protocols apply.",
            ]
            st.session_state.messages.append({"role":"assistant","content":random.choice(replies)})
    st.rerun()

# ── Data for current county ───────────────────────────────────────
county  = st.session_state.county
metric  = st.session_state.metric
data    = get_county_data(county) or {}
risk    = data.get("risk_index")
level, _ = risk_level(risk)
risk_str = str(int(round(risk))) if risk is not None else "--"

def card_colors(r):
    if r is None: return "#2a2a2a","#e0e0e0"
    if r < 20:    return "#1a4731","#d0ffe0"
    elif r < 40:  return "#1e5c38","#c8ffd4"
    elif r < 60:  return "#6b3a00","#ffe8a0"
    elif r < 80:  return "#6b1010","#ffe0e0"
    else:         return "#3c000c","#ffd0d0"

card_bg, card_text = card_colors(risk)

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

# ── Map HTML (folium) ─────────────────────────────────────────────
map_folium = build_map(active_county=county)
map_html   = map_folium._repr_html_()

# ── Sparkline for chart panel ─────────────────────────────────────
pts = [40 + 30*math.sin(i/2.5) + 10*math.sin(i/0.8) for i in range(24)]
mx, mn = max(pts), min(pts)
W, H = 300, 72
def sc(v): return H - int((v - mn)/(mx - mn + 0.001)*(H-8)) - 4
poly     = " ".join(f"{int(i*(W/23))},{sc(v)}" for i,v in enumerate(pts))
area_pts = f"0,{H} {poly} {W},{H}"

# ── Active-metric data ────────────────────────────────────────────
metric_label = next((l for k,l,_,u in METRICS if k==metric), "")
metric_unit  = next((u for k,l,_,u in METRICS if k==metric), "")
metric_value = fmt(metric) if metric else ""

# ── Last chat message ─────────────────────────────────────────────
last_msg = next((m["content"] for m in reversed(st.session_state.messages)
                 if m["role"]=="assistant"),
                "Ask me about dust risk, health precautions, or work recommendations.")
# Escape for JS string
last_msg_js  = json.dumps(last_msg)
county_opts  = json.dumps(CENTRAL_VALLEY_COUNTIES)
county_js    = json.dumps(county)
metric_js    = json.dumps(metric)

# ── Build 2×2 grid cards HTML ─────────────────────────────────────
grid_cards = ""
for key, label, value, unit in METRICS:
    grid_cards += f"""
      <div class="card" onclick="act('metric','{key}')">
        <div class="clbl">{label}</div>
        <div class="cval">{value}</div>
        <div class="cunt">{unit}</div>
      </div>"""

# ── County option tags ────────────────────────────────────────────
county_options = "".join(
    f'<option value="{c}" {"selected" if c==county else ""}>{c}</option>'
    for c in CENTRAL_VALLEY_COUNTIES
)

# ── Single components.html — all three sections ───────────────────
# Viewport height is split exactly 1/3 each using CSS grid rows.
# All navigation is via window.parent.location query params.
html = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{
    width:100%;height:100%;
    font-family:'DM Sans',sans-serif;
    background:#f0ede8;color:#1a1614;
    overflow:hidden;
  }}

  /* ── Three equal rows ── */
  .shell{{
    display:grid;
    grid-template-rows:1fr 1fr 1fr;
    width:100%;height:100%;
  }}

  /* ═══════════════════════════════════════════
     ROW 1 — MAP
  ═══════════════════════════════════════════ */
  .row-map{{
    position:relative;
    overflow:hidden;
    background:#c8d8e8;
  }}
  #map-iframe{{
    position:absolute;top:0;left:0;
    width:100%;height:100%;border:none;
  }}
  /* Risk card: centered over map */
  .risk-card{{
    position:absolute;
    top:50%;left:50%;
    transform:translate(-50%,-50%);
    z-index:999;
    width:124px;
    background:{card_bg};
    border-radius:16px;
    padding:12px 14px;
    text-align:center;
    box-shadow:0 6px 28px rgba(0,0,0,0.5),0 2px 8px rgba(0,0,0,0.25);
    border:1.5px solid rgba(255,255,255,0.18);
    pointer-events:none;
  }}
  .rc-name{{
    font-size:10px;font-weight:700;letter-spacing:.07em;
    text-transform:uppercase;color:{card_text};opacity:.72;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    margin-bottom:2px;
  }}
  .rc-num{{
    font-size:52px;font-weight:500;line-height:1;letter-spacing:-4px;
    font-family:'DM Mono','Courier New',monospace;color:{card_text};
  }}
  .rc-lvl{{
    font-size:10px;font-weight:700;letter-spacing:.09em;
    text-transform:uppercase;color:{card_text};opacity:.82;margin-top:3px;
  }}

  /* ═══════════════════════════════════════════
     ROW 2 — COUNTY PICKER + GRID or CHART
  ═══════════════════════════════════════════ */
  .row-mid{{
    display:flex;flex-direction:column;
    background:#f0ede8;
    border-top:1px solid #d4cfc8;
    border-bottom:1px solid #d4cfc8;
    overflow:hidden;
  }}

  /* County picker */
  .county-row{{
    flex:0 0 auto;
    padding:8px 14px;
    border-bottom:1px solid #e4e0da;
  }}
  .county-select{{
    width:100%;padding:6px 10px;
    font-size:13px;font-family:'DM Sans',sans-serif;
    color:#1a1614;background:#fff;
    border:1px solid #d0cbc2;border-radius:8px;
    outline:none;cursor:pointer;
    -webkit-appearance:none;appearance:none;
  }}

  /* Grid area fills remaining space in row 2 */
  .grid-area{{
    flex:1 1 0;
    display:grid;grid-template-columns:1fr 1fr;
    gap:10px;padding:10px 14px 10px;
    overflow:hidden;
  }}
  .card{{
    background:#fff;border:1px solid #d4cfc8;border-radius:10px;
    padding:12px 12px 10px;cursor:pointer;user-select:none;
    display:flex;flex-direction:column;justify-content:center;
    transition:background .1s,border-color .1s;
  }}
  .card:hover{{background:#faf8f5;border-color:#a09880}}
  .card:active{{background:#f0ece5;border-color:#7a6e5f;transform:scale(.98)}}
  .clbl{{font-size:10px;font-weight:600;letter-spacing:.08em;
         text-transform:uppercase;color:#8a8070;margin-bottom:6px}}
  .cval{{font-size:26px;font-weight:600;color:#1a1614;
         font-family:'DM Mono',monospace;letter-spacing:-1px;line-height:1}}
  .cunt{{font-size:10px;color:#a09880;font-family:'DM Mono',monospace;margin-top:3px}}

  /* Chart panel (replaces grid area) */
  .chart-area{{
    flex:1 1 0;display:flex;flex-direction:column;overflow:hidden;
    padding:10px 14px 8px;
  }}
  .chart-hdr{{
    display:flex;align-items:center;justify-content:space-between;
    margin-bottom:8px;
  }}
  .back-btn{{
    font-size:12px;font-weight:600;color:#7a6e5f;
    background:none;border:none;cursor:pointer;font-family:inherit;padding:0;
  }}
  .back-btn:hover{{color:#1a1614}}
  .chart-title{{font-size:12px;font-weight:600;color:#4a4438}}
  .chart-loc{{font-size:11px;color:#a09880}}
  .chart-val{{
    font-size:28px;font-weight:600;color:#1a1614;
    font-family:'DM Mono',monospace;letter-spacing:-1px;line-height:1;
    margin-bottom:6px;
  }}
  .chart-unit{{font-size:11px;color:#a09880;font-family:'DM Mono',monospace;margin-left:2px}}
  .chart-svg-wrap{{flex:1 1 0;min-height:0}}
  svg{{width:100%;height:100%;overflow:visible;display:block}}
  .time-row{{display:flex;justify-content:space-between;margin-top:4px}}
  .time-lbl{{font-size:9px;color:#b0a898;font-family:'DM Mono',monospace}}

  /* ═══════════════════════════════════════════
     ROW 3 — CHATBOT
  ═══════════════════════════════════════════ */
  .row-chat{{
    display:flex;flex-direction:column;
    background:#f0ede8;
    overflow:hidden;
  }}
  .chat-label{{
    flex:0 0 auto;
    font-size:10px;font-weight:600;letter-spacing:.08em;
    text-transform:uppercase;color:#8a8070;
    padding:10px 14px 0;
  }}
  .chat-body{{
    flex:1 1 0;overflow:hidden;
    padding:8px 14px 6px;
    font-size:13px;line-height:1.6;color:#2a2218;
    /* clamp to 3 lines so it doesn't overflow */
    display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;
    overflow:hidden;
  }}
  .chat-form{{
    flex:0 0 auto;
    display:flex;gap:8px;padding:0 14px 12px;
  }}
  .chat-input{{
    flex:1;padding:8px 12px;
    font-size:13px;font-family:'DM Sans',sans-serif;
    color:#1a1614;background:#fff;
    border:1px solid #d0cbc2;border-radius:10px;
    outline:none;
  }}
  .chat-input::placeholder{{color:#a09880}}
  .chat-send{{
    padding:8px 14px;
    font-size:12px;font-weight:600;font-family:'DM Sans',sans-serif;
    background:#3a3028;color:#f0ede8;
    border:none;border-radius:10px;cursor:pointer;white-space:nowrap;
  }}
  .chat-send:hover{{background:#1a1614}}
</style>
</head>
<body>
<div class="shell">

  <!-- ── ROW 1: MAP ── -->
  <div class="row-map">
    <iframe id="map-iframe" scrolling="no" sandbox="allow-scripts allow-same-origin"></iframe>
    <div class="risk-card">
      <div class="rc-name">{county}</div>
      <div class="rc-num">{risk_str}</div>
      <div class="rc-lvl">{level}</div>
    </div>
  </div>

  <!-- ── ROW 2: PICKER + GRID/CHART ── -->
  <div class="row-mid">
    <div class="county-row">
      <select class="county-select" id="csel" onchange="act('county',this.value)">
        {county_options}
      </select>
    </div>

    {"<!-- grid -->" if not metric else ""}
    <div class="grid-area" id="grid-area" style="{'display:none' if metric else ''}">
      {grid_cards}
    </div>

    {"<!-- chart -->" if metric else ""}
    <div class="chart-area" id="chart-area" style="{'display:flex' if metric else 'display:none'}">
      <div class="chart-hdr">
        <button class="back-btn" onclick="act('back','')">← back</button>
        <span class="chart-title">{metric_label}</span>
        <span class="chart-loc">{county}</span>
      </div>
      <div>
        <span class="chart-val">{metric_value}</span>
        <span class="chart-unit">{metric_unit}</span>
      </div>
      <div class="chart-svg-wrap">
        <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none">
          <polygon points="{area_pts}" fill="rgba(122,110,95,0.12)" stroke="none"/>
          <polyline points="{poly}" fill="none" stroke="#7a6e5f" stroke-width="2"
                    stroke-linejoin="round" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="time-row">
        <span class="time-lbl">24h ago</span>
        <span class="time-lbl">12h ago</span>
        <span class="time-lbl">now</span>
      </div>
    </div>
  </div>

  <!-- ── ROW 3: CHAT ── -->
  <div class="row-chat">
    <div class="chat-label">AI Assistant</div>
    <div class="chat-body" id="chat-body">{last_msg}</div>
    <div class="chat-form">
      <input class="chat-input" id="chat-in" type="text"
             placeholder="Ask about conditions, health risks, PPE…"
             onkeydown="if(event.key==='Enter')sendChat()">
      <button class="chat-send" onclick="sendChat()">Ask</button>
    </div>
  </div>

</div>

<script>
  // Navigation bridge: all state changes go through query params → Streamlit rerun
  function act(action, payload) {{
    var url = new URL(window.parent.location.href);
    url.searchParams.set('action',  action);
    url.searchParams.set('payload', payload);
    window.parent.location.href = url.toString();
  }}

  function sendChat() {{
    var inp = document.getElementById('chat-in');
    var msg = inp.value.trim();
    if (!msg) return;
    inp.value = '';
    act('chat', msg);
  }}

  // Load folium map via Blob to avoid srcdoc escaping corruption
  (function() {{
    var mapHtml = {json.dumps(map_html)};
    var blob = new Blob([mapHtml], {{type:'text/html'}});
    document.getElementById('map-iframe').src = URL.createObjectURL(blob);
  }})();
</script>
</body>
</html>"""

# Single components.html call — 100vh = the iframe fills the Streamlit viewport
components.html(html, height=700, scrolling=False)
