// Screen D: client picker. Demo clients (with a saved committee run) first, C04 leading; then everyone else.
import { useEffect, useState } from 'react'
import { getClients, getDemo } from '../api.js'
import ClientCard from '../components/ClientCard.jsx'
import { ErrorNote, Spinner } from '../components/ui.jsx'

// Mr. Alvarez: the best live debate, shown first when data/demo_runs/C04.json exists.
const FEATURED = 'C04'
const COMPACT_LIMIT = 6

function SectionHead({ title, note }) {
  return (
    <div className="flex items-baseline justify-between border-b border-ink pb-2.5">
      <span className="label">{title}</span>
      <span className="text-ui text-muted">{note}</span>
    </div>
  )
}

export default function ClientsPage() {
  const [clients, setClients] = useState(null)
  const [demos, setDemos] = useState({})
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    getClients()
      .then((all) => {
        setClients(all)
        // Each demo client's status (compliant / repaired / needs approval) comes from its saved run.
        all.filter((c) => c.has_demo).forEach((c) =>
          getDemo(c.client_id).then((d) => setDemos((m) => ({ ...m, [c.client_id]: d }))).catch(() => {}),
        )
      })
      .catch((e) => setError(e.message))
  }, [])

  const q = query.trim().toLowerCase()
  const matches = (c) =>
    !q || c.name.toLowerCase().includes(q) || c.client_id.toLowerCase().includes(q) || c.rules.some((r) => r.source.toLowerCase().includes(q))
  const rank = (c) => (c.client_id === FEATURED ? 0 : 1)
  const featured = (clients ?? []).filter((c) => c.has_demo && matches(c)).sort((a, b) => rank(a) - rank(b) || a.client_id.localeCompare(b.client_id))
  const rest = (clients ?? []).filter((c) => !c.has_demo && matches(c)).sort((a, b) => b.rules.length - a.rules.length)
  const shownRest = showAll || q ? rest : rest.slice(0, COMPACT_LIMIT)

  return (
    <div className="mx-auto max-w-page px-6 pb-16 pt-14 xl:px-0">
      <div className="flex flex-wrap items-end justify-between gap-12 pb-8">
        <div className="flex max-w-lede flex-col gap-2.5">
          <h1 className="font-display text-6xl font-semibold tracking-tight">Clients</h1>
          <p className="font-display text-lead text-prose">
            Pick a client. Three AI analysts draft a portfolio; the Referee checks it against the client's own rules.
          </p>
        </div>
        <label className="flex w-80 items-center gap-2.5 border border-line bg-surface px-3.5 py-2.5">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden className="shrink-0 stroke-muted">
            <circle cx="6" cy="6" r="4.8" fill="none" strokeWidth="1.4" />
            <path d="M9.6 9.6 L13 13" strokeWidth="1.4" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or rule"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
          />
          <span className="num text-xs text-muted">{clients ? featured.length + rest.length : ''}</span>
        </label>
      </div>

      {error && <ErrorNote>Could not reach the API: {error}. Is `uvicorn api:app --port 8000` running?</ErrorNote>}
      {!clients && !error && <Spinner label="Loading clients…" />}

      {featured.length > 0 && (
        <section className="pb-12">
          <SectionHead title="Start here · demo clients" note="Each one shows a different outcome" />
          {featured.map((c, i) => (
            <ClientCard key={c.client_id} client={c} demo={demos[c.client_id]} primary={i === 0} />
          ))}
        </section>
      )}

      {rest.length > 0 && (
        <section>
          <SectionHead title="All clients" note={`${rest.length} more, sorted by number of rules`} />
          {shownRest.map((c) => (
            <ClientCard key={c.client_id} client={c} compact />
          ))}
          {shownRest.length < rest.length && (
            <div className="flex justify-center pt-5">
              <button className="btn-ghost border-line bg-surface" onClick={() => setShowAll(true)}>
                Show all <span className="num">{rest.length}</span> clients
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
