"""
components/info_panel.py

ROOT CAUSE OF CLEAR BUTTON FAILURE (both modes):
  render_map() is @st.fragment with a fixed key. st_folium caches
  last_object_clicked_popup in its own internal component state. On every
  full-app rerun — including the one triggered by the Clear button —
  the map fragment re-runs, st_folium replays the cached popup, _handle_click
  sees selected_feature=None (just cleared) so the guard `raw_id == current.get('id')`
  does NOT fire, and set_selection() immediately restores the feature we just
  cleared. The Clear button was working; the map was undoing it 1 frame later.

  County mode: restores once → panel re-appears (looks like "does nothing").
  ZIP mode: restores → clears → restores → loop (the st_folium popup keeps
  replaying because the ZIP rerun path calls st.rerun(scope='app') again).

FIX:
  _clear_btn() stores the cleared feature id in st.session_state['_cv_just_cleared'].
  map_component._handle_click() checks this flag before calling set_selection()
  and skips (+ deletes the flag) when the incoming popup matches the cleared id.
  This requires a matching change in map_component.py.

  The two-rerun pending-clear dance is also removed — it's no longer needed
  because the real problem was the map restoring state, not the rerun loop.
  Now: button click → clear state + set _cv_just_cleared → st.rerun() once → done.
"""

from __future__ import annotations
import streamlit as st
from datetime import datetime

from utils.risk_colors import risk_index_to_level
from utils.session import clear_selection

# ── Per-level Aqua bar themes ─────────────────────────────────────────────────
_BAR_THEMES = {
    "risk-none": {
        "bg":           "linear-gradient(180deg,#237a4a 0%,#1a5c38 40%,#164d30 100%)",
        "gloss_top":    "rgba(255,255,255,0.22)",
        "bt":           "#2e9458",
        "bb":           "#0c3020",
        "text":         "#c8ffe0",
        "sub":          "rgba(180,255,210,0.70)",
        "badge_bg":     "linear-gradient(180deg,#44d878 0%,#1e9848 40%,#126830 100%)",
        "badge_border": "#0a4820",
        "dot":          "#98ffbe",
        "dot_glow":     "rgba(80,255,140,0.7)",
    },
    "risk-low": {
        "bg":           "linear-gradient(180deg,#268a50 0%,#1c6a3c 40%,#185830 100%)",
        "gloss_top":    "rgba(255,255,255,0.18)",
        "bt":           "#34b060",
        "bb":           "#0c3818",
        "text":         "#b8ffd0",
        "sub":          "rgba(160,255,192,0.70)",
        "badge_bg":     "linear-gradient(180deg,#4adc80 0%,#26a855 40%,#167840 100%)",
        "badge_border": "#0c4018",
        "dot":          "#88ffb0",
        "dot_glow":     "rgba(60,255,120,0.7)",
    },
    "risk-moderate": {
        "bg":           "linear-gradient(180deg,#926000 0%,#744c00 40%,#603e00 100%)",
        "gloss_top":    "rgba(255,230,120,0.18)",
        "bt":           "#c07800",
        "bb":           "#381e00",
        "text":         "#ffe090",
        "sub":          "rgba(255,218,120,0.70)",
        "badge_bg":     "linear-gradient(180deg,#f4ac24 0%,#c47c00 40%,#905a00 100%)",
        "badge_border": "#583000",
        "dot":          "#ffd860",
        "dot_glow":     "rgba(255,200,40,0.7)",
    },
    "risk-high": {
        "bg":           "linear-gradient(180deg,#922222 0%,#741a1a 40%,#601414 100%)",
        "gloss_top":    "rgba(255,200,200,0.16)",
        "bt":           "#c03434",
        "bb":           "#380808",
        "text":         "#ffd0d0",
        "sub":          "rgba(255,200,200,0.70)",
        "badge_bg":     "linear-gradient(180deg,#f45454 0%,#c42a2a 40%,#941818 100%)",
        "badge_border": "#580a0a",
        "dot":          "#ffaaaa",
        "dot_glow":     "rgba(255,80,80,0.7)",
    },
    "risk-critical": {
        "bg":           "linear-gradient(180deg,#6e0018 0%,#52000e 40%,#400008 100%)",
        "gloss_top":    "rgba(255,170,190,0.15)",
        "bt":           "#980028",
        "bb":           "#260006",
        "text":         "#ffc0d0",
        "sub":          "rgba(255,180,200,0.70)",
        "badge_bg":     "linear-gradient(180deg,#e43464 0%,#b41232 40%,#840018 100%)",
        "badge_border": "#480010",
        "dot":          "#ff88aa",
        "dot_glow":     "rgba(255,60,100,0.7)",
    },
}

_CLEAR_BTN_CSS = """<style>
[data-testid="stButton"] {
    display: flex !important;
    justify-content: center !important;
    padding-top: 16px !important;
    background: transparent !important;
}
[data-testid="stBaseButton-primary"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 6px 36px !important;
    border-radius: 99px !important;
    border: 1px solid #4a0e98 !important;
    cursor: pointer !important;
    width: auto !important;
    min-width: 130px !important;
    min-height: unset !important;
    position: relative !important;
    overflow: hidden !important;
    background: linear-gradient(180deg,#d090ff 0%,#9840e8 22%,#6818c0 52%,#7828d0 74%,#c078f8 100%) !important;
    background-color: transparent !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.60),
        inset 0 -1px 0 rgba(30,0,80,0.35),
        0 2px 8px rgba(80,0,180,0.50) !important;
    transition: filter 0.12s, box-shadow 0.12s !important;
}
[data-testid="stBaseButton-primary"]::before {
    content: "" !important;
    position: absolute !important;
    inset: 0 0 50% 0 !important;
    background: linear-gradient(180deg,rgba(255,255,255,0.40) 0%,rgba(255,255,255,0.00) 100%) !important;
    border-radius: 99px 99px 0 0 !important;
    pointer-events: none !important;
    z-index: 1 !important;
}
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span,
[data-testid="stBaseButton-primary"] div {
    color: #ffffff !important;
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    text-shadow: 0 -1px 0 rgba(30,0,80,0.45) !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
    position: relative !important;
    z-index: 2 !important;
}
[data-testid="stBaseButton-primary"]:hover {
    filter: brightness(1.15) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.65),
        inset 0 -1px 0 rgba(30,0,80,0.40),
        0 4px 14px rgba(80,0,180,0.65) !important;
}
[data-testid="stBaseButton-primary"]:active {
    filter: brightness(0.87) !important;
}
</style>"""


def render_info_panel():
    st.markdown(_CLEAR_BTN_CSS, unsafe_allow_html=True)

    sel = st.session_state.get("selected_feature")
    _render_status_bar(sel)

    st.markdown('<div class="info-section">', unsafe_allow_html=True)
    if sel is None:
        _render_empty()
    elif sel["type"] == "zip":
        _render_zip(sel["id"], sel["data"])
    elif sel["type"] == "county":
        _render_county(sel["name"], sel["data"])
    st.markdown('</div>', unsafe_allow_html=True)


# ── Status bar ────────────────────────────────────────────────────────────────

def _render_status_bar(sel):
    if sel is None:
        st.markdown(
            '<div class="status-bar status-bar-empty">'
            '<span class="status-bar-hint">'
            'Click a county or ZIP on the map to view risk data'
            '</span></div>',
            unsafe_allow_html=True,
        )
        return

    data     = sel["data"]
    risk     = data.get("risk_index")
    level    = risk_index_to_level(risk)
    risk_str = str(round(risk, 1)) if risk is not None else "N/A"

    t            = _BAR_THEMES.get(level.css_class, _BAR_THEMES["risk-none"])
    bg           = t["bg"]
    gloss_top    = t["gloss_top"]
    bt           = t["bt"]
    bb           = t["bb"]
    text_col     = t["text"]
    sub_col      = t["sub"]
    badge_bg     = t["badge_bg"]
    badge_border = t["badge_border"]
    dot          = t["dot"]
    dot_glow     = t["dot_glow"]

    if sel["type"] == "zip":
        area_name = "ZIP " + sel["id"]
        sub_label = data.get("county", "\u2014") + " County"
        tag_text  = "ZIP"
    else:
        area_name = sel["name"] + " County"
        sub_label = "avg of " + str(data.get("zip_count", "?")) + " ZIPs"
        tag_text  = "COUNTY"

    risk_label = "Risk\u00a0" + risk_str + "\u00a0\u00b7\u00a0" + level.label

    html = (
        '<div style="'
            'display:flex;align-items:center;justify-content:space-between;'
            'flex-wrap:wrap;gap:8px;padding:0 18px;min-height:54px;'
            'background:' + bg + ';'
            'border-top:1px solid ' + bt + ';'
            'border-bottom:1px solid ' + bb + ';'
            'box-shadow:'
                'inset 0 1px 0 ' + gloss_top + ','
                'inset 0 -2px 0 rgba(0,0,0,0.30),'
                '0 2px 10px rgba(0,0,0,0.32);'
            'position:relative;overflow:hidden;">'
        '<div style="'
            'position:absolute;top:0;left:0;right:0;height:46%;'
            'background:linear-gradient(180deg,' + gloss_top + ',rgba(255,255,255,0));'
            'pointer-events:none;"></div>'
        '<div style="'
            'position:absolute;bottom:0;left:0;right:0;height:1px;'
            'background:linear-gradient(90deg,transparent,rgba(255,255,255,0.18),transparent);'
            'pointer-events:none;"></div>'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;position:relative;z-index:1;">'
        '<span style="'
            'font-family:\'IBM Plex Sans\',sans-serif;'
            'font-size:15px;font-weight:600;letter-spacing:0.01em;'
            'color:' + text_col + ';'
            'text-shadow:0 1px 3px rgba(0,0,0,0.50),0 -1px 0 rgba(255,255,255,0.08);">'
            + area_name +
        '</span>'
        '<span style="'
            'display:inline-flex;align-items:center;'
            'padding:2px 10px;border-radius:99px;'
            'background:rgba(255,255,255,0.16);'
            'border:1px solid rgba(255,255,255,0.30);'
            'box-shadow:inset 0 1px 0 rgba(255,255,255,0.28),inset 0 -1px 0 rgba(0,0,0,0.14);'
            'font-family:\'DM Mono\',monospace;font-size:9px;'
            'letter-spacing:0.12em;text-transform:uppercase;'
            'color:' + text_col + ';opacity:0.92;'
            'text-shadow:0 1px 1px rgba(0,0,0,0.30);">'
            + tag_text +
        '</span>'
        '<span style="'
            'font-family:\'DM Mono\',monospace;font-size:10px;'
            'color:' + sub_col + ';'
            'text-shadow:0 1px 1px rgba(0,0,0,0.25);">'
            + sub_label +
        '</span>'
        '</div>'
        '<div style="display:flex;align-items:center;flex-shrink:0;position:relative;z-index:1;">'
        '<span style="'
            'display:inline-flex;align-items:center;gap:7px;'
            'padding:5px 16px;border-radius:99px;'
            'background:' + badge_bg + ';'
            'border:1px solid ' + badge_border + ';'
            'box-shadow:'
                'inset 0 1px 0 rgba(255,255,255,0.35),'
                'inset 0 -1px 0 rgba(0,0,0,0.30),'
                '0 2px 8px rgba(0,0,0,0.40);'
            'font-family:\'IBM Plex Sans\',sans-serif;'
            'font-size:11px;font-weight:600;'
            'letter-spacing:0.05em;text-transform:uppercase;'
            'color:' + text_col + ';'
            'text-shadow:0 -1px 0 rgba(0,0,0,0.40);'
            'position:relative;overflow:hidden;">'
        '<span style="'
            'position:absolute;top:0;left:0;right:0;height:50%;'
            'background:linear-gradient(180deg,rgba(255,255,255,0.30),rgba(255,255,255,0));'
            'border-radius:99px 99px 0 0;pointer-events:none;"></span>'
        '<span style="'
            'width:7px;height:7px;border-radius:50%;flex-shrink:0;'
            'background:' + dot + ';'
            'box-shadow:0 0 7px ' + dot_glow + ';'
            'position:relative;"></span>'
        '<span style="position:relative;">' + risk_label + '</span>'
        '</span>'
        '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


# ── Empty state ───────────────────────────────────────────────────────────────

def _render_empty():
    st.markdown(
        '<div class="info-panel"><div class="info-empty">'
        '<div class="info-empty-icon">🗺️</div>'
        '<div class="info-empty-text">'
        'Click a county or ZIP code on the map<br>to view detailed risk data here.'
        '</div></div></div>',
        unsafe_allow_html=True,
    )


# ── ZIP detail ────────────────────────────────────────────────────────────────

def _render_zip(zip_code: str, data: dict):
    risk = data.get("risk_index")
    st.markdown('<div class="info-panel"><div class="info-panel-body">', unsafe_allow_html=True)
    _metric_grid(data)
    st.markdown("---", unsafe_allow_html=True)
    _table({
        "ZIP Code":            zip_code,
        "County":              data.get("county", "\u2014"),
        "Risk Index":          (str(round(risk, 1)) + " / 100") if risk is not None else "N/A",
        "Precipitation (24h)": str(data.get("precipitation", "N/A")) + " mm",
        "Soil Moisture":       (str(round(data["soil_moisture"] * 100, 1)) + " %") if data.get("soil_moisture") is not None else "N/A",
        "Wind Speed (10m)":    str(data.get("wind_speed", "N/A")) + " m/s",
        "PM2.5":               str(data.get("pm25", "N/A")) + " \u00b5g/m\u00b3",
        "PM10":                str(data.get("pm10", "N/A")) + " \u00b5g/m\u00b3",
        "Last Updated":        _fmt_time(data.get("updated_at")),
    })
    st.markdown('</div></div>', unsafe_allow_html=True)
    _clear_btn()


# ── County detail ─────────────────────────────────────────────────────────────

def _render_county(county_name: str, data: dict):
    risk = data.get("risk_index")
    st.markdown('<div class="info-panel"><div class="info-panel-body">', unsafe_allow_html=True)
    _metric_grid(data, county_avg=True)
    st.markdown("---", unsafe_allow_html=True)
    _table({
        "County":              county_name,
        "ZIP Codes Averaged":  str(data.get("zip_count", "?")),
        "Avg Risk Index":      (str(round(risk, 1)) + " / 100") if risk is not None else "N/A",
        "Avg Precipitation":   str(data.get("precipitation", "N/A")) + " mm",
        "Avg Soil Moisture":   (str(round(data["soil_moisture"] * 100, 1)) + " %") if data.get("soil_moisture") is not None else "N/A",
        "Avg Wind Speed":      str(data.get("wind_speed", "N/A")) + " m/s",
        "Avg PM2.5":           str(data.get("pm25", "N/A")) + " \u00b5g/m\u00b3",
        "Avg PM10":            str(data.get("pm10", "N/A")) + " \u00b5g/m\u00b3",
        "Last Updated":        _fmt_time(data.get("updated_at")),
    })
    st.markdown('</div></div>', unsafe_allow_html=True)
    _clear_btn()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _metric_grid(data: dict, county_avg: bool = False):
    sub    = "county avg" if county_avg else ""
    risk   = data.get("risk_index")
    sm     = data.get("soil_moisture")
    sm_pct = round(sm * 100, 1) if sm is not None else None

    def _v(val):
        return (str(round(val, 1)) if isinstance(val, float) else str(val)) if val is not None else "N/A"

    cards = [
        ("PRECIP",     _v(data.get("precipitation")), "mm",    "#3ab8f0"),
        ("SOIL MOIST", _v(sm_pct),                    "%",     "#7dd4f8"),
        ("WIND",       _v(data.get("wind_speed")),    "m/s",   "#b088f8"),
        ("PM2.5",      _v(data.get("pm25")),          "\u00b5g/m\u00b3", "#f87171"),
        ("PM10",       _v(data.get("pm10")),          "\u00b5g/m\u00b3", "#fb923c"),
        ("RISK",       _v(risk),                      "/ 100", "#fbbf24"),
    ]
    parts = ['<div class="metrics-grid">']
    for label, val, unit, accent in cards:
        sub_html = '<div class="metric-sub">' + sub + '</div>' if sub else ""
        parts.append(
            '<div class="metric-card" style="--metric-accent:' + accent + '">'
            '<div class="metric-label">' + label + '</div>'
            '<div style="line-height:1">'
            '<span class="metric-value">' + val + '</span>'
            '<span class="metric-unit">' + unit + '</span>'
            '</div>' + sub_html + '</div>'
        )
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def _clear_btn():
    """
    On click: record the feature id we're clearing in _cv_just_cleared so
    map_component._handle_click() can ignore the stale popup that st_folium
    will replay on the next rerun. Then clear state and rerun once.
    """
    clicked = st.button(
        "\u2715  Clear selection",
        key="cv_clear_btn",
        type="primary",
        use_container_width=False,
    )
    if clicked:
        # Grab the id BEFORE clearing so _handle_click can filter it out
        sel = st.session_state.get("selected_feature")
        if sel:
            st.session_state["_cv_just_cleared"] = sel["id"]
        clear_selection()
        st.rerun()


def _table(rows: dict) -> None:
    parts = ['<table class="data-table"><tbody>']
    for label, value in rows.items():
        parts.append("<tr><td>" + label + "</td><td>" + value + "</td></tr>")
    parts.append("</tbody></table>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def _fmt_time(iso_str) -> str:
    if not iso_str:
        return "\u2014"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(iso_str)
