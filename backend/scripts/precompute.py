"""
Make the saved copies of the two slowest results (see app/api/precomputed.py).

Run from the backend/ folder, after changing the data or the maths:
    .venv\\Scripts\\python.exe scripts\\precompute.py
then commit the files in data/processed/precomputed/. CI fails if you forget
(tests/test_precomputed.py rebuilds them and compares).
"""

import sys
from pathlib import Path

# Let this script import our "app" package (it lives one folder up, in backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import precomputed, store  # noqa: E402


def main():
    store.load()
    start, end = store.DATE_RANGES["horizon"]
    curve = store.compute_horizon_curve(start, end)
    precomputed.save(precomputed.HORIZON_CURVE_FILE, precomputed.jsonable(curve))

    table = store.compute_comparison("decision_day", None)
    precomputed.save(precomputed.DECISION_DAY_FILE, precomputed.table_to_json(table))

    for path in (precomputed.HORIZON_CURVE_FILE, precomputed.DECISION_DAY_FILE):
        print(f"wrote {path.relative_to(Path.cwd())}  ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
