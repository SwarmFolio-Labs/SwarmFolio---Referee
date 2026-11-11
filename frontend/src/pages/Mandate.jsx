// One mandate: its constraints, every recorded AI draft (re-verifiable live), and what each constraint costs.
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDemo, getPrices, verifyRound } from '../api.js'
import { Certificate, Checks, Pending, useLive, Verdict, WeightsDiff } from '../components/Live.jsx'
import { formal, mandateId, mandateName } from '../mandates.js'

const top = (w) =>
  Object.entries(w)
    .filter(([, x]) => x > 1e-4)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([t, x]) => `${t} ${Math.round(x * 100)}`)
    .join(' · ')

/** One recorded round: the draft, and a live re-check on demand. */
function Round({ client, n, draft, recorded, open }) {
  const [state, setState] = useState({ data: null, error: null, busy: false })
  const run = () => {
    setState((s) => ({ ...s, busy: true, error: null }))
    verifyRound(client.client_id, n)
      .then((data) => setState({ data, error: null, busy: false }))
      .catch((e) => setState({ data: null, error: e.message, busy: false }))
  }
  useEffect(() => {
    if (open) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])
  const r = state.data?.receipt
  return (
    <section style={{ borderTop: '1px solid var(--rule)', padding: '14px 0' }}>
      <div className="ex-head" style={{ borderBottom: 0, paddingBottom: 0 }}>
        <span>
          <b>Round {n}</b> <span className="muted small">&nbsp;{top(draft)}…</span>
        </span>
        <span className="links small">
          <span className="muted">recorded: {recorded?.verdict === 'PASS' ? 'compliant' : `${recorded?.checks.filter((c) => !c.passed).length ?? '?'} violated`}</span>
          <button className="btn ghost" onClick={run} disabled={state.busy}>
            {state.busy ? 'Solving…' : r ? 'Re-solve ↻' : 'Verify live →'}
          </button>
        </span>
      </div>
      <Pending busy={state.busy && !r} error={state.error} />
      {r && (
        <>
          <div className="gap" />
          <p>
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <div className="gap" />
          <Checks checks={r.checks} rules={client.rules} />
          {r.verdict === 'VIOLATIONS_REPAIRED' && (
            <>
              <div className="gap" />
              <WeightsDiff before={draft} after={r.repaired_weights} beforeLabel="AI draft" />
            </>
          )}
          <Certificate cert={state.data.certificate} receipt={r} onRerun={run} busy={state.busy} />
        </>
      )}
    </section>
  )
}

export default function Mandate({ clients }) {
  const { id } = useParams()
  const client = clients?.find((c) => c.client_id === id)
  const demo = useLive(() => getDemo(id).catch(() => null), [id])
  const prices = useLive(() => getPrices(id), [id])
  const drafts = demo.data?.extras?.proposals ?? []
  const recorded = demo.data?.extras?.receipts ?? []

  return (
    <main className="page">
      <header className="bar">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <b>SwarmFolio Verify</b>
        </Link>
        <nav>
          <Link to="/#mandates">← Mandate book</Link>
        </nav>
      </header>
      <div className="gap2" />
      {!client ? (
        <Pending busy={!clients} error={clients ? `No mandate ${id}` : null} />
      ) : (
        <>
          <span className="tag">Mandate {mandateId(id)} · synthetic</span>
          <div className="gap" />
          <h1 className="title" style={{ fontSize: 'clamp(30px, 5vw, 48px)' }}>
            {mandateName(client)}
          </h1>
          <div className="gap" />
          <p className="lede muted">{client.story}</p>

          <h2 className="sec small">
            <b>§1</b> Constraints
          </h2>
          <div className="scroll">
            <table className="tbl">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>As written</th>
                  <th>Formal</th>
                  <th className="r">Priority</th>
                </tr>
              </thead>
              <tbody>
                {client.rules.map((r) => (
                  <tr key={r.id}>
                    <td className="faint">{r.id}</td>
                    <td>{r.source.replace(/\.$/, '')}</td>
                    <td className="nw muted">{formal(r)}</td>
                    <td className="r">{r.hard ? 'hard' : r.priority}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="sec small">
            <b>§2</b> Recorded AI drafts, verified live
          </h2>
          <p className="lede muted">
            The allocator LLM's drafts for this mandate{demo.data?.extras?.model ? ` (${demo.data.extras.model})` : ''}{' '}
            were recorded on {demo.data?.extras?.saved_at?.slice(0, 10) ?? 'Oct 18, 2026'}. Each one is re-checked
            against the mandate by the verifier when you ask; the final round is checked on load.
          </p>
          <div className="gap" />
          <Pending busy={demo.busy} error={null} />
          {!demo.busy && drafts.length === 0 && <p className="muted">No recorded drafts for this mandate.</p>}
          {drafts.map((d, i) => (
            <Round
              key={i}
              client={client}
              n={i + 1}
              draft={d}
              recorded={recorded[i]}
              open={i === drafts.length - 1}
            />
          ))}

          <h2 className="sec small">
            <b>§3</b> Shadow cost of each constraint
          </h2>
          <p className="lede muted">
            How much risk-adjusted return the best portfolio gives up because of each constraint: re-solve without
            it and compare. Constraints that never bind cost nothing.
          </p>
          <div className="gap" />
          <Pending busy={prices.busy} error={prices.error} />
          {prices.data && (
            <div className="scroll">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Constraint</th>
                    <th className="r">Cost (pts/yr)</th>
                    <th className="r">Sharpe with → without</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.data.map((p) => (
                    <tr key={p.rule_id}>
                      <td className="faint">{p.rule_id}</td>
                      <td>{p.source.replace(/\.$/, '')}</td>
                      <td className={`r ${p.binds ? '' : 'faint'}`}>{p.binds ? p.utility_cost_pts.toFixed(2) : '0 · slack'}</td>
                      <td className="r nw muted">
                        {p.sharpe_with.toFixed(2)} → {p.sharpe_without.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <footer className="foot links muted">
            <Link to="/">SwarmFolio Verify</Link>
            <a href="https://github.com/SwarmFolio-Labs/SwarmFolio---Referee">GitHub ↗</a>
          </footer>
        </>
      )}
    </main>
  )
}
