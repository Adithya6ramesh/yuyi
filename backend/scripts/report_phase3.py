"""
Phase 3 report: accuracy numbers, breakdowns, safety cushion and back-test,
on the real January 2026 data.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe scripts\\report_phase3.py
"""

import sys
from pathlib import Path

import pandas as pd

# Let this script import our "app" package (it lives one folder up, in backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.cushion import (  # noqa: E402
    BACKTEST_SPLIT,
    CONFIDENCE_LEVELS,
    back_test,
    learn_one_size,
    learn_per_group,
)
from app.core.matching import build_comparison, build_decision_day_comparison  # noqa: E402
from app.core.metrics import breakdowns, horizon_curve, summary  # noqa: E402
from app.data.settings import ACTUALS_FILE, FORECASTS_FILE  # noqa: E402

BREAKDOWN_HOURS_AHEAD = 24      # the app's default slider value
BACKTEST_HOURS_AHEAD = [0, 12, 24, 43]

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)


def heading(text):
    print("\n" + "=" * 78 + "\n" + text + "\n" + "=" * 78)


def mw(value):
    return f"{value:,.0f} MW"


def print_summary(name, s):
    print(f"\n{name}  ({s['hours_counted']} hours, average real lead {s['average_lead_time_h']:.1f}h)")
    print(f"  average miss      {mw(s['average_miss_mw'])}")
    print(f"  typical miss      {mw(s['typical_miss_mw'])}   (median)")
    print(f"  bad-hour miss     {mw(s['bad_hour_miss_mw'])}   (1 hour in 10 is worse)")
    print(f"  worst shortfall   {mw(s['worst_shortfall_mw'])} at {s['worst_shortfall_time']:%d %b %H:%M}"
          "   (less wind than forecast)")
    print(f"  worst overshoot   {mw(s['worst_overshoot_mw'])} at {s['worst_overshoot_time']:%d %b %H:%M}"
          "   (more wind than forecast)")
    print(f"  lean              {mw(s['lean_mw'])}   (forecast too high in "
          f"{s['pct_hours_too_high']:.0f}% of hours)")
    print(f"  wobble            {mw(s['wobble_mw'])}")
    print(f"  overall miss      {mw(s['overall_miss_mw'])}   -> {s['lean_share_pct']:.0f}% lean, "
          f"{100 - s['lean_share_pct']:.0f}% wobble")


def rounded(table):
    return table.astype(float).round(0).astype(int).to_string()


def main():
    actuals = pd.read_parquet(ACTUALS_FILE)
    forecasts = pd.read_parquet(FORECASTS_FILE)
    decision_day = build_decision_day_comparison(actuals, forecasts)
    by_hours = {h: build_comparison(actuals, forecasts, h) for h in BACKTEST_HOURS_AHEAD}

    heading("1. HEADLINE ACCURACY (all of January)")
    print_summary("H = 0 (newest forecast before the hour)", summary(by_hours[0]))
    print_summary("H = 24", summary(by_hours[24]))
    print_summary("Decision Day (09:50 the day before)", summary(decision_day))

    heading("2. HORIZON CURVE: miss vs hours ahead")
    curve = horizon_curve(actuals, forecasts).set_index("hours_ahead")
    print(curve.round(1).to_string())

    heading(f"3. BREAKDOWNS (H = {BREAKDOWN_HOURS_AHEAD})")
    parts = breakdowns(build_comparison(actuals, forecasts, BREAKDOWN_HOURS_AHEAD))
    print("\nBy time of day (3-hour blocks, UTC = UK time in January):")
    print(rounded(parts["time_of_day"]))
    low, high = parts["thresholds"]
    print(f"\nBy wind level, grouped by FORECAST: low < {mw(low)} <= medium < {mw(high)} <= high")
    print(rounded(parts["wind_level"]))

    heading("4. SAFETY CUSHION learned from all of January (H = 24 and Decision Day)")
    for name, table in [("H = 24", by_hours[24]), ("Decision Day", decision_day)]:
        print(f"\n{name}:")
        for c in CONFIDENCE_LEVELS:
            band = learn_one_size(table, c)
            groups = learn_per_group(table, c)["bands"]
            per_group = ", ".join(f"{k} {mw(b['cushion_mw'])}" for k, b in groups.items())
            print(f"  C={c}%: one-size cushion {mw(band['cushion_mw'])} "
                  f"(range forecast {band['lower_mw']:+,.0f} to {band['upper_mw']:+,.0f})"
                  f" | per-group: {per_group}")

    heading(f"5. BACK-TEST: learn 1-24 Jan, test {BACKTEST_SPLIT[-2:]}-31 Jan (never seen)")
    cases = [(f"H={h}", by_hours[h]) for h in BACKTEST_HOURS_AHEAD]
    cases.append(("DecisionDay", decision_day))
    print(f"{'mode':<12}{'C':>4} | {'one-size inside':>15} {'below':>6} {'cushion':>9} | "
          f"{'per-group inside':>16} {'below':>6} {'cushion':>9} | {'below raw fc':>12}")
    print("-" * 100)
    for name, table in cases:
        for c in CONFIDENCE_LEVELS:
            r = back_test(table, c)
            o, g = r["one_size"], r["per_group"]
            print(f"{name:<12}{c:>4} | {o['pct_inside']:>14.1f}% {o['pct_below_range']:>5.1f}% "
                  f"{o['average_cushion_mw']:>9,.0f} | {g['pct_inside']:>15.1f}% "
                  f"{g['pct_below_range']:>5.1f}% {g['average_cushion_mw']:>9,.0f} | "
                  f"{o['pct_below_raw']:>11.1f}%")
    r = back_test(decision_day, 90)
    print(f"\n(learned from {r['train_hours']} hours, tested on {r['test_hours']} hours; "
          f"'below' = actual came in under the range, the costly side)")

    heading("6. WAS THE TEST WEEK DIFFERENT? (Decision Day)")
    train = decision_day[decision_day["start_time"] < pd.Timestamp(BACKTEST_SPLIT, tz="UTC")]
    test = decision_day[(decision_day["start_time"] >= pd.Timestamp(BACKTEST_SPLIT, tz="UTC"))
                        & (decision_day["start_time"] < pd.Timestamp("2026-02-01", tz="UTC"))]
    for name, part in [("learning 1-24 Jan", train), ("test 25-31 Jan", test)]:
        s = summary(part)
        print(f"  {name:<18} average actual {mw(part['actual_mw'].mean()):>10}, "
              f"average forecast {mw(part['forecast_mw'].mean()):>10}, "
              f"lean {mw(s['lean_mw']):>10}, wobble {mw(s['wobble_mw']):>9}")


if __name__ == "__main__":
    main()
