from __future__ import annotations
import random
from datetime import datetime, timezone

CENTRAL_VALLEY_COUNTIES = [
    "Fresno", "Kern", "Kings", "Madera", "Merced",
    "San Joaquin", "Stanislaus", "Tulare",
    "Sacramento", "Yolo", "Sutter", "Yuba",
    "Colusa", "Glenn", "Tehama", "Butte", "Shasta",
]

def _record(name: str) -> dict:
    r = random.Random(hash(name) % 2**32)
    return {
        "county":        name,
        "risk_index":    round(r.uniform(0, 100), 1),
        "precipitation": round(r.uniform(0, 40), 2),
        "soil_moisture": round(r.uniform(0.05, 0.45), 3),
        "wind_speed":    round(r.uniform(0.5, 18), 2),
        "pm10":          round(r.uniform(5, 150), 1),
        "updated_at":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

def get_county_data(name: str) -> dict | None:
    return _record(name) if name in CENTRAL_VALLEY_COUNTIES else None

def get_all_county_data() -> dict[str, dict]:
    return {c: _record(c) for c in CENTRAL_VALLEY_COUNTIES}
