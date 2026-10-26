/*
  Tests for the desk page. The API functions are replaced by fakes that answer with
  the fixtures, so we can check exactly which requests the page makes.
*/
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api.js'
import Desk from '../pages/Desk.jsx'
import * as fixtures from './fixtures.js'

vi.mock('../api.js', async (importOriginal) => {
  const real = await importOriginal() // keep the real buildUrl / exportCsvUrl / ApiError
  return {
    ...real,
    getConfig: vi.fn(),
    getSeries: vi.fn(),
    getSummary: vi.fn(),
    getHorizonCurve: vi.fn(),
    getBreakdowns: vi.fn(),
    getBacktest: vi.fn(),
    getDecisionDay: vi.fn(),
    getQuality: vi.fn(),
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  api.getConfig.mockResolvedValue(fixtures.config)
  api.getSeries.mockResolvedValue(fixtures.series)
  api.getSummary.mockResolvedValue(fixtures.summary)
  api.getHorizonCurve.mockResolvedValue(fixtures.horizonCurve)
  api.getBreakdowns.mockResolvedValue(fixtures.breakdowns)
  api.getBacktest.mockResolvedValue(fixtures.backtest)
  api.getDecisionDay.mockResolvedValue(fixtures.decisionDay)
  api.getQuality.mockResolvedValue(fixtures.quality)
})

const renderDesk = () =>
  render(
    <MemoryRouter>
      <Desk />
    </MemoryRouter>,
  )

describe('the desk', () => {
  it('asks for the defaults from /api/config, not hard-coded values', async () => {
    renderDesk()
    await screen.findByText('Plan for less wind by')
    expect(api.getSeries).toHaveBeenCalledWith({
      mode: 'horizon',
      start: '2026-01-01',
      end: '2026-01-31',
      confidence: 90,
      horizon: 24,
    })
    expect(screen.getByText(/learned from 1–24 Jan 2026/)).toBeInTheDocument()
  })

  it('moving the slider changes the request, once the user pauses (debounce)', async () => {
    renderDesk()
    const slider = await screen.findByLabelText(/Forecast made/)
    // three quick moves, like a drag
    fireEvent.change(slider, { target: { value: '25' } })
    fireEvent.change(slider, { target: { value: '26' } })
    fireEvent.change(slider, { target: { value: '30' } })
    expect(screen.getByText('30h ahead')).toBeInTheDocument() // the label updates at once

    await waitFor(() => expect(api.getSeries).toHaveBeenCalledWith(expect.objectContaining({ horizon: 30 })))
    const horizonsAsked = api.getSeries.mock.calls.map(([params]) => params.horizon)
    expect(horizonsAsked).not.toContain(25) // the in-between positions were never requested
    expect(horizonsAsked).not.toContain(26)
  })

  it('shows a friendly message when the server cannot be reached', async () => {
    api.getConfig.mockRejectedValue(new api.ApiError(api.SERVER_DOWN_MESSAGE))
    renderDesk()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Can't reach the server. Is the backend running?",
    )
  })

  it('the Export CSV button links to /api/export.csv with the current settings', async () => {
    renderDesk()
    const link = await screen.findByRole('link', { name: /Export CSV/ })
    expect(link).toHaveAttribute(
      'href',
      '/api/export.csv?mode=horizon&start=2026-01-01&end=2026-01-31&confidence=90&horizon=24',
    )

    fireEvent.click(screen.getByRole('button', { name: /95%/ }))
    await waitFor(() => expect(link).toHaveAttribute('href', expect.stringContaining('confidence=95')))
  })

  it('in Decision day mode the CSV link drops the hours-ahead setting', async () => {
    renderDesk()
    const link = await screen.findByRole('link', { name: /Export CSV/ })
    fireEvent.click(screen.getByRole('button', { name: /Decision day/ }))
    await waitFor(() =>
      expect(link).toHaveAttribute(
        'href',
        '/api/export.csv?mode=decision_day&start=2026-01-02&end=2026-02-01&confidence=90',
      ),
    )
  })
})
