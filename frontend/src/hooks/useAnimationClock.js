/*
  A ticking clock for the animations: returns the number of seconds the animation has
  been running, updated `fps` times a second.

      const [ref, t] = useAnimationClock(20)
      <div ref={ref}> ...draw using t... </div>

  The clock STOPS (and the picture freezes) when:
    - the computer asks for reduced motion (an accessibility setting),
    - the browser tab is hidden,
    - the animation is scrolled out of view (saves battery; nothing pops in or fades).
  When it starts again it carries on from where it stopped, with no jump.
*/

import { useEffect, useRef, useState } from 'react'

export function useAnimationClock(fps = 20) {
  const ref = useRef(null)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    let onScreen = true
    let observer
    if (ref.current && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(([entry]) => {
        onScreen = entry.isIntersecting
      })
      observer.observe(ref.current)
    }

    let frame
    let previous = null
    let running = 0 // milliseconds the animation has actually been moving
    let lastShown = -Infinity
    const tick = (now) => {
      frame = requestAnimationFrame(tick)
      const step = previous === null ? 0 : now - previous
      previous = now
      if (reduceMotion?.matches || document.hidden || !onScreen) return
      running += Math.min(step, 100) // after a pause, don't jump ahead
      if (running - lastShown < 1000 / fps) return
      lastShown = running
      setSeconds(running / 1000)
    }
    frame = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [fps])

  return [ref, seconds]
}
