"""
Tests for app/core/cushion.py, with tiny fake data whose answers can be checked by hand.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest -v
"""

import pandas as pd
import pytest

from app.core.cushion import (
    apply_one_size,
    apply_per_group,
    back_test,
    coverage,
    error_band,
    learn_one_size,
    learn_per_group,
)


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


# Errors [-300, -100, 0, +100, +300], C = 80 -> percentiles 10 and 90.
# By hand (straight-line interpolation between sorted values, positions 0..4):
#   10th: position 0.1*4 = 0.4 -> -300 + 0.4 * (-100 - -300) = -220
#   90th: position 0.9*4 = 3.6 ->  100 + 0.6 * ( 300 -  100) =  220
SYMMETRIC = [-300, -100, 0, 100, 300]


def test_error_band_by_hand():
    band = error_band(SYMMETRIC, 80)
    assert band["lower_mw"] == pytest.approx(-220)
    assert band["upper_mw"] == pytest.approx(220)
    assert band["cushion_mw"] == pytest.approx(220)  # cushion = -lower


def test_range_is_forecast_plus_band():
    band = learn_one_size(comparison(SYMMETRIC), 80)
    applied = apply_one_size(comparison([0], forecast=5000), band)
    assert applied["range_low_mw"].iloc[0] == pytest.approx(4780)
    assert applied["range_high_mw"].iloc[0] == pytest.approx(5220)


def test_coverage_counts():
    band = {"lower_mw": -100, "upper_mw": 100}
    # errors: inside, inside, below range, above range; 3 of 4 below the raw forecast
    result = coverage(apply_one_size(comparison([-50, 100, -150, 150]), band))
    assert result["pct_inside"] == 50
    assert result["pct_below_range"] == 25
    assert result["pct_above_range"] == 25
    assert result["pct_below_raw"] == 50
    assert result["average_cushion_mw"] == 100


def test_wider_confidence_gives_bigger_cushion():
    errors = list(range(-1000, 1001, 10))
    assert (error_band(errors, 80)["cushion_mw"] < error_band(errors, 90)["cushion_mw"]
            < error_band(errors, 95)["cushion_mw"])


def test_per_group_cushion_uses_forecast_not_actual():
    """
    Learning data: low-forecast hours miss by a little, high-forecast hours by a lot.
    Then a NEW hour with a LOW forecast but a HUGE actual must get the LOW-wind band,
    because at decision time only the forecast is known.
    """
    low = comparison([-10, -20, -30, -40, -50, -60], forecast=1000)
    medium = comparison([-100, -200, -300, -400, -500, -600], forecast=10000,
                        start="2026-01-15 00:00")
    high = comparison([-1000, -2000, -3000, -4000, -5000, -6000], forecast=20000,
                      start="2026-01-16 00:00")
    model = learn_per_group(pd.concat([low, medium, high], ignore_index=True), 80)

    new_hour = comparison([19000], forecast=1000, start="2026-01-20 00:00")  # actual 20,000
    applied = apply_per_group(new_hour, model)

    assert applied["wind_level"].iloc[0] == "low"
    expected_low = 1000 + model["bands"]["low"]["lower_mw"]
    assert applied["range_low_mw"].iloc[0] == pytest.approx(expected_low)


def test_empty_wind_level_falls_back_to_one_size():
    # Every forecast identical -> both split points equal -> low and medium are empty.
    model = learn_per_group(comparison(SYMMETRIC), 80)
    assert model["bands"]["low"]["fallback"] is True
    assert model["bands"]["low"]["cushion_mw"] == pytest.approx(220)  # the one-size value
    assert model["bands"]["high"]["fallback"] is False


def test_thresholds_learned_from_forecasts_only():
    table = comparison([-10, -20, -30, -40, -50, -60],
                       forecast=[1000, 2000, 3000, 4000, 5000, 6000])
    changed = table.copy()
    changed["actual_mw"] = changed["actual_mw"] * 10  # wildly different actuals
    assert learn_per_group(table, 80)["thresholds"] == learn_per_group(changed, 80)["thresholds"]


def test_back_test_learns_only_from_before_the_split():
    # Learning days: tiny errors. Test days: huge errors.
    learn = comparison([-10, 10] * 24, start="2026-01-23 00:00")   # 23-24 Jan
    test = comparison([-5000, 5000] * 24, start="2026-01-25 00:00")  # 25-26 Jan
    result = back_test(pd.concat([learn, test], ignore_index=True), 80)
    assert result["train_hours"] == 48
    assert result["test_hours"] == 48
    # The band only knows the tiny learning errors, so it can't cover the test week.
    assert result["one_size_band"]["cushion_mw"] == pytest.approx(10)
    assert result["one_size"]["pct_inside"] == 0
