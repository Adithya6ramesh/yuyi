/*
  Small date helpers. The API speaks UTC everywhere ("2026-01-15", "2026-01-15T10:00:00Z"),
  so we always format in UTC too (= UK time in January).
*/

const DAY = 24 * 3600 * 1000

/** "2026-01-15" + 2 -> "2026-01-17" */
export function addDays(isoDate, days) {
  return new Date(Date.parse(`${isoDate}T00:00:00Z`) + days * DAY).toISOString().slice(0, 10)
}

/** Number of days from a to b: ("2026-01-01", "2026-01-31") -> 30 */
export function daysBetween(a, b) {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / DAY)
}

const utc = (value) => new Date(value.length === 10 ? `${value}T00:00:00Z` : value)

/** "2026-01-15" -> "January 2026" */
export const monthYear = (value) =>
  utc(value).toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' })

/** "2026-01-15" -> "2026-01" */
export const yearMonth = (value) => value.slice(0, 7)

/** "2026-01-15..." -> "15 JAN" */
export const dayMonth = (value) =>
  utc(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' }).toUpperCase()

/** "2026-01-15T10:00:00Z" -> "15 JAN 10:00" */
export const dayMonthTime = (value) => `${dayMonth(value)} ${utc(value).toISOString().slice(11, 16)}`

/** "2026-01-15", "2026-01-16" -> "15–16 Jan 2026" */
export function dateSpan(start, end) {
  const a = utc(start)
  const b = utc(end)
  const month = (d) => d.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' })
  if (start === end) return `${b.getUTCDate()} ${month(b)} ${b.getUTCFullYear()}`
  const first = a.getUTCMonth() === b.getUTCMonth() ? `${a.getUTCDate()}` : `${a.getUTCDate()} ${month(a)}`
  return `${first}–${b.getUTCDate()} ${month(b)} ${b.getUTCFullYear()}`
}
