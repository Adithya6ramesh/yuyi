/*
  THE FORECAST CHART, hand-drawn in SVG (no chart library):
    green solid line  = actual wind
    amber dashed line = the forecast available at the deadline
    pale green band   = the safety range (forecast + cushion)

  rows: from /api/series -> [{ time, actual_mw, forecast_mw, range_low_mw, range_high_mw }, ...]
  cursorIndex: optional, draws a marker on that hour.
  onCursorChange: optional. If given, the chart follows the mouse / finger / arrow keys
                  and calls onCursorChange(index) with the hour picked.
  label: what a screen reader hears instead of the picture.
  children: optional function (layout) => extra SVG, drawn behind the lines (e.g. the
            desk's "test week" shading). layout has x(time) and y(mw).
*/

import { useRef } from 'react'

const LEFT = 56
const RIGHT = 984
const TOP = 20
const BOTTOM = 264
const HOUR = 3600 * 1000
const STEP_MW = 5000 // a grid line every 5 GW

const labelStyle = { fill: 'var(--muted-2)', fontSize: 12, fontFamily: 'var(--mono)' }

/** Positions on the chart for a set of rows (shared with overlays such as the desk's). */
export function chartLayout(rows) {
  const times = rows.map((r) => Date.parse(r.time))
  const start = times[0]
  const end = times[times.length - 1] + HOUR // the last hour runs until here
  const highest = Math.max(
    STEP_MW,
    ...rows.flatMap((r) => [r.actual_mw, r.forecast_mw, r.range_high_mw]).filter((v) => v != null),
  )
  const top = Math.ceil(highest / STEP_MW) * STEP_MW
  return {
    times,
    start,
    end,
    top,
    x: (time) => LEFT + ((time - start) / (end - start)) * (RIGHT - LEFT),
    y: (mw) => TOP + (1 - Math.max(0, Math.min(top, mw)) / top) * (BOTTOM - TOP),
  }
}

/** "M x y L x y ...", starting a new piece wherever a value is missing. */
function linePath(rows, key, layout) {
  let path = ''
  let drawing = false
  rows.forEach((row, i) => {
    const value = row[key]
    if (value == null) {
      drawing = false
      return
    }
    path += `${drawing ? 'L' : 'M'}${layout.x(layout.times[i]).toFixed(1)} ${layout.y(value).toFixed(1)} `
    drawing = true
  })
  return path
}

function bandPath(rows, layout) {
  const inside = rows.map((r, i) => ({ ...r, t: layout.times[i] })).filter((r) => r.range_low_mw != null)
  if (!inside.length) return ''
  const point = (t, mw) => `${layout.x(t).toFixed(1)} ${layout.y(mw).toFixed(1)}`
  const upper = inside.map((r) => point(r.t, r.range_high_mw))
  const lower = inside.reverse().map((r) => point(r.t, r.range_low_mw))
  return `M${upper.join(' L')} L${lower.join(' L')} Z`
}

const dayLabel = (time) =>
  new Date(time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' }).toUpperCase()

/** The row whose hour is closest to a position across the chart (0..1000). */
function nearestIndex(layout, svgX) {
  const time = layout.start + ((svgX - LEFT) / (RIGHT - LEFT)) * (layout.end - layout.start)
  let best = 0
  layout.times.forEach((t, i) => {
    if (Math.abs(t - time) < Math.abs(layout.times[best] - time)) best = i
  })
  return best
}

const KEY_STEPS = { ArrowLeft: -1, ArrowRight: 1, PageUp: -24, PageDown: 24 }

export default function SeriesChart({ rows, cursorIndex = null, onCursorChange, label, children }) {
  const svgRef = useRef(null)
  if (!rows?.length) return null
  const layout = chartLayout(rows)
  const interactive = Boolean(onCursorChange)

  // Mouse or finger: find where on the chart it is, in chart units.
  const pick = (event) => {
    const box = svgRef.current.getBoundingClientRect()
    onCursorChange(nearestIndex(layout, ((event.clientX - box.left) / box.width) * 1000))
  }
  // Keyboard: arrows move one hour, Page Up/Down one day, Home/End to the ends.
  const onKeyDown = (event) => {
    const last = rows.length - 1
    let next
    if (event.key in KEY_STEPS) next = (cursorIndex ?? 0) + KEY_STEPS[event.key]
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = last
    else return
    event.preventDefault()
    onCursorChange(Math.max(0, Math.min(last, next)))
  }

  const gridLines = []
  for (let mw = 0; mw <= layout.top; mw += STEP_MW) gridLines.push(mw)

  // a label at every midnight between start and end
  const days = []
  for (let t = layout.start; t <= layout.end; t += 24 * HOUR) days.push(t)
  // on long ranges, keep about 8 day labels so they don't overlap
  const every = Math.max(1, Math.ceil(days.length / 8))
  const shownDays = days.filter((_, i) => i % every === 0 || i === days.length - 1)

  const cursor = cursorIndex != null && rows[cursorIndex]
  const cursorX = cursor ? layout.x(layout.times[cursorIndex]).toFixed(1) : null

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 1000 300"
      role="img"
      aria-label={interactive ? `${label} Use the left and right arrow keys to move through the hours.` : label}
      className={`series-chart${interactive ? ' series-chart--interactive' : ''}`}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={interactive ? onKeyDown : undefined}
    >
      <path
        d={gridLines.map((mw) => `M${LEFT} ${layout.y(mw).toFixed(1)} H${RIGHT}`).join(' ')}
        style={{ stroke: 'var(--line)', strokeWidth: 1 }}
      />
      {gridLines.map((mw) => (
        <text key={mw} x={LEFT - 10} y={layout.y(mw) + 4} style={{ ...labelStyle, textAnchor: 'end' }}>
          {mw === 0 ? '0' : `${mw / 1000}GW`}
        </text>
      ))}
      {children?.(layout)}
      <path d={bandPath(rows, layout)} style={{ fill: 'var(--accent-soft)' }} />
      <path
        d={linePath(rows, 'forecast_mw', layout)}
        style={{ fill: 'none', stroke: 'var(--forecast)', strokeWidth: 2, strokeDasharray: '6 5' }}
      />
      <path
        d={linePath(rows, 'actual_mw', layout)}
        style={{ fill: 'none', stroke: 'var(--accent)', strokeWidth: 2.6, strokeLinejoin: 'round' }}
      />
      {cursor && cursor.actual_mw != null && (
        <>
          <path
            d={`M${cursorX} ${TOP} V${BOTTOM}`}
            style={{ stroke: 'var(--accent)', strokeWidth: 1, strokeDasharray: '2 4', strokeOpacity: 0.6 }}
          />
          <circle
            cx={cursorX}
            cy={layout.y(cursor.actual_mw).toFixed(1)}
            r="5"
            style={{ fill: 'var(--bg)', stroke: 'var(--accent)', strokeWidth: 2 }}
          />
        </>
      )}
      {interactive && (
        // an invisible layer over the plot that catches the mouse / finger
        <rect
          x={LEFT}
          y={TOP}
          width={RIGHT - LEFT}
          height={BOTTOM - TOP}
          fill="transparent"
          onPointerMove={pick}
          onPointerDown={pick}
        />
      )}
      {shownDays.map((t, i) => {
        const anchor = i === 0 ? 'start' : i === shownDays.length - 1 ? 'end' : 'middle'
        return (
          <text key={t} x={layout.x(t)} y="290" style={{ ...labelStyle, textAnchor: anchor }}>
            {dayLabel(t)}
          </text>
        )
      })}
    </svg>
  )
}
