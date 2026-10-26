/* Terminal-style loading and error lines, used wherever data is on its way. */

export function Loading({ label = 'loading' }) {
  return (
    <p className="status-line" role="status">
      {label} <span className="blink" aria-hidden="true">▍</span>
    </p>
  )
}

export function ErrorNote({ message }) {
  return (
    <p className="status-line status-line--error" role="alert">
      [!!] {message}
    </p>
  )
}
