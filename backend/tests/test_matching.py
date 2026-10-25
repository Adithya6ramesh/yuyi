"""
Tests for app/core/matching.py - the forecast-matching rule.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest -v
"""

import pandas as pd
import pytest

from app.core.matching import (
    build_comparison,
    count_missing,
    select_forecasts,
    select_forecasts_at_deadline,
)
from app.data.settings import FORECASTS_FILE

TARGET = "2026-01-14T12:00:00Z"


def forecast_rows(rows):
    """Build a forecasts table from (start_time, publish_time, MW) tuples."""
    table = pd.DataFrame(rows, columns=["start_time", "publish_time", "generation_mw"])
    table["start_time"] = pd.to_datetime(table["start_time"], utc=True)
    table["publish_time"] = pd.to_datetime(table["publish_time"], utc=True)
    return table


def versions_for_target():
    """Five forecasts for 14 Jan 12:00, published at different times."""
    return forecast_rows([
        (TARGET, "2026-01-13T02:30:00Z", 100),
        (TARGET, "2026-01-13T11:30:00Z", 200),
        (TARGET, "2026-01-13T15:30:00Z", 300),
        (TARGET, "2026-01-14T09:30:00Z", 400),
        (TARGET, "2026-01-14T15:30:00Z", 999),  # published AFTER the target hour
    ])


def pick(forecasts, hours_ahead):
    """The single row chosen for TARGET."""
    result = select_forecasts(forecasts, hours_ahead)
    return result[result["start_time"] == pd.Timestamp(TARGET)].iloc[0]


# ---------- picks the newest forecast published before the deadline ----------

def test_picks_newest_forecast_before_deadline():
    # H = 24 -> deadline 13 Jan 12:00 -> newest at or before it is 11:30 (200 MW)
    row = pick(versions_for_target(), 24)
    assert row["forecast_mw"] == 200
    assert row["publish_time"] == pd.Timestamp("2026-01-13T11:30:00Z")
    assert row["lead_time_h"] == 24.5


# ---------- NEVER picks a forecast published after the deadline ----------

def test_never_picks_forecast_published_after_deadline():
    forecasts = versions_for_target()
    for hours_ahead in [0, 1, 2, 3, 6, 12, 20, 24, 30]:
        row = pick(forecasts, hours_ahead)
        deadline = pd.Timestamp(TARGET) - pd.Timedelta(hours=hours_ahead)
        assert row["publish_time"] <= deadline
        assert row["forecast_mw"] != 999  # the after-the-fact forecast is never used


def test_never_cheats_on_real_data():
    """The same 'no cheating' check on ALL of our real data, for every H in 0..48."""
    if not FORECASTS_FILE.exists():
        pytest.skip("processed data not built; run app.data.fetch and app.data.clean")
    forecasts = pd.read_parquet(FORECASTS_FILE)
    for hours_ahead in range(0, 49):
        result = select_forecasts(forecasts, hours_ahead).dropna()
        deadline = result["start_time"] - pd.Timedelta(hours=hours_ahead)
        assert (result["publish_time"] <= deadline).all()
        assert (result["lead_time_h"] >= hours_ahead).all()


# ---------- a forecast published EXACTLY at the deadline is allowed ----------

def test_forecast_exactly_at_deadline_is_allowed():
    forecasts = forecast_rows([
        (TARGET, "2026-01-13T10:00:00Z", 100),
        (TARGET, "2026-01-13T12:00:00Z", 200),  # exactly T - 24h
    ])
    row = pick(forecasts, 24)
    assert row["forecast_mw"] == 200
    assert row["lead_time_h"] == 24


# ---------- returns empty (not a guess) when no forecast exists ----------

def test_empty_when_no_forecast_qualifies():
    # Every forecast was published less than 48h before the target.
    row = pick(versions_for_target(), 48)
    assert pd.isna(row["forecast_mw"])
    assert pd.isna(row["publish_time"])
    assert pd.isna(row["lead_time_h"])


def test_comparison_keeps_empty_hours_and_counts_them():
    actuals = pd.DataFrame({
        "start_time": pd.to_datetime(["2026-01-14T11:00:00Z", "2026-01-14T11:30:00Z",
                                      "2026-01-14T12:00:00Z"], utc=True),
        "generation_mw": [500, 550, 600],
    })
    table = build_comparison(actuals, versions_for_target(), 24,
                             start="2026-01-14 11:00", end="2026-01-14 13:00")
    # Two on-the-hour times (11:00, 12:00); the 11:30 actual is left out.
    assert list(table["start_time"].dt.hour) == [11, 12]
    # 11:00 has no forecasts at all -> kept, but empty.
    assert pd.isna(table.iloc[0]["forecast_mw"])
    assert count_missing(table) == {"hours": 2, "without_forecast": 1, "without_actual": 0}
    # 12:00: error = actual - forecast = 600 - 200
    assert table.iloc[1]["error_mw"] == 400


# ---------- larger H never picks a NEWER forecast than smaller H ----------

def test_larger_horizon_never_picks_newer_forecast():
    forecasts = versions_for_target()
    previous = None
    for hours_ahead in range(0, 49):
        publish = pick(forecasts, hours_ahead)["publish_time"]
        if pd.isna(publish):
            continue  # nothing old enough - fine
        if previous is not None:
            assert publish <= previous
        previous = publish


# ---------- the fixed-deadline mode uses ONE deadline for the whole day ----------

def test_fixed_deadline_same_for_every_hour():
    # A forecast published 13 Jan 09:30 and another at 10:30, both covering all of 14 Jan.
    hours = pd.date_range("2026-01-14", periods=24, freq="h", tz="UTC")
    rows = [(h, "2026-01-13T09:30:00Z", 1000) for h in hours]
    rows += [(h, "2026-01-13T10:30:00Z", 2000) for h in hours]  # after the 09:50 deadline
    result = select_forecasts_at_deadline(forecast_rows(rows), "2026-01-14", "09:50")

    assert len(result) == 24
    assert result["deadline"].nunique() == 1
    assert result["deadline"].iloc[0] == pd.Timestamp("2026-01-13T09:50:00Z")
    assert (result["publish_time"] == pd.Timestamp("2026-01-13T09:30:00Z")).all()
    assert (result["forecast_mw"] == 1000).all()
    # Same forecast, so lead time grows hour by hour: 14.5h at 00:00 ... 37.5h at 23:00.
    assert result["lead_time_h"].iloc[0] == 14.5
    assert result["lead_time_h"].iloc[-1] == 37.5
