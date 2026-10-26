"""
ACCURACY NUMBERS - how good were the forecasts?

Everything here works on a "comparison" table from app/core/matching.py, with columns:
    start_time, actual_mw, forecast_mw, publish_time, lead_time_h, error_mw
where error_mw = actual_mw - forecast_mw.

Plain-English names used throughout:
    miss   = |actual - forecast|        how far off, ignoring direction
    lean   = average of (actual - forecast)
             negative -> forecasts run too HIGH (less wind came than expected)
    wobble = how much the error jumps around once the lean is taken out
             (the standard deviation of the error)

A handy fact that ties them together (always exactly true):
    overall_miss^2 = lean^2 + wobble^2
where overall_miss is the "root mean square" error: square every error, average
them, take the square root. It counts big misses more heavily than small ones.
So we can say what share of the problem is the steady lean and what share is wobble.
"""

import numpy as np
import pandas as pd

from app.core.matching import build_comparison

SLIDER_HOURS = range(0, 44)  # 0..43 hours ahead, as decided in Phase 1
WIND_LEVELS = ["low", "medium", "high"]


def complete_rows(comparison):
    """Only hours that have BOTH a forecast and an actual can be scored."""
    return comparison.dropna(subset=["forecast_mw", "actual_mw"])


def summary(comparison):
    """
    The headline accuracy numbers for a comparison table.

    hours_counted          - hours that had both a forecast and an actual.
    average_miss_mw        - on average, how many MW the forecast was off by.
    typical_miss_mw        - the median miss: half the hours missed by less, half by more.
    bad_hour_miss_mw       - the 90th percentile miss: only 1 hour in 10 missed by more.
    worst_shortfall_mw     - the most negative error: the hour with the most LESS wind
                             than forecast (worst_shortfall_time says when).
    worst_overshoot_mw     - the most positive error: the hour with the most MORE wind
                             than forecast (worst_overshoot_time says when).
    lean_mw                - average of (actual - forecast). Negative = forecasts too high.
    pct_hours_too_high     - % of hours where the forecast was higher than the actual.
    wobble_mw              - how much the error jumps around after removing the lean.
    overall_miss_mw        - root-mean-square error (big misses count more).
    lean_share_pct         - % of overall_miss^2 that comes from the lean
                             (the rest, 100 - this, comes from wobble).
    average_lead_time_h    - how old the forecasts really were, on average.
    """
    rows = complete_rows(comparison)
    if rows.empty:
        return {"hours_counted": 0}

    error = rows["error_mw"]
    miss = error.abs()
    lean = error.mean()
    # ddof=0 ("divide by n") so that overall_miss^2 = lean^2 + wobble^2 exactly.
    wobble = error.std(ddof=0)
    overall = np.sqrt((error**2).mean())

    shortfall = rows.loc[error.idxmin()]
    overshoot = rows.loc[error.idxmax()]
    return {
        "hours_counted": int(len(rows)),
        "average_miss_mw": float(miss.mean()),
        "typical_miss_mw": float(miss.median()),
        "bad_hour_miss_mw": float(miss.quantile(0.9)),
        "worst_shortfall_mw": float(shortfall["error_mw"]),
        "worst_shortfall_time": shortfall["start_time"],
        "worst_overshoot_mw": float(overshoot["error_mw"]),
        "worst_overshoot_time": overshoot["start_time"],
        "lean_mw": float(lean),
        "pct_hours_too_high": float((error < 0).mean() * 100),
        "wobble_mw": float(wobble),
        "overall_miss_mw": float(overall),
        "lean_share_pct": float(lean**2 / overall**2 * 100) if overall else 0.0,
        "average_lead_time_h": float(rows["lead_time_h"].mean()),
    }


def horizon_curve(actuals, forecasts, hours_ahead=SLIDER_HOURS):
    """
    The summary for every "hours ahead" value (default 0..43), one row each, so the
    app can draw "miss vs hours ahead" - with lean and wobble as separate lines.
    """
    rows = []
    for h in hours_ahead:
        s = summary(build_comparison(actuals, forecasts, h))
        rows.append(
            {
                "hours_ahead": h,
                "hours_counted": s["hours_counted"],
                "average_miss_mw": s["average_miss_mw"],
                "bad_hour_miss_mw": s["bad_hour_miss_mw"],
                "lean_mw": s["lean_mw"],
                "wobble_mw": s["wobble_mw"],
                "lean_share_pct": s["lean_share_pct"],
                "average_lead_time_h": s["average_lead_time_h"],
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Wind levels - always decided from the FORECAST, never the actual
# ---------------------------------------------------------------------------


def wind_level_thresholds(forecast_mw):
    """
    Split points that divide the given FORECAST values into equal thirds.
    Returns (low_to_medium, medium_to_high) in MW.
    """
    values = pd.Series(forecast_mw).dropna()
    return float(values.quantile(1 / 3)), float(values.quantile(2 / 3))


def assign_wind_level(forecast_mw, thresholds):
    """
    Label each hour low / medium / high using ONLY its forecast.
    (At decision time the actual is unknown, so using it would be cheating.)
        low:    forecast <  low_to_medium
        medium: low_to_medium <= forecast < medium_to_high
        high:   forecast >= medium_to_high
    """
    low_to_medium, medium_to_high = thresholds
    forecast = pd.Series(forecast_mw, dtype=float).reset_index(drop=True)
    # np.select picks the first matching label; it also copes when both split points
    # are equal (then "medium" is simply empty).
    labels = np.select(
        [forecast < low_to_medium, forecast < medium_to_high, forecast.notna()],
        WIND_LEVELS,
        default=None,
    )
    return pd.Series(pd.Categorical(labels, categories=WIND_LEVELS))


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------

BREAKDOWN_COLUMNS = [
    "hours_counted",
    "average_miss_mw",
    "typical_miss_mw",
    "bad_hour_miss_mw",
    "lean_mw",
    "pct_hours_too_high",
    "wobble_mw",
]


def _table_by(rows, groups):
    """Run summary() for each group and put the results in one table."""
    table = {name: summary(group) for name, group in rows.groupby(groups, observed=True)}
    return pd.DataFrame(table).T[BREAKDOWN_COLUMNS]


def breakdowns(comparison, thresholds=None):
    """
    Accuracy split two ways:

    time_of_day - 3-hour blocks ("00-03" ... "21-24"). We use blocks rather than
                  single hours because one hour of the day only has 31 values in
                  January - too few for trustworthy numbers. A block has ~93.
    wind_level  - low / medium / high, grouped by the FORECAST (see assign_wind_level).
                  thresholds: the split points; if not given, the thirds of the
                  forecasts in this table are used. Reported back as 'thresholds'.
    """
    rows = complete_rows(comparison).copy()

    start_hour = rows["start_time"].dt.hour // 3 * 3
    rows["block"] = start_hour.map(lambda h: f"{h:02d}-{h + 3:02d}")

    if thresholds is None:
        thresholds = wind_level_thresholds(rows["forecast_mw"])
    rows["wind_level"] = assign_wind_level(rows["forecast_mw"], thresholds).to_numpy()

    return {
        "time_of_day": _table_by(rows, "block"),
        "wind_level": _table_by(rows, "wind_level"),
        "thresholds": thresholds,
    }
