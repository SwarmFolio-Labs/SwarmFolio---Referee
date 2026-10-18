// Client picker: one card per client, rules in the client's own words.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getClients } from '../api.js'
import RuleChip from '../components/RuleChip.jsx'
import { Badge, ErrorNote, Spinner } from '../components/ui.jsx'
import { displayName, isSynthetic } from '../format.js'

export default function ClientsPage() {
  const [clients, setClients] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getClients().then(setClients).catch((e) => setError(e.message))
  }, [])

  // Clients with a saved committee run first: those are the demo.
  const sorted = clients && [...clients].sort((a, b) => Number(b.has_demo) - Number(a.has_demo))

  return (
    <div>
      <div className="mb-8 max-w-3xl">
        <div className="label mb-2">Pick a client</div>
        <h1 className="font-display text-3xl font-bold tracking-tight">
          An AI investment committee, refereed by exact math.
        </h1>
        <p className="mt-3 text-muted">
          Three analyst agents and a Chair propose a portfolio. The Referee checks it against the client's rules with a
          solver, explains what broke, and the committee debates until it complies — or proves the rules can't all hold.
        </p>
      </div>

      {error && <ErrorNote>Could not reach the API: {error}. Is `uvicorn api:app --port 8000` running?</ErrorNote>}
      {!clients && !error && <Spinner label="Loading clients…" />}

      <div className="grid gap-4 md:grid-cols-2">
        {sorted?.map((c) => (
          <Link
            key={c.client_id}
            to={`/client/${c.client_id}`}
            className="card p-5 flex flex-col gap-3 transition hover:border-ink/30 hover:-translate-y-0.5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="num text-xs text-muted">{c.client_id}</span>
                  {isSynthetic(c.name) && <span className="text-[10px] uppercase tracking-wide text-muted">synthetic</span>}
                </div>
                <h2 className="font-display text-lg font-semibold tracking-tight">{displayName(c.name)}</h2>
              </div>
              {c.has_demo ? <Badge tone="accent">committee run</Badge> : <Badge>referee only</Badge>}
            </div>
            <p className="text-sm text-muted">{c.story}</p>
            <div className="flex flex-wrap gap-1.5">
              {c.rules.map((r) => (
                <RuleChip key={r.id} rule={r} />
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
