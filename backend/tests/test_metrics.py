"""
Tests for app/core/metrics.py, with tiny fake data whose answers can be checked by hand.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest -v
"""

import math

import pandas as pd
import pytest

from app.core.metrics import assign_wind_level, breakdowns, summary, wind_level_thresholds


def comparison(errors, forecast=1000, start="2026-01-14 00:00"):
    """A comparison table with the given errors (actual = forecast + error)."""
    times = pd.date_range(start, periods=len(errors), freq="h", tz="UTC")
    forecasts = [forecast] * len(errors) if not isinstance(forecast, list) else forecast
    return pd.DataFrame({
        "start_time": times,
        "actual_mw": [f + e for f, e in zip(forecasts, errors)],
        "forecast_mw": forecasts,
        "publish_time": times - pd.Timedelta(hours=25),
        "lead_time_h": [25.0] * len(errors),
        "error_mw": errors,
    })


# Errors [-300, -100, 0, +100, +300]. By hand:
#   lean   = 0 / 5 = 0
#   misses = 300, 100, 0, 100, 300 -> average 800 / 5 = 160, median 100
#   90th percentile of misses: sorted 0,100,100,300,300 -> position 0.9*4 = 3.6 -> 300
#   wobble = sqrt((90000 + 10000 + 0 + 10000 + 90000) / 5) = sqrt(40000) = 200
#   too high (error < 0): 2 of 5 = 40%
SYMMETRIC = [-300, -100, 0, 100, 300]


def test_summary_numbers_by_hand():
    s = summary(comparison(SYMMETRIC))
    assert s["hours_counted"] == 5
    assert s["lean_mw"] == 0
    assert s["average_miss_mw"] == 160
    assert s["typical_miss_mw"] == 100
    assert s["bad_hour_miss_mw"] == 300
    assert s["wobble_mw"] == 200
    assert s["pct_hours_too_high"] == 40
    assert s["average_lead_time_h"] == 25


def test_worst_shortfall_and_overshoot_with_times():
    s = summary(comparison(SYMMETRIC))
    assert s["worst_shortfall_mw"] == -300
    assert s["worst_shortfall_time"] == pd.Timestamp("2026-01-14 00:00", tz="UTC")
    assert s["worst_overshoot_mw"] == 300
    assert s["worst_overshoot_time"] == pd.Timestamp("2026-01-14 04:00", tz="UTC")


def test_lean_and_wobble_split():
    # Every hour 100 MW too high: all lean, no wobble.
    s = summary(comparison([-100, -100, -100, -100]))
    assert s["lean_mw"] == -100
    assert s["wobble_mw"] == 0
    assert s["lean_share_pct"] == 100
    assert s["pct_hours_too_high"] == 100
    # Symmetric errors: no lean, all wobble.
    assert summary(comparison(SYMMETRIC))["lean_share_pct"] == 0


def test_overall_miss_squared_is_lean_squared_plus_wobble_squared():
    s = summary(comparison([-500, -200, -100, 50, 0, -900]))
    assert math.isclose(s["overall_miss_mw"] ** 2, s["lean_mw"] ** 2 + s["wobble_mw"] ** 2)


def test_hours_without_forecast_are_skipped():
    table = comparison(SYMMETRIC)
    table.loc[0, ["forecast_mw", "error_mw"]] = None  # first hour has no forecast
    s = summary(table)
    assert s["hours_counted"] == 4
    assert s["lean_mw"] == pytest.approx(75)  # (-100 + 0 + 100 + 300) / 4


def test_wind_level_thresholds_are_thirds():
    low_to_medium, medium_to_high = wind_level_thresholds([0, 300, 600, 900])
    assert low_to_medium == pytest.approx(300)
    assert medium_to_high == pytest.approx(600)


def test_wind_level_boundaries():
    levels = assign_wind_level([100, 300, 599, 600, 5000], (300, 600))
    assert list(levels) == ["low", "medium", "medium", "high", "high"]


def test_breakdowns_group_by_forecast_and_time_block():
    # 6 hours: forecasts 1000,1000,5000,5000,9000,9000 -> one third in each level.
    table = comparison([-10, -10, -50, -50, -90, -90],
                       forecast=[1000, 1000, 5000, 5000, 9000, 9000])
    parts = breakdowns(table)
    wind = parts["wind_level"]
    assert wind.loc["low", "lean_mw"] == -10
    assert wind.loc["medium", "lean_mw"] == -50
    assert wind.loc["high", "lean_mw"] == -90
    # Hours 00:00-05:00 -> blocks 00-03 (3 hours) and 03-06 (3 hours)
    assert list(parts["time_of_day"].index) == ["00-03", "03-06"]
    assert list(parts["time_of_day"]["hours_counted"]) == [3, 3]
