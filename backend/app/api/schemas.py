"""
SHAPES of what goes into and comes out of the API.

Pydantic in one sentence: we describe what each input and output should look like
(a whole number, a date, one of a fixed list...) and Pydantic checks real data against
that description automatically, rejecting anything that doesn't fit.

These shapes also appear on the automatic /docs page, so the frontend developer can
see exactly what each endpoint returns.
"""

from datetime import date, datetime
from enum import Enum, IntEnum

from pydantic import BaseModel

from app.core.cushion import CONFIDENCE_LEVELS

# ---------------------------------------------------------------------------
# Inputs: the allowed choices
# ---------------------------------------------------------------------------


class Mode(str, Enum):
    horizon = "horizon"            # each hour uses the newest forecast made H hours before it
    decision_day = "decision_day"  # every hour uses the newest forecast at 09:50 the day before


class Method(str, Enum):
    one_size = "one_size"    # one cushion for every hour (the default, passed the back-test)
    per_group = "per_group"  # a cushion per wind level (experimental, failed the back-test)


# 80, 90 or 95, taken from cushion.py so the list lives in one place. A numbered choice
# list (IntEnum) because web addresses arrive as text ("90") and this turns it into 90.
ConfidenceLevel = IntEnum("ConfidenceLevel", {f"pct_{c}": c for c in CONFIDENCE_LEVELS})


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    start: date
    end: date


class Period(BaseModel):
    """A stretch of days, e.g. the weeks a cushion was learned from."""
    start: date | None
    end: date | None
    hours: int
    label: str  # e.g. "1-24 January 2026"


class Health(BaseModel):
    status: str
    available_dates: DateRange
    actual_rows: int
    forecast_versions: int


class SeriesRow(BaseModel):
    """One hour on the chart. Values are empty (null) if there was nothing to show."""
    time: datetime                 # the hour being delivered (UTC)
    actual_mw: float | None
    forecast_mw: float | None      # the forecast that was available at the deadline
    publish_time: datetime | None  # when that forecast was published
    deadline: datetime             # the latest publish_time allowed for this hour
    lead_time_h: float | None      # how long before the hour it was published
    error_mw: float | None         # actual - forecast; negative = forecast too high
    range_low_mw: float | None     # forecast + lower cushion percentile
    range_high_mw: float | None    # forecast + upper cushion percentile


class SeriesResponse(BaseModel):
    mode: Mode
    horizon: int | None  # null in decision_day mode (H doesn't apply there)
    confidence: int
    start: date
    end: date
    cushion_mw: float
    cushion_learned_from: Period
    hours: int
    rows: list[SeriesRow]


class SummaryResponse(BaseModel):
    """metrics.summary() numbers (empty if no hours matched) plus the cushion."""
    mode: Mode
    horizon: int | None
    confidence: int
    start: date
    end: date
    hours_counted: int
    average_miss_mw: float | None = None
    typical_miss_mw: float | None = None
    bad_hour_miss_mw: float | None = None
    worst_shortfall_mw: float | None = None
    worst_shortfall_time: datetime | None = None
    worst_overshoot_mw: float | None = None
    worst_overshoot_time: datetime | None = None
    lean_mw: float | None = None
    pct_hours_too_high: float | None = None
    wobble_mw: float | None = None
    overall_miss_mw: float | None = None
    lean_share_pct: float | None = None
    average_lead_time_h: float | None = None
    cushion_mw: float
    range_lower_mw: float  # add to a forecast to get the bottom of the range
    range_upper_mw: float  # add to a forecast to get the top of the range
    cushion_learned_from: Period
    plain_english: str


class HorizonPoint(BaseModel):
    hours_ahead: int
    hours_matched: int
    average_miss_mw: float | None
    bad_hour_miss_mw: float | None
    lean_mw: float | None
    wobble_mw: float | None
    average_lead_time_h: float | None


class HorizonCurveResponse(BaseModel):
    start: date
    end: date
    points: list[HorizonPoint]


class BreakdownRow(BaseModel):
    group: str  # "00-03" ... "21-24", or "low" / "medium" / "high"
    hours_counted: int
    average_miss_mw: float
    typical_miss_mw: float
    bad_hour_miss_mw: float
    lean_mw: float
    pct_hours_too_high: float
    wobble_mw: float


class WindThresholds(BaseModel):
    low_to_medium_mw: float
    medium_to_high_mw: float
    grouped_by: str
    rule: str


class BreakdownsResponse(BaseModel):
    mode: Mode
    horizon: int | None
    start: date
    end: date
    time_of_day: list[BreakdownRow]
    wind_level: list[BreakdownRow]
    wind_level_thresholds: WindThresholds


class BacktestResponse(BaseModel):
    mode: Mode
    horizon: int | None
    confidence: int
    method: Method
    experimental: bool
    method_label: str
    train_period: Period
    test_period: Period
    target_pct: float
    actual_coverage_pct: float     # actual landed inside the range
    caught_short_pct: float        # actual came in BELOW the range (the costly side)
    above_range_pct: float
    below_raw_forecast_pct: float  # actual below the plain forecast (no cushion at all)
    average_cushion_mw: float
    honest_verdict: str


class DailyAverages(BaseModel):
    hours_counted: int
    average_actual_mw: float | None
    average_forecast_mw: float | None
    average_miss_mw: float | None
    lean_mw: float | None
    pct_hours_too_high: float | None


class DecisionDayResponse(BaseModel):
    delivery_date: date
    deadline: datetime
    confidence: int
    cushion_mw: float
    cushion_learned_from: Period
    rows: list[SeriesRow]
    daily: DailyAverages
