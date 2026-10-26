/* The data-checks strip along the bottom of the desk, from the Phase 1 quality report. */

import { getQuality } from '../../api.js'
import { fmtMw } from '../../art/ascii.js'
import { ErrorNote, Loading } from '../../components/Status.jsx'
import { useApi } from '../../hooks/useApi.js'

function Check({ ok, children }) {
  return (
    <li>
      <span className={ok ? 'check-ok' : 'check-warn'}>{ok ? '[ok]' : '[!!]'}</span> {children}
    </li>
  )
}

export default function DataChecks() {
  const quality = useApi(getQuality, [])

  let items
  if (quality.error) items = <ErrorNote message={quality.error} />
  else if (!quality.data) items = <Loading />
  else {
    const { actuals, forecasts, lead_time: lead, scale_check: scale } = quality.data
    const usable = forecasts.usable_versions_per_january_target_hour
    const duplicates = actuals.duplicates_removed + forecasts.duplicates_removed
    const overForecast = Math.round((scale.forecast_to_actual_ratio - 1) * 100)
    items = (
      <ul className="checks__list">
        <Check ok={actuals.missing_half_hours.length === 0}>
          {fmtMw(actuals.found_half_hours)} of {fmtMw(actuals.expected_half_hours)} half-hours of actual wind
          present
        </Check>
        <Check ok>{fmtMw(duplicates)} duplicate rows removed</Check>
        <Check ok>
          {usable.min}–{usable.max} usable forecasts per hour (typically {usable.typical})
        </Check>
        <Check ok>
          every hour has a forecast up to {lead.january_targets.longest_lead_available_for_every_hour}h ahead
        </Check>
        <Check ok={false}>
          {fmtMw(lead.counts_by_group['negative (published after target)'])} forecasts published after their
          hour: never used
        </Check>
        <Check ok={Math.abs(overForecast) < 5}>
          latest forecasts averaged {overForecast}% {overForecast >= 0 ? 'above' : 'below'} actual
        </Check>
      </ul>
    )
  }

  return (
    <section id="checks" className="checks" aria-labelledby="checks-title">
      <h2 id="checks-title" className="checks__title">
        Data checks
      </h2>
      {items}
      <p className="checks__tz">times in UTC (= UK time in January)</p>
    </section>
  )
}
