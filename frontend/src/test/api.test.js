// Tests for src/api.js: building addresses and turning failures into friendly messages.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildUrl, exportCsvUrl, getSummary, SERVER_DOWN_MESSAGE } from '../api.js'

afterEach(() => vi.unstubAllGlobals())

describe('buildUrl', () => {
  it('adds the settings and leaves out empty ones', () => {
    expect(buildUrl('/api/summary', { mode: 'decision_day', horizon: undefined, start: '', confidence: 90 })).toBe(
      '/api/summary?mode=decision_day&confidence=90',
    )
  })

  it('builds the CSV export address from the current settings', () => {
    expect(exportCsvUrl({ mode: 'horizon', start: '2026-01-14', end: '2026-01-15', confidence: 95, horizon: 12 })).toBe(
      '/api/export.csv?mode=horizon&start=2026-01-14&end=2026-01-15&confidence=95&horizon=12',
    )
  })
})

describe('friendly errors', () => {
  it('says the server is unreachable when there is no answer at all', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(getSummary()).rejects.toThrow(SERVER_DOWN_MESSAGE)
  })

  it('says the server is unreachable when the dev proxy answers 500 with no message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('proxy error', { status: 500 })))
    await expect(getSummary()).rejects.toThrow(/Is the backend running\?/)
  })

  it("passes on the backend's own plain-English message for bad inputs", async () => {
    const body = JSON.stringify({ error: 'horizon must be a whole number of hours from 0 to 43.' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 422 })))
    await expect(getSummary({ horizon: 99 })).rejects.toThrow('horizon must be a whole number of hours from 0 to 43.')
  })
})
