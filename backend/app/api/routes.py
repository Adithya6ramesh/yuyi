"""
THE ENDPOINTS - one function per URL.

Each function does three small things:
    1. check the inputs (FastAPI checks types; we check dates and give friendly errors)
    2. ask store.py for the (cached) numbers
    3. hand them back in the shape described in schemas.py

All URLs here start with /api (added in main.py).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api import store, wording
from app.api.errors import HORIZON_MAX, InputError
from app.api.schemas import (
    BacktestResponse,
    BreakdownsResponse,
    ConfidenceLevel,
    DecisionDayResponse,
    Health,
    HorizonCurveResponse,
    Method,
    Mode,
    SeriesResponse,
    SummaryResponse,
)
from app.core.cushion import CONFIDENCE_LEVELS, apply_one_size
from app.core.matching import decision_deadline
from app.core.metrics import breakdowns as metrics_breakdowns
from app.core.metrics import summary as metrics_summary
from app.data.settings import DECISION_DEADLINE_TIME

router = APIRouter()

DEFAULT_HORIZON = 24
DEFAULT_CONFIDENCE = 90

# ---------------------------------------------------------------------------
# The inputs, described once and shared by the endpoints
# ---------------------------------------------------------------------------

StartQ = Annotated[
    date | None,
    Query(description="First delivery day, YYYY-MM-DD (UTC). Default: the first available day."),
]
EndQ = Annotated[
    date | None,
    Query(description="Last delivery day, YYYY-MM-DD, included. Default: the last available day."),
]
HorizonQ = Annotated[
    int,
    Query(
        ge=0,
        le=HORIZON_MAX,
        description=f"Hours ahead (0-{HORIZON_MAX}). Ignored in decision_day mode.",
    ),
]
ConfidenceQ = Annotated[
    ConfidenceLevel, Query(description="% of hours the cushion should cover: 80, 90 or 95.")
]
ModeQ = Annotated[
    Mode,
    Query(
        description="horizon = forecast made H hours before each hour; "
        "decision_day = forecast available at 09:50 UTC the day before."
    ),
]

SERIES_COLUMNS = [
    "time",
    "actual_mw",
    "forecast_mw",
    "publish_time",
    "deadline",
    "lead_time_h",
    "error_mw",
    "range_low_mw",
    "range_high_mw",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_dates(mode, start, end):
    """Fill in default dates and make sure they are allowed for this mode."""
    first, last = store.DATE_RANGES[mode]
    start, end = start or first, end or last
    why = (
        "every hour of January 2026"
        if mode == "horizon"
        else "the delivery days for decisions made 1-31 January 2026"
    )
    for name, value in (("start", start), ("end", end)):
        if not first <= value <= last:
            raise InputError(
                name,
                f"{name} must be between {first} and {last} in {mode} mode "
                f"({why}). You asked for {value}.",
            )
    if start > end:
        raise InputError(
            "start",
            f"start ({start}) is after end ({end}). Pick a start date on or before the end date.",
        )
    return start, end


def _shown_horizon(mode, horizon):
    """H only means something in horizon mode; report null otherwise."""
    return horizon if mode == "horizon" else None


def _records(table):
    """A table -> a list of rows, with empty values turned into null."""
    return table.astype(object).where(table.notna(), None).to_dict("records")


def _series_table(mode, horizon, confidence, start, end):
    """The chart rows: forecast vs actual, plus the cushion range around the forecast."""
    rows = store.between(store.comparison(mode, horizon), start, end)
    band = store.cushion(mode, horizon, confidence)
    ranged = apply_one_size(rows, band)
    rows = rows.merge(
        ranged[["start_time", "range_low_mw", "range_high_mw"]], on="start_time", how="left"
    )
    return rows.rename(columns={"start_time": "time"})[SERIES_COLUMNS], band


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=Health)
def health():
    """Is the server alive, and which dates can it answer for?"""
    return {
        "status": "ok",
        "available_dates": {
            "start": store.DATE_RANGES["horizon"][0],
            "end": store.DATE_RANGES["decision_day"][1],
        },
        "actual_rows": len(store.get("actuals")),
        "forecast_versions": len(store.get("forecasts")),
    }


@router.get("/config")
def config():
    """Settings the screen needs, so it doesn't hard-code them."""
    backtest = store.backtest("horizon", DEFAULT_HORIZON, DEFAULT_CONFIDENCE)
    return {
        "horizon_slider": {
            "min": 0,
            "max": HORIZON_MAX,
            "default": DEFAULT_HORIZON,
            "why_max": f"{HORIZON_MAX} hours is the furthest ahead that every hour of "
            "January 2026 still has a forecast published in time.",
        },
        "confidence_levels": list(CONFIDENCE_LEVELS),
        "default_confidence": DEFAULT_CONFIDENCE,
        "modes": [
            {"value": "horizon", "label": "Hours ahead (use the slider)"},
            {
                "value": "decision_day",
                "label": f"Decision Day ({DECISION_DEADLINE_TIME:%H:%M} UTC the day before)",
            },
        ],
        "default_mode": "horizon",
        "cushion_methods": [
            {
                "value": m.value,
                "label": wording.METHOD_LABELS[m.value],
                "experimental": m is Method.per_group,
            }
            for m in Method
        ],
        "default_cushion_method": "one_size",
        "date_ranges": {
            mode: {"start": first, "end": last} for mode, (first, last) in store.DATE_RANGES.items()
        },
        "decision_deadline": {
            "time_utc": f"{DECISION_DEADLINE_TIME:%H:%M}",
            "day": "the day before delivery",
            "why": "Gate closure of Nord Pool's GB day-ahead auction (to be confirmed "
            "with the client).",
        },
        "backtest": {
            "train_period": backtest["train_period"],
            "test_period": backtest["test_period"],
        },
        "cushion_learned_from": backtest["train_period"],
        "timezone": "UTC (the same as UK time in January)",
        "data_sources": [
            {
                "name": "FUELHH",
                "what": "Actual wind generation, every 30 minutes",
                "publisher": "Elexon BMRS",
                "url": "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH",
            },
            {
                "name": "WINDFOR",
                "what": "National wind forecasts, every version kept",
                "publisher": "Elexon BMRS",
                "url": "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR",
            },
        ],
    }


@router.get("/series", response_model=SeriesResponse)
def series(
    start: StartQ = None,
    end: EndQ = None,
    horizon: HorizonQ = DEFAULT_HORIZON,
    confidence: ConfidenceQ = DEFAULT_CONFIDENCE,
    mode: ModeQ = Mode.horizon,
):
    """One row per hour: actual, the forecast available at the deadline, and the range."""
    start, end = _check_dates(mode.value, start, end)
    table, band = _series_table(mode.value, horizon, confidence, start, end)
    return {
        "mode": mode,
        "horizon": _shown_horizon(mode.value, horizon),
        "confidence": confidence,
        "start": start,
        "end": end,
        "cushion_mw": band["cushion_mw"],
        "cushion_learned_from": band["learned_from"],
        "hours": len(table),
        "rows": _records(table),
    }


@router.get("/summary", response_model=SummaryResponse)
def summary(
    start: StartQ = None,
    end: EndQ = None,
    horizon: HorizonQ = DEFAULT_HORIZON,
    confidence: ConfidenceQ = DEFAULT_CONFIDENCE,
    mode: ModeQ = Mode.horizon,
):
    """The headline accuracy numbers, the cushion, and a plain-English explanation."""
    start, end = _check_dates(mode.value, start, end)
    numbers = metrics_summary(store.between(store.comparison(mode.value, horizon), start, end))
    band = store.cushion(mode.value, horizon, confidence)
    return {
        "mode": mode,
        "horizon": _shown_horizon(mode.value, horizon),
        "confidence": confidence,
        "start": start,
        "end": end,
        **numbers,
        "cushion_mw": band["cushion_mw"],
        "range_lower_mw": band["lower_mw"],
        "range_upper_mw": band["upper_mw"],
        "cushion_learned_from": band["learned_from"],
        "plain_english": wording.summary_text(numbers, band, mode.value, horizon, confidence),
    }


@router.get("/horizon-curve", response_model=HorizonCurveResponse)
def horizon_curve(start: StartQ = None, end: EndQ = None):
    """For every H from 0 to 43: average miss, lean, wobble and hours matched."""
    start, end = _check_dates("horizon", start, end)
    points = [{**s, "hours_matched": s["hours_counted"]} for s in store.horizon_curve(start, end)]
    for point in points:  # hours with nothing to measure: show empty values
        for name in (
            "average_miss_mw",
            "bad_hour_miss_mw",
            "lean_mw",
            "wobble_mw",
            "average_lead_time_h",
        ):
            point.setdefault(name, None)
    return {"start": start, "end": end, "points": points}


@router.get("/breakdowns", response_model=BreakdownsResponse)
def breakdowns(
    start: StartQ = None,
    end: EndQ = None,
    horizon: HorizonQ = DEFAULT_HORIZON,
    mode: ModeQ = Mode.horizon,
):
    """Accuracy by 3-hour block of the day and by wind level (grouped by the FORECAST)."""
    start, end = _check_dates(mode.value, start, end)
    rows = store.between(store.comparison(mode.value, horizon), start, end)
    if rows["forecast_mw"].notna().sum() == 0:
        raise InputError("start", "There are no hours with a forecast in these dates.")
    parts = metrics_breakdowns(rows)
    low_to_medium, medium_to_high = parts["thresholds"]

    def as_rows(table):
        return [{"group": str(group), **values} for group, values in table.iterrows()]

    return {
        "mode": mode,
        "horizon": _shown_horizon(mode.value, horizon),
        "start": start,
        "end": end,
        "time_of_day": as_rows(parts["time_of_day"]),
        "wind_level": as_rows(parts["wind_level"]),
        "wind_level_thresholds": {
            "low_to_medium_mw": low_to_medium,
            "medium_to_high_mw": medium_to_high,
            "grouped_by": "forecast",
            "rule": "Split points divide these dates' forecasts into equal thirds. "
            "The FORECAST is used, not the actual, because that is what the "
            "buyer knew at decision time.",
        },
    }


@router.get("/backtest", response_model=BacktestResponse)
def backtest(
    confidence: ConfidenceQ = DEFAULT_CONFIDENCE,
    horizon: HorizonQ = DEFAULT_HORIZON,
    mode: ModeQ = Mode.horizon,
    method: Method = Method.one_size,
):
    """Learn the cushion on the training weeks, then check it on the unseen test week."""
    result = store.backtest(mode.value, horizon, confidence)
    tested = result[method.value]
    return {
        "mode": mode,
        "horizon": _shown_horizon(mode.value, horizon),
        "confidence": confidence,
        "method": method,
        "experimental": method is Method.per_group,
        "method_label": wording.METHOD_LABELS[method.value],
        "train_period": result["train_period"],
        "test_period": result["test_period"],
        "target_pct": confidence,
        "actual_coverage_pct": tested["pct_inside"],
        "caught_short_pct": tested["pct_below_range"],
        "above_range_pct": tested["pct_above_range"],
        "below_raw_forecast_pct": tested["pct_below_raw"],
        "average_cushion_mw": tested["average_cushion_mw"],
        "honest_verdict": wording.backtest_verdict(result, method.value, confidence),
    }


@router.get("/decision-day", response_model=DecisionDayResponse)
def decision_day(
    delivery: Annotated[
        date | None,
        Query(
            alias="date",
            description="The delivery day, YYYY-MM-DD. Default: the first available day.",
        ),
    ] = None,
    confidence: ConfidenceQ = DEFAULT_CONFIDENCE,
):
    """One delivery day as the buyer saw it at 09:50 the day before."""
    first, last = store.DATE_RANGES["decision_day"]
    delivery = delivery or first
    if not first <= delivery <= last:
        raise InputError(
            "date",
            f"date must be between {first} and {last} (the delivery "
            "days for decisions made 1-31 January 2026). "
            f"You asked for {delivery}.",
        )
    table, band = _series_table("decision_day", None, confidence, delivery, delivery)
    numbers = metrics_summary(table.rename(columns={"time": "start_time"}))
    counted = numbers["hours_counted"] > 0
    return {
        "delivery_date": delivery,
        "deadline": decision_deadline(delivery),
        "confidence": confidence,
        "cushion_mw": band["cushion_mw"],
        "cushion_learned_from": band["learned_from"],
        "rows": _records(table),
        "daily": {
            "hours_counted": numbers["hours_counted"],
            "average_actual_mw": table["actual_mw"].mean() if counted else None,
            "average_forecast_mw": table["forecast_mw"].mean() if counted else None,
            "average_miss_mw": numbers.get("average_miss_mw"),
            "lean_mw": numbers.get("lean_mw"),
            "pct_hours_too_high": numbers.get("pct_hours_too_high"),
        },
    }


@router.get("/quality")
def quality():
    """The data quality report (gaps, duplicates, lead times, scale check)."""
    return store.get("quality")


@router.get("/export.csv", response_class=Response, responses={200: {"content": {"text/csv": {}}}})
def export_csv(
    start: StartQ = None,
    end: EndQ = None,
    horizon: HorizonQ = DEFAULT_HORIZON,
    confidence: ConfidenceQ = DEFAULT_CONFIDENCE,
    mode: ModeQ = Mode.horizon,
):
    """The same rows as /api/series, as a CSV file to open in Excel."""
    start, end = _check_dates(mode.value, start, end)
    table, _ = _series_table(mode.value, horizon, confidence, start, end)
    h = f"H{horizon}" if mode is Mode.horizon else "decision_day"
    filename = f"wind_{h}_C{confidence}_{start}_{end}.csv"
    return Response(
        content=table.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%SZ"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
