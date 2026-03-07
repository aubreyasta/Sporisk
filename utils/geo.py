"""
utils/geo.py — Point-in-polygon county detection

find_county_for_point(lat, lon) -> str | None

Strategy (in order):
  1. Try shapely + cached GeoJSON (accurate, requires network + shapely).
  2. Fall back to hardcoded county bounding polygons (approximate but
     good enough for the 10 CV counties; no external deps needed).

Returns the matched county name (must be in CENTRAL_VALLEY_COUNTIES),
or None if the point is outside all CV counties.
"""
from __future__ import annotations
from data.mock_data import CENTRAL_VALLEY_COUNTIES

# ── Approximate bounding polygons for each CV county ────────────────
# These are rough convex-hull approximations of the actual county shapes,
# good enough for a point clearly inside a county.
# Replace with real GeoJSON + shapely for production accuracy.
_CV_COUNTY_POLYGONS: dict[str, list[tuple[float, float]]] = {
    # (lat, lon) vertices, counter-clockwise
    "Fresno": [
        (37.58, -120.91), (37.58, -119.58), (37.48, -119.20),
        (36.98, -118.97), (36.49, -118.97), (35.79, -119.57),
        (35.79, -120.91),
    ],
    "Kern": [
        (35.79, -120.05), (35.79, -118.30), (34.89, -118.30),
        (34.89, -119.54), (35.10, -120.05),
    ],
    "Kings": [
        (36.61, -120.35), (36.61, -119.45), (35.79, -119.45),
        (35.79, -120.35),
    ],
    "Madera": [
        (37.58, -120.07), (37.58, -119.20), (36.74, -118.97),
        (36.74, -119.20), (36.98, -119.58), (36.98, -120.07),
    ],
    "Merced": [
        (37.63, -121.25), (37.63, -120.05), (36.98, -120.05),
        (36.98, -120.48), (37.11, -121.25),
    ],
    "San Joaquin": [
        (38.27, -121.58), (38.27, -120.92), (37.71, -120.92),
        (37.46, -121.21), (37.46, -121.58),
    ],
    "Stanislaus": [
        (37.77, -121.22), (37.77, -120.42), (37.18, -120.42),
        (37.18, -120.73), (37.46, -121.22),
    ],
    "Tulare": [
        (36.74, -119.57), (36.74, -118.35), (35.79, -118.35),
        (35.79, -119.57),
    ],
    "Sacramento": [
        (38.74, -121.85), (38.74, -121.02), (38.25, -121.02),
        (38.25, -121.85),
    ],
    "Yolo": [
        (38.86, -122.41), (38.86, -121.58), (38.27, -121.58),
        (38.27, -122.41),
    ],
}


def _point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    """
    Ray-casting algorithm.
    polygon: list of (lat, lon) vertices.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _find_county_shapely(lat: float, lon: float, geojson: dict) -> str | None:
    """Use shapely for accurate polygon testing."""
    try:
        from shapely.geometry import Point, shape
    except ImportError:
        return None

    pt = Point(lon, lat)  # shapely uses (lon, lat) = (x, y)
    for feat in geojson.get("features", []):
        name = feat.get("properties", {}).get("name", "")
        if name not in CENTRAL_VALLEY_COUNTIES:
            continue
        try:
            if shape(feat["geometry"]).contains(pt):
                return name
        except Exception:
            continue
    return None


_CV_CENTROIDS: dict[str, tuple[float, float]] = {
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


def find_county_for_point(lat: float, lon: float) -> str | None:
    """
    Return the CV county name containing (lat, lon), or None if out of range.

    Strategy:
      1. Try shapely + remote GeoJSON (accurate, needs network + shapely).
      2. Fallback: ray-cast on baked approximate polygons.
         If multiple polygons match (they overlap at edges), pick the one
         whose centroid is closest to the point — this resolves ambiguity
         at county borders cleanly.
      3. If nothing matches, return None (out of range).
    """
    import math

    # Try shapely + cached GeoJSON
    try:
        from utils.map_builder import _fetch_geojson, CA_COUNTIES_URL
        geojson, err = _fetch_geojson(CA_COUNTIES_URL)
        if geojson and not err:
            result = _find_county_shapely(lat, lon, geojson)
            if result is not None:
                return result
    except Exception:
        pass

    # Fallback: ray-casting, then centroid tiebreaker
    matches = [
        county for county, polygon in _CV_COUNTY_POLYGONS.items()
        if _point_in_polygon(lat, lon, polygon)
    ]

    if not matches:
        return None  # out of range

    if len(matches) == 1:
        return matches[0]

    # Multiple matches — pick the closest centroid
    return min(
        matches,
        key=lambda c: math.hypot(
            _CV_CENTROIDS[c][0] - lat,
            _CV_CENTROIDS[c][1] - lon,
        ),
    )
