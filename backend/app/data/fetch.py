"""
Step 1 of the data pipeline: DOWNLOAD the raw data from Elexon.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe -m app.data.fetch

It always starts from scratch: the old raw files are deleted and everything is
downloaded again, in weekly pieces. Each piece is saved untouched as a JSON file
in backend/data/raw/, so we can always look at exactly what Elexon sent us.
"""

import json
import shutil
import time
from datetime import timedelta

import requests

from app.data.settings import (
    ACTUALS_FIRST_DAY,
    ACTUALS_LAST_DAY,
    BASE_URL,
    FORECASTS_FIRST_PUBLISH_DAY,
    FORECASTS_LAST_PUBLISH_DAY,
    RAW_ACTUALS_DIR,
    RAW_FORECASTS_DIR,
)

ATTEMPTS = 4  # how many times we try one request before giving up


def get_with_retry(url, params):
    """
    Download one piece of data. If it fails (e.g. the internet hiccups or Elexon
    is busy), wait a little and try again, waiting longer each time.
    """
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=120)
            response.raise_for_status()  # treat "server error" replies as failures too
            return response.json()
        except requests.RequestException as error:
            if attempt == ATTEMPTS:
                raise  # out of attempts: stop with the real error
            wait_seconds = 5 * attempt
            print(f"    attempt {attempt} failed ({error}); retrying in {wait_seconds}s")
            time.sleep(wait_seconds)


def weekly_chunks(first_day, last_day):
    """
    Split a date range into pieces of up to 7 days.
    Example: 30 Dec -> 12 Jan becomes (30 Dec, 5 Jan) and (6 Jan, 12 Jan).
    Both days of each piece are included.
    """
    start = first_day
    while start <= last_day:
        end = min(start + timedelta(days=6), last_day)
        yield start, end
        start = end + timedelta(days=1)


def start_fresh(folder):
    """Delete a folder's old files so every run is a clean re-download."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)


def save_json(rows, folder, first_day, last_day):
    path = folder / f"{first_day}_{last_day}.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def fetch_actuals():
    """Actual wind generation (FUELHH), wind only, one week at a time."""
    print("Actuals (FUELHH, WIND):")
    start_fresh(RAW_ACTUALS_DIR)
    total = 0
    for first_day, last_day in weekly_chunks(ACTUALS_FIRST_DAY, ACTUALS_LAST_DAY):
        rows = get_with_retry(
            f"{BASE_URL}/FUELHH/stream",
            {
                "settlementDateFrom": first_day.isoformat(),
                "settlementDateTo": last_day.isoformat(),
                "fuelType": "WIND",
            },
        )
        save_json(rows, RAW_ACTUALS_DIR, first_day, last_day)
        print(f"    {first_day} -> {last_day}: {len(rows)} rows")
        total += len(rows)
    print(f"    total: {total} rows")


def fetch_forecasts():
    """
    Wind forecasts (WINDFOR), chosen by PUBLISH time, one week at a time.
    Elexon includes both ends of the time filter, so each piece ends at 23:59:59
    to stop the pieces overlapping.
    """
    print("Forecasts (WINDFOR):")
    start_fresh(RAW_FORECASTS_DIR)
    total = 0
    for first_day, last_day in weekly_chunks(
        FORECASTS_FIRST_PUBLISH_DAY, FORECASTS_LAST_PUBLISH_DAY
    ):
        rows = get_with_retry(
            f"{BASE_URL}/WINDFOR/stream",
            {
                "publishDateTimeFrom": f"{first_day}T00:00:00Z",
                "publishDateTimeTo": f"{last_day}T23:59:59Z",
            },
        )
        save_json(rows, RAW_FORECASTS_DIR, first_day, last_day)
        print(f"    published {first_day} -> {last_day}: {len(rows)} rows")
        total += len(rows)
    print(f"    total: {total} rows")


def main():
    fetch_actuals()
    fetch_forecasts()
    print("Download finished. Next step: python -m app.data.clean")


if __name__ == "__main__":
    main()
