import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import ClientsPage from './pages/ClientsPage.jsx'
import ClientPage from './pages/ClientPage.jsx'
import ExperimentPage from './pages/ExperimentPage.jsx'

// The Referee mark: a striped referee band in one color.
function Mark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden className="shrink-0 fill-ink stroke-ink">
      <rect x="1" y="1" width="20" height="20" fill="none" strokeWidth="1.5" />
      <rect x="5" y="1" width="3" height="20" />
      <rect x="11" y="1" width="3" height="20" />
      <rect x="17" y="1" width="3" height="20" />
    </svg>
  )
}

function NavItem({ to, active, children }) {
  return (
    <NavLink
      to={to}
      className={`border-b-2 py-5 text-sm ${active ? 'border-ink font-medium text-ink' : 'border-transparent text-muted hover:text-ink'}`}
    >
      {children}
    </NavLink>
  )
}

export default function App() {
  const { pathname, search } = useLocation()
  const onPrices = pathname.startsWith('/client/') && search.includes('tab=prices')
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 max-w-page items-center justify-between px-6 xl:px-0">
          <NavLink to="/" className="flex items-center gap-2.5">
            <Mark />
            <span className="font-display text-lg font-semibold">SwarmFolio Referee</span>
            <span className="ml-1 hidden border-l border-line pl-3.5 text-ui text-muted sm:inline">AI proposes. Math decides.</span>
          </NavLink>
          <nav className="flex items-center gap-7">
            <NavItem to="/" active={pathname === '/' || (pathname.startsWith('/client/') && !onPrices)}>Clients</NavItem>
            <NavItem to="/client/C04?tab=prices" active={onPrices}>Price tags</NavItem>
            <NavItem to="/experiment" active={pathname === '/experiment'}>Experiment</NavItem>
          </nav>
        </div>
      </header>
      <main className="w-full flex-1">
        <Routes>
          <Route path="/" element={<ClientsPage />} />
          <Route path="/client/:id" element={<ClientPage />} />
          <Route path="/experiment" element={<div className="mx-auto max-w-page px-6 py-14 xl:px-0"><ExperimentPage /></div>} />
        </Routes>
      </main>
    </div>
  )
}
