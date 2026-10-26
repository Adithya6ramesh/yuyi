/* The "404 · page not found" screen, for any address the app doesn't know. */

import { Link, useLocation } from 'react-router-dom'
import './landing.css'

export default function NotFound() {
  const { pathname } = useLocation()
  return (
    <main id="main-content" className="not-found wrap">
      <pre className="not-found__terminal" aria-hidden="true">
        {`windhedge$ open ${pathname}`}
      </pre>
      <h1 className="not-found__title">
        <span className="check-warn">[!!]</span> 404 · page not found
      </h1>
      <p className="not-found__text">
        There’s nothing at <code>{pathname}</code>. The app has two pages:
      </p>
      <ul className="not-found__links">
        <li>
          <Link to="/">→ the landing page</Link>
        </li>
        <li>
          <Link to="/desk">→ the desk (dashboard)</Link>
        </li>
      </ul>
      <p className="status-line">
        windhedge${' '}
        <span className="blink" aria-hidden="true">
          ▍
        </span>
      </p>
    </main>
  )
}
