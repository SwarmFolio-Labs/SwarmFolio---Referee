import { NavLink, Route, Routes } from 'react-router-dom'
import ClientsPage from './pages/ClientsPage.jsx'
import ClientPage from './pages/ClientPage.jsx'
import ExperimentPage from './pages/ExperimentPage.jsx'

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-md text-sm transition ${isActive ? 'bg-sunken text-ink' : 'text-muted hover:text-ink'}`
      }
    >
      {children}
    </NavLink>
  )
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto max-w-page px-6 h-14 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-2.5">
            <span className="h-7 w-7 rounded-md bg-ink text-bg grid place-items-center font-mono text-xs font-bold">
              SR
            </span>
            <span className="font-display font-semibold tracking-tight">SwarmFolio Referee</span>
          </NavLink>
          <nav className="flex items-center gap-1">
            <NavItem to="/">Clients</NavItem>
            <NavItem to="/experiment">Experiment</NavItem>
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-page px-6 py-8">
        <Routes>
          <Route path="/" element={<ClientsPage />} />
          <Route path="/client/:id" element={<ClientPage />} />
          <Route path="/experiment" element={<ExperimentPage />} />
        </Routes>
      </main>
      <footer className="border-t border-line text-xs text-muted">
        <div className="mx-auto max-w-page px-6 py-4 flex justify-between">
          <span>AI committee proposes. An exact solver (CVXPY + SCIP) referees.</span>
          <span>LA Hacks 2026</span>
        </div>
      </footer>
    </div>
  )
}
