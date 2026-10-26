"""
THE SAFETY CUSHION - how much wind should the buyer plan to be "missing"?

Idea: look at past errors (actual - forecast). If we want to be right C% of the time,
cut off the worst (100-C)/2 % of errors on each side:

    lower = the (100-C)/2 percentile of the errors          (e.g. 5th for C=90)
    upper = the 100-(100-C)/2 percentile of the errors      (e.g. 95th for C=90)

    range for a new forecast F = [F + lower, F + upper]
    cushion = -lower   -> the MW of wind to plan as "missing"

Example: C=90, lower=-4,000 MW. With a forecast of 12,000 MW the buyer plans as if
only 8,000 MW of wind will arrive, and is right about 9 hours in 10 - IF the future
behaves like the past. back_test() checks whether it does.

Two flavours:
    one-size  - one set of numbers for every hour
    per-group - separate numbers for low / medium / high wind, where the group is
                chosen from the FORECAST (never the actual)
"""

import numpy as np
import pandas as pd

from app.core.metrics import WIND_LEVELS, assign_wind_level, complete_rows, wind_level_thresholds

CONFIDENCE_LEVELS = (80, 90, 95)
BACKTEST_SPLIT = "2026-01-25"  # learn from hours BEFORE this, test on hours from it on
BACKTEST_END = "2026-02-01"  # ...up to (not including) this


def error_band(errors, confidence):
    """
    The lower and upper error percentiles for confidence C, plus the cushion.
    A negative cushion would mean forecasts are almost never too high - we report
    it as-is rather than hiding it.
    """
    tail = (100 - confidence) / 2
    errors = pd.Series(errors).dropna()
    lower = float(np.percentile(errors, tail))
    upper = float(np.percentile(errors, 100 - tail))
    return {
        "confidence": confidence,
        "lower_mw": lower,
        "upper_mw": upper,
        "cushion_mw": -lower,
        "hours_learned_from": int(len(errors)),
    }


# ---------------------------------------------------------------------------
# Learning the cushion
# ---------------------------------------------------------------------------


def learn_one_size(comparison, confidence):
    """One band from all the hours given."""
    return error_band(complete_rows(comparison)["error_mw"], confidence)


def learn_per_group(comparison, confidence, thresholds=None):
    """
    A band for each wind level. The thresholds (split points) are learned from the
    FORECASTS of the hours given, unless passed in.
    If a level has no hours to learn from, it uses the one-size band instead and is
    marked "fallback": True - we never invent numbers for an empty group.
    """
    rows = complete_rows(comparison)
    if thresholds is None:
        thresholds = wind_level_thresholds(rows["forecast_mw"])
    levels = assign_wind_level(rows["forecast_mw"], thresholds).to_numpy()
    one_size = error_band(rows["error_mw"], confidence)

    bands = {}
    for level in WIND_LEVELS:
        errors = rows.loc[levels == level, "error_mw"]
        if errors.empty:
            bands[level] = {**one_size, "fallback": True}
        else:
            bands[level] = {**error_band(errors, confidence), "fallback": False}
    return {"confidence": confidence, "thresholds": thresholds, "bands": bands}


# ---------------------------------------------------------------------------
# Applying the cushion to (new) hours
# ---------------------------------------------------------------------------


def apply_one_size(comparison, band):
    """Add range_low_mw / range_high_mw columns using one band for every hour."""
    rows = complete_rows(comparison).copy()
    rows["range_low_mw"] = rows["forecast_mw"] + band["lower_mw"]
    rows["range_high_mw"] = rows["forecast_mw"] + band["upper_mw"]
    return rows


def apply_per_group(comparison, model):
    """
    Add range columns using the band of each hour's wind level.
    The level comes from the hour's FORECAST and the LEARNED thresholds.
    """
    rows = complete_rows(comparison).copy()
    rows["wind_level"] = assign_wind_level(rows["forecast_mw"], model["thresholds"]).to_numpy()
    lower = rows["wind_level"].map({k: b["lower_mw"] for k, b in model["bands"].items()})
    upper = rows["wind_level"].map({k: b["upper_mw"] for k, b in model["bands"].items()})
    rows["range_low_mw"] = rows["forecast_mw"] + lower.astype(float)
    rows["range_high_mw"] = rows["forecast_mw"] + upper.astype(float)
    return rows


def coverage(applied):
    """
    How did the ranges do?
        pct_inside           - actual fell inside [range_low, range_high]  (target: C)
        pct_below_range      - actual came in BELOW the range (the costly side)
        pct_above_range      - actual came in above the range
        pct_below_raw        - actual came in below the plain forecast (no cushion)
        average_cushion_mw   - average MW planned as "missing"
    """
    actual = applied["actual_mw"]
    return {
        "hours": int(len(applied)),
        "pct_inside": float(
            ((actual >= applied["range_low_mw"]) & (actual <= applied["range_high_mw"])).mean()
            * 100
        ),
        "pct_below_range": float((actual < applied["range_low_mw"]).mean() * 100),
        "pct_above_range": float((actual > applied["range_high_mw"]).mean() * 100),
        "pct_below_raw": float((actual < applied["forecast_mw"]).mean() * 100),
        "average_cushion_mw": float((applied["forecast_mw"] - applied["range_low_mw"]).mean()),
    }


# ---------------------------------------------------------------------------
# Back-test: learn on the past, test on the (unseen) future
# ---------------------------------------------------------------------------


def split_train_test(comparison, split=BACKTEST_SPLIT, end=BACKTEST_END):
    """Learning hours: before `split`. Test hours: from `split` up to `end`."""
    rows = complete_rows(comparison)
    split, end = pd.Timestamp(split, tz="UTC"), pd.Timestamp(end, tz="UTC")
    train = rows[rows["start_time"] < split]
    test = rows[(rows["start_time"] >= split) & (rows["start_time"] < end)]
    return train, test


def back_test(comparison, confidence, split=BACKTEST_SPLIT, end=BACKTEST_END):
    """
    Learn both cushions from hours before `split` only, then check them on the
    hours from `split` to `end`, which they have never seen.
    Nothing from the test hours is used for learning - not even the wind-level
    thresholds.
    """
    train, test = split_train_test(comparison, split, end)
    one_size = learn_one_size(train, confidence)
    per_group = learn_per_group(train, confidence)
    return {
        "confidence": confidence,
        "train_hours": int(len(train)),
        "test_hours": int(len(test)),
        "one_size_band": one_size,
        "per_group_model": per_group,
        "one_size": coverage(apply_one_size(test, one_size)),
        "per_group": coverage(apply_per_group(test, per_group)),
    }
