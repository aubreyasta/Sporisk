"""
utils/map_builder.py

FIX (map not rendering):
  - _fetch_geojson now catches ALL exceptions (including requests not being
    installed, or the sandbox blocking outbound connections) and returns a
    clear error string instead of raising.
  - build_map always returns a valid folium.Map. If both county AND zip
    GeoJSON fetches fail, the map still renders with the base tile layer
    plus a visible warning marker so the developer can see it's alive.
  - Removed maxBounds / fit_bounds (still absent — they cause zoom resets).
  - Center/zoom still restored from session state.
  - My Location Leaflet control still injected via JS.
"""

from __future__ import annotations
import folium
from folium import GeoJson, GeoJsonTooltip, GeoJsonPopup
import streamlit as st

from utils.risk_colors import risk_index_to_fill, fill_opacity_for_risk
from data.mock_data import (
    get_all_zip_data, get_all_county_data,
    CENTRAL_VALLEY_COUNTIES, _CV_ZIPS_BY_COUNTY,
)

CV_CENTER    = [37.0, -120.0]
DEFAULT_ZOOM = 7
MIN_ZOOM     = 5
MAX_ZOOM     = 14

CA_COUNTIES_URL = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
    "master/public/data/california-counties.geojson"
)
CA_ZCTA_URL = (
    "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/"
    "master/ca_california_zip_codes_geo.min.json"
)

_CV_COUNTY_SET = {c.lower() for c in CENTRAL_VALLEY_COUNTIES}
_CV_ZIP_SET    = {z for zips in _CV_ZIPS_BY_COUNTY.values() for z in zips}

_TOOLTIP_STYLE = (
    "background:rgba(250,248,255,0.97); color:#1a0a2e; "
    "font-family:'IBM Plex Sans',sans-serif; font-size:12px; "
    "border:1px solid #c0a8e0; border-radius:5px; padding:5px 10px; "
    "box-shadow: 0 2px 6px rgba(80,0,160,0.15);"
)

# ── Inject JS for My Location Leaflet control ──────────────────────────────────
_MAP_JS = """
<script>
(function() {
  function initMapExtras() {
    var containers = document.querySelectorAll('.leaflet-container');
    var map = null;
    for (var i = 0; i < containers.length; i++) {
      var id = containers[i]._leaflet_id;
      if (id && window['leaflet_map_' + id]) {
        map = window['leaflet_map_' + id]; break;
      }
    }
    if (!map) {
      for (var k in window) {
        try {
          if (window[k] && typeof window[k].flyTo === 'function' && window[k]._leaflet_id) {
            map = window[k]; break;
          }
        } catch(e) {}
      }
    }
    if (!map) { setTimeout(initMapExtras, 300); return; }
    if (window._cv_map_ready) return;
    window._cv_map_ready = true;
    window.cv_map = map;

    var LocControl = L.Control.extend({
      options: { position: 'topleft' },
      onAdd: function() {
        var c = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        var btn = L.DomUtil.create('a', 'cv-loc-btn', c);
        btn.innerHTML = '&#x1F4CD;';
        btn.title = 'My location';
        btn.href = '#';
        btn.role = 'button';
        L.DomEvent.disableClickPropagation(c);
        L.DomEvent.on(btn, 'click', function(e) {
          L.DomEvent.preventDefault(e);
          if (!navigator.geolocation) { alert('Geolocation not supported.'); return; }
          btn.innerHTML = '&#x23F3;';
          navigator.geolocation.getCurrentPosition(
            function(pos) {
              btn.innerHTML = '&#x1F4CD;';
              map.flyTo([pos.coords.latitude, pos.coords.longitude], 11, {duration: 1.0});
            },
            function(err) {
              btn.innerHTML = '&#x1F4CD;';
              alert('Location error: ' + err.message);
            },
            { timeout: 10000, enableHighAccuracy: false }
          );
        });
        return c;
      }
    });
    new LocControl().addTo(map);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(initMapExtras, 400); });
  } else {
    setTimeout(initMapExtras, 400);
  }
})();
</script>
"""


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_geojson(url: str) -> tuple[dict | None, str | None]:
    """
    Fetch a GeoJSON URL.  Returns (data, None) on success, (None, error_str)
    on any failure — including network sandbox blocks, timeouts, 404s, and
    import errors (requests not installed).
    """
    try:
        import requests  # imported here so missing package gives a clean error
    except ImportError:
        return None, "requests library not installed — run `pip install requests`"

    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 404:
            return None, f"404 — GeoJSON unavailable ({url})"
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as exc:
        # Sandbox / firewall blocks show up as ConnectionError
        return None, f"Network unavailable (blocked or offline): {exc}"
    except requests.exceptions.Timeout:
        return None, "Request timed out (>20 s)."
    except Exception as exc:
        return None, str(exc)


def _filter_cv_counties(geojson: dict) -> dict:
    feats = [
        f for f in geojson.get("features", [])
        if f.get("properties", {}).get("name", "").lower() in _CV_COUNTY_SET
    ]
    return {**geojson, "features": feats}


def _filter_cv_zips(geojson: dict) -> dict:
    feats = []
    for f in geojson.get("features", []):
        props = f.get("properties", {})
        zc = (
            props.get("ZCTA5CE10") or props.get("GEOID10")
            or props.get("zip") or props.get("ZIP_CODE")
            or props.get("zip_code") or ""
        )
        if zc in _CV_ZIP_SET:
            props["zip"] = zc
            feats.append(f)
    return {**geojson, "features": feats}


def _style_county(feature, county_data):
    name = feature["properties"].get("name", "")
    rec  = county_data.get(name)
    risk = rec["risk_index"] if rec else None
    return {
        "fillColor":   risk_index_to_fill(risk),
        "color":       "#7040b0",
        "weight":      1.8,
        "fillOpacity": fill_opacity_for_risk(risk),
        "opacity":     0.9,
    }


def _style_zip(feature, zip_data):
    zc   = feature.get("properties", {}).get("zip", "")
    rec  = zip_data.get(zc)
    risk = rec["risk_index"] if rec else None
    return {
        "fillColor":   risk_index_to_fill(risk),
        "color":       "#9060c8",
        "weight":      0.7,
        "fillOpacity": fill_opacity_for_risk(risk),
        "opacity":     0.85,
    }


def build_map(lod: str = "county") -> folium.Map:
    center = st.session_state.get("map_center", CV_CENTER)
    zoom   = st.session_state.get("map_zoom",   DEFAULT_ZOOM)

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        min_zoom=MIN_ZOOM,
        max_zoom=MAX_ZOOM,
        tiles=None,
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
    )

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        name="Light",
        subdomains="abcd",
        max_zoom=MAX_ZOOM,
    ).add_to(m)

    # My Location control
    m.get_root().html.add_child(folium.Element(_MAP_JS))

    county_data = get_all_county_data()
    zip_data    = get_all_zip_data()

    if lod == "county":
        _add_county_layer(m, county_data)
    else:
        _add_zip_layer(m, zip_data)

    # The map always has the base tile layer, so it always renders.
    return m


def _add_county_layer(m: folium.Map, county_data: dict):
    geojson, err = _fetch_geojson(CA_COUNTIES_URL)
    if err:
        # Show error in Streamlit UI but still return a working map
        st.warning(
            f"⚠️ County borders unavailable — map shows base tiles only. "
            f"({err})",
            icon="🗺️",
        )
        # Render stub circles so the user knows data IS loaded even without shapes
        _render_county_stubs(m, county_data)
        return

    cv = _filter_cv_counties(geojson)
    if not cv["features"]:
        st.warning("⚠️ No Central Valley counties matched in GeoJSON.")
        _render_county_stubs(m, county_data)
        return

    for feat in cv["features"]:
        feat["properties"]["_id"] = feat["properties"].get("name", "")

    GeoJson(
        cv,
        name="Counties",
        style_function=lambda f: _style_county(f, county_data),
        highlight_function=lambda _f: {"weight": 3, "color": "#6020b0", "fillOpacity": 0.72},
        tooltip=GeoJsonTooltip(
            fields=["name"], aliases=["County:"],
            style=_TOOLTIP_STYLE, sticky=True,
        ),
        popup=GeoJsonPopup(fields=["_id"], aliases=[""], labels=False, max_width=200),
    ).add_to(m)


def _add_zip_layer(m: folium.Map, zip_data: dict):
    geojson, err = _fetch_geojson(CA_ZCTA_URL)
    if err:
        st.warning(
            f"⚠️ ZIP boundaries unavailable — showing dev stubs. ({err})",
            icon="🗺️",
        )
        _render_zip_stubs(m, zip_data)
        return

    cv_zips = _filter_cv_zips(geojson)
    if not cv_zips["features"]:
        st.warning("⚠️ No Central Valley ZIPs matched. Falling back to stubs.")
        _render_zip_stubs(m, zip_data)
        return

    _render_zip_geojson(m, cv_zips, zip_data)


def _render_zip_geojson(m: folium.Map, geojson: dict, zip_data: dict):
    for feat in geojson["features"]:
        zc = feat["properties"].get("zip") or feat["properties"].get("ZCTA5CE10") or ""
        feat["properties"]["zip"] = zc
        feat["properties"]["_id"] = zc

    GeoJson(
        geojson,
        name="ZIP Codes",
        style_function=lambda f: _style_zip(f, zip_data),
        highlight_function=lambda _f: {"weight": 2, "color": "#8020d0", "fillOpacity": 0.82},
        tooltip=GeoJsonTooltip(
            fields=["zip"], aliases=["ZIP:"],
            style=_TOOLTIP_STYLE, sticky=True,
        ),
        popup=GeoJsonPopup(fields=["_id"], aliases=[""], labels=False, max_width=200),
    ).add_to(m)


def _render_county_stubs(m: folium.Map, county_data: dict):
    """
    Fallback: render a circle marker per county centroid when
    GeoJSON borders are unavailable.  Clickable popup sends county name.
    """
    _COUNTY_CENTROIDS: dict[str, tuple[float, float]] = {
        "Fresno":      (36.75, -119.77),
        "Kern":        (35.34, -118.73),
        "Kings":       (36.07, -119.82),
        "Madera":      (37.22, -119.77),
        "Merced":      (37.19, -120.72),
        "San Joaquin": (37.93, -121.27),
        "Stanislaus":  (37.56, -120.99),
        "Tulare":      (36.13, -119.16),
        "Sacramento":  (38.57, -121.47),
        "Yolo":        (38.68, -121.90),
    }
    from utils.risk_colors import risk_index_to_fill, fill_opacity_for_risk
    for county, (lat, lon) in _COUNTY_CENTROIDS.items():
        rec  = county_data.get(county, {})
        risk = rec.get("risk_index")
        color = risk_index_to_fill(risk)
        folium.CircleMarker(
            location=[lat, lon],
            radius=18,
            color="#7040b0",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity_for_risk(risk),
            tooltip=f"{county} County",
            popup=folium.Popup(county, max_width=200),
        ).add_to(m)


def _render_zip_stubs(m: folium.Map, zip_data: dict):
    """Dev-only approximate squares when real ZCTA GeoJSON is unavailable."""
    centroids: dict[str, tuple[float, float]] = {
        "93701":(36.745,-119.796),"93702":(36.742,-119.768),"93703":(36.753,-119.746),
        "93704":(36.779,-119.796),"93705":(36.768,-119.821),"93706":(36.717,-119.843),
        "93710":(36.831,-119.771),"93720":(36.877,-119.718),"93721":(36.732,-119.795),
        "93722":(36.780,-119.868),"93725":(36.658,-119.752),"93726":(36.792,-119.768),
        "93727":(36.753,-119.690),"93728":(36.754,-119.817),"93730":(36.897,-119.753),
        "93301":(35.375,-119.018),"93304":(35.341,-119.057),"93305":(35.392,-118.992),
        "93306":(35.395,-118.946),"93307":(35.330,-118.987),"93308":(35.426,-119.059),
        "93309":(35.342,-119.049),"93311":(35.289,-119.084),"93312":(35.422,-119.100),
        "93313":(35.296,-119.037),"93314":(35.420,-119.136),
        "93230":(36.330,-119.643),"93232":(36.260,-119.611),"93234":(36.332,-120.105),
        "93242":(36.431,-119.965),"93245":(36.204,-119.747),
        "93636":(36.968,-120.066),"93637":(36.960,-120.045),"93638":(37.000,-120.059),
        "93643":(37.221,-119.713),"93644":(37.160,-119.647),
        "95340":(37.302,-120.482),"95341":(37.299,-120.484),"95348":(37.272,-120.450),
        "95360":(37.075,-120.706),"95365":(37.385,-120.283),"95374":(37.098,-120.471),
        "95201":(37.948,-121.286),"95202":(37.958,-121.290),"95203":(37.956,-121.310),
        "95204":(37.966,-121.315),"95205":(37.958,-121.261),"95206":(37.930,-121.305),
        "95207":(37.973,-121.336),"95209":(38.003,-121.359),"95210":(38.002,-121.306),
        "95212":(38.024,-121.247),"95215":(37.976,-121.231),"95219":(38.000,-121.417),
        "95240":(38.130,-121.271),"95336":(37.797,-121.196),"95337":(37.762,-121.215),
        "95376":(37.734,-121.440),
        "95350":(37.648,-120.999),"95351":(37.628,-121.010),"95354":(37.634,-120.993),
        "95355":(37.655,-120.960),"95356":(37.680,-121.020),"95357":(37.644,-120.950),
        "95358":(37.605,-121.035),"95361":(37.674,-121.073),"95363":(37.585,-121.128),
        "95380":(37.527,-120.856),
        "93274":(36.206,-119.347),"93277":(36.330,-119.295),"93256":(35.872,-119.408),
        "93257":(35.903,-119.000),"93265":(36.140,-118.948),"93272":(35.964,-119.355),
        "95814":(38.576,-121.494),"95815":(38.589,-121.459),"95816":(38.570,-121.464),
        "95817":(38.548,-121.458),"95818":(38.558,-121.497),"95819":(38.561,-121.440),
        "95820":(38.533,-121.448),"95821":(38.618,-121.381),"95822":(38.519,-121.491),
        "95823":(38.495,-121.449),"95824":(38.523,-121.427),"95825":(38.587,-121.400),
        "95826":(38.555,-121.383),"95827":(38.558,-121.345),"95828":(38.508,-121.400),
        "95831":(38.499,-121.529),"95832":(38.451,-121.498),"95833":(38.614,-121.506),
        "95834":(38.647,-121.512),"95835":(38.678,-121.508),"95838":(38.651,-121.432),
        "95842":(38.678,-121.368),"95843":(38.694,-121.346),"95864":(38.579,-121.380),
        "95616":(38.537,-121.740),"95618":(38.550,-121.694),"95694":(38.648,-121.780),
        "95695":(38.688,-121.780),"95776":(38.677,-121.745),
    }
    d = 0.07
    features = []
    for zc, rec in zip_data.items():
        if zc not in centroids:
            continue
        lat, lon = centroids[zc]
        box = [[lon-d,lat-d],[lon+d,lat-d],[lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]]
        features.append({
            "type": "Feature",
            "properties": {"zip": zc, "_id": zc, "county": rec.get("county","")},
            "geometry": {"type": "Polygon", "coordinates": [box]},
        })
    _render_zip_geojson(m, {"type":"FeatureCollection","features":features}, zip_data)
