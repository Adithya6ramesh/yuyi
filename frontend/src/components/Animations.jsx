/*
  THE ANIMATED PICTURES. Each one has its own clock (useAnimationClock), so when it
  moves only that small piece of the page is redrawn. All are decoration: hidden from
  screen readers (aria-hidden), with a text description where the picture carries meaning.
*/

import { useMemo } from 'react'
import { asciiTurbine, flowField } from '../art/ascii.js'
import { heroScene } from '../art/heroScene.js'
import { useAnimationClock } from '../hooks/useAnimationClock.js'

// The designs start a few seconds in, so a frozen (reduced-motion) frame looks good.
const START_OFFSET = 4

/** The 3D wireframe turbine on rippling terrain (landing page hero). */
export function HeroScene({ horizonHours }) {
  const [ref, seconds] = useAnimationClock(20)
  const scene = useMemo(() => heroScene(seconds + START_OFFSET), [seconds])
  return (
    <div className="hero-scene" ref={ref}>
      <span className="corner corner--tl" />
      <span className="corner corner--tr" />
      <span className="corner corner--bl" />
      <span className="corner corner--br" />
      <svg viewBox="0 0 840 620" aria-hidden="true">
        <path d={scene.terrain} style={{ fill: 'none', stroke: 'var(--accent)', strokeWidth: 0.8, strokeOpacity: 0.32 }} />
        <path
          d={scene.wind}
          style={{ fill: 'none', stroke: 'var(--forecast)', strokeWidth: 1.6, strokeLinecap: 'round', strokeOpacity: 0.85 }}
        />
        <path d={scene.tower} style={{ fill: 'none', stroke: 'var(--text)', strokeWidth: 1, strokeOpacity: 0.8 }} />
        <path d={scene.blades} style={{ fill: 'none', stroke: 'var(--accent)', strokeWidth: 1.4, strokeLinejoin: 'round' }} />
      </svg>
      <div className="hero-scene__label hero-scene__label--top" aria-hidden="true">
        Wind field · model view
        <br />
        Yaw {scene.yawDeg}° · rotor {scene.rpm} rpm
      </div>
      <div className="hero-scene__label hero-scene__label--bottom" aria-hidden="true">
        54.0°N 2.0°W
        <br />
        {horizonHours != null ? `T + ${horizonHours}h` : 'T + …'}
      </div>
    </div>
  )
}

/** The wind field rendered as text, with its running clock. */
export function FlowFieldBand() {
  const [ref, seconds] = useAnimationClock(20)
  const t = seconds + START_OFFSET
  const field = useMemo(() => flowField(t), [t])
  return (
    <section className="flow" ref={ref} aria-hidden="true">
      <div className="flow__head">
        <span>Wind field, rendered as text</span>
        <span>t = {t.toFixed(1).padStart(6, ' ')}s</span>
      </div>
      <pre className="flow__field">{field}</pre>
    </section>
  )
}

/** The turbine drawn in text characters (closing call to action). */
export function AsciiTurbineArt() {
  const [ref, seconds] = useAnimationClock(20)
  const art = useMemo(() => asciiTurbine(seconds + START_OFFSET), [seconds])
  return (
    <pre className="cta__turbine" ref={ref} aria-hidden="true">
      {art}
    </pre>
  )
}

/** The scrolling ticker tape (pure CSS animation, stops for reduced motion). */
export function Ticker({ text }) {
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker__track">
        <span>{text}</span>
        <span>{text}</span>
      </div>
    </div>
  )
}
