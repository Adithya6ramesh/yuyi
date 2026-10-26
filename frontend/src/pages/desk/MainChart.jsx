/*
  The desk's main chart: actual, forecast, safety range, the test week marked, and a
  details line for whichever hour the user points at (mouse, finger or arrow keys).
*/

import { useState } from 'react'
import { fmtMw } from '../../art/ascii.js'
import SeriesChart from '../../components/SeriesChart.jsx'
import { addDays, dateSpan, dayMonthTime } from '../../dates.js'

// the chart's drawing area, in SeriesChart's coordinates
const TOP = 20
const BOTTOM = 264
const RIGHT = 984

/** Shade the back-test week, if it falls inside the dates on screen. */
function testWeek(period) {
  return (layout) => {
    const from = Math.max(Date.parse(`${period.start}T00:00:00Z`), layout.start)
    const to = Math.min(Date.parse(`${addDays(period.end, 1)}T00:00:00Z`), layout.end)
    if (from >= to) return null
    const x1 = layout.x(from)
    const x2 = layout.x(to)
    const nearRight = x1 > RIGHT - 260
    return (
      <g aria-hidden="true">
        <rect x={x1} y={TOP} width={x2 - x1} height={BOTTOM - TOP} style={{ fill: 'var(--bg-hover)' }} />
        <path
          d={`M${x1.toFixed(1)} ${TOP} V${BOTTOM}`}
          style={{ stroke: 'var(--line-strong)', strokeWidth: 1, strokeDasharray: '3 4' }}
        />
        <text
          x={nearRight ? Math.min(x2, RIGHT) - 6 : x1 + 8}
          y={TOP + 14}
          style={{
            fill: 'var(--muted-2)',
            fontSize: 11,
            fontFamily: 'var(--mono)',
            textAnchor: nearRight ? 'end' : 'start',
          }}
        >
          ▸ TEST WEEK · CUSHION NEVER SAW THESE DAYS
        </text>
      </g>
    )
  }
}

function HourDetails({ row }) {
  if (!row) {
    return (
      <p className="chart-details chart-details--hint">
        ▸ Hover, tap, or focus the chart and use the arrow keys to read any hour.
      </p>
    )
  }
  const miss = row.error_mw
  return (
    <p className="chart-details">
      <span>▸ {dayMonthTime(row.time)}</span>
      <span className="chart-details__actual">actual {row.actual_mw == null ? '—' : `${fmtMw(row.actual_mw)} MW`}</span>
      <span className="chart-details__forecast">
        forecast {row.forecast_mw == null ? '—' : `${fmtMw(row.forecast_mw)} MW`}
      </span>
      <span className={miss < 0 ? 'chart-details__short' : undefined}>
        miss {miss == null ? '—' : `${miss < 0 ? '−' : '+'}${fmtMw(Math.abs(miss))} MW`}
      </span>
      <span>
        forecast published {row.publish_time ? `${dayMonthTime(row.publish_time)} (${row.lead_time_h}h before)` : '—'}
      </span>
    </p>
  )
}

export default function MainChart({ series, settings, config, updating }) {
  const [cursor, setCursor] = useState(null)
  const rows = series?.rows ?? []
  const row = cursor != null && cursor < rows.length ? rows[cursor] : null
  const deadline = config.decision_deadline.time_utc
  const which =
    settings.mode === 'horizon'
      ? `forecasts made ${settings.horizon}h ahead`
      : `forecast available at ${deadline} the day before`

  return (
    <section className="panel" aria-labelledby="chart-title">
      <div className="chart-head">
        <h2 id="chart-title" className="chart-head__title">
          GB wind output · hourly · {which}
          {updating && (
            <span className="chart-head__updating">
              {' '}
              · updating <span className="blink" aria-hidden="true">▍</span>
            </span>
          )}
        </h2>
        <p className="legend">
          <span className="legend--actual">━ actual</span>
          <span className="legend--forecast">╍ forecast</span>
          <span>░ {settings.confidence}% range</span>
          <span>▒ test week</span>
        </p>
      </div>
      {rows.length > 0 && (
        <SeriesChart
          rows={rows}
          cursorIndex={cursor}
          onCursorChange={setCursor}
          label={`Line chart: actual wind output and the ${which}, ${dateSpan(series.start, series.end)}, with the ${settings.confidence}% safety range. The back-test week is shaded.`}
        >
          {testWeek(config.backtest.test_period)}
        </SeriesChart>
      )}
      {/* aria-live: screen readers read out the hour as the user moves through the chart */}
      <div aria-live="polite">
        <HourDetails row={row} />
      </div>
    </section>
  )
}
