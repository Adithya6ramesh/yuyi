"""
Tests for app/data/clean.py, using tiny fake data (no internet needed).

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest -v
"""

import pandas as pd

from app.data.clean import clean_actuals, clean_forecasts


def fake_actuals():
    """Raw rows shaped like Elexon's FUELHH reply."""
    return pd.DataFrame(
        [
            {"startTime": "2026-01-13T00:30:00Z", "fuelType": "WIND", "generation": 120},
            {"startTime": "2026-01-13T00:00:00Z", "fuelType": "WIND", "generation": 100},
            {
                "startTime": "2026-01-13T00:00:00Z",
                "fuelType": "WIND",
                "generation": 100,
            },  # exact copy
            {
                "startTime": "2026-01-13T00:00:00Z",
                "fuelType": "CCGT",
                "generation": 999,
            },  # not wind
        ]
    )


def fake_forecasts():
    """Raw rows shaped like Elexon's WINDFOR reply: one target hour, three versions."""
    return pd.DataFrame(
        [
            {
                "startTime": "2026-01-14T12:00:00Z",
                "publishTime": "2026-01-13T02:30:00Z",
                "generation": 6500,
            },
            {
                "startTime": "2026-01-14T12:00:00Z",
                "publishTime": "2026-01-12T02:30:00Z",
                "generation": 6200,
            },
            {
                "startTime": "2026-01-14T12:00:00Z",
                "publishTime": "2026-01-14T11:30:00Z",
                "generation": 8100,
            },
            {
                "startTime": "2026-01-14T12:00:00Z",
                "publishTime": "2026-01-14T11:30:00Z",
                "generation": 8100,
            },  # exact copy
        ]
    )


# ---------- duplicates are removed ----------


def test_actuals_exact_duplicates_are_removed():
    clean, stats = clean_actuals(fake_actuals())
    assert stats["duplicates_removed"] == 1
    assert len(clean) == 2


def test_forecasts_exact_duplicates_are_removed():
    clean, stats = clean_forecasts(fake_forecasts())
    assert stats["duplicates_removed"] == 1
    assert len(clean) == 3


# ---------- times end up in UTC ----------


def test_times_are_utc():
    actuals, _ = clean_actuals(fake_actuals())
    forecasts, _ = clean_forecasts(fake_forecasts())
    assert str(actuals["start_time"].dt.tz) == "UTC"
    assert str(forecasts["start_time"].dt.tz) == "UTC"
    assert str(forecasts["publish_time"].dt.tz) == "UTC"


def test_other_time_zones_are_converted_to_utc():
    raw = pd.DataFrame(
        [
            # 13:00 in UTC+1 is 12:00 UTC
            {"startTime": "2026-07-01T13:00:00+01:00", "fuelType": "WIND", "generation": 50},
        ]
    )
    clean, _ = clean_actuals(raw)
    assert clean["start_time"].iloc[0] == pd.Timestamp("2026-07-01T12:00:00Z")


# ---------- all forecast versions are kept ----------


def test_all_forecast_versions_are_kept():
    clean, _ = clean_forecasts(fake_forecasts())
    # Same target hour, three different publish times -> three rows, not one.
    assert clean["start_time"].nunique() == 1
    assert clean["publish_time"].nunique() == 3
    assert sorted(clean["generation_mw"]) == [6200, 6500, 8100]


def test_forecasts_sorted_oldest_version_first():
    clean, _ = clean_forecasts(fake_forecasts())
    assert clean["publish_time"].is_monotonic_increasing


# ---------- other cleaning rules ----------


def test_only_wind_and_needed_columns_kept():
    actuals, _ = clean_actuals(fake_actuals())
    forecasts, _ = clean_forecasts(fake_forecasts())
    assert list(actuals.columns) == ["start_time", "generation_mw"]
    assert list(forecasts.columns) == ["start_time", "publish_time", "generation_mw"]
    assert 999 not in actuals["generation_mw"].values  # the CCGT row is gone


def test_actuals_sorted_by_time():
    clean, _ = clean_actuals(fake_actuals())
    assert clean["start_time"].is_monotonic_increasing
