/*
  TALKING TO THE BACKEND: one function per endpoint, all in this file.

  Where requests go:
    - VITE_API_URL (from a .env file) is the backend's address when deployed.
    - During development it is empty, so requests go to "/api/..." on the Vite server,
      and Vite's proxy (vite.config.js) passes them on to http://127.0.0.1:8000.

  Every function returns a Promise of the JSON data, or throws an ApiError whose
  .message is already written for a human to read.
*/

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export const SERVER_DOWN_MESSAGE =
  "Can't reach the server. Is the backend running? " +
  'Start it from backend/ with: .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload'

export class ApiError extends Error {}

/** Build a full URL, leaving out any empty settings. */
export function buildUrl(path, params = {}) {
  const query = new URLSearchParams()
  for (const [name, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(name, value)
  }
  const text = query.toString()
  return `${BASE_URL}${path}${text ? `?${text}` : ''}`
}

async function get(path, params) {
  let response
  try {
    response = await fetch(buildUrl(path, params))
  } catch {
    throw new ApiError(SERVER_DOWN_MESSAGE) // no answer at all
  }
  if (response.ok) return response.json()

  // Our backend explains bad inputs as {"error": "..."}. Anything else (e.g. the dev
  // proxy answering 500 because the backend is off) means we couldn't reach it.
  const body = await response.json().catch(() => null)
  if (body?.error) throw new ApiError(body.error)
  if (response.status >= 500) throw new ApiError(SERVER_DOWN_MESSAGE)
  throw new ApiError(`The server said no (error ${response.status}).`)
}

// /api/config never changes while the app is open, so ask for it only once.
let configPromise = null
export function getConfig() {
  configPromise ??= get('/api/config').catch((error) => {
    configPromise = null // allow a retry later
    throw error
  })
  return configPromise
}

export const getHealth = () => get('/api/health')

/** params: { start, end, horizon, confidence, mode } (all optional) */
export const getSeries = (params) => get('/api/series', params)
export const getSummary = (params) => get('/api/summary', params)

/** params: { start, end } */
export const getHorizonCurve = (params) => get('/api/horizon-curve', params)

/** params: { start, end, horizon, mode } */
export const getBreakdowns = (params) => get('/api/breakdowns', params)

/** params: { confidence, horizon, mode, method } */
export const getBacktest = (params) => get('/api/backtest', params)

/** params: { date, confidence } */
export const getDecisionDay = (params) => get('/api/decision-day', params)

export const getQuality = () => get('/api/quality')

/** Not fetched: the CSV link is given to the browser, which downloads the file. */
export const exportCsvUrl = (params) => buildUrl('/api/export.csv', params)
