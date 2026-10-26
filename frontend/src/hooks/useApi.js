import { useEffect, useState } from 'react'

/*
  Load something from the API and remember its state:
      const { data, error, loading } = useApi(() => getSummary(params), [params...])

  - loading: true while waiting
  - error:   a human-readable message if it failed
  - data:    the answer
  If the inputs change before the answer arrives, the old answer is ignored, so the
  screen never shows numbers for settings the user has already moved away from.
  Pass `null` instead of a function to wait (e.g. until /api/config has loaded).
*/
export function useApi(load, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(load) })

  useEffect(() => {
    if (!load) return undefined
    let current = true
    setState((previous) => ({ ...previous, error: null, loading: true }))
    load()
      .then((data) => current && setState({ data, error: null, loading: false }))
      .catch((error) => current && setState({ data: null, error: error.message, loading: false }))
    return () => {
      current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
