# Windhedge: design notes

*How the app is built, and why. Written for a technical reader. For what the data
showed, see [FINDINGS.md](FINDINGS.md).*

---

## 1. Overview

A UK energy company buys electricity on the **day-ahead market**: orders for tomorrow go
in today. Wind is a big and changeable share of supply, so the buyer needs to know two
things:

1. What did the national wind forecast say **at the moment the order was due**? (Not a
   later, better forecast, because that didn't exist yet.)
2. How wrong have those forecasts been, and so how much **safety margin** ("cushion")
   should be planned for?

Windhedge answers both for purchase decisions made in **January 2026**, using public
Elexon data. It **displays and evaluates existing forecasts**. It doesn't build a
prediction model of its own.

## 2. Architecture

```
 Elexon BMRS API ──(downloaded once)──▶ backend/data/raw/   (git-ignored)
                                           │ clean + quality checks
                                           ▼
                                 backend/data/processed/*.parquet  (committed, < 120 KB)
                                           │ loaded once at start-up
                                           ▼
   ┌──────────────────────── backend (Python, FastAPI) ────────────────────────┐
   │ app/core/matching.py  → which forecast was available at the deadline      │
   │ app/core/metrics.py   → miss, lean, wobble, breakdowns                    │
   │ app/core/cushion.py   → safety cushion + back-test                        │
   │ app/api/              → cached results served as JSON under /api          │
   └───────────────────────────────────────────────────────────────────────────┘
                                           │ HTTP / JSON
                                           ▼
   ┌──────────────────────── frontend (React, Vite) ───────────────────────────┐
   │ /      landing page (live numbers from the API)                           │
   │ /desk  dashboard: controls, chart, readouts, analysis                     │
   └───────────────────────────────────────────────────────────────────────────┘
```

| Folder | What's in it |
|---|---|
| `backend/app/data/` | Download (`fetch.py`), cleaning (`clean.py`), quality report (`quality.py`), settings |
| `backend/app/core/` | The maths: matching rule, metrics, cushion and back-test |
| `backend/app/api/` | FastAPI endpoints, input checks, caching, plain-English wording |
| `backend/data/processed/` | The clean data the app reads (Parquet) and `quality_report.json` |
| `backend/scripts/` | One-off scripts: data exploration, matching check, the accuracy report |
| `backend/tests/` | pytest tests |
| `frontend/src/` | React app: `api.js`, `pages/`, `components/`, `art/` (animation maths), `hooks/` |
| `frontend/design/` | The approved design mockups (reference only) |
| `docker-compose.yml` | Runs backend + frontend together |

## 3. Data

### Sources

Both are from Elexon's public BMRS API (no key needed):

| | **FUELHH** (what happened) | **WINDFOR** (what was forecast) |
|---|---|---|
| Endpoint | `/datasets/FUELHH/stream`, `fuelType=WIND` | `/datasets/WINDFOR/stream` |
| Filtered by | Settlement date | **Publish time only** (you can't ask for "forecasts for day X") |
| Time step | Every 30 minutes | Hourly, on the hour |
| Rows per time | One | Many: one per forecast version that covered it |

FUELHH's `WIND` covers wind farms the grid operator measures directly. As far as we can
tell, WINDFOR forecasts the same group, and the scale check below supports that.

### Date range, and why

The scope is decisions made **1–31 January 2026**:

- **Forecasts:** published from **30 Dec 2025 00:00 to 1 Feb 2026 00:00 UTC**. A decision
  just after midnight on 1 January uses the 31 December 22:30 forecast; one extra day
  is a safety margin.
- **Actuals:** **30 Dec 2025 to 3 Feb 2026**, to score every hour those forecasts cover,
  including deliveries on 1 February for the 31 January decision.

**Times are UTC everywhere.** In January UK time (GMT) equals UTC, so there's no clock
change to handle. The next one is 29 March 2026.

### Cleaning and quality checks

`python -m app.data.fetch` downloads in **weekly pieces with up to 4 attempts each**.
`python -m app.data.clean` keeps wind only, removes exact duplicates, **keeps every
forecast version**, saves Parquet, and writes `quality_report.json`:

| Check | Result |
|---|---|
| Actual half-hours present | **1,728 of 1,728** (36 days × 48), no gaps |
| Duplicates / empty / negative values | none, in either dataset |
| Forecasts published | 264 (**8 a day**, at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC); one came out at 12:25 instead of 11:30 on 15 Jan, which is harmless |
| Forecast rows | **19,272** (264 × 73 hours) |
| Versions per January hour | typically **24**, of which **19** were published before the hour |
| Scale check | average actual 11,581 MW vs average newest forecast 13,174 MW (ratio 1.14). Same scale, so same kind of quantity; the gap itself is a real finding (see FINDINGS) |

Non-exact repeats (the same hour twice with different values) would be **reported, not
silently removed**. None were found.

### Lead time: how far ahead is a forecast?

*Lead time = target hour − publish time.*

Each forecast covers a **fixed 73-hour window**, from 21:00 the evening before it's
published to 21:00 two days later. So:

- Its early hours are already in the past. **3,961 rows (21%) were published after
  their target hour.** These must never count as "available".
- How far ahead you can look depends on the hour of day. **Every January hour has
  forecasts from 0.5 h up to 43.5 h ahead**, and some (around 21:00) go up to 66.5 h.
- The newest forecast for any hour is at most **3.5 h** old (the overnight gap from
  22:30 to 02:30).

That's why the **"hours ahead" slider runs from 0 to 43 h** (default 24 h). Up to 43 h,
every hour has an answer, so the numbers are comparable. At 48 h, 155 hours (22:00–02:00
each day) would have no forecast.

## 4. The matching rule

> For a target hour **T** and "hours ahead" **H**, use the **most recent forecast whose
> `publish_time` is at or before T − H**. Anything published later is ignored, even if
> it's more accurate, because it didn't exist yet when the decision was made.

The rule is applied in exactly **one** place, `_newest_forecast_before()` in
`backend/app/core/matching.py`. It uses pandas' `merge_asof`, set to look **only
backwards in time** and only at forecasts for the same hour.

### Worked example: 12:00 UTC on 14 January 2026 (actual = 7,828 MW)

The hour has 24 forecast versions, published between 57.5 h before and 10.5 h after it.
What the rule picks (miss = actual − forecast; negative means the forecast was too high):

| H | Deadline | Picked (published) | Real lead time | Forecast | Miss |
|---|---|---|---|---|---|
| 1 | 14 Jan 11:00 | 14 Jan 09:30 | 2.5 h | 8,049 | −221 |
| 6 | 14 Jan 06:00 | 14 Jan 04:30 | 7.5 h | 8,036 | −208 |
| 12 | 14 Jan 00:00 | 13 Jan 22:30 | 13.5 h | 8,042 | −214 |
| 24 | 13 Jan 12:00 | 13 Jan 11:30 | 24.5 h | 7,043 | +785 |
| 36 | 13 Jan 00:00 | 12 Jan 22:30 | 37.5 h | 6,914 | +914 |
| 43 | 12 Jan 17:00 | 12 Jan 15:30 | 44.5 h | 7,270 | +558 |

- The **real lead time is always H or a bit more**, because forecasts only come out every
  2–4 hours. Every result row stores it.
- The three versions published *after* 12:00 (15:30, 18:30, 22:30) are never picked.
- One hour can be "lucky" (here H = 43 beat H = 36). Only month-wide numbers show the
  trend.

### Two modes

| | **Hours ahead** | **Decision day** |
|---|---|---|
| Deadline | Different for every hour: T − H | **One** for the whole delivery day: **09:50 UTC the day before** |
| Lead time | About H for every hour | 14.5 h (00:00) up to 37.5 h (23:00); 26.0 h on average |
| Answers | "How good is a forecast made H hours ahead?" | "What did the buyer really see when placing orders?" |

09:50 is the gate closure of **Nord Pool's GB day-ahead auction** (09:50 UK time = UTC in
January). It's one setting, `DECISION_DEADLINE_TIME` in `backend/app/data/settings.py`,
and **must be confirmed with the client**: other exchanges close at different times.

### "No cheating" protection

- **Built into the code:** after every match, `_newest_forecast_before()` checks that no
  chosen forecast was published after its deadline, and **stops with an error** if one
  was.
- **Tests** (`backend/tests/test_matching.py`, written alongside the rule) check:
  - forecasts published after the deadline are never used, even when they're more
    accurate;
  - "published exactly at the deadline" counts;
  - hours with no qualifying forecast stay empty (no guessing);
  - Decision day uses one deadline for all 24 hours.
- **API tests** check that no `/api/series` row has `publish_time` after its `deadline`,
  for H = 0, 24, 43 and Decision day.

## 5. Metrics and cushion

### Plain-English names (`app/core/metrics.py`)

| Name | Meaning | Formula |
|---|---|---|
| **miss** | How far off, ignoring direction | \|actual − forecast\| |
| **lean** | The steady tilt. Negative = forecasts run **too high** | mean(actual − forecast) |
| **wobble** | How much the error jumps around once the lean is removed | standard deviation of (actual − forecast) |
| overall miss | Root-mean-square error (big misses count more) | √mean(error²) |

They tie together exactly: **overall miss² = lean² + wobble²**. So we can say what share
of the problem is steady (lean) and what share is jumpy (wobble).

Breakdowns are by **3-hour block** (one clock hour has only 31 values in January, too
few to trust; a block has 93) and by **wind level**. Wind levels are grouped by the
**forecast**, never the actual, because at decision time the actual is unknown. The split
points divide the forecasts into equal thirds and are reported with the results.

### The cushion (`app/core/cushion.py`)

For a caution level C (80, 90 or 95%), cut off the worst (100 − C)/2 % of past errors on
each side:

- `lower` = the (100 − C)/2 percentile of the errors (the 5th for C = 90)
- `upper` = the 100 − (100 − C)/2 percentile (the 95th for C = 90)
- the range for a new forecast F is **[F + lower, F + upper]**
- **cushion = −lower**: the MW of wind to plan as "missing"

Two flavours were built:
- **one-size:** one band for every hour;
- **per-group:** a band per wind level.

### Back-test

- **Learn on 1–24 January, test on 25–31 January** (168 hours the cushion never saw).
- Nothing from the test week is used for learning, not even the per-group split points.
- The app shows the cushion **learned from the training weeks only**, and says so
  (`cushion_learned_from`). That makes it exactly the cushion the back-test checked, and
  makes the chart's shaded test week an honest test.
- The cost: it ignores the last (worst) week. For real purchases after January, re-learn
  from all available data.

### Why per-group was rejected

Windy-looking hours clearly miss more (see FINDINGS), so a per-wind-level cushion looked
promising. It **failed the back-test in every setting**:
- at 90% it covered 82% (H = 24) and 77% (Decision day) of unseen hours, against 95% and
  88% for one-size;
- it gave calm-looking hours a small cushion, because in 1–24 Jan they were only about
  500–950 MW too high;
- in the test week those hours were about 1,950–2,650 MW too high.

It's still available on the desk as a clearly labelled "experimental, failed the test"
toggle, for comparison only.

## 6. API

FastAPI, all under `/api`, JSON unless stated. Full details and a "Try it out" button are
on the automatic **`/docs`** page.

| Endpoint | Returns |
|---|---|
| `GET /api/health` | `{"status": "ok"}` and the dates available |
| `GET /api/config` | Slider limits, caution levels, modes, date ranges, deadline, data sources |
| `GET /api/series` | One row per hour: actual, forecast, publish time, deadline, lead time, error, range |
| `GET /api/summary` | Headline numbers, the cushion, `cushion_learned_from`, `plain_english` |
| `GET /api/horizon-curve` | For H = 0–43: average miss, lean, wobble, hours matched |
| `GET /api/breakdowns` | By 3-hour block and by wind level (with the thresholds) |
| `GET /api/backtest` | Train/test periods, coverage, caught-short %, no-cushion %, `honest_verdict` |
| `GET /api/decision-day` | One delivery day as seen at 09:50 the day before: 24 rows + daily averages |
| `GET /api/quality` | The data quality report |
| `GET /api/export.csv` | The `/api/series` rows as a CSV download |

- **Data loading and caching:** the data is loaded **once at start-up**. Results are
  **cached** per (mode, H, caution level), so repeat requests take about 0.01 s.
- **Precomputed results:** the two slowest calculations are also saved as small JSON
  files in `backend/data/processed/precomputed/` (`app/api/precomputed.py`):
  - the whole-month horizon curve (about 1–2.5 s to compute);
  - the Decision day table (about 1 s).

  A fresh copy of the API answers these in about 0.01–0.04 s instead. Other date ranges
  are still computed live.
  - **They can't go stale:** `scripts/precompute.py` makes them with the same functions
    the API uses, and `tests/test_precomputed.py` rebuilds them on every CI run and
    fails on any difference. A 1 MW change, or changed data without a re-run, is caught.
  - If the files are missing, the API simply computes live.
- **Input checks:** bad inputs return **422** with a plain-English `error`, e.g. *"horizon
  must be a whole number of hours from 0 to 43. 43 is the limit because…"*.
- **CORS:** the addresses allowed to call the API come from `ALLOWED_ORIGINS`
  (comma-separated; default `http://localhost:5173`).

## 7. Frontend

React + Vite, plain JavaScript and plain CSS (no UI kit, no chart library, no icon
library).

- **`src/api.js`:**
  - one function per endpoint; the base address comes from `VITE_API_URL` (empty in
    development: Vite's proxy forwards `/api` to the backend);
  - errors arrive as readable messages, e.g. *"Can't reach the server. Is the backend
    running?"*
- **Nothing hard-coded:** slider limits, caution levels, date ranges and the 09:50
  deadline all come from `/api/config`.
- **Desk:**
  - the settings live in one object, and the API is only asked once they stop changing
    for 300 ms (debounce), so dragging the slider sends one request, not dozens;
  - every section uses exactly the same settings.
- **Charts** are hand-drawn SVG (`components/SeriesChart.jsx`): actual, forecast, the
  shaded range and the test week, plus hover, tap and arrow-key reading. The analysis
  charts are ASCII bars inside real `<table>`s, so screen readers can read them.
- **Design rules:**
  - **Colours and type:** colours live in `styles/tokens.css`; Instrument Serif for
    headings, IBM Plex Mono for numbers, IBM Plex Sans for text.
  - **Shape:** hairline dividers, sharp corners, text symbols instead of icons.
  - **Not allowed:** gradients, glows or "card" layouts.
- **Animations** (3D wireframe turbine and terrain, ASCII wind field, ASCII turbine,
  ticker, mini mesh, the method flow chart's moving packet) share one clock,
  `hooks/useAnimationClock.js`. It **freezes** them when the computer asks for reduced
  motion, when the tab is hidden, and when they're scrolled out of view. CSS animations
  stop under reduced motion too.
- **Accessibility:**
  - real buttons, links and labels; everything reachable by keyboard, with a visible
    focus outline;
  - decorative ASCII and SVG are hidden from screen readers, with a text description
    where they carry meaning;
  - the chart can be read with the arrow keys.
- **Phones:** the sidebar stacks on top, panels stack, wide tables scroll inside their own
  box, and the chart uses larger, fewer labels on narrow screens.

## 8. Docker and deployment

`docker compose up --build` runs everything, then open <http://localhost:8080>.

- **backend image:**
  - `python:3.12-slim` with only the runtime requirements, the app and the processed data,
    so it needs no internet;
  - runs as a non-root user on `0.0.0.0:8000`, with a `HEALTHCHECK` on `/api/health`;
  - about 600 MB, mostly pandas, numpy and pyarrow.
- **frontend image:**
  - multi-stage: Node builds the React app, then unprivileged nginx serves it (about
    75 MB);
  - nginx sends unknown paths to `index.html` (so refreshing `/desk` works) and forwards
    `/api/` and `/docs` to the backend. The browser talks to one address, so no CORS is
    needed;
  - the frontend starts only once the backend is healthy.
- **Tests in Docker:** a separate `test` build stage runs them
  (`docker compose --profile test run --rm backend-tests`). The normal image contains no
  tests and no pytest.

**Hosting:** the brief allows Vercel or Heroku. The app is set up for **Vercel**, using its
native (generally available) FastAPI support. It's one Vercel project with **Root Directory
`backend/`**:

- **Finding the app:** Vercel finds `app/main.py` and its `app` by itself, and installs the
  dependencies listed in `backend/pyproject.toml`. That list must match `requirements.txt`,
  and a test checks it does.
- **Building the website:** the build step (`scripts/build_frontend.py`, set in
  `pyproject.toml`) builds the React app into `backend/frontend_dist/`.
- **One address:** `main.py` hands that folder to FastAPI's `app.frontend("/",
  fallback="index.html")`, and Vercel serves those files from its CDN. So the site and the
  API share one address:
  - `/api/*`, `/docs` and `/openapi.json` reach FastAPI (API routes always win);
  - every other page address gets `index.html`, so refreshing `/desk` works and unknown
    addresses show the app's 404 screen.
  - The frontend keeps calling `/api/...` (`VITE_API_URL` stays empty), and no CORS is
    needed. `ALLOWED_ORIGINS` still works for other setups.
- **What goes into the function:** the processed data travels with the function.
  `backend/vercel.json` (`excludeFiles`) leaves out tests, scripts, raw and sample data, and
  caches. The bundle is far below Vercel's 500 MB Python limit.
- **Python version:** Vercel offers 3.12–3.14, so Docker and CI use **3.12** too, and NumPy
  is pinned to the tested version.
- **Cold starts:** each new serverless copy has to start Python, load pandas and read the
  data (about 1 s). The slowest results are precomputed (see §6), so nothing on the first
  page load has to be worked out from scratch.
- **Why not run our Docker image on Vercel?** Vercel's Container Runtime can now run Docker
  images, but it's in **beta**. The native runtime is generally available and serves the
  React build from the CDN.
- **Heroku** would run the container directly but has no free plan.
- Docker is still proven on every push: CI builds and starts both images (see §9).

**Live site:** <https://windhedge.vercel.app>

**Security** (checked with a full audit):

- **Headers:** every response carries security headers, set in `backend/vercel.json` for
  Vercel and in `frontend/security-headers.conf` + `nginx.conf` for Docker:
  - a strict **Content-Security-Policy**: only our own scripts run; styles and fonts also
    from Google Fonts. `/docs` gets a slightly looser one, because Swagger UI loads from
    cdn.jsdelivr.net;
  - `X-Frame-Options: DENY` (no clickjacking);
  - `X-Content-Type-Options: nosniff`;
  - a `Referrer-Policy`;
  - a `Permissions-Policy` (no camera, microphone or location).
  - Vercel adds HTTPS-only (HSTS) and redirects http → https.
- **CORS:** the API only accepts calls from other sites listed in `ALLOWED_ORIGINS`. On
  Vercel the default is none (same address); locally it's the Vite dev server.
- **Inputs:** every input is type- and range-checked (422 with a plain message).
  - There's no database, no login, no user data and no file upload.
  - Error pages don't show internals.
  - The CSV export only contains numbers and dates, with a filename built from checked
    inputs.
- **Containers:** both run as non-root users.
- **Secrets:** there are none in the code or the git history (checked), and `.env` files
  are ignored.
- **Dependencies:** pinned, and checked on every push by CI's `audit` job (`pip-audit` +
  `npm audit`). The audit upgraded pyarrow (to 23.0.1), requests and pytest past known
  vulnerabilities. The pyarrow one (a bug when reading Arrow IPC files) couldn't be
  triggered here, because we only read our own Parquet files.
- **CI:** its token is read-only (`permissions: contents: read`).
- **Not done (not needed at this size):** rate limiting (Vercel's firewall can add it),
  pinning GitHub Actions to exact commit IDs, and self-hosting the Google Fonts (visitors'
  browsers contact Google to load them).

**Deploying:**
1. On vercel.com, choose Add New → Project and import the GitHub repository.
2. Set **Root Directory** to `backend` and keep "Include files outside the root directory in
   the Build Step" on (the build needs `frontend/`).
3. Deploy. No environment variables are needed.

Every push to `main` then redeploys.

## 9. Testing and CI

| Where | What | How to run |
|---|---|---|
| `backend/tests/` (pytest) | Cleaning, matching rule (incl. "no cheating"), metrics with hand-checkable numbers, cushion and back-test, every API endpoint, bad inputs, CSV columns, CORS setting, Vercel setup, precomputed results match the live code | `cd backend` → `.venv\Scripts\python.exe -m pytest` |
| `frontend/src/test/` (Vitest + Testing Library) | Friendly API errors, URL building, slider → request (with debounce), CSV link, Decision day mode, keyboard access, 404 page | `cd frontend` → `npm test` |
| Lint / format | ruff (backend), ESLint + Prettier (frontend) | see README |

**CI** (`.github/workflows/ci.yml`, GitHub Actions, on every push and pull request) has
three jobs:

1. **backend:** Python 3.12, `ruff check`, `ruff format --check`, `pytest`.
2. **frontend:** Node 22, `npm ci`, ESLint, Prettier check, `npm test`, `npm run build`.
3. **docker:** builds both images, starts them with `docker compose`, waits until
   `/api/health` answers **through nginx on port 8080**, then stops them.

## 10. Key decisions and trade-offs

| Decision | Why | Alternative considered |
|---|---|---|
| Compare at **on-the-hour times only** | WINDFOR is hourly; we never invent forecast values | Average the :00 and :30 actuals; or stretch each forecast over both half-hours |
| **Keep every forecast version** | The "available at the deadline" rule needs the full history | Keep only the latest forecast, which would make the rule impossible |
| **Parquet** for processed data | Keeps exact types (UTC times stay times) and is small (< 120 KB) | CSV: bigger, and types must be re-parsed |
| **Weekly downloads with retries** | One failed request doesn't mean starting over | One request per dataset (works, but fragile) |
| Rule in **one function** with a built-in check | One place to get right and test; it fails loudly if broken | Repeating the logic per mode |
| Slider **0–43 h**, default 24 h | Every January hour has a forecast up to 43.5 h ahead | 0–48 h, which would leave 155 empty hours |
| Decision day deadline **09:50** | Nord Pool GB day-ahead gate closure | EPEX or other auction times (configurable; confirm with client) |
| **3-hour blocks** for time of day | 93 values per block vs 31 per clock hour | Single hours (too noisy) |
| Wind level by **forecast**, not actual | The actual is unknown at decision time | Grouping by actual, which looks better but cheats |
| **One-size cushion** by default | Passed the back-test; per-group failed it | Per-wind-level cushion (kept as "experimental") |
| Cushion learned from **training weeks only** | Matches the back-test; the test week stays an honest test | Learn from all of January (bigger cushion, but the chart would be graded on its own homework) |
| Load data **once**, cache per setting | Repeat clicks are instant | Recompute per request (about 1 s for Decision day) |
| **Hand-drawn SVG charts** | Exact match to the design, no library styling leaking through, small bundle | A chart library: less code, harder to restyle |
| **JavaScript**, not TypeScript | Simpler for a first React project | TypeScript: safer types, more to learn |
| **nginx forwards `/api`** in Docker | One address, so no CORS needed | Expose both containers and configure CORS |
| **Vercel** for hosting | Free; both brief platforms considered | Heroku container (paid); Render or Fly (not in the brief) |

## 11. Limitations, and what I'd build next

**Limitations**
- **One month of data** (January 2026). Other months and seasons may behave differently.
- **Small learning sample for the cushion.** The 90% cushion is set by the worst 5% of 576
  learning hours, so about 29 hours, and at H = 24 25 of those 29 come from **one storm on
  11–12 January**. So neighbouring settings can land in a surprising order:
  - The H = 43 cushion (5,050 MW) comes out slightly *smaller* than H = 24's (5,100 MW),
    even though misses grow with H.
  - The reason: in the learning weeks, 43-hour forecasts happened to lean a little less
    too high (−1,592 vs −1,722 MW).
  - Learned from all of January, the expected order returns: 5,614 vs 5,097 MW.
  - The method was deliberately not changed to hide this. Differences of a few hundred MW
    between settings are noise.
- **The test week was unusual:** its lean was −2,508 MW vs −1,531 MW in the learning
  weeks (Decision day). The over-forecast isn't stable even within a month.
- The **09:50 deadline** is Nord Pool's; **confirm the client's actual auction**.
- **Curtailment** (wind farms paid to switch off when the grid is full) is the likely
  reason forecasts run high on windy hours. It's **not proven**: we have no curtailment or
  demand data.
- **No demand or price data**, so the app can't say what a miss *costs*, only its size in
  MW.
- **National level only:** no regional or per-wind-farm view.

**What I'd build next**
1. More months of data, re-learning the cushion as each week arrives (a rolling window).
2. Bring in curtailment data (e.g. Elexon balancing actions) to test the curtailment
   explanation.
3. Bring in prices, so the cushion can be sized by cost, not just by % of hours covered.
4. A cushion that adapts to recent lean (e.g. last 7 days), if a longer back-test supports it.
5. Handle British Summer Time properly before using months outside winter.

## 12. How AI tools were used

The app was built with **Claude** (Anthropic's AI assistant, through Claude Code) acting
as a senior full-stack engineer and mentor. I directed the work; the AI wrote most of the
code and documents under these working rules:

- **Phase by phase.** The work was split into phases: data, matching rule, metrics,
  API, frontend, Docker, quality, deployment. The AI did **only the phase asked for**,
  then stopped for review.
- **Plan first, then approve.** Each phase started with a plain-English plan, and work
  began only after I said "go". Where something was unclear, the AI was told to **ask
  instead of guessing** (e.g. the decision deadline, the brand name, which cushion
  period to show).
- **Tests first on tricky logic.** The forecast-matching rule was written with its
  tests: forecasts published after the deadline must never be used. That check is also
  built into the code itself. Metrics and cushion tests use small, hand-checkable
  numbers.
- **Honesty rules.**
  - Report failures as they are: the per-group cushion is shown as "failed the test",
    not hidden.
  - Explain surprising results instead of "fixing" the method to hide them (the H = 43
    cushion).
  - Mark unproven explanations (curtailment) as unproven.
  - Every number in these documents was re-checked against the code.
- **No prediction model.** The AI was explicitly told never to build an AI or
  machine-learning forecast. The job is to display and evaluate the existing forecasts.
- **Plain English.** I'm a beginner, so every step was explained without jargon, and the
  app's own wording ("miss", "lean", "wobble", "cushion", "caught short") follows the
  same rule.
- **Design.** The visual design (landing page and dashboard mockups in
  `frontend/design/`) was made with AI assistance, then rebuilt by hand as React
  components.

I reviewed every plan and result, chose between the options offered, and asked for
changes. For example, I had the method diagram redrawn, and had the readout show its
exact settings so its numbers could be matched against the desk.
