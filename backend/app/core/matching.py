"""
THE FORECAST-MATCHING RULE - the heart of the project.

The rule in one sentence:
    For a target hour T and "hours ahead" H, use the MOST RECENT forecast whose
    publish_time is at or before the deadline T - H.

Forecasts published after the deadline are never used, even if they are more
accurate - they did not exist yet when the decision was made. Using them would be
"cheating" (looking into the future).

Two modes:
  1. "H hours ahead"  -> select_forecasts() / build_comparison()
     Every target hour gets its OWN deadline (T - H). Good for asking
     "how accurate are forecasts made H hours ahead?"
  2. "Decision Day"   -> select_forecasts_at_deadline()
     Every hour of the delivery day shares ONE deadline (e.g. 09:50 the day before).
     This is what the buyer really saw when placing day-ahead orders.

Column names used everywhere:
  forecasts: start_time, publish_time, generation_mw   (all versions kept)
  actuals:   start_time, generation_mw                  (every 30 minutes)
All times are UTC.
"""

from datetime import date, datetime, time, timedelta

import pandas as pd

from app.data.settings import DECISION_DEADLINE_TIME, DECISION_MONTH_END, DECISION_MONTH_START

ONE_HOUR = pd.Timedelta(hours=1)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _utc(value):
    """Turn a date/time (text, Timestamp, datetime) into a UTC Timestamp."""
    stamp = pd.Timestamp(value)
    return stamp.tz_localize("UTC") if stamp.tz is None else stamp.tz_convert("UTC")


def _utc_column(values):
    """Make a column of times UTC with one fixed precision, so tables can be joined."""
    return pd.to_datetime(values, utc=True).astype("datetime64[ns, UTC]")


def _newest_forecast_before(forecasts, targets):
    """
    The one place where the rule is applied. Every public function below uses it.

    'targets' is a table with two columns:
        start_time - the hour we want a forecast for
        deadline   - the latest publish_time we are allowed to use for it

    For each target row we look ONLY at forecasts for the same start_time, and pick
    the one with the latest publish_time that is <= deadline.

    We use pandas' merge_asof: for each row it finds the closest EARLIER-OR-EQUAL
    match in the other table. direction="backward" means it can only look back in
    time, never forward; by="start_time" means it only looks at forecasts for the
    same hour. If nothing qualifies, the forecast columns are left empty.
    """
    left = pd.DataFrame(
        {
            "start_time": _utc_column(targets["start_time"]),
            "deadline": _utc_column(targets["deadline"]),
        }
    ).sort_values("deadline")  # merge_asof needs both sides sorted by time

    right = pd.DataFrame(
        {
            "start_time": _utc_column(forecasts["start_time"]),
            "publish_time": _utc_column(forecasts["publish_time"]),
            "forecast_mw": forecasts["generation_mw"].to_numpy(),
        }
    ).sort_values("publish_time")

    chosen = pd.merge_asof(
        left,
        right,
        left_on="deadline",
        right_on="publish_time",
        by="start_time",
        direction="backward",  # only publish_time <= deadline
        allow_exact_matches=True,  # published EXACTLY at the deadline is allowed
    )

    # Safety net: prove that nothing was published after its deadline.
    # If this ever fails, the rule is broken and we must stop immediately.
    cheating = chosen["publish_time"] > chosen["deadline"]
    if cheating.any():
        raise RuntimeError(f"{cheating.sum()} forecasts published after their deadline!")

    chosen["lead_time_h"] = (chosen["start_time"] - chosen["publish_time"]) / ONE_HOUR
    return chosen.sort_values("start_time").reset_index(drop=True)


def _january_hours(start=None, end=None):
    """Every on-the-hour time from start (included) to end (not included)."""
    start = _utc(start or DECISION_MONTH_START)
    end = _utc(end or DECISION_MONTH_END)
    return pd.date_range(start.ceil("h"), end, freq="h", inclusive="left")


# ---------------------------------------------------------------------------
# Mode 1: "H hours ahead"
# ---------------------------------------------------------------------------


def select_forecasts(forecasts, horizon_hours, target_times=None):
    """
    For each target hour, the newest forecast published at least `horizon_hours`
    before it.

    target_times: which hours to answer for. Default: every on-the-hour start_time
                  that appears in the forecasts.

    Returns one row per target hour:
        start_time, forecast_mw, publish_time, lead_time_h
    forecast_mw / publish_time / lead_time_h are EMPTY if no forecast qualifies.
    lead_time_h is the REAL lead time: always >= horizon_hours, usually a bit more,
    because forecasts only come out every 2-4 hours.
    """
    if horizon_hours < 0:
        raise ValueError("horizon_hours must be 0 or more")

    if target_times is None:
        times = _utc_column(forecasts["start_time"])
        target_times = times[times.dt.minute == 0].drop_duplicates()
    target_times = _utc_column(pd.Series(target_times))

    targets = pd.DataFrame(
        {
            "start_time": target_times,
            "deadline": target_times - pd.Timedelta(hours=horizon_hours),
        }
    )
    chosen = _newest_forecast_before(forecasts, targets)
    return chosen[["start_time", "forecast_mw", "publish_time", "lead_time_h"]]


def build_comparison(actuals, forecasts, horizon_hours, start=None, end=None):
    """
    Forecast vs actual, side by side, for every on-the-hour time between start and
    end (default: all of January 2026).

    Returns one row per hour:
        start_time, actual_mw, forecast_mw, publish_time, lead_time_h, error_mw
    error_mw = actual_mw - forecast_mw
        negative -> the forecast was too HIGH (less wind came than expected)
        positive -> the forecast was too LOW
    Hours without a forecast (or actual) keep the row with empty values - we never
    guess. Use count_missing() to see how many.
    """
    hours = _january_hours(start, end)
    chosen = select_forecasts(forecasts, horizon_hours, target_times=hours)

    actual = pd.DataFrame(
        {
            "start_time": _utc_column(actuals["start_time"]),
            "actual_mw": actuals["generation_mw"].to_numpy(),
        }
    )
    # how="left": keep every hour from 'chosen'. Half-hour actuals (:30) have no
    # matching row there, so they simply drop out - we compare on the hour only.
    table = chosen.merge(actual, on="start_time", how="left")
    table["error_mw"] = table["actual_mw"] - table["forecast_mw"]
    return table[
        ["start_time", "actual_mw", "forecast_mw", "publish_time", "lead_time_h", "error_mw"]
    ]


def count_missing(comparison):
    """How many hours in a comparison table have no forecast / no actual."""
    return {
        "hours": int(len(comparison)),
        "without_forecast": int(comparison["forecast_mw"].isna().sum()),
        "without_actual": int(comparison["actual_mw"].isna().sum()),
    }


# ---------------------------------------------------------------------------
# Mode 2: "Decision Day" (one fixed deadline the day before)
# ---------------------------------------------------------------------------


def decision_deadline(delivery_date, deadline_time=DECISION_DEADLINE_TIME):
    """The deadline for a delivery day: deadline_time (UTC) on the day before."""
    if isinstance(delivery_date, str):
        delivery_date = date.fromisoformat(delivery_date)
    if isinstance(deadline_time, str):
        deadline_time = time.fromisoformat(deadline_time)
    day_before = delivery_date - timedelta(days=1)
    return _utc(datetime.combine(day_before, deadline_time))


def select_forecasts_at_deadline(forecasts, delivery_date, deadline_time=DECISION_DEADLINE_TIME):
    """
    For each of the 24 hours of `delivery_date`, the newest forecast published at
    or before ONE fixed deadline: `deadline_time` on the day before.

    Example: delivery 14 Jan, deadline 09:50 -> every hour of 14 Jan uses the
    newest forecast published by 13 Jan 09:50 (the 09:30 one, normally).

    Returns one row per hour:
        start_time, forecast_mw, publish_time, lead_time_h, deadline
    Here lead_time_h DIFFERS per hour (about 14.5h for 00:00 up to 37.5h for 23:00),
    because the deadline is fixed but the hours are not.

    Note: hours are taken in UTC. In January UTC = UK time, so "the delivery day"
    is the same either way. (In summer this would need adjusting.)
    """
    deadline = decision_deadline(delivery_date, deadline_time)
    day_start = _utc(pd.Timestamp(str(delivery_date)))
    hours = pd.date_range(day_start, periods=24, freq="h")

    targets = pd.DataFrame({"start_time": hours, "deadline": deadline})
    chosen = _newest_forecast_before(forecasts, targets)
    return chosen[["start_time", "forecast_mw", "publish_time", "lead_time_h", "deadline"]]


def build_decision_day_comparison(
    actuals,
    forecasts,
    first_delivery_day="2026-01-02",
    last_delivery_day="2026-02-01",
    deadline_time=DECISION_DEADLINE_TIME,
):
    """
    Decision Day mode for many delivery days, side by side with the actuals.
    Default: decisions made 1-31 Jan -> delivery days 2 Jan - 1 Feb.

    Returns the same columns as build_comparison(), plus 'deadline':
        start_time, actual_mw, forecast_mw, publish_time, lead_time_h, error_mw, deadline
    """
    days = pd.date_range(first_delivery_day, last_delivery_day, freq="D")
    chosen = pd.concat(
        [select_forecasts_at_deadline(forecasts, day.date(), deadline_time) for day in days],
        ignore_index=True,
    )
    actual = pd.DataFrame(
        {
            "start_time": _utc_column(actuals["start_time"]),
            "actual_mw": actuals["generation_mw"].to_numpy(),
        }
    )
    table = chosen.merge(actual, on="start_time", how="left")
    table["error_mw"] = table["actual_mw"] - table["forecast_mw"]
    return table[
        [
            "start_time",
            "actual_mw",
            "forecast_mw",
            "publish_time",
            "lead_time_h",
            "error_mw",
            "deadline",
        ]
    ]
