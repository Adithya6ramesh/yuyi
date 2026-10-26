/*
  "Skip to content": the first thing the Tab key reaches. Hidden until focused, it lets
  keyboard users jump past the navigation straight to the page's main content.
*/

export default function SkipLink({ to }) {
  return (
    <a className="skip-link" href={`#${to}`}>
      Skip to content
    </a>
  )
}
