/*
  A box that scrolls sideways when its content is too wide (e.g. tables on a phone).
  It can be focused with the Tab key, so keyboard users can scroll it with the arrow keys.
*/

export default function ScrollBox({ label, children }) {
  return (
    // tabIndex={0}: a region that scrolls must be reachable by keyboard
    <div className="table-scroll" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  )
}
