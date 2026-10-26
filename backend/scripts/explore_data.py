"""
First look: explore the Elexon wind data before building anything.

What this script does (read top to bottom, it is meant to be read like a story):
  1. Downloads a small sample of ACTUAL wind generation  (FUELHH dataset)
  2. Downloads a small sample of wind FORECASTS            (WINDFOR dataset)
  3. Prints what the data looks like and runs simple quality checks
  4. Saves the raw samples as CSV files in backend/data/samples/

How to run it (from the project root folder):
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\explore_data.py

No API key is needed - the Elexon data is free and public.
"""

from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# All Elexon "datasets" live under this web address.
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# Our sample: Tuesday 13 and Wednesday 14 January 2026.
SAMPLE_FIRST_DAY = "2026-01-13"
SAMPLE_LAST_DAY = "2026-01-14"

# Forecasts are filtered by when they were PUBLISHED, not by the time they are
# about. Each forecast looks up to ~3 days ahead, so to see every forecast made
# for our 2 sample days we also need the ones published the day before (12 Jan).
FORECAST_PUBLISHED_FROM = "2026-01-12T00:00:00Z"
FORECAST_PUBLISHED_TO = "2026-01-15T00:00:00Z"

# The one "time being forecast" we zoom in on, to see how forecasts change.
EXAMPLE_START_TIME = "2026-01-14T12:00:00Z"  # 14 Jan 2026, 12:00 midday

# Where the CSV files go: backend/data/samples/
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

# Make pandas print wide tables on one line instead of wrapping them.
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)


# ---------------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------------


def heading(text):
    """Print a big, easy-to-spot heading."""
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def download(dataset, params):
    """
    Ask the Elexon API for one dataset and return it as a pandas table (DataFrame).
    'params' are the filters, e.g. which dates we want.
    """
    url = f"{BASE_URL}/{dataset}/stream"
    print(f"Downloading {dataset} ... filters: {params}")
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()  # stop with a clear error if the request failed
    table = pd.DataFrame(response.json())  # the "stream" endpoints return a plain JSON list

    # The times arrive as text like "2026-01-13T00:00:00Z". Turn them into real
    # date-times so we can sort them and do maths on them. The "Z" means UTC.
    for column in ["publishTime", "startTime"]:
        if column in table.columns:
            table[column] = pd.to_datetime(table[column], utc=True)
    return table


def describe(table, name):
    """Print the column names, the first few rows and the number of rows."""
    print(f"\n--- {name} ---")
    print("Columns    :", list(table.columns))
    print("Row count  :", len(table))
    print("First 5 rows:")
    print(table.head(5).to_string(index=False))


def check_duplicates(table, key_columns, name):
    """
    A 'duplicate' is two rows that describe the same thing.
    - Exact duplicates: every column identical.
    - Key duplicates: the same key (e.g. same startTime) appears more than once.
    """
    exact = table.duplicated().sum()
    by_key = table.duplicated(subset=key_columns).sum()
    print(f"[{name}] exact duplicate rows            : {exact}")
    print(f"[{name}] duplicates of {key_columns}: {by_key}")
    if by_key:
        dupes = table[table.duplicated(subset=key_columns, keep=False)]
        print(dupes.sort_values(key_columns).head(10).to_string(index=False))


def check_odd_values(table, name):
    """Look for empty cells and strange generation numbers."""
    print(f"[{name}] empty cells per column:")
    print("   ", table.isna().sum().to_dict())
    generation = table["generation"]
    print(
        f"[{name}] generation (MW): min={generation.min()}, max={generation.max()}, "
        f"average={generation.mean():.0f}"
    )
    print(
        f"[{name}] negative values: {(generation < 0).sum()}, "
        f"zero values: {(generation == 0).sum()}"
    )
    # Great Britain has roughly 30,000 MW of wind measured this way, so anything
    # above ~35,000 MW would be suspicious.
    print(f"[{name}] values above 35,000 MW: {(generation > 35000).sum()}")


def check_time_steps(times, expected_step, first, last, name):
    """
    Check the times go up in regular steps (e.g. every 30 minutes) with no gaps.
    'first' and 'last' are the first and last times we EXPECT to see.
    """
    times = pd.Series(sorted(times.unique()))
    gaps = times.diff().dropna().value_counts()
    print(f"[{name}] distance between neighbouring times (how often it happens):")
    for step, count in gaps.items():
        print(f"    {step}  ->  {count} times")

    expected = pd.date_range(first, last, freq=expected_step, tz="UTC")
    missing = expected.difference(pd.DatetimeIndex(times))
    print(
        f"[{name}] expected {len(expected)} time slots, found {len(times)}, missing {len(missing)}"
    )
    if len(missing):
        print("    missing:", [str(m) for m in missing[:10]])


# ---------------------------------------------------------------------------
# Part 1: ACTUAL wind generation (FUELHH)
# ---------------------------------------------------------------------------


def explore_fuelhh():
    heading("PART 1: FUELHH - actual generation, every fuel type, every half hour")

    # We ask for ALL fuel types (not just wind) so you can see what else is in
    # there. Later phases can ask the API for wind only with fuelType=WIND.
    everything = download(
        "FUELHH",
        {
            "settlementDateFrom": SAMPLE_FIRST_DAY,
            "settlementDateTo": SAMPLE_LAST_DAY,
        },
    )
    describe(everything, "FUELHH, all fuel types")
    print("\nFuel types present:", sorted(everything["fuelType"].unique()))

    # Keep only wind.
    wind = everything[everything["fuelType"] == "WIND"].sort_values("startTime")
    describe(wind, "FUELHH, WIND only")

    # Show how 'settlement period' numbers relate to clock times.
    # (A settlement period is one of the 48 half-hours in a day, numbered 1-48.)
    print("\nSettlement period vs startTime (first 3 and last 3 of the sample):")
    columns = ["settlementDate", "settlementPeriod", "startTime", "publishTime"]
    print(pd.concat([wind.head(3), wind.tail(3)])[columns].to_string(index=False))

    print("\nQuality checks:")
    check_time_steps(
        wind["startTime"],
        "30min",
        f"{SAMPLE_FIRST_DAY} 00:00",
        f"{SAMPLE_LAST_DAY} 23:30",
        "FUELHH WIND",
    )
    check_duplicates(wind, ["startTime"], "FUELHH WIND")
    check_odd_values(wind, "FUELHH WIND")

    # Save the raw downloads (all fuels) and the wind-only version.
    everything.to_csv(SAMPLES_DIR / "fuelhh_all_fuels_sample.csv", index=False)
    wind.to_csv(SAMPLES_DIR / "fuelhh_wind_sample.csv", index=False)
    return wind


# ---------------------------------------------------------------------------
# Part 2: wind FORECASTS (WINDFOR)
# ---------------------------------------------------------------------------


def explore_windfor():
    heading("PART 2: WINDFOR - wind forecasts")

    forecasts = download(
        "WINDFOR",
        {
            "publishDateTimeFrom": FORECAST_PUBLISHED_FROM,
            "publishDateTimeTo": FORECAST_PUBLISHED_TO,
        },
    )
    forecasts = forecasts.sort_values(["publishTime", "startTime"])
    describe(forecasts, "WINDFOR")

    # --- How often are forecasts published, and how far ahead do they look? ---
    print("\nOne line per published forecast:")
    per_forecast = forecasts.groupby("publishTime")["startTime"].agg(
        first_time_covered="min", last_time_covered="max", rows="count"
    )
    one_hour = pd.Timedelta(hours=1)
    per_forecast["hours_ahead_of_last"] = (
        per_forecast["last_time_covered"] - per_forecast.index
    ) / one_hour
    print(per_forecast.to_string())
    print("\nTime between one forecast and the next:")
    print(forecasts["publishTime"].drop_duplicates().diff().value_counts().to_string())

    # --- Is WINDFOR every 30 minutes or every hour? ---
    print(
        "\nMinutes past the hour used by startTime:",
        sorted(forecasts["startTime"].dt.minute.unique()),
    )
    one_forecast = forecasts[forecasts["publishTime"] == forecasts["publishTime"].iloc[0]]
    check_time_steps(
        one_forecast["startTime"],
        "1h",
        one_forecast["startTime"].min(),
        one_forecast["startTime"].max(),
        "WINDFOR (one forecast)",
    )

    # --- Zoom in on ONE startTime: every forecast ever made for it ---
    example_time = pd.Timestamp(EXAMPLE_START_TIME)
    history = forecasts[forecasts["startTime"] == example_time].copy()
    history["hours_before"] = (example_time - history["publishTime"]) / one_hour
    print(f"\nAll forecasts for startTime {example_time} ({len(history)} of them), oldest first:")
    print(history[["publishTime", "hours_before", "generation"]].to_string(index=False))

    print("\nQuality checks:")
    # In WINDFOR the same startTime appears many times ON PURPOSE (once per
    # forecast), so a real duplicate is the same (publishTime, startTime) pair.
    check_duplicates(forecasts, ["publishTime", "startTime"], "WINDFOR")
    check_odd_values(forecasts, "WINDFOR")

    forecasts.to_csv(SAMPLES_DIR / "windfor_sample.csv", index=False)
    history.to_csv(SAMPLES_DIR / "windfor_one_starttime_history.csv", index=False)
    return forecasts


# ---------------------------------------------------------------------------
# Part 3: a first peek at forecast vs actual, side by side
# ---------------------------------------------------------------------------


def compare_example(wind, forecasts):
    heading("PART 3: forecast vs actual for the example time (just a peek)")
    example_time = pd.Timestamp(EXAMPLE_START_TIME)
    actual = wind.loc[wind["startTime"] == example_time, "generation"]
    history = forecasts[forecasts["startTime"] == example_time].sort_values("publishTime")

    # WARNING: WINDFOR keeps "forecasting" an hour even AFTER that hour has
    # passed. Those rows were not available beforehand, so we must ignore them.
    published_after = history[history["publishTime"] > example_time]
    usable = history[history["publishTime"] <= example_time]
    latest = usable.iloc[-1]

    print(f"Actual wind at {example_time}: {actual.iloc[0]} MW")
    print(
        f"Latest forecast published BEFORE that time "
        f"({latest['publishTime']}): {latest['generation']} MW"
    )
    print(
        f"Forecasts published AFTER the time had already passed "
        f"(must be ignored): {len(published_after)}"
    )


def main():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    wind = explore_fuelhh()
    forecasts = explore_windfor()
    compare_example(wind, forecasts)
    heading(f"Done. CSV files saved in {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
