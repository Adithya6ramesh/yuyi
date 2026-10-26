"""
The saved results in data/processed/precomputed/ must equal what the live code computes
right now. If the data or the maths change and nobody re-runs scripts/precompute.py,
these tests fail in CI, so the saved copies can never silently go stale.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m pytest tests/test_precomputed.py -v
"""

import math

import pandas as pd
import pytest

from app.api import precomputed, store

FIX = "Re-run `python scripts/precompute.py` (from backend/) and commit the files."


def assert_same(saved, live, where="result"):
    """
    Every key, list item and text must be identical. Decimal numbers may differ only
    in their last digits (1 part in a trillion), because Windows and Linux can round
    the very last digit of a calculation differently. A real change is far bigger.
    """
    if isinstance(live, dict):
        assert isinstance(saved, dict) and saved.keys() == live.keys(), f"{where}: keys differ"
        for key in live:
            assert_same(saved[key], live[key], f"{where}.{key}")
    elif isinstance(live, list):
        assert isinstance(saved, list) and len(saved) == len(live), f"{where}: lengths differ"
        for i, (a, b) in enumerate(zip(saved, live, strict=True)):
            assert_same(a, b, f"{where}[{i}]")
    elif isinstance(live, float) and not isinstance(saved, bool):
        assert isinstance(saved, (int, float)), f"{where}: {saved!r} is not a number"
        assert math.isclose(saved, live, rel_tol=1e-12, abs_tol=1e-9), (
            f"{where}: saved {saved} but the live code gives {live}"
        )
    else:
        assert saved == live, f"{where}: saved {saved!r} but the live code gives {live!r}"


@pytest.fixture(autouse=True)
def fresh_caches():
    # Make sure nothing cached earlier (by other tests) hides a difference.
    store._comparison.cache_clear()
    store._horizon_curve.cache_clear()
    yield
    store._comparison.cache_clear()
    store._horizon_curve.cache_clear()


def test_saved_horizon_curve_matches_the_live_code():
    saved = precomputed.load(precomputed.HORIZON_CURVE_FILE)
    assert saved is not None, f"{precomputed.HORIZON_CURVE_FILE} is missing. {FIX}"
    live = precomputed.jsonable(store.compute_horizon_curve(*store.DATE_RANGES["horizon"]))
    assert_same(saved, live, "horizon_curve")


def test_saved_decision_day_table_matches_the_live_code():
    saved = precomputed.load(precomputed.DECISION_DAY_FILE)
    assert saved is not None, f"{precomputed.DECISION_DAY_FILE} is missing. {FIX}"
    live = store.compute_comparison("decision_day", None)
    # Exact: same rows, same values, same column types.
    pd.testing.assert_frame_equal(precomputed.table_from_json(saved), live, check_exact=True)


def test_the_api_really_uses_the_saved_copies(monkeypatch):
    # If the API tried to compute these live, this would blow up.
    def refuse(*args):
        raise AssertionError("computed live instead of using the saved copy")

    monkeypatch.setattr(store, "compute_comparison", refuse)
    monkeypatch.setattr(store, "compute_horizon_curve", refuse)
    assert len(store.comparison("decision_day", 24)) == 744
    assert len(store.horizon_curve(*store.DATE_RANGES["horizon"])) == 44
