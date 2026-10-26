/*
  True while a CSS media query matches, e.g. useMediaQuery('(max-width: 600px)') on a phone.
  Updates when the window is resized or the phone is turned.
*/

import { useEffect, useState } from 'react'

export function useMediaQuery(query) {
  const read = () => Boolean(window.matchMedia?.(query).matches)
  const [matches, setMatches] = useState(read)

  useEffect(() => {
    const list = window.matchMedia?.(query)
    if (!list) return undefined
    const update = () => setMatches(list.matches)
    list.addEventListener('change', update)
    return () => list.removeEventListener('change', update)
  }, [query])

  return matches
}
