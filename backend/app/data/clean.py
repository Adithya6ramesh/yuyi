"""
Step 2 of the data pipeline: CLEAN the raw downloads and SAVE them.

Run from the backend/ folder (after app.data.fetch):
    .venv\\Scripts\\python.exe -m app.data.clean

What it does:
  1. Reads every raw JSON file from backend/data/raw/
  2. Keeps only the columns we need, with clear names
  3. Makes every time a proper UTC timestamp
  4. Removes exact duplicate rows (and counts them)
  5. Sorts by time
  6. Saves the result as Parquet files in backend/data/processed/
  7. Runs the quality checks and writes quality_report.json

IMPORTANT: every forecast version (every publish_time) is kept. Phase 2 needs all of
them to pick the forecast that was really available at decision time.
"""

import json

import pandas as pd

from app.data.quality import build_report, print_summary
from app.data.settings import (
    ACTUALS_FILE,
    FORECASTS_FILE,
    PROCESSED_DIR,
    QUALITY_REPORT_FILE,
    RAW_ACTUALS_DIR,
    RAW_FORECASTS_DIR,
)


def load_raw(folder):
    """Read all the raw JSON files in a folder into one table."""
    files = sorted(folder.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No raw files in {folder}. Run: python -m app.data.fetch")
    rows = []
    for path in files:
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    return pd.DataFrame(rows)


def to_utc(values):
    """
    Turn time text like "2026-01-13T00:00:00Z" into real UTC timestamps.
    Times written with another offset (e.g. "+01:00") are converted to UTC too.
    """
    return pd.to_datetime(values, utc=True)


def remove_duplicates(table):
    """Drop rows that are identical in every column. Returns (table, how many removed)."""
    before = len(table)
    table = table.drop_duplicates()
    return table, before - len(table)


def clean_actuals(raw):
    """
    Raw FUELHH rows -> table with columns: start_time, generation_mw.
    Returns (clean table, small dict of numbers for the quality report).
    """
    wind = raw[raw["fuelType"] == "WIND"]  # the download asks for wind only; double-check
    table = pd.DataFrame(
        {
            "start_time": to_utc(wind["startTime"]),
            # errors="coerce": anything that isn't a number becomes empty, so the
            # quality check can find it instead of the script crashing.
            "generation_mw": pd.to_numeric(wind["generation"], errors="coerce"),
        }
    )
    table, removed = remove_duplicates(table)
    table = table.sort_values("start_time").reset_index(drop=True)
    stats = {
        "raw_rows": len(raw),
        "non_wind_rows_dropped": len(raw) - len(wind),
        "duplicates_removed": removed,
        "clean_rows": len(table),
    }
    return table, stats


def clean_forecasts(raw):
    """
    Raw WINDFOR rows -> table with columns: start_time, publish_time, generation_mw.
    ALL versions are kept: the same start_time appears once per forecast that covered it.
    """
    table = pd.DataFrame(
        {
            "start_time": to_utc(raw["startTime"]),
            "publish_time": to_utc(raw["publishTime"]),
            "generation_mw": pd.to_numeric(raw["generation"], errors="coerce"),
        }
    )
    table, removed = remove_duplicates(table)
    table = table.sort_values(["start_time", "publish_time"]).reset_index(drop=True)
    stats = {"raw_rows": len(raw), "duplicates_removed": removed, "clean_rows": len(table)}
    return table, stats


def main():
    actuals, actuals_stats = clean_actuals(load_raw(RAW_ACTUALS_DIR))
    forecasts, forecasts_stats = clean_forecasts(load_raw(RAW_FORECASTS_DIR))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    actuals.to_parquet(ACTUALS_FILE, index=False)
    forecasts.to_parquet(FORECASTS_FILE, index=False)
    print(f"Saved {len(actuals)} actual rows   -> {ACTUALS_FILE}")
    print(f"Saved {len(forecasts)} forecast rows -> {FORECASTS_FILE}")

    report = build_report(actuals, forecasts, actuals_stats, forecasts_stats)
    QUALITY_REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_summary(report)
    print(f"\nFull report saved -> {QUALITY_REPORT_FILE}")


if __name__ == "__main__":
    main()
