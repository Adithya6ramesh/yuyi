"""
Data quality checks. Called by clean.py after cleaning.

build_report() returns a plain dictionary (saved as quality_report.json).
print_summary() prints the same information in a human-friendly way.
"""

import pandas as pd

from app.data.settings import (
    ACTUALS_FIRST_DAY,
    ACTUALS_LAST_DAY,
    DECISION_MONTH_END,
    DECISION_MONTH_START,
)

ONE_HOUR = pd.Timedelta(hours=1)

# Lead-time groups, in hours. "Lead time" = how long before the target hour the
# forecast was published.
LEAD_BINS = [float("-inf"), 0, 6, 12, 24, 36, 48, float("inf")]
LEAD_LABELS = [
    "negative (published after target)",
    "0-6h",
    "6-12h",
    "12-24h",
    "24-36h",
    "36-48h",
    "48h+",
]

# If average forecast / average actual is outside this range, we warn.
SCALE_OK_RANGE = (0.8, 1.25)


def _time_text(timestamps):
    """Timestamps -> list of readable text, for the JSON report."""
    return [t.strftime("%Y-%m-%d %H:%M UTC") for t in timestamps]


def check_actuals(actuals, stats):
    expected = pd.date_range(
        f"{ACTUALS_FIRST_DAY} 00:00", f"{ACTUALS_LAST_DAY} 23:30", freq="30min", tz="UTC"
    )
    found = pd.DatetimeIndex(actuals["start_time"].unique())
    missing = expected.difference(found)
    # Same half-hour more than once but with DIFFERENT values: not an exact
    # duplicate, so not removed, but we must know about it.
    conflicting = actuals["start_time"].duplicated().sum()
    generation = actuals["generation_mw"]
    return {
        **stats,
        "expected_half_hours": len(expected),
        "found_half_hours": len(found),
        "missing_half_hours": _time_text(missing),
        "half_hours_with_conflicting_values": int(conflicting),
        "empty_values": int(generation.isna().sum()),
        "negative_values": int((generation < 0).sum()),
        "min_mw": float(generation.min()),
        "max_mw": float(generation.max()),
        "mean_mw": round(float(generation.mean()), 1),
    }


def check_forecasts(forecasts, stats):
    generation = forecasts["generation_mw"]
    publishes = forecasts["publish_time"].drop_duplicates()
    per_day = publishes.dt.date.value_counts().sort_index()

    # How many versions (forecasts) exist for each target hour?
    versions = forecasts.groupby("start_time").size()
    # Target hours inside January are the ones we care about; hours at the very
    # edges of the download naturally have fewer versions.
    january = versions[
        (versions.index >= DECISION_MONTH_START) & (versions.index < DECISION_MONTH_END)
    ]
    usable = forecasts[forecasts["publish_time"] <= forecasts["start_time"]]
    usable_january = usable.groupby("start_time").size().reindex(january.index, fill_value=0)

    return {
        **stats,
        "distinct_publish_times": int(publishes.size),
        "publish_times_of_day": sorted(publishes.dt.strftime("%H:%M").unique().tolist()),
        "days_without_8_publishes": {str(d): int(n) for d, n in per_day.items() if n != 8},
        "distinct_target_hours": int(versions.size),
        "target_hours_not_on_the_hour": int((forecasts["start_time"].dt.minute != 0).sum()),
        "versions_per_target_hour_all": {
            "min": int(versions.min()),
            "max": int(versions.max()),
            "typical": int(versions.median()),
        },
        "versions_per_january_target_hour": {
            "min": int(january.min()),
            "max": int(january.max()),
            "typical": int(january.median()),
        },
        "usable_versions_per_january_target_hour": {
            "note": "only versions published at or before the target hour",
            "min": int(usable_january.min()),
            "max": int(usable_january.max()),
            "typical": int(usable_january.median()),
        },
        "empty_values": int(generation.isna().sum()),
        "negative_values": int((generation < 0).sum()),
        "min_mw": float(generation.min()),
        "max_mw": float(generation.max()),
    }


def check_lead_times(forecasts):
    """lead time (hours) = start_time - publish_time."""
    lead = (forecasts["start_time"] - forecasts["publish_time"]) / ONE_HOUR
    groups = pd.cut(lead, bins=LEAD_BINS, labels=LEAD_LABELS, right=False)
    counts = groups.value_counts().reindex(LEAD_LABELS)

    # For each January target hour: what is the LONGEST lead time available
    # (counting only forecasts published before the target)? The smallest of
    # these is how far ahead we can look for EVERY hour in January.
    table = forecasts.assign(lead_hours=lead)
    table = table[
        (table["lead_hours"] >= 0)
        & (table["start_time"] >= DECISION_MONTH_START)
        & (table["start_time"] < DECISION_MONTH_END)
    ]
    longest_per_target = table.groupby("start_time")["lead_hours"].max()
    shortest_per_target = table.groupby("start_time")["lead_hours"].min()

    return {
        "min_hours": float(lead.min()),
        "max_hours": float(lead.max()),
        "median_hours": float(lead.median()),
        "counts_by_group": {label: int(n) for label, n in counts.items()},
        "january_targets": {
            "longest_lead_available_for_every_hour": float(longest_per_target.min()),
            "longest_lead_available_for_some_hours": float(longest_per_target.max()),
            "shortest_lead_available_worst_case": float(shortest_per_target.max()),
        },
    }


def check_scale(actuals, forecasts):
    """
    Are forecasts and actuals measuring the same thing? Compare the January average
    of actual wind with the average of the LATEST forecast published before each hour.
    On-the-hour times only.
    """
    usable = forecasts[forecasts["publish_time"] <= forecasts["start_time"]]
    latest = usable.sort_values("publish_time").groupby("start_time").tail(1)
    both = latest.merge(actuals, on="start_time", suffixes=("_forecast", "_actual"))
    both = both[
        (both["start_time"] >= DECISION_MONTH_START) & (both["start_time"] < DECISION_MONTH_END)
    ]

    mean_actual = both["generation_mw_actual"].mean()
    mean_forecast = both["generation_mw_forecast"].mean()
    ratio = mean_forecast / mean_actual
    low, high = SCALE_OK_RANGE
    return {
        "hours_compared": int(len(both)),
        "mean_actual_mw": round(float(mean_actual), 1),
        "mean_latest_forecast_mw": round(float(mean_forecast), 1),
        "forecast_to_actual_ratio": round(float(ratio), 3),
        "same_scale": bool(low <= ratio <= high),
    }


def build_report(actuals, forecasts, actuals_stats, forecasts_stats):
    return {
        "actuals": check_actuals(actuals, actuals_stats),
        "forecasts": check_forecasts(forecasts, forecasts_stats),
        "lead_time": check_lead_times(forecasts),
        "scale_check": check_scale(actuals, forecasts),
    }


def print_summary(report):
    a, f = report["actuals"], report["forecasts"]
    lead, scale = report["lead_time"], report["scale_check"]

    print("\n================ DATA QUALITY SUMMARY ================")
    print("\nACTUALS (FUELHH wind, every 30 min)")
    print(f"  half-hours expected / found : {a['expected_half_hours']} / {a['found_half_hours']}")
    print(
        f"  missing half-hours          : {len(a['missing_half_hours'])} "
        f"{a['missing_half_hours'][:10]}"
    )
    print(f"  duplicates removed          : {a['duplicates_removed']}")
    print(f"  conflicting values          : {a['half_hours_with_conflicting_values']}")
    print(f"  empty / negative values     : {a['empty_values']} / {a['negative_values']}")
    print(
        f"  range                       : {a['min_mw']:.0f} - {a['max_mw']:.0f} MW "
        f"(average {a['mean_mw']:.0f})"
    )

    print("\nFORECASTS (WINDFOR, hourly)")
    print(
        f"  rows                        : {f['clean_rows']} "
        f"(duplicates removed: {f['duplicates_removed']})"
    )
    print(
        f"  forecasts published         : {f['distinct_publish_times']} "
        f"at {', '.join(f['publish_times_of_day'])} UTC"
    )
    print(f"  days without 8 forecasts    : {f['days_without_8_publishes'] or 'none'}")
    print(f"  distinct target hours       : {f['distinct_target_hours']}")
    v, j, u = (
        f["versions_per_target_hour_all"],
        f["versions_per_january_target_hour"],
        f["usable_versions_per_january_target_hour"],
    )
    print(
        f"  versions per target hour    : all hours min {v['min']} / max {v['max']}; "
        f"January hours min {j['min']} / typical {j['typical']} / max {j['max']}"
    )
    print(
        f"  ...published BEFORE target  : January hours min {u['min']} / "
        f"typical {u['typical']} / max {u['max']}"
    )
    print(f"  empty / negative values     : {f['empty_values']} / {f['negative_values']}")

    print("\nLEAD TIME (target time minus publish time)")
    print(f"  min {lead['min_hours']}h, max {lead['max_hours']}h, median {lead['median_hours']}h")
    for label, count in lead["counts_by_group"].items():
        print(f"    {label:<36} {count:>6}")
    jt = lead["january_targets"]
    longest = jt["longest_lead_available_for_every_hour"]
    print(f"  every January hour has forecasts from up to {longest}h ahead")
    print(
        f"  (some hours have up to {jt['longest_lead_available_for_some_hours']}h); "
        f"the freshest forecast is never more than {jt['shortest_lead_available_worst_case']}h old"
    )

    print("\nSCALE CHECK (January, on-the-hour, latest forecast published before target)")
    print(f"  average actual   : {scale['mean_actual_mw']:.0f} MW")
    print(f"  average forecast : {scale['mean_latest_forecast_mw']:.0f} MW")
    print(f"  ratio            : {scale['forecast_to_actual_ratio']}")
    if scale["same_scale"]:
        print("  OK: forecasts and actuals are on the same scale.")
    else:
        print("  WARNING: forecasts and actuals look like they measure different things!")
