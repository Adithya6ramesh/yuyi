"""
DATA STORE - loads the data ONCE and remembers (caches) results.

Caching in one sentence: the first time someone asks for, say, "H = 24", we work the
answer out and keep it in memory, so every later request for the same thing is
answered instantly instead of being recalculated.

Nothing here invents new maths. Every number comes from app/core/ (Phases 2-3):
    matching.py -> which forecast was available, side by side with the actual
    metrics.py  -> miss, lean, wobble, breakdowns
    cushion.py  -> the safety cushion and the back-test

Tables returned by the cached functions are SHARED between requests: never change
them in place. between() hands out a copy, which is safe to change.
"""

import json
from datetime import date, timedelta
from functools import cache

import pandas as pd

from app.core.cushion import back_test, split_train_test
from app.core.matching import build_comparison, build_decision_day_comparison
from app.core.metrics import SLIDER_HOURS, summary
from app.data.settings import (
    ACTUALS_FILE,
    DECISION_MONTH_END,
    DECISION_MONTH_START,
    FORECASTS_FILE,
    QUALITY_REPORT_FILE,
)

MODES = ("horizon", "decision_day")

# Which dates (of the HOUR being delivered) each mode can answer for, both ends included.
#   horizon:      every hour of January 2026.
#   decision_day: the delivery days for decisions made 1-31 January, i.e. 2 Jan - 1 Feb
#                 (the decision on 31 Jan, 09:50, is for 1 Feb).
_MONTH_FIRST = date.fromisoformat(DECISION_MONTH_START)
_MONTH_AFTER = date.fromisoformat(DECISION_MONTH_END)
ONE_DAY = timedelta(days=1)
DATE_RANGES = {
    "horizon": (_MONTH_FIRST, _MONTH_AFTER - ONE_DAY),
    "decision_day": (_MONTH_FIRST + ONE_DAY, _MONTH_AFTER),
}

# ---------------------------------------------------------------------------
# Loading the data (once)
# ---------------------------------------------------------------------------

_data = {}


def load():
    """
    Read the data files into memory. main.py calls this once when the server starts.
    If something asks for data before that, it is loaded then - still only once.
    """
    if _data:
        return
    _data["actuals"] = pd.read_parquet(ACTUALS_FILE)
    _data["forecasts"] = pd.read_parquet(FORECASTS_FILE)
    _data["quality"] = json.loads(QUALITY_REPORT_FILE.read_text(encoding="utf-8"))


def get(name):
    """One of the loaded things: "actuals", "forecasts" or "quality"."""
    load()
    return _data[name]


# ---------------------------------------------------------------------------
# Cached calculations, one per (mode, H) combination
# ---------------------------------------------------------------------------


def _key(mode, horizon):
    """Decision Day ignores H (its deadline is fixed), so all H share one cache entry."""
    return (mode, None) if mode == "decision_day" else (mode, int(horizon))


def comparison(mode, horizon):
    """
    The full forecast-vs-actual table for one mode (and H), with a 'deadline' column:
    the latest publish_time that was allowed for that hour.
    """
    return _comparison(*_key(mode, horizon))


@cache
def _comparison(mode, horizon):
    actuals, forecasts = get("actuals"), get("forecasts")
    if mode == "decision_day":
        return build_decision_day_comparison(actuals, forecasts)
    table = build_comparison(actuals, forecasts, horizon)
    table["deadline"] = table["start_time"] - pd.Timedelta(hours=horizon)
    return table


def backtest(mode, horizon, confidence):
    """cushion.back_test() for this (mode, H, confidence): learn 1-24 Jan, test 25-31 Jan."""
    return _backtest(*_key(mode, horizon), confidence)


@cache
def _backtest(mode, horizon, confidence):
    table = comparison(mode, horizon)
    result = back_test(table, confidence)
    train, test = split_train_test(table)
    result["train_period"] = period(train)
    result["test_period"] = period(test)
    return result


def cushion(mode, horizon, confidence):
    """
    The one-size cushion shown on the chart and in the summary.

    It is learned from the TRAINING weeks only (before the back-test week), so it is
    exactly the cushion the back-test checked. See README "Where the cushion is
    learned from" for why.
    Returns cushion.error_band() numbers plus 'learned_from' (a period).
    """
    result = backtest(mode, horizon, confidence)
    return {**result["one_size_band"], "learned_from": result["train_period"]}


def horizon_curve(start, end):
    """summary() for every H from 0 to 43, over the chosen dates."""
    return _horizon_curve(start, end)


@cache
def _horizon_curve(start, end):
    return [
        {"hours_ahead": h, **summary(between(comparison("horizon", h), start, end))}
        for h in SLIDER_HOURS
    ]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def between(table, start, end):
    """The rows whose hour falls on the dates start..end (both days included). A copy."""
    first = pd.Timestamp(start, tz="UTC")
    after_last = pd.Timestamp(end + ONE_DAY, tz="UTC")
    inside = (table["start_time"] >= first) & (table["start_time"] < after_last)
    return table.loc[inside].copy()


def period(rows):
    """Describe the dates a set of rows covers, e.g. '1-24 January 2026'."""
    if rows.empty:
        return {"start": None, "end": None, "hours": 0, "label": "no hours"}
    first, last = rows["start_time"].min().date(), rows["start_time"].max().date()
    if (first.year, first.month) == (last.year, last.month):
        label = f"{first.day}-{last.day} {last:%B %Y}"
    else:
        label = f"{first.day} {first:%B} - {last.day} {last:%B %Y}"
    return {"start": first, "end": last, "hours": int(len(rows)), "label": label}
