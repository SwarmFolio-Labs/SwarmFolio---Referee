import { Link } from 'react-router-dom'

/** The masthead: name on the left, bracketed links on the right. */
export function TopBar({ children }) {
  return (
    <header className="masthead">
      <Link to="/">
        <b>SwarmFolio Certus</b> <span className="faint">· working paper no. 1</span>
      </Link>
      <nav>{children}</nav>
    </header>
  )
}
