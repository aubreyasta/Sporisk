"""
Export a static JSON snapshot of every API response the frontend needs.

Run with GEMINI_API_KEY unset so all summaries/insights are the deterministic
rule-based fallback. Output is sorted and timestamp-free so re-running
produces no diff.

Usage:
  cd Backend && python export_static.py
"""
import json
import os
import sys

os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("DATABASE_URL", None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api  # noqa: E402

OUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "src", "data", "snapshot.json"
)


def strip_generated_at(summary: dict) -> dict:
    summary = dict(summary)
    summary.pop("generated_at", None)
    return summary


def build_snapshot() -> dict:
    counties = list(api.COUNTY_META.keys())

    by_county = {}
    for county in counties:
        by_county[county] = {
            "risk": api.get_risk_by_county(county),
            "history": api.get_history(county, start_year=2021, end_year=2026),
            "summary": strip_generated_at(api.get_ai_summary(county)),
            "insights": api.get_historical_insights(county),
            "envHistory": api.get_env_history(county, months=24),
            "reports": api.get_county_reports(county, hours=24),
        }

    return {
        "counties": api.list_counties(),
        "clinics": api.get_all_clinics_endpoint(),
        "vulnerableZones": api.get_all_vulnerable_zones(),
        "byCounty": by_county,
    }


if __name__ == "__main__":
    snapshot = build_snapshot()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUT_PATH}")
