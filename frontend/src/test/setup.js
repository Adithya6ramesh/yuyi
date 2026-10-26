// Runs before every test file.
import '@testing-library/jest-dom/vitest' // adds checks like expect(el).toBeInTheDocument()
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())

// jsdom has no matchMedia; pretend the user asked for reduced motion so animations stay still.
window.matchMedia ??= (query) => ({
  matches: query.includes('reduce'),
  media: query,
  addEventListener() {},
  removeEventListener() {},
})
