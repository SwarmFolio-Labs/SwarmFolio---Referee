// Client picker: one card per client, rules in the client's own words.
import { useEffect, useState } from 'react'
import { getClients } from '../api.js'
import ClientCard from '../components/ClientCard.jsx'
import { ErrorNote, Spinner } from '../components/ui.jsx'

// Mr. Alvarez: the best live debate, shown first when data/demo_runs/C04.json exists.
const FEATURED = 'C04'

export default function ClientsPage() {
  const [clients, setClients] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getClients().then(setClients).catch((e) => setError(e.message))
  }, [])

  // Clients with a saved committee run first (those are the demo); C04 leads once its run is saved.
  const rank = (c) => (c.client_id === FEATURED && c.has_demo ? 0 : c.has_demo ? 1 : 2)
  const sorted = clients && [...clients].sort((a, b) => rank(a) - rank(b))

  return (
    <div>
      <div className="mb-8 max-w-prose">
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
          <ClientCard key={c.client_id} client={c} />
        ))}
      </div>
    </div>
  )
}
