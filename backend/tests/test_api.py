"""
Tests for the web API (app/main.py and app/api/), on the real January 2026 data.

TestClient pretends to be a browser: it calls the endpoints without starting a real
server, so these tests are quick and need no network.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest -v
"""

import csv
import importlib
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.matching import build_comparison, build_decision_day_comparison
from app.core.metrics import summary
from app.data.settings import ACTUALS_FILE, FORECASTS_FILE
from app.main import app

SERIES_COLUMNS = ["time", "actual_mw", "forecast_mw", "publish_time", "deadline",
                  "lead_time_h", "error_mw", "range_low_mw", "range_high_mw"]


@pytest.fixture(scope="module")
def client():
    # "with" runs the start-up step (loading the data) once for all tests in this file.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def data():
    return pd.read_parquet(ACTUALS_FILE), pd.read_parquet(FORECASTS_FILE)


# ---------------------------------------------------------------------------
# Every endpoint answers with its defaults
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "/api/health", "/api/config", "/api/series", "/api/summary", "/api/horizon-curve",
    "/api/breakdowns", "/api/backtest", "/api/decision-day", "/api/quality",
    "/api/export.csv",
    # and a few non-default choices
    "/api/series?mode=decision_day", "/api/summary?mode=decision_day&confidence=95",
    "/api/backtest?method=per_group", "/api/breakdowns?mode=decision_day",
    "/api/decision-day?date=2026-02-01",
])
def test_endpoint_returns_200(client, url):
    assert client.get(url).status_code == 200


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["available_dates"] == {"start": "2026-01-01", "end": "2026-02-01"}


def test_config_has_slider_and_choices(client):
    body = client.get("/api/config").json()
    assert body["horizon_slider"] == {**body["horizon_slider"], "min": 0, "max": 43, "default": 24}
    assert body["confidence_levels"] == [80, 90, 95]
    assert body["default_confidence"] == 90
    assert body["decision_deadline"]["time_utc"] == "09:50"
    per_group = [m for m in body["cushion_methods"] if m["value"] == "per_group"][0]
    assert per_group["experimental"] is True


# ---------------------------------------------------------------------------
# Bad inputs -> 422 with a helpful message
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url, field, words", [
    ("/api/series?horizon=44", "horizon", "0 to 43"),
    ("/api/series?horizon=-1", "horizon", "0 to 43"),
    ("/api/series?horizon=abc", "horizon", "0 to 43"),
    ("/api/series?mode=weekly", "mode", "horizon, decision_day"),
    ("/api/summary?confidence=85", "confidence", "80, 90, 95"),
    ("/api/backtest?method=magic", "method", "one_size, per_group"),
    ("/api/series?start=2025-12-31", "start", "between 2026-01-01 and 2026-01-31"),
    ("/api/series?end=2026-02-01", "end", "between 2026-01-01 and 2026-01-31"),
    ("/api/series?mode=decision_day&start=2026-01-01", "start", "between 2026-01-02"),
    ("/api/series?start=2026-01-20&end=2026-01-10", "start", "is after end"),
    ("/api/series?start=15-01-2026", "start", "YYYY-MM-DD"),
    ("/api/decision-day?date=2026-03-01", "date", "between 2026-01-02 and 2026-02-01"),
])
def test_bad_input_gives_helpful_message(client, url, field, words):
    response = client.get(url)
    assert response.status_code == 422
    body = response.json()
    assert body["problems"][0]["field"] == field
    assert words in body["error"]


# ---------------------------------------------------------------------------
# The forecast-matching rule is never broken
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query", ["horizon=0", "horizon=24", "horizon=43", "mode=decision_day"])
def test_series_never_uses_a_forecast_published_after_its_deadline(client, query):
    rows = pd.DataFrame(client.get(f"/api/series?{query}").json()["rows"])
    assert len(rows) == 744
    publish = pd.to_datetime(rows["publish_time"])
    assert publish.notna().all()
    assert (publish <= pd.to_datetime(rows["deadline"])).all()


def test_decision_day_uses_one_deadline_the_day_before(client):
    body = client.get("/api/decision-day?date=2026-01-15").json()
    assert body["deadline"] == "2026-01-14T09:50:00Z"
    rows = pd.DataFrame(body["rows"])
    assert len(rows) == 24
    assert (rows["deadline"] == body["deadline"]).all()
    assert (pd.to_datetime(rows["publish_time"]) <= pd.Timestamp(body["deadline"])).all()


# ---------------------------------------------------------------------------
# The API serves the Phase 3 numbers unchanged
# ---------------------------------------------------------------------------

def assert_same_summary(api, expected):
    for name, value in expected.items():
        if name.endswith("_time"):
            assert pd.Timestamp(api[name]) == value, name
        else:
            assert api[name] == pytest.approx(value), name


def test_summary_matches_metrics_summary(client, data):
    actuals, forecasts = data
    api = client.get("/api/summary?horizon=24&start=2026-01-10&end=2026-01-16").json()
    # build_comparison's end is NOT included, so 17 Jan = "up to and including 16 Jan".
    expected = summary(build_comparison(actuals, forecasts, 24, "2026-01-10", "2026-01-17"))
    assert_same_summary(api, expected)


def test_decision_day_summary_matches_metrics_summary(client, data):
    actuals, forecasts = data
    api = client.get("/api/summary?mode=decision_day").json()
    assert_same_summary(api, summary(build_decision_day_comparison(actuals, forecasts)))


def test_cushion_is_learned_from_training_weeks_only(client):
    body = client.get("/api/summary").json()
    assert body["cushion_learned_from"]["start"] == "2026-01-01"
    assert body["cushion_learned_from"]["end"] == "2026-01-24"
    assert body["cushion_mw"] == pytest.approx(-body["range_lower_mw"])
    assert "plan for about" in body["plain_english"]


def test_series_range_is_forecast_plus_cushion(client):
    body = client.get("/api/series").json()
    row = body["rows"][0]
    assert row["range_low_mw"] == pytest.approx(row["forecast_mw"] - body["cushion_mw"])


def test_backtest_per_group_is_labelled_experimental(client):
    body = client.get("/api/backtest?method=per_group").json()
    assert body["experimental"] is True
    assert "EXPERIMENTAL" in body["method_label"]
    assert body["honest_verdict"]


# ---------------------------------------------------------------------------
# CSV export and CORS
# ---------------------------------------------------------------------------

def test_export_csv_has_expected_columns(client):
    response = client.get("/api/export.csv?start=2026-01-14&end=2026-01-14")
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == SERIES_COLUMNS
    assert len(rows) == 1 + 24  # header + one row per hour of 14 Jan


def test_frontend_dev_server_is_allowed(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_allowed_origins_come_from_the_environment(monkeypatch):
    import app.main as main_module

    monkeypatch.setenv("ALLOWED_ORIGINS", "https://windhedge.example, http://localhost:8080 ,")
    try:
        reloaded = importlib.reload(main_module)  # re-read the setting, as at start-up
        assert reloaded.ALLOWED_ORIGINS == ["https://windhedge.example", "http://localhost:8080"]
    finally:
        monkeypatch.delenv("ALLOWED_ORIGINS")
        importlib.reload(main_module)  # back to the default for any later tests
