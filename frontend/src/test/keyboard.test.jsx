/*
  Keyboard-only use, and the 404 page. A keyboard user must be able to reach and use
  every control on the desk with Tab, Enter/Space and the arrow keys.
*/
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api.js'
import App from '../App.jsx'
import * as fixtures from './fixtures.js'

vi.mock('../api.js', async (importOriginal) => ({
  ...(await importOriginal()),
  getConfig: vi.fn(),
  getSeries: vi.fn(),
  getSummary: vi.fn(),
  getHorizonCurve: vi.fn(),
  getBreakdowns: vi.fn(),
  getBacktest: vi.fn(),
  getDecisionDay: vi.fn(),
  getQuality: vi.fn(),
}))

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

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )

/** Press Tab until every element has been visited once; return them in order. */
async function tabThroughEverything(user) {
  const visited = []
  for (let i = 0; i < 80; i++) {
    await user.tab()
    if (visited.includes(document.activeElement)) break
    visited.push(document.activeElement)
  }
  return visited
}

describe('keyboard only', () => {
  it('reaches every control on the desk, starting with "Skip to content"', async () => {
    const user = userEvent.setup()
    renderAt('/desk')
    await screen.findByText('In plain English')
    const visited = await tabThroughEverything(user)

    expect(visited[0]).toHaveTextContent('Skip to content')
    const mustReach = [
      screen.getByRole('link', { name: /Export CSV/ }),
      screen.getByRole('button', { name: 'Hours ahead' }),
      screen.getByRole('button', { name: /Decision day/ }),
      screen.getByLabelText('From'),
      screen.getByLabelText('To'),
      screen.getByLabelText(/Forecast made/),
      screen.getByRole('button', { name: /80%/ }),
      screen.getByRole('button', { name: /90%/ }),
      screen.getByRole('button', { name: /95%/ }),
      screen.getByRole('img', { name: /Line chart/ }),
      screen.getByLabelText('Delivery date'),
      screen.getByRole('button', { name: /Per wind level/ }),
      screen.getByRole('region', { name: 'The 24 hours' }), // a scrollable table
    ]
    for (const element of mustReach) expect(visited).toContain(element)
  })

  it('caution buttons work with the keyboard, and the chart reads hours with arrow keys', async () => {
    const user = userEvent.setup()
    renderAt('/desk')
    await screen.findByText('In plain English')

    const cautious = screen.getByRole('button', { name: /95%/ })
    cautious.focus()
    await user.keyboard('{Enter}')
    expect(cautious).toHaveAttribute('aria-pressed', 'true')

    screen.getByRole('img', { name: /Line chart/ }).focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByText(/14 JAN 01:00/)).toBeInTheDocument() // the second hour
  })
})

describe('unknown pages', () => {
  it('shows a 404 screen with links back to the landing page and the desk', () => {
    renderAt('/nonsense/page')
    expect(screen.getByRole('heading', { name: /404 · page not found/ })).toBeInTheDocument()
    const main = screen.getByRole('main')
    expect(within(main).getByText('/nonsense/page')).toBeInTheDocument()
    expect(within(main).getByRole('link', { name: /landing page/ })).toHaveAttribute('href', '/')
    expect(within(main).getByRole('link', { name: /desk/ })).toHaveAttribute('href', '/desk')
  })
})
