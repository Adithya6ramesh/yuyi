/*
  DECISION DAY REPLAY (/api/decision-day): pick a delivery date and see exactly what the
  buyer saw at the deadline the day before, hour by hour, next to what really happened.
*/

import { useState } from 'react'
import { getDecisionDay } from '../../api.js'
import { fmtMw } from '../../art/ascii.js'
import ScrollBox from '../../components/ScrollBox.jsx'
import { ErrorNote, Loading } from '../../components/Status.jsx'
import { dayMonthTime } from '../../dates.js'
import { useApi } from '../../hooks/useApi.js'

const signed = (value) => `${value < 0 ? '−' : '+'}${fmtMw(Math.abs(value))}`
const dots = (name) => `${name} `.padEnd(21, '.') + ' '

function verdict(row) {
  if (row.actual_mw == null || row.range_low_mw == null) return ['—', '']
  if (row.actual_mw < row.range_low_mw) return ['[!!] short', 'is-short']
  if (row.actual_mw > row.range_high_mw) return ['above', '']
  return ['[ok]', 'is-ok']
}

export default function DecisionReplay({ config, confidence }) {
  const range = config.date_ranges.decision_day
  const [date, setDate] = useState(range.start)
  const valid = date >= range.start && date <= range.end
  const replay = useApi(valid ? () => getDecisionDay({ date, confidence }) : null, [date, confidence, valid])

  let body
  if (!valid) body = <ErrorNote message={`Pick a delivery date between ${range.start} and ${range.end}.`} />
  else if (replay.error) body = <ErrorNote message={replay.error} />
  else if (!replay.data) body = <Loading />
  else {
    const { daily, rows, deadline } = replay.data
    const tooHigh = Math.round(((daily.pct_hours_too_high ?? 0) * daily.hours_counted) / 100)
    const summary = [
      `$ replay --delivery ${date} --confidence ${confidence}`,
      dots('deadline used') + `${dayMonthTime(deadline)} UTC (day before)`,
      dots('forecast said') + `${fmtMw(daily.average_forecast_mw)} MW  (daily avg)`,
      dots('wind delivered') + `${fmtMw(daily.average_actual_mw)} MW`,
      dots('difference') + `${signed(daily.average_actual_mw - daily.average_forecast_mw)} MW`,
      dots('average miss') +
        `${fmtMw(daily.average_miss_mw)} MW · too high in ${tooHigh} of ${daily.hours_counted} hours`,
    ].join('\n')

    body = (
      <>
        <ScrollBox label="Daily summary">
          <pre className="terminal">{summary}</pre>
        </ScrollBox>
        <ScrollBox label="The 24 hours">
          <table className="hours-table">
            <caption className="sr-only">
              The 24 hours of {date}: forecast available at the deadline, actual, miss, and the {confidence}%
              range.
            </caption>
            <thead>
              <tr>
                <th scope="col">UTC</th>
                <th scope="col">forecast</th>
                <th scope="col">actual</th>
                <th scope="col">miss</th>
                <th scope="col">{confidence}% range</th>
                <th scope="col">covered?</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const [word, tone] = verdict(row)
                return (
                  <tr key={row.time}>
                    <th scope="row">{row.time.slice(11, 16)}</th>
                    <td className="hours-table__forecast">
                      {row.forecast_mw == null ? '—' : fmtMw(row.forecast_mw)}
                    </td>
                    <td className="hours-table__actual">
                      {row.actual_mw == null ? '—' : fmtMw(row.actual_mw)}
                    </td>
                    <td className={row.error_mw < 0 ? 'is-short' : undefined}>
                      {row.error_mw == null ? '—' : signed(row.error_mw)}
                    </td>
                    <td>
                      {row.range_low_mw == null
                        ? '—'
                        : `${fmtMw(row.range_low_mw)}–${fmtMw(row.range_high_mw)}`}
                    </td>
                    <td className={tone}>{word}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </ScrollBox>
      </>
    )
  }

  return (
    <section className="panel panel--half panel--alt" aria-labelledby="replay-title">
      <div className="panel__head">
        <h2 id="replay-title" className="mono-heading">
          Decision day replay
        </h2>
        <label className="inline-date">
          <span>Delivery date</span>
          <input
            type="date"
            value={date}
            min={range.start}
            max={range.end}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
      </div>
      {body}
    </section>
  )
}
