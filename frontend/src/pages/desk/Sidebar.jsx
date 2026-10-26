/* The desk's left column: brand, section links, and the animated mini wind-field mesh. */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { miniMesh, spinner } from '../../art/mesh.js'
import { useAnimationClock } from '../../hooks/useAnimationClock.js'

const SECTIONS = [
  ['overview', 'Overview'],
  ['decision', 'Decision day'],
  ['accuracy', 'Accuracy'],
  ['cushion', 'Safety cushion'],
  ['checks', 'Data checks'],
]

function MiniMesh() {
  const [ref, seconds] = useAnimationClock(15)
  const t = seconds + 3 // the design starts 3 s in, so a frozen frame looks good
  const path = useMemo(() => miniMesh(t), [t])
  return (
    <div className="mesh" ref={ref} aria-hidden="true">
      <div className="mesh__head">
        <span>Wind field</span>
        <span>{spinner(t)}</span>
      </div>
      <svg viewBox="0 0 260 150">
        <path d={path} />
      </svg>
    </div>
  )
}

export default function Sidebar() {
  const [current, setCurrent] = useState('overview')
  return (
    <aside className="sidebar">
      <Link to="/" className="sidebar__brand">
        ✻ Windhedge <span>desk</span>
      </Link>
      <nav className="sidebar__nav" aria-label="Desk sections">
        {SECTIONS.map(([id, name], i) => (
          <a
            key={id}
            href={`#${id}`}
            aria-current={current === id ? 'location' : undefined}
            onClick={() => setCurrent(id)}
          >
            <span className="sidebar__number">{String(i + 1).padStart(2, '0')}</span>
            {name}
          </a>
        ))}
      </nav>
      <div className="sidebar__foot">
        <MiniMesh />
        <p>
          Source · Elexon BMRS
          <br />
          FUELHH + WINDFOR
        </p>
      </div>
    </aside>
  )
}
