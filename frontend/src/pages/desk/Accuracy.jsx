/*
  ACCURACY: two ASCII bar charts.
    1. "The miss grows the further ahead you look"  (/api/horizon-curve)
       lean and wobble as separate bars, the slider's value highlighted.
    2. "When is the forecast shakiest?"              (/api/breakdowns)
       by 3-hour block of the day, and by wind level (with the MW thresholds used).
*/

import { getBreakdowns, getHorizonCurve } from '../../api.js'
import { asciiBar, fmtMw } from '../../art/ascii.js'
import { ErrorNote, Loading } from '../../components/Status.jsx'
import { useApi } from '../../hooks/useApi.js'

const BAR = 12 // characters per bar
const EVERY = 3 // show every 3rd hour ahead (plus the slider's value and the last one)
const WIND_ORDER = ['low', 'medium', 'high'] // the API may send them in another order

const clampDate = (date, range) => (date < range.start ? range.start : date > range.end ? range.end : date)
const mw = (value) => (value == null ? '—' : fmtMw(value)).padStart(6, ' ')

function HorizonBars({ config, settings, series }) {
  // The curve is always "hours ahead" data, so keep the dates inside that mode's range.
  const range = config.date_ranges.horizon
  const start = clampDate(settings.start, range)
  const end = clampDate(settings.end, range)
  const curve = useApi(() => getHorizonCurve({ start, end }), [start, end])

  const { min, max } = config.horizon_slider
  const isHorizon = settings.mode === 'horizon'
  // In Decision day mode, show how old those forecasts were, using the chart's rows.
  const leads = !isHorizon && series ? series.rows.map((r) => r.lead_time_h).filter((v) => v != null) : []
  const oldest = leads.length ? Math.max(...leads) : null
  const newest = leads.length ? Math.min(...leads) : null

  let body
  if (curve.error) body = <ErrorNote message={curve.error} />
  else if (!curve.data) body = <Loading />
  else {
    const shown = curve.data.points.filter(
      (p) => (p.hours_ahead - min) % EVERY === 0 || p.hours_ahead === max || (isHorizon && p.hours_ahead === settings.horizon),
    )
    const biggest = Math.max(...shown.flatMap((p) => [Math.abs(p.lean_mw ?? 0), p.wobble_mw ?? 0]))
    body = (
      <>
        <table className="ascii-table">
          <caption className="sr-only">
            Lean (how far too high on average) and wobble (how much the error jumps around), in MW,
            for each number of hours ahead.
          </caption>
          <thead>
            <tr>
              <th scope="col">ahead</th>
              <th scope="col" className="ascii-table__lean">lean (too high)</th>
              <th scope="col" className="ascii-table__wobble">wobble</th>
              <th scope="col">avg miss</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((p) => {
              const current = isHorizon && p.hours_ahead === settings.horizon
              const inDecisionSpan = oldest != null && p.hours_ahead >= Math.floor(newest) && p.hours_ahead <= oldest
              return (
                <tr
                  key={p.hours_ahead}
                  className={current ? 'is-current' : inDecisionSpan ? 'is-span' : undefined}
                  aria-current={current ? 'true' : undefined}
                >
                  <th scope="row">
                    {`${p.hours_ahead}h`.padStart(3, ' ')}
                    {current ? ' ◀' : ''}
                  </th>
                  <td>
                    <span className="ascii-table__lean" aria-hidden="true">
                      {asciiBar(-(p.lean_mw ?? 0), biggest, BAR)}
                    </span>{' '}
                    {mw(p.lean_mw)}
                  </td>
                  <td>
                    <span className="ascii-table__wobble" aria-hidden="true">
                      {asciiBar(p.wobble_mw ?? 0, biggest, BAR)}
                    </span>{' '}
                    {mw(p.wobble_mw)}
                  </td>
                  <td>{mw(p.average_miss_mw)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="section-note">
          {isHorizon
            ? `◀ your slider (${settings.horizon}h). Lean is the steady over-forecast; wobble is the jumping around on top of it.`
            : oldest != null
              ? `Shaded: Decision day forecasts are ${newest}–${oldest}h old by the hour they cover.`
              : 'Decision day forecasts use one fixed deadline, so their age varies by hour.'}
        </p>
      </>
    )
  }

  return (
    <section className="panel panel--half" aria-labelledby="horizon-title">
      <h2 id="horizon-title" className="section-title">
        The miss grows the further ahead you look
      </h2>
      <p className="section-sub">
        MW by hours ahead · {start} → {end}
      </p>
      {body}
    </section>
  )
}

function BreakdownTable({ rows, caption, highlight }) {
  const biggest = Math.max(...rows.map((r) => r.average_miss_mw))
  return (
    <table className="ascii-table">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          <th scope="col">{rows[0]?.group.includes('-') ? 'UTC' : 'wind'}</th>
          <th scope="col">avg miss</th>
          <th scope="col">too high</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.group} className={highlight && r.average_miss_mw === biggest ? 'is-worst' : undefined}>
            <th scope="row">{r.group.replace('-', '–')}</th>
            <td>
              <span aria-hidden="true">{asciiBar(r.average_miss_mw, biggest, BAR + 4)}</span> {mw(r.average_miss_mw)}
            </td>
            <td>{`${Math.round(r.pct_hours_too_high)}%`.padStart(4, ' ')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Shakiest({ query }) {
  const params = { mode: query.mode, start: query.start, end: query.end, horizon: query.horizon }
  const key = JSON.stringify(params)
  const parts = useApi(() => getBreakdowns(params), [key])
  const which = query.mode === 'horizon' ? `${query.horizon}h ahead` : 'decision day'

  let body
  if (parts.error) body = <ErrorNote message={parts.error} />
  else if (!parts.data) body = <Loading />
  else {
    const t = parts.data.wind_level_thresholds
    body = (
      <>
        <p className="section-sub">Average miss (MW) by time of day · {which}</p>
        <BreakdownTable rows={parts.data.time_of_day} caption="Average miss by 3-hour block of the day (UTC)" highlight />
        <p className="section-sub section-sub--gap">By wind level · grouped by the FORECAST</p>
        <BreakdownTable
          rows={[...parts.data.wind_level].sort((a, b) => WIND_ORDER.indexOf(a.group) - WIND_ORDER.indexOf(b.group))}
          caption="Average miss by wind level, grouped by the forecast"
        />
        <p className="section-note">
          low &lt; {fmtMw(t.low_to_medium_mw)} MW ≤ medium &lt; {fmtMw(t.medium_to_high_mw)} MW ≤ high. Split
          points are thirds of these dates’ forecasts; the forecast is used because the actual is unknown at
          decision time.
        </p>
      </>
    )
  }

  return (
    <section className="panel panel--half" aria-labelledby="shaky-title">
      <h2 id="shaky-title" className="section-title">
        When is the forecast shakiest?
      </h2>
      {body}
    </section>
  )
}

export default function Accuracy({ config, settings, query, series }) {
  return (
    <div id="accuracy" className="split">
      <HorizonBars config={config} settings={settings} series={series} />
      <Shakiest query={query} />
    </div>
  )
}
