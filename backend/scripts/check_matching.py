"""
Sanity check for the matching rule, on the real January 2026 data.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe scripts\\check_matching.py

For each "hours ahead" value H it prints:
  - hours matched / missing (out of 744 January hours)
  - average miss  = average of |actual - forecast|  (how far off, ignoring direction)
  - average error = average of  actual - forecast   (negative = forecasts too high)
  - average real lead time (always >= H)
We EXPECT the average miss to grow as H grows: older forecasts should be worse.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# Let this script import our "app" package (it lives one folder up, in backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.matching import build_comparison, count_missing, select_forecasts_at_deadline  # noqa: E402
from app.data.settings import ACTUALS_FILE, DECISION_DEADLINE_TIME, FORECASTS_FILE  # noqa: E402

HORIZONS = [0, 3, 6, 12, 24, 36, 43]
EXTRA_HORIZON = 48  # outside the app's slider range: some hours have no forecast this old


def summarise(table):
    matched = table.dropna(subset=["forecast_mw", "actual_mw"])
    missing = count_missing(table)
    return {
        "matched": len(matched),
        "missing": missing["without_forecast"],
        "avg_miss": matched["error_mw"].abs().mean(),
        "avg_error": matched["error_mw"].mean(),
        "avg_lead": matched["lead_time_h"].mean(),
    }


def print_row(label, s, note=""):
    print(f"{label:>10} | {s['matched']:>7} | {s['missing']:>7} | {s['avg_miss']:>9.0f} | "
          f"{s['avg_error']:>+10.0f} | {s['avg_lead']:>8.1f}  {note}")


def decision_day_comparison(actuals, forecasts):
    """
    Decision Day mode over the whole month: decisions on 1-31 Jan, so delivery days
    2 Jan - 1 Feb, each using the forecast available at 09:50 the day before.
    """
    days = [date(2026, 1, 2) + timedelta(days=i) for i in range(31)]
    chosen = pd.concat(select_forecasts_at_deadline(forecasts, day) for day in days)
    actual = actuals.rename(columns={"generation_mw": "actual_mw"})
    table = chosen.merge(actual, on="start_time", how="left")
    table["error_mw"] = table["actual_mw"] - table["forecast_mw"]
    return table


def main():
    actuals = pd.read_parquet(ACTUALS_FILE)
    forecasts = pd.read_parquet(FORECASTS_FILE)

    print("MODE 1: 'H hours ahead' - all 744 on-the-hour times in January 2026")
    print(f"{'H (hours)':>10} | {'matched':>7} | {'missing':>7} | {'avg miss':>9} | "
          f"{'avg error':>10} | {'avg lead':>8}")
    print("-" * 70)

    misses = []
    for hours_ahead in HORIZONS:
        s = summarise(build_comparison(actuals, forecasts, hours_ahead))
        misses.append(s["avg_miss"])
        print_row(hours_ahead, s)
    s = summarise(build_comparison(actuals, forecasts, EXTRA_HORIZON))
    print_row(EXTRA_HORIZON, s, "<- outside slider range, gaps expected")

    print("\nDo misses grow as H grows (within the slider range)?")
    worse = [(HORIZONS[i], HORIZONS[i + 1]) for i in range(len(misses) - 1)
             if misses[i + 1] < misses[i]]
    if not worse:
        print("  YES - every step further ahead has a bigger average miss.")
    else:
        print(f"  NOT ALWAYS - the miss got SMALLER between H = {worse}. Investigate!")

    print(f"\nMODE 2: 'Decision Day' - deadline {DECISION_DEADLINE_TIME:%H:%M} UTC the day before,"
          " delivery 2 Jan - 1 Feb")
    s = summarise(decision_day_comparison(actuals, forecasts))
    print_row("deadline", s, "(lead time varies 14.5h-37.5h across the day)")


if __name__ == "__main__":
    main()
