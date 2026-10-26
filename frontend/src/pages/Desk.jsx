/*
  THE DESK ("/desk"), rebuilt from design/Dashboard.dc.html.

  How it works:
    1. Load /api/config (limits, defaults, dates, deadline).
    2. Keep the user's settings (mode, dates, hours ahead, caution) in one object.
    3. Wait until the settings stop changing for a moment (debounce), then ask the API
       for the chart rows (/api/series) and the numbers (/api/summary) with exactly
       those settings. The analysis sections below use the same settings.
*/

import { useState } from 'react'
import { exportCsvUrl, getConfig, getSeries, getSummary } from '../api.js'
import SkipLink from '../components/SkipLink.jsx'
import { ErrorNote, Loading } from '../components/Status.jsx'
import { monthYear } from '../dates.js'
import { useApi } from '../hooks/useApi.js'
import { useDebouncedValue } from '../hooks/useDebouncedValue.js'
import Accuracy from './desk/Accuracy.jsx'
import Backtest from './desk/Backtest.jsx'
import Controls from './desk/Controls.jsx'
import DataChecks from './desk/DataChecks.jsx'
import DecisionReplay from './desk/DecisionReplay.jsx'
import MainChart from './desk/MainChart.jsx'
import Readouts from './desk/Readouts.jsx'
import Sidebar from './desk/Sidebar.jsx'
import './desk.css'

const DEBOUNCE_MS = 300

function defaultSettings(config) {
  const mode = config.default_mode
  return {
    mode,
    start: config.date_ranges[mode].start,
    end: config.date_ranges[mode].end,
    horizon: config.horizon_slider.default,
    confidence: config.default_confidence,
  }
}

/** Keep a date inside the allowed range (used when switching mode). */
const clamp = (date, range) => (date < range.start ? range.start : date > range.end ? range.end : date)

/** A plain-English problem with the dates, or null if they are fine. */
function datesProblem({ mode, start, end }, config) {
  const range = config.date_ranges[mode]
  if (!start || !end) return 'Pick both a start and an end date.'
  if (start < range.start || end > range.end)
    return `Dates must be between ${range.start} and ${range.end} in this view.`
  if (start > end) return 'The start date is after the end date. Pick a start on or before the end.'
  return null
}

/** The settings as API parameters (hours ahead only matters in "hours ahead" mode). */
function toQuery({ mode, start, end, horizon, confidence }) {
  return { mode, start, end, confidence, horizon: mode === 'horizon' ? horizon : undefined }
}

function DeskHeader({ month, exportHref }) {
  return (
    <header className="desk__header">
      <div>
        <p className="mono-label">Desk / {month} / Wind</p>
        <h1 className="desk__title">
          How far can you trust the <em>forecast</em>?
        </h1>
      </div>
      {exportHref && (
        // a link, not a fetch: the browser downloads the file itself
        <a className="btn-solid btn-solid--small" href={exportHref} download>
          ↓ Export CSV
        </a>
      )}
    </header>
  )
}

function DeskBody({ config }) {
  const [settings, setSettings] = useState(() => defaultSettings(config))
  const settled = useDebouncedValue(settings, DEBOUNCE_MS)

  const change = (update) =>
    setSettings((old) => {
      const next = { ...old, ...update }
      if (update.mode && update.mode !== old.mode) {
        // Viewing the whole range? Then show the whole range of the new mode, so the
        // numbers match the backend's defaults. Otherwise just keep the dates allowed.
        const before = config.date_ranges[old.mode]
        const range = config.date_ranges[update.mode]
        const wasWholeRange = old.start === before.start && old.end === before.end
        next.start = wasWholeRange ? range.start : clamp(next.start, range)
        next.end = wasWholeRange ? range.end : clamp(next.end, range)
      }
      return next
    })

  const problem = datesProblem(settled, config)
  const query = problem ? null : toQuery(settled)
  const key = JSON.stringify(query)
  const series = useApi(query && (() => getSeries(query)), [key])
  const summary = useApi(query && (() => getSummary(query)), [key])

  const error = series.error || summary.error
  const updating = series.loading || summary.loading || settings !== settled
  const ready = !problem && !error && summary.data

  return (
    <>
      <DeskHeader
        month={monthYear(config.date_ranges.horizon.start)}
        exportHref={query && exportCsvUrl(query)}
      />
      <Controls config={config} settings={settings} onChange={change} />

      {(problem || error) && (
        <div className="panel">
          <ErrorNote message={problem || error} />
        </div>
      )}
      {!problem && !error && !summary.data && (
        <div className="panel">
          <Loading />
        </div>
      )}

      {ready && (
        <>
          <section id="cushion" aria-label="Headline numbers">
            <Readouts summary={summary.data} confidence={summary.data.confidence} />
          </section>
          <MainChart series={series.data} settings={settled} config={config} updating={updating} />
          <Accuracy config={config} settings={settled} query={query} series={series.data} />
          <div id="decision" className="split">
            <DecisionReplay config={config} confidence={settled.confidence} />
            <div className="split__stack">
              <Backtest query={query} />
              <section className="panel plain" aria-labelledby="plain-title">
                <h2 id="plain-title" className="plain__label">
                  In plain English
                </h2>
                <p className="plain__text">
                  {summary.data.plain_english}
                  <span className="blink" aria-hidden="true">
                    ▍
                  </span>
                </p>
              </section>
            </div>
          </div>
        </>
      )}
      <DataChecks />
    </>
  )
}

export default function Desk() {
  const config = useApi(getConfig, [])

  return (
    <div className="desk">
      <SkipLink to="overview" />
      <Sidebar />
      <main id="overview" className="desk__main">
        {config.data ? (
          <DeskBody config={config.data} />
        ) : (
          <>
            <DeskHeader month="…" />
            <div className="panel">{config.error ? <ErrorNote message={config.error} /> : <Loading />}</div>
          </>
        )}
      </main>
    </div>
  )
}
