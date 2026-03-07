"""
components/map_component.py

FIX — Clear button was broken because st_folium caches last_object_clicked_popup
in its own internal component state and replays it on every rerun, including
the full-app rerun triggered by the Clear button. _handle_click would then see
selected_feature=None (just cleared) and the incoming popup id ≠ None, so it
passed the guard and immediately restored the selection we just cleared.

Fix: info_panel._clear_btn() stores the cleared feature id in
st.session_state['_cv_just_cleared']. _handle_click checks this flag: if the
incoming popup matches the just-cleared id, it skips the restore and deletes
the flag. The flag persists for exactly one rerun — the one where st_folium
replays the stale popup — then is gone.
"""

from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

from utils.map_builder import build_map
from utils.risk_colors import LEGEND_ITEMS
from utils.session import set_selection
from data.mock_data import get_zip_data, get_county_data

try:
    _fragment = st.fragment
except AttributeError:
    def _fragment(func=None, **_kw):
        if func is not None:
            return func
        return lambda f: f


@_fragment
def render_map():
    st.markdown('<div class="map-section">', unsafe_allow_html=True)

    st.markdown('<div class="map-toolbar">', unsafe_allow_html=True)
    lod = st.radio(
        label="lod",
        options=["County", "ZIP Code"],
        horizontal=True,
        label_visibility="collapsed",
        key="lod_radio",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    lod_key = "county" if lod == "County" else "zip"

    st.markdown('<div class="map-frame">', unsafe_allow_html=True)
    m = build_map(lod=lod_key)

    try:
        from streamlit_folium import st_folium

        map_data = st_folium(
            m,
            width="100%",
            height=520,
            key="cv_risk_map",
            returned_objects=["last_object_clicked_popup"],
        )
        _handle_click(map_data, lod_key)

    except ImportError:
        components.html(m._repr_html_(), height=530, scrolling=False)
        st.caption("Install streamlit-folium: `pip install streamlit-folium`")

    st.markdown('</div>', unsafe_allow_html=True)

    legend_html = '<div class="risk-legend">'
    for color, label in LEGEND_ITEMS:
        legend_html += (
            '<div class="legend-item">'
            '<div class="legend-swatch" style="background:' + color + '"></div>'
            '<span>' + label + '</span></div>'
        )
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def _handle_click(map_data: dict | None, lod_key: str):
    if not map_data:
        return
    popup = map_data.get("last_object_clicked_popup")
    if not popup:
        return

    raw_id: str | None = None
    if isinstance(popup, dict):
        raw_id = popup.get("_id") or popup.get("") or next(iter(popup.values()), None)
    elif isinstance(popup, str):
        raw_id = popup.strip()

    if not raw_id:
        return
    raw_id = str(raw_id).strip()

    # ── Guard: ignore stale popup replayed after a Clear ─────────────────────
    # When the Clear button fires, info_panel stores the cleared id here.
    # st_folium replays the same popup on the next rerun; we swallow it once
    # and delete the flag so the user can re-click the same feature afterwards.
    just_cleared = st.session_state.get("_cv_just_cleared")
    if just_cleared is not None and raw_id == just_cleared:
        del st.session_state["_cv_just_cleared"]
        return  # do not restore the selection we just cleared

    # ── Normal guard: same feature already selected ───────────────────────────
    current = st.session_state.get("selected_feature") or {}
    if raw_id == current.get("id"):
        return

    if lod_key == "county":
        data = get_county_data(raw_id)
        if data:
            set_selection("county", raw_id, raw_id, data)
            st.rerun(scope="app")
    else:
        data = get_zip_data(raw_id)
        if data:
            set_selection("zip", raw_id, f"ZIP {raw_id}", data)
            st.rerun(scope="app")
