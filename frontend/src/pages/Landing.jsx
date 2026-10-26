/*
  THE LANDING PAGE ("/"), rebuilt from design/Main.dc.html.

  Every number on it comes from the API:
    /api/config   default hours-ahead, caution level, month
    /api/summary  hours checked, lean, cushion
    /api/backtest coverage on the unseen week
    /api/series   the preview chart, and the "one hour, many forecasts" example
    /api/quality  how many forecast versions an hour typically gets
*/

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { getBacktest, getConfig, getQuality, getSeries, getSummary } from '../api.js'
import { asciiBar, fmtAbout, fmtMw } from '../art/ascii.js'
import { AsciiTurbineArt, FlowFieldBand, HeroScene, Ticker } from '../components/Animations.jsx'
import MethodFlow from '../components/MethodFlow.jsx'
import SeriesChart from '../components/SeriesChart.jsx'
import { ErrorNote, Loading } from '../components/Status.jsx'
import { addDays, dateSpan, dayMonth, dayMonthTime, daysBetween, monthYear, yearMonth } from '../dates.js'
import { useAnimationClock } from '../hooks/useAnimationClock.js'
import { useApi } from '../hooks/useApi.js'
import './landing.css'

export const TAGLINE = 'Don’t guess the gust, buy what you must.'
const WALKTHROUGH_EMAIL = 'mailto:hello@example.com?subject=Windhedge%20walkthrough' // placeholder
const EXAMPLE_HOUR = '10:00' // the hour used in the "one hour, many forecasts" example

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

/** The 2 days in the middle of the month: used for the preview chart. */
function previewDays(config) {
  const { start, end } = config.date_ranges.horizon
  const first = addDays(start, Math.floor((daysBetween(start, end) - 1) / 2))
  return { start: first, end: addDays(first, 1) }
}

/**
 * One real hour, as forecast at the longest, default and shortest hours-ahead:
 * three forecasts published at different times, plus what actually happened.
 */
async function loadConvergence(config, day) {
  const { min, max, default: usual } = config.horizon_slider
  const horizons = [...new Set([max, usual, min])]
  const answers = await Promise.all(
    horizons.map((horizon) =>
      getSeries({ start: day, end: day, horizon, confidence: config.default_confidence }),
    ),
  )
  const target = `${day}T${EXAMPLE_HOUR}:00Z`
  const seen = new Set()
  const versions = answers
    .map((answer) => answer.rows.find((row) => row.time === target))
    .filter((row) => row && row.forecast_mw != null && !seen.has(row.publish_time) && seen.add(row.publish_time))
  return { target, versions }
}

function useLandingData() {
  const config = useApi(getConfig, [])
  const cfg = config.data
  // ONE set of settings for every number on the page, so they can be matched on the desk
  const settings = cfg && {
    mode: cfg.default_mode,
    horizon: cfg.horizon_slider.default,
    confidence: cfg.default_confidence,
  }
  const days = cfg && previewDays(cfg)

  const summary = useApi(cfg && (() => getSummary(settings)), [cfg])
  const backtest = useApi(cfg && (() => getBacktest(settings)), [cfg])
  const preview = useApi(cfg && (() => getSeries({ ...settings, ...days })), [cfg])
  const convergence = useApi(cfg && (() => loadConvergence(cfg, days.end)), [cfg])
  const quality = useApi(getQuality, [])

  return { config, cfg, settings, days, summary, backtest, preview, convergence, quality }
}

// ---------------------------------------------------------------------------
// Text pictures built from the data
// ---------------------------------------------------------------------------

function convergenceText({ target, versions }) {
  const rule = '─────────────────────────────────────────────'
  const actual = versions[0]?.actual_mw
  const biggest = Math.max(actual ?? 0, ...versions.map((v) => v.forecast_mw))
  const bar = (mw) => asciiBar(mw, biggest, 15).replace(/·+$/, '')
  const mw = (value) => `${fmtMw(value)} MW`.padStart(9, ' ')
  return [
    `target      ${dayMonth(target)} · ${EXAMPLE_HOUR} UTC`,
    rule,
    'published      ahead    forecast',
    ...versions.map(
      (v) => `${dayMonthTime(v.publish_time)}   ${`${v.lead_time_h}h`.padStart(5, ' ')}   ${mw(v.forecast_mw)}  ${bar(v.forecast_mw)}`,
    ),
    rule,
    `actual                 ${mw(actual)}  ${bar(actual)}`,
  ].join('\n')
}

function leanWords(leanMw) {
  if (leanMw < -100) return `too high (~${fmtAbout(-leanMw)} MW)`
  if (leanMw > 100) return `too low (~${fmtAbout(leanMw)} MW)`
  return 'about right'
}

function readoutText({ cfg, settings, summary, backtest, rows, index }) {
  const dots = (name) => `${name} `.padEnd(23, '.') + ' '
  const row = rows[index]
  const miss = row.actual_mw - row.forecast_mw
  return [
    // every number below comes from exactly these settings (the desk's defaults)
    `windhedge$ evaluate --month ${yearMonth(cfg.date_ranges.horizon.start)} --mode ${settings.mode} ` +
      `--ahead ${settings.horizon}h --confidence ${settings.confidence}`,
    '── real output, January data ─────────────',
    dots('cursor') + dayMonthTime(row.time),
    dots('actual') + `${fmtMw(row.actual_mw)} MW`,
    dots('forecast') + `${fmtMw(row.forecast_mw)} MW`,
    dots('miss') + `${miss >= 0 ? '+' : '−'}${fmtMw(Math.abs(miss))} MW`,
    '',
    dots('hours checked') + fmtMw(summary.hours_counted),
    dots('forecast leans') + leanWords(summary.lean_mw),
    dots(`cushion @ ${settings.confidence}%`) +
      `${fmtAbout(summary.cushion_mw)} MW (learned ${summary.cushion_learned_from.label})`,
    dots('back-test coverage') +
      `${Math.round(backtest.actual_coverage_pct)}% (target ${backtest.target_pct}%)`,
    'windhedge$ ',
  ].join('\n')
}

// ---------------------------------------------------------------------------
// Sections that need data
// ---------------------------------------------------------------------------

function Convergence({ convergence }) {
  if (convergence.error) return <ErrorNote message={convergence.error} />
  if (!convergence.data) return <Loading />
  const { target, versions } = convergence.data
  const description =
    `Real example: forecasts for ${dayMonthTime(target)} UTC. ` +
    versions
      .map((v) => `Published ${dayMonthTime(v.publish_time)}: ${fmtMw(v.forecast_mw)} MW.`)
      .join(' ') +
    ` Actual: ${fmtMw(versions[0]?.actual_mw)} MW.`
  return (
    <>
      <p className="sr-only">{description}</p>
      <pre className="convergence" aria-hidden="true">
        {convergenceText(convergence.data)}
      </pre>
    </>
  )
}

/** The preview chart plus the terminal readout; a cursor walks through the real hours. */
function Preview({ data }) {
  const { cfg, settings, days, summary, backtest, preview } = data
  const [ref, seconds] = useAnimationClock(6)
  const rows = preview.data?.rows ?? []
  const index = rows.length ? Math.floor((seconds + 4) * 6) % rows.length : null

  const ready = cfg && summary.data && backtest.data && rows.length
  const error = data.config.error || summary.error || backtest.error || preview.error
  const readout = ready
    ? readoutText({ cfg, settings, summary: summary.data, backtest: backtest.data, rows, index })
    : null

  return (
    <div className="preview" ref={ref}>
      <div className="preview__chart">
        <div className="preview__head mono-label">
          <span>
            GB wind · {days ? dateSpan(days.start, days.end) : '…'} ·{' '}
            {settings ? `${settings.horizon} h ahead` : '…'}
          </span>
          <span className="legend">
            <span className="legend--actual">━ actual</span>
            <span className="legend--forecast">╍ forecast</span>
            <span>░ {settings ? `${settings.confidence}%` : ''} range</span>
          </span>
        </div>
        {error ? (
          <ErrorNote message={error} />
        ) : rows.length ? (
          <SeriesChart
            rows={rows}
            cursorIndex={index}
            label={`Line chart: actual wind output and the forecast made ${settings.horizon} hours ahead, ${dateSpan(days.start, days.end)}, with the ${settings.confidence}% safety range around the forecast.`}
          />
        ) : (
          <Loading />
        )}
      </div>
      <div className="preview__readout">
        {readout ? (
          <>
            <p className="sr-only">
              {`${summary.data.hours_counted} hours checked. Forecasts lean ${leanWords(summary.data.lean_mw)}. Cushion at ${settings.confidence}%: about ${fmtAbout(summary.data.cushion_mw)} MW. On the unseen test week the range covered ${Math.round(backtest.data.actual_coverage_pct)}% of hours against a target of ${backtest.data.target_pct}%.`}
            </p>
            <pre aria-hidden="true">
              {readout}
              <span className="blink">█</span>
            </pre>
          </>
        ) : error ? (
          <ErrorNote message={error} />
        ) : (
          <Loading label="windhedge$ loading" />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

const DESK_ROWS = [
  ['Forecast at decision time', 'What the forecast said when the order was due, not the hindsight version.'],
  ['Accuracy, in plain numbers', 'Average miss, worst miss, and whether forecasts lean too high or too low.'],
  ['A safety cushion', 'A realistic range around every forecast, at the caution level you choose.'],
  ['Proof it holds up', 'The cushion is checked against a week of days it never learned from.'],
]

export default function Landing() {
  const data = useLandingData()
  const { cfg, summary, quality } = data

  const month = cfg ? monthYear(cfg.date_ranges.horizon.start) : '…'
  const hours = summary.data ? fmtMw(summary.data.hours_counted) : '…'
  const versions = quality.data?.forecasts?.versions_per_january_target_hour?.typical

  // e.g. caution 90% -> the 5th and 95th percentiles of the misses
  const tail = cfg ? (100 - cfg.default_confidence) / 2 : null
  const pct = (p) => `p${String(p).padStart(2, '0')}`
  const percentiles = tail != null ? `${pct(tail)} / ${pct(100 - tail)}` : 'percentiles'
  const cushionFormula = tail != null ? `cushion = −${pct(tail)}(miss)` : 'cushion = a low percentile of the miss'

  const tickerText = useMemo(
    () =>
      [
        'FUELHH', 'fuelType = WIND', 'startTime', 'generation (MW)', 'WINDFOR', 'publishTime',
        'latest forecast before T − H', 'miss = actual − forecast', percentiles,
        'back-test on unseen days', 'day-ahead market',
      ].join(' ◆ ') + ' ◆',
    [percentiles],
  )

  return (
    <div className="landing">
      {/* TOP BAR */}
      <header className="topbar">
        <nav className="topbar__nav" aria-label="Main">
          <a href="#top" className="brand">
            <span className="brand__name">✻ Windhedge</span>
            <span className="brand__sub hide-sm">// wind forecast desk</span>
          </a>
          <div className="topbar__links hide-sm">
            <a href="#problem">[01] Problem</a>
            <a href="#method">[02] Method</a>
            <a href="#preview">[03] Preview</a>
          </div>
          <Link to="/desk" className="btn-solid btn-solid--small">
            Open the desk ↗
          </Link>
        </nav>
      </header>

      <main>
        {/* HERO */}
        <section id="top" className="hero wrap">
          <div className="hero__text">
            <p className="mono-label hero__eyebrow">▚ {TAGLINE}</p>
            <h1 className="hero__title">
              Tomorrow’s wind, <em>priced&nbsp;in</em> today.
            </h1>
            <p className="hero__lede">
              Windhedge shows your trading desk the wind forecast that existed when the order had to go
              in, how wrong that forecast has been, and how much margin to plan for.
            </p>
            <div className="actions">
              <Link to="/desk" className="btn-solid">
                Open the desk →
              </Link>
              <a className="link-ul" href="#method">
                Read the method
              </a>
            </div>
            <p className="hero__facts mono-label">
              <span>Hourly comparison</span>
              <span aria-hidden="true">/</span>
              <span>{hours} hours checked</span>
              <span aria-hidden="true">/</span>
              <span>{month}</span>
              <span aria-hidden="true">/</span>
              <span>Elexon BMRS</span>
            </p>
          </div>
          <HeroScene horizonHours={cfg?.horizon_slider.default} />
        </section>

        <Ticker text={tickerText} />

        {/* 01 PROBLEM */}
        <section id="problem" className="section wrap">
          <p className="section__number">[01] THE PROBLEM</p>
          <div className="problem">
            <div className="problem__left">
              <h2 className="section__title">
                Wind is the cheapest power on the grid. It is also the <em>hardest</em> to plan for.
              </h2>
              <ol className="points">
                <li>
                  <span className="points__mark">a.</span>
                  <div>
                    <h3>It changes its mind.</h3>
                    <p>Output swings by thousands of megawatts in a day. Orders go in the day before.</p>
                  </div>
                </li>
                <li>
                  <span className="points__mark">b.</span>
                  <div>
                    <h3>Forecasts keep rewriting themselves.</h3>
                    <p>
                      {versions
                        ? `One hour typically gets ${versions} forecasts. `
                        : 'One hour gets many forecasts. '}
                      Only those published before your deadline count.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="points__mark">c.</span>
                  <div>
                    <h3>A single number hides the risk.</h3>
                    <p>Without a range, nobody knows how much margin to buy.</p>
                  </div>
                </li>
              </ol>
            </div>
            <figure className="problem__right">
              <figcaption className="mono-label">One hour, many forecasts · real example</figcaption>
              <Convergence convergence={data.convergence} />
              <p className="problem__note">
                ↳ each new forecast replaces the last. Only the ones out before the deadline count, and
                the order can’t wait.
              </p>
            </figure>
          </div>
        </section>

        <FlowFieldBand />

        {/* 02 METHOD */}
        <section id="method" className="section wrap">
          <p className="section__number">[02] THE METHOD</p>
          <h2 className="section__title section__title--narrow">
            Three moves from raw data to a <em>confident</em> order.
          </h2>
          <MethodFlow
            cfg={cfg}
            quality={quality.data}
            summary={summary.data}
            backtest={data.backtest.data}
          />
          <ol className="steps">
            <li>
              <span className="steps__number">STEP 01</span>
              <div className="steps__text">
                <h3>Collect the official data</h3>
                <p>Actual wind output and every published forecast, downloaded once, cleaned and checked for gaps.</p>
              </div>
              <code>GET /datasets/FUELHH/stream · fuelType=WIND</code>
            </li>
            <li>
              <span className="steps__number">STEP 02</span>
              <div className="steps__text">
                <h3>Pick the forecast you’d really have had</h3>
                <p>For each hour, the latest forecast published before your deadline. Anything later is ignored.</p>
              </div>
              <code>forecast(T) = latest where publishTime ≤ T − H</code>
            </li>
            <li>
              <span className="steps__number">STEP 03</span>
              <div className="steps__text">
                <h3>Measure, then plan a cushion</h3>
                <p>Every miss is recorded. The bad hours become a safety margin, tested on a week it never saw.</p>
              </div>
              <code>miss = actual − forecast · {cushionFormula}</code>
            </li>
          </ol>
        </section>

        {/* WHAT THE DESK DOES */}
        <section className="section section--short wrap">
          <div className="desk-head">
            <p className="section__number">WHAT THE DESK DOES</p>
            <p className="desk-head__count">4 tools · 1 screen</p>
          </div>
          <ul className="desk-rows">
            {DESK_ROWS.map(([title, text]) => (
              <li key={title}>
                <Link to="/desk" className="desk-row">
                  <span className="desk-row__title">{title}</span>
                  <span className="desk-row__text">{text}</span>
                  <span className="desk-row__arrow" aria-hidden="true">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* 03 PREVIEW */}
        <section id="preview" className="section wrap">
          <p className="section__number">[03] PREVIEW</p>
          <h2 className="section__title section__title--narrow">
            Forecast, reality, and the <em>range</em> in between.
          </h2>
          <Preview data={data} />
        </section>

        {/* CTA */}
        <section className="cta">
          <div className="cta__inner wrap">
            <AsciiTurbineArt />
            <div className="cta__text">
              <h2 className="cta__title">
                See tomorrow’s wind <em>before</em> you buy.
              </h2>
              <p>Explore {month} on the desk, or walk through it with our team.</p>
              <div className="actions">
                <Link to="/desk" className="btn-solid">
                  Open the desk →
                </Link>
                <a className="link-ul" href={WALKTHROUGH_EMAIL}>
                  Book a walkthrough
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="footer__inner wrap">
          <span className="footer__brand">✻ Windhedge</span>
          <span>{TAGLINE}</span>
          <span>Data · Elexon BMRS · FUELHH + WINDFOR</span>
          <span>React · Python</span>
        </div>
      </footer>
    </div>
  )
}
