"""
data/mock_data.py
Stub data — real CV counties, real ZIP codes, no bogus SLO ZIP.
Replace get_all_zip_data() with your backend call when ready.
"""

from __future__ import annotations
import random
from datetime import datetime, timezone

# ── Correct Central Valley counties (removed: Sutter, Colusa, Yuba, Butte, Glenn, Tehama, Shasta)
CENTRAL_VALLEY_COUNTIES = [
    "Fresno", "Kern", "Kings", "Madera",
    "Merced", "San Joaquin", "Stanislaus",
    "Tulare", "Sacramento", "Yolo",
]

# ── Real ZIP codes per county (Census ZCTA / USPS verified) ──────────────────
_CV_ZIPS_BY_COUNTY: dict[str, list[str]] = {
    "Fresno": [
        "93601","93602","93603","93604","93605","93606","93607","93608","93609",
        "93610","93611","93612","93613","93614","93615","93616","93618","93619",
        "93620","93621","93622","93623","93624","93625","93626","93627","93628",
        "93630","93631","93634","93636","93637","93640","93641","93642","93643",
        "93644","93645","93646","93647","93648","93649","93650","93651","93652",
        "93653","93654","93656","93657","93660","93662","93664","93667","93668",
        "93675","93701","93702","93703","93704","93705","93706","93710","93711",
        "93720","93721","93722","93723","93725","93726","93727","93728","93730",
    ],
    "Kern": [
        "93203","93204","93205","93206","93207","93208","93215","93216","93220",
        "93221","93222","93223","93224","93225","93226","93238","93240","93241",
        "93243","93249","93250","93251","93252","93254","93255","93263","93268",
        "93276","93280","93283","93285","93287","93301","93304","93305","93306",
        "93307","93308","93309","93311","93312","93313","93314",
    ],
    "Kings": [
        "93210","93212","93230","93232","93234","93239","93242","93245","93291",
    ],
    "Madera": [
        "93601","93614","93636","93637","93638","93639","93643","93644","93645",
        "93653","93669",
    ],
    "Merced": [
        "95301","95303","95306","95307","95309","95310","95312","95313","95315",
        "95316","95317","95318","95319","95321","95322","95323","95324","95325",
        "95326","95328","95329","95333","95334","95338","95340","95341","95344",
        "95345","95348","95360","95365","95369","95374","95379","95388",
    ],
    "San Joaquin": [
        "95201","95202","95203","95204","95205","95206","95207","95208","95209",
        "95210","95212","95215","95219","95220","95227","95230","95231","95236",
        "95237","95240","95241","95242","95258","95304","95320","95330","95336",
        "95337","95361","95366","95376","95377","95378","95385","95391",
    ],
    "Stanislaus": [
        "95303","95307","95313","95316","95319","95323","95326","95328","95329",
        "95350","95351","95354","95355","95356","95357","95358","95360","95361",
        "95363","95366","95367","95368","95369","95370","95372","95374","95380",
        "95382","95383","95385","95386","95387",
    ],
    "Tulare": [
        "93201","93202","93207","93208","93215","93216","93218","93219","93221",
        "93223","93227","93234","93235","93238","93242","93244","93247","93256",
        "93257","93258","93260","93261","93262","93265","93266","93267","93268",
        "93270","93271","93272","93274","93275","93277","93279","93286",
    ],
    "Sacramento": [
        "95608","95610","95621","95624","95626","95628","95630","95632","95638",
        "95641","95652","95655","95660","95662","95670","95672","95673","95678",
        "95683","95691","95741","95742","95757","95758","95762","95811","95814",
        "95815","95816","95817","95818","95819","95820","95821","95822","95823",
        "95824","95825","95826","95827","95828","95829","95831","95832","95833",
        "95834","95835","95836","95837","95838","95842","95843","95864",
    ],
    "Yolo": [
        "95605","95606","95607","95612","95616","95617","95618","95620","95625",
        "95627","95645","95653","95691","95694","95695","95697","95698","95776",
    ],
}

# Build flat list for iteration
_SAMPLE_ZIPS: list[dict] = [
    {"zip": z, "county": county}
    for county, zips in _CV_ZIPS_BY_COUNTY.items()
    for z in zips
]

_rng = random.Random(42)  # fixed seed → stable mock values


def _random_zip_record(zip_info: dict) -> dict:
    r = random.Random(int(zip_info["zip"]))  # per-ZIP seed so values are stable
    risk = round(r.uniform(0, 100), 1)
    return {
        "zip":           zip_info["zip"],
        "county":        zip_info["county"],
        "risk_index":    risk,
        "precipitation": round(r.uniform(0, 40), 2),
        "soil_moisture": round(r.uniform(0.05, 0.45), 3),
        "wind_speed":    round(r.uniform(0.5, 18), 2),
        "pm25":          round(r.uniform(2, 75), 1),
        "pm10":          round(r.uniform(5, 150), 1),
        "updated_at":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_zip_data() -> dict[str, dict]:
    """ZIP str → record dict. Replace with real backend call."""
    return {z["zip"]: _random_zip_record(z) for z in _SAMPLE_ZIPS}


def get_zip_data(zip_code: str) -> dict | None:
    return get_all_zip_data().get(zip_code)


def get_county_data(county_name: str) -> dict | None:
    all_zips = get_all_zip_data()
    county_zips = [v for v in all_zips.values() if v["county"] == county_name]
    if not county_zips:
        return None

    def _avg(field):
        vals = [z[field] for z in county_zips if z[field] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "county":        county_name,
        "zip_count":     len(county_zips),
        "risk_index":    _avg("risk_index"),
        "precipitation": _avg("precipitation"),
        "soil_moisture": _avg("soil_moisture"),
        "wind_speed":    _avg("wind_speed"),
        "pm25":          _avg("pm25"),
        "pm10":          _avg("pm10"),
        "updated_at":    county_zips[0]["updated_at"],
    }


def get_all_county_data() -> dict[str, dict]:
    result = {}
    for county in CENTRAL_VALLEY_COUNTIES:
        data = get_county_data(county)
        if data:
            result[county] = data
    return result
