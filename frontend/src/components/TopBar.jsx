import { Link } from 'react-router-dom'

/** The Certus mark: a feasible polygon with a point inside it. */
export function Mark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="6" fill="var(--accent)" />
      <path d="M7 22 L12 8 L25 11 L23 24 Z" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinejoin="round" />
      <circle cx="17.5" cy="16" r="3" fill="#fff" />
    </svg>
  )
}

export function TopBar({ children }) {
  return (
    <header className="top">
      <div className="top-inner">
        <Link to="/" className="brand">
          <Mark />
          <span><span className="sf">SwarmFolio </span>Certus</span>
        </Link>
        <nav>{children}</nav>
      </div>
    </header>
  )
}
