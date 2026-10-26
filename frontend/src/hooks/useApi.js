/*
  Load something from the API and remember its state:
      const { data, error, loading } = useApi(() => getSummary(params), [params...])

  - loading: true while waiting for the answer to the CURRENT inputs
  - error:   a human-readable message if that request failed
  - data:    the latest answer (the previous one stays on screen while a new one loads)
  If the inputs change before the answer arrives, the old answer is ignored, so the
  screen never shows numbers for settings the user has already moved away from.
  Pass `null` instead of a function to wait (e.g. until /api/config has loaded).
*/

import { useEffect, useState } from 'react'

export function useApi(load, deps) {
  // Each answer is stored with the inputs it belongs to, so "loading" can be worked out
  // (answer for different inputs = still loading) instead of being set by hand.
  const key = JSON.stringify(deps)
  const [result, setResult] = useState({ key: null, data: null, error: null })

  useEffect(() => {
    if (!load) return undefined
    let current = true
    load()
      .then((data) => current && setResult({ key, data, error: null }))
      .catch((error) => current && setResult({ key, data: null, error: error.message }))
    return () => {
      current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const isCurrent = result.key === key
  return {
    data: result.data,
    error: isCurrent ? result.error : null,
    loading: Boolean(load) && !isCurrent,
  }
}
