"""
Shared settings for the data pipeline: which dates we download and where files go.
Change things here, not in the individual scripts.
"""

from datetime import date, time
from pathlib import Path

# Elexon's public API. No key needed.
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# --- Date ranges (why these: see docs/DESIGN.md, section 3 "Data") ---
# Forecasts: everything PUBLISHED from 30 Dec 2025 00:00 up to (not including) 1 Feb 2026 00:00 UTC.
FORECASTS_FIRST_PUBLISH_DAY = date(2025, 12, 30)
FORECASTS_LAST_PUBLISH_DAY = date(2026, 1, 31)

# Actuals: every half-hour of these days (both days included).
ACTUALS_FIRST_DAY = date(2025, 12, 30)
ACTUALS_LAST_DAY = date(2026, 2, 3)

# The month our purchase decisions are in. Used by the quality checks.
DECISION_MONTH_START = "2026-01-01"
DECISION_MONTH_END = "2026-02-01"  # not included

# --- "Decision Day" mode: the fixed deadline on the day BEFORE delivery ---
# Default 09:50 UTC = gate closure of Nord Pool's GB day-ahead auction (09:50 UK time;
# UK time = UTC in January). Other exchanges (e.g. EPEX) have different deadlines,
# so CONFIRM with the client which auction they actually use.
# With 09:50, the 09:30 forecast of that morning is still usable.
DECISION_DEADLINE_TIME = time(9, 50)

# --- Folders ---
BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # untouched downloads (git-ignored)
PROCESSED_DIR = DATA_DIR / "processed"  # clean files the app will read

RAW_ACTUALS_DIR = RAW_DIR / "fuelhh"
RAW_FORECASTS_DIR = RAW_DIR / "windfor"

ACTUALS_FILE = PROCESSED_DIR / "actuals.parquet"
FORECASTS_FILE = PROCESSED_DIR / "forecasts.parquet"
QUALITY_REPORT_FILE = PROCESSED_DIR / "quality_report.json"
