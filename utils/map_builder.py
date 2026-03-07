from __future__ import annotations
import folium
from folium import GeoJson
import streamlit as st
from utils.risk_colors import risk_fill, risk_fill_opacity
from data.mock_data import get_all_county_data, CENTRAL_VALLEY_COUNTIES

CENTROIDS: dict[str, list[float]] = {
    "Fresno":      [36.75, -119.77],
    "Kern":        [35.34, -118.73],
    "Kings":       [36.07, -119.82],
    "Madera":      [37.22, -119.77],
    "Merced":      [37.19, -120.72],
    "San Joaquin": [37.93, -121.27],
    "Stanislaus":  [37.56, -120.99],
    "Tulare":      [36.13, -119.16],
    "Sacramento":  [38.57, -121.47],
    "Yolo":        [38.68, -121.90],
    "Sutter":      [39.03, -121.69],
    "Yuba":        [39.26, -121.44],
    "Colusa":      [39.18, -122.24],
    "Glenn":       [39.60, -122.39],
    "Tehama":      [40.13, -122.23],
    "Butte":       [39.67, -121.60],
    "Shasta":      [40.76, -121.97],
}

CV_CENTER = [37.5, -121.5]
_CV_SET   = {c.lower() for c in CENTRAL_VALLEY_COUNTIES}

GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
    "master/public/data/california-counties.geojson"
)
CA_COUNTIES_URL = GEOJSON_URL  # alias used by geo.py


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_geojson(url: str):
    try:
        import requests
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def build_map(active_county: str | None = None) -> folium.Map:
    center = CENTROIDS.get(active_county, CV_CENTER) if active_county else CV_CENTER
    zoom   = 8 if active_county else 6

    m = folium.Map(
        location=center, zoom_start=zoom,
        min_zoom=6, max_zoom=9,
        tiles=None,
        zoom_control=False, scrollWheelZoom=False,
        dragging=False, doubleClickZoom=False,
        touchZoom=False, keyboard=False,
        attributionControl=False,
    )
    folium.TileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="&copy; OSM &copy; CARTO",
        subdomains="abcd", max_zoom=9,
    ).add_to(m)

    county_data = get_all_county_data()
    geojson, err = _fetch_geojson(GEOJSON_URL)

    if geojson:
        feats = [f for f in geojson.get("features", [])
                 if f.get("properties", {}).get("name", "").lower() in _CV_SET]
        filtered = {**geojson, "features": feats}

        def style_fn(feature):
            name = feature["properties"].get("name", "")
            rec  = county_data.get(name, {})
            risk = rec.get("risk_index")
            if name == active_county:
                return {"fillColor": risk_fill(risk), "color": "#3d2860",
                        "weight": 2.5, "fillOpacity": max(0.55, risk_fill_opacity(risk)), "opacity": 1.0}
            return {"fillColor": risk_fill(risk), "color": "#9080b8",
                    "weight": 0.6, "fillOpacity": 0.07, "opacity": 0.12}

        GeoJson(filtered, style_function=style_fn).add_to(m)
    else:
        # Circle fallback
        for name, centroid in CENTROIDS.items():
            rec  = county_data.get(name, {})
            risk = rec.get("risk_index")
            folium.CircleMarker(
                location=centroid,
                radius=20 if name == active_county else 12,
                color="#3d2860" if name == active_county else "#9080b8",
                weight=2.5 if name == active_county else 0.8,
                fill=True,
                fill_color=risk_fill(risk),
                fill_opacity=risk_fill_opacity(risk) if name == active_county else 0.07,
            ).add_to(m)

    return m

_fetch = _fetch_geojson  # backwards compat alias
