# UK wind forecast accuracy

A UK energy company buys electricity on the day-ahead market. This app shows the national
wind forecast that was available when each purchase decision was made, and measures how
accurate those forecasts were. That tells the company how big a safety margin to buy.

- **Data:** Elexon FUELHH (actual wind, every 30 minutes) and WINDFOR (national wind
  forecasts, every published version kept), for purchase decisions made in January 2026.
- **Times:** all UTC, which is the same as UK time in January.
- **No prediction model:** the app only displays and evaluates forecasts that already exist.

## API

The backend is a FastAPI app in `backend/`. Every endpoint is under `/api`, and every
date is a delivery day written as `YYYY-MM-DD`.

### Run it

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt   # first time only
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs>. This page is generated automatically. Click an
endpoint, then **Try it out**, then **Execute**.

Run the tests with `.venv\Scripts\python.exe -m pytest -v` (from `backend/`).

### Endpoints

| Endpoint | What it returns |
|---|---|
| `GET /api/health` | `{"status": "ok"}` and the dates the API can answer for |
| `GET /api/config` | Slider range, caution levels, modes, date ranges, decision deadline, data sources |
| `GET /api/series?start=&end=&horizon=24&confidence=90&mode=horizon` | One row per hour: actual, forecast, publish time, deadline, lead time, error, range low/high |
| `GET /api/summary?start=&end=&horizon=&confidence=&mode=` | Headline accuracy numbers, the cushion, and a `plain_english` explanation |
| `GET /api/horizon-curve?start=&end=` | For H = 0–43: average miss, lean, wobble, hours matched |
| `GET /api/breakdowns?start=&end=&horizon=&mode=` | Accuracy by 3-hour block and by wind level (with the thresholds used) |
| `GET /api/backtest?confidence=&horizon=&mode=&method=one_size\|per_group` | How the cushion did on the unseen week, plus an `honest_verdict` |
| `GET /api/decision-day?date=2026-01-15` | One delivery day as seen at 09:50 UTC the day before: 24 rows and daily averages |
| `GET /api/quality` | The Phase 1 data quality report |
| `GET /api/export.csv?start=&end=&horizon=&confidence=&mode=` | The `/api/series` rows as a CSV file |

**Choices you can make:**
- `mode`:
  - `horizon` uses the newest forecast made at least H hours before each hour.
  - `decision_day` uses the newest forecast available at 09:50 UTC the day before
    delivery. H is ignored in this mode.
- `horizon`: 0–43, default 24.
- `confidence`: 80, 90 or 95, default 90.
- `method`: `one_size` (default) or `per_group`. **`per_group` is experimental: it failed
  the back-test.**
- `start`, `end` (both included):
  - `horizon` mode: 2026-01-01 to 2026-01-31.
  - `decision_day` mode: 2026-01-02 to 2026-02-01, because the 31 January decision is
    for 1 February.
  - Leave them out to get the whole range.

If an input isn't allowed, you get status 422 with a plain-English `error`, for example:
`horizon must be a whole number of hours from 0 to 43. 43 is the limit because...`

### Example

`GET /api/summary?horizon=24&confidence=90` (numbers shortened):

```json
{
  "mode": "horizon", "horizon": 24, "confidence": 90,
  "start": "2026-01-01", "end": "2026-01-31",
  "hours_counted": 744,
  "average_miss_mw": 2050.2,
  "lean_mw": -1854.2,
  "pct_hours_too_high": 86.8,
  "wobble_mw": 1703.5,
  "cushion_mw": 5096.25,
  "range_lower_mw": -5096.25,
  "range_upper_mw": 980.25,
  "cushion_learned_from": {"start": "2026-01-01", "end": "2026-01-24", "hours": 576,
                           "label": "1-24 January 2026"},
  "plain_english": "Forecasts made 24 hours ahead missed by about 2,050 MW on average and were too high in 87% of hours. To be covered 9 hours in 10, plan for about 5,100 MW less wind than the forecast says. This cushion was learned from 1-24 January 2026 only (the weeks before the back-test week)."
}
```

### Where the cushion is learned from

The cushion in `/api/series`, `/api/summary` and `/api/decision-day` is learned from the
**training weeks only** (1–24 January; 2–24 January in Decision Day mode). Every response
says so in `cushion_learned_from`.

**Why:**
- It's exactly the cushion the back-test checked, so "it covered 88% of the unseen week"
  is true of the number on screen.
- On the chart, the band over 25–31 January is a fair test. The cushion never saw those
  hours, so where the actual drops out of the band, that's a real miss.

**What it costs:**
- It ignores the last week, which was the worst-forecast week of the month. So the
  Decision Day cushion here is about 4,900 MW at 90%, against about 5,300 MW if learned
  from the whole month.
- For real purchases after January, re-learn the cushion from all the data you have.
