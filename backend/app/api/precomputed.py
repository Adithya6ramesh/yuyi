"""
PRECOMPUTED RESULTS: the two slowest calculations, worked out once and saved, so a fresh
copy of the API (e.g. a new serverless instance on Vercel) can answer straight away
instead of spending seconds on them.

    horizon_curve.json  summary() for every H from 0 to 43 over the whole month
                        (what the desk asks for when it first opens; ~2.5 s to compute)
    decision_day.json   the Decision Day forecast-vs-actual table, all 744 hours
                        (used by Decision Day mode and the replay; ~1 s to compute)

How they stay correct:
  - scripts/precompute.py makes them, using the same functions the API uses live.
  - tests/test_precomputed.py rebuilds them from the live code on every CI run and fails
    if anything differs, so they can never silently go stale. (After changing the data
    or the maths, re-run the script.)
  - If the files are missing, the API simply computes everything live, as before.
"""

import json
import math
from datetime import date, datetime

import numpy as np
import pandas as pd

from app.data.settings import PROCESSED_DIR

PRECOMPUTED_DIR = PROCESSED_DIR / "precomputed"
HORIZON_CURVE_FILE = PRECOMPUTED_DIR / "horizon_curve.json"
DECISION_DAY_FILE = PRECOMPUTED_DIR / "decision_day.json"


def jsonable(value):
    """Turn numbers, times and nested lists/dicts into plain JSON-friendly values."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if math.isnan(value) else float(value)
    return value


def table_to_json(table):
    """A table -> {"dtypes": {...}, "columns": {...}}: keeps each column's exact type."""
    return {
        "dtypes": {name: str(dtype) for name, dtype in table.dtypes.items()},
        "columns": {name: jsonable(table[name].tolist()) for name in table.columns},
    }


def table_from_json(data):
    """The reverse of table_to_json(): the same table, with the same column types."""
    columns = {}
    for name, dtype in data["dtypes"].items():
        values = data["columns"][name]
        if dtype.startswith("datetime64"):
            columns[name] = pd.to_datetime(values, utc=True).astype(dtype)
        else:
            columns[name] = pd.Series(values).astype(dtype)
    return pd.DataFrame(columns)


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def load(path):
    """The saved JSON, or None if the file isn't there."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
