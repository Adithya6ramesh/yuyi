/*
  Debounce: wait until a value has stopped changing for `delay` milliseconds before
  passing it on. While the user drags the slider the screen label updates at once, but
  the API is only asked once they pause, not once per pixel.

      const settled = useDebouncedValue(settings, 300)
*/

import { useEffect, useState } from 'react'

export function useDebouncedValue(value, delay = 300) {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer) // value changed again: restart the wait
  }, [value, delay])
  return settled
}
