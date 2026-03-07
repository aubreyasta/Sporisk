"""
utils/location.py — User location provider

Hardcoded for now to Merced County coordinates.
To switch to real browser geolocation, replace get_user_location() with
a components.html() postMessage bridge that writes lat/lon into session_state,
then read from there.
"""
from __future__ import annotations

# ── Swap this out when wiring real geolocation ──────────────────────
_HARDCODED_LAT =  37.3670317917114
_HARDCODED_LON = -120.4232512601139


def get_user_location() -> tuple[float, float]:
    """Return (lat, lon) for the current user."""
    return (_HARDCODED_LAT, _HARDCODED_LON)
