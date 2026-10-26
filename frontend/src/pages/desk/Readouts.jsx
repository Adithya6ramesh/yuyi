/* The 4 headline numbers: average miss, worst shortfall, lean, and the cushion. */

import { fmtAbout, fmtMw } from '../../art/ascii.js'
import { dateSpan, dayMonthTime } from '../../dates.js'

const LEAN_THRESHOLD_MW = 100 // smaller leans count as "about right"

function lean(summary) {
  const mw = summary.lean_mw
  const share = `${Math.round(summary.pct_hours_too_high)}% of hours too high`
  if (mw < -LEAN_THRESHOLD_MW)
    return { label: 'Too high', note: `Over-promises wind by ~${fmtAbout(-mw)} MW · ${share}` }
  if (mw > LEAN_THRESHOLD_MW)
    return { label: 'Too low', note: `Under-promises wind by ~${fmtAbout(mw)} MW · ${share}` }
  return { label: 'About right', note: `No clear lean · ${share}` }
}

export default function Readouts({ summary, confidence }) {
  if (!summary || summary.hours_counted === 0) {
    return (
      <div className="readouts readouts--empty">
        <p className="status-line">No hours with both a forecast and an actual in these dates.</p>
      </div>
    )
  }
  const shortfall = summary.worst_shortfall_mw
  const leaning = lean(summary)
  const learned = summary.cushion_learned_from

  return (
    <div className="readouts">
      <div className="readout">
        <p className="readout__label">Average miss</p>
        <p className="readout__value">
          {fmtMw(summary.average_miss_mw)}
          <small> MW</small>
        </p>
        <p className="readout__note">
          Average gap, forecast vs reality · {fmtMw(summary.hours_counted)} hours
        </p>
      </div>

      <div className="readout">
        <p className="readout__label">Worst shortfall</p>
        <p className="readout__value readout__value--short">
          {shortfall < 0 ? `−${fmtMw(-shortfall)}` : 'none'}
          {shortfall < 0 && <small> MW</small>}
        </p>
        <p className="readout__note">
          {shortfall < 0
            ? `Biggest hourly shortfall · ${dayMonthTime(summary.worst_shortfall_time)}`
            : 'Wind never fell short of the forecast'}
        </p>
      </div>

      <div className="readout">
        <p className="readout__label">Forecast leans</p>
        <p className="readout__value readout__value--serif">{leaning.label}</p>
        <p className="readout__note">{leaning.note}</p>
      </div>

      <div className="readout readout--cushion">
        <p className="readout__label">Plan for less wind by</p>
        <p className="readout__value">
          {fmtAbout(summary.cushion_mw)}
          <small> MW</small>
        </p>
        <p className="readout__note">
          Safety cushion at {confidence}% caution
          <br />
          learned from {dateSpan(learned.start, learned.end)}
        </p>
      </div>
    </div>
  )
}
