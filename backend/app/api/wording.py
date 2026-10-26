"""
PLAIN-ENGLISH SENTENCES built from the numbers, for the screen to show as-is.

Only wording lives here: every number passed in was calculated elsewhere.
"""

from app.data.settings import DECISION_DEADLINE_TIME

HOURS_IN_TEN = {80: "8 hours in 10", 90: "9 hours in 10", 95: "19 hours in 20"}
METHOD_LABELS = {
    "one_size": "One-size cushion (the same for every hour)",
    "per_group": "EXPERIMENTAL: per-wind-level cushion (failed the back-test)",
}


def about(mw):
    """Round to the nearest 50 MW for reading aloud: 2,047.3 -> '2,050'."""
    return f"{round(mw / 50) * 50:,.0f}"


def which_forecasts(mode, horizon):
    """Who we are talking about, as the start of a sentence."""
    if mode == "decision_day":
        return (
            f"The forecasts available at the {DECISION_DEADLINE_TIME:%H:%M} UTC deadline "
            "the day before"
        )
    if horizon == 0:
        return "The newest forecasts available at each hour"
    return f"Forecasts made {horizon} hour{'s' if horizon != 1 else ''} ahead"


def summary_text(numbers, band, mode, horizon, confidence):
    """2-3 sentences: how big the miss was, how big a cushion to plan for, and why."""
    if numbers["hours_counted"] == 0:
        return (
            "There are no hours with both a forecast and an actual in these dates, "
            "so there is nothing to measure."
        )

    first = (
        f"{which_forecasts(mode, horizon)} missed by about "
        f"{about(numbers['average_miss_mw'])} MW on average and were too high in "
        f"{numbers['pct_hours_too_high']:.0f}% of hours."
    )
    if band["cushion_mw"] > 0:
        second = (
            f"To be covered {HOURS_IN_TEN[confidence]}, plan for about "
            f"{about(band['cushion_mw'])} MW less wind than the forecast says."
        )
    else:
        second = (
            f"In the learning weeks the forecast was rarely too high, so no cushion "
            f"is needed to be covered {HOURS_IN_TEN[confidence]}."
        )
    third = (
        f"This cushion was learned from {band['learned_from']['label']} only "
        "(the weeks before the back-test week)."
    )
    return " ".join([first, second, third])


def backtest_verdict(result, method, confidence):
    """An honest sentence or three about how the cushion did on the unseen week."""
    tested = result[method]
    inside, short = tested["pct_inside"], tested["pct_below_range"]
    if inside >= confidence:
        outcome = f"held up: it covered {inside:.0f}% of hours against a target of {confidence}%"
    elif inside >= confidence - 3:
        outcome = f"came close: it covered {inside:.0f}% of hours against a target of {confidence}%"
    else:
        outcome = (
            f"fell short: it covered only {inside:.0f}% of hours against a target of {confidence}%"
        )

    name = "one-size" if method == "one_size" else "experimental per-wind-level"
    sentences = [
        f"On the {result['test_hours']} hours it had never seen "
        f"({result['test_period']['label']}), the {name} cushion {outcome}, and the buyer "
        f"was caught short in {short:.0f}% of hours.",
        f"With no cushion at all they would have been caught short in "
        f"{tested['pct_below_raw']:.0f}% of hours.",
    ]
    if method == "per_group":
        sentences.append(
            f"On the same hours the one-size cushion covered "
            f"{result['one_size']['pct_inside']:.0f}%."
        )
    sentences.append("This is one week of data, so a few points either way can be chance.")
    return " ".join(sentences)
