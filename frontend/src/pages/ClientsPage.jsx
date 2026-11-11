// Screen D: what the Referee is, then the case-study picker. Demo clients (with a saved committee run) first, C04 leading; then everyone else.
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

function Stat({ value, children }) {
  return (
    <div className="flex flex-col gap-1.5 border-t border-ink pt-3">
      <span className="num text-3xl font-semibold">{value}</span>
      <span className="text-sm text-muted">{children}</span>
    </div>
  )
}

const STEPS = [
  ['Propose', 'Three LLM analysts (macro, fundamentals, risk) write memos; a Chair agent turns them into portfolio weights.'],
  ['Verify', 'A deterministic Referee encodes every client rule as a mixed-integer program (CVXPY + SCIP) and checks the draft exactly: which rules fail, and by how much.'],
  ['Prove or repair', 'If the rules cannot all hold, it proves it and isolates the smallest conflicting set. Otherwise it repairs the draft to the nearest compliant portfolio (minimum turnover).'],
]

function Intro() {
  return (
    <section className="flex flex-col gap-10 border-b border-line pb-14">
      <div className="flex max-w-lede flex-col gap-4">
        <span className="label">LA Hacks 2026 · built solo in 24 hours</span>
        <h1 className="font-display text-5xl font-semibold tracking-tight">An exact verifier for AI-drafted portfolios</h1>
        <p className="font-display text-lead text-prose">
          LLMs can draft an investment portfolio, but nothing guarantees the draft obeys the client's rules: a volatility cap, a
          turnover limit for taxes, a sector ban. SwarmFolio Referee lets the AI propose and makes an optimization solver decide.
        </p>
      </div>
      <div className="grid gap-6 sm:grid-cols-3">
        <Stat value="81%">of LLM first drafts broke at least one client rule (26 of 32 trials, two models)</Stat>
        <Stat value="2 of 16">broken drafts the LLM fixed on its own after three rounds of feedback (20-trial run)</Stat>
        <Stat value="100%">of drafts end compliant, or the conflict is proven: the Referee's repair is exact, not a heuristic</Stat>
      </div>
      <ol className="grid gap-6 sm:grid-cols-3">
        {STEPS.map(([title, body], i) => (
          <li key={title} className="flex flex-col gap-1.5">
            <span className="num text-ui text-muted">{String(i + 1).padStart(2, '0')}</span>
            <span className="font-display text-h3 font-semibold">{title}</span>
            <span className="text-sm text-prose">{body}</span>
          </li>
        ))}
      </ol>
    </section>
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
      <Intro />
      <div className="flex flex-wrap items-end justify-between gap-12 pb-8 pt-12">
        <div className="flex max-w-lede flex-col gap-2.5">
          <h2 className="font-display text-4xl font-semibold tracking-tight">Case studies</h2>
          <p className="font-display text-lead text-prose">
            Synthetic clients with rules in their own words. Open one to replay the agents' drafts and the Referee's verdict each round.
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
      {!clients && !error && (
        <Spinner label="Loading case studies…" slowLabel="Waking the solver server (free hosting tier, up to ~50 s)…" />
      )}

      {featured.length > 0 && (
        <section className="pb-12">
          <SectionHead title="Start here · featured cases" note="Each one shows a different outcome" />
          {featured.map((c, i) => (
            <ClientCard key={c.client_id} client={c} demo={demos[c.client_id]} primary={i === 0} />
          ))}
        </section>
      )}

      {rest.length > 0 && (
        <section>
          <SectionHead title="All cases" note={`${rest.length} more, sorted by number of rules`} />
          {shownRest.map((c) => (
            <ClientCard key={c.client_id} client={c} compact />
          ))}
          {shownRest.length < rest.length && (
            <div className="flex justify-center pt-5">
              <button className="btn-ghost border-line bg-surface" onClick={() => setShowAll(true)}>
                Show all <span className="num">{rest.length}</span> cases
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
