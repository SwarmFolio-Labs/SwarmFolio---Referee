// One mandate: its constraints, every recorded AI draft (re-verifiable live), and what each constraint costs.
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDemo, getPrices, verifyRound } from '../api.js'
import { Dumbbell } from '../components/Figures.jsx'
import { Certificate, Checks, Pending, useLive, Verdict } from '../components/Live.jsx'
import { TopBar } from '../components/TopBar.jsx'
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
    <section className="case" style={{ marginTop: 16 }}>
      <div className="case-head">
        <span>
          <b>Round {n}</b> <span className="muted small num">&nbsp;{top(draft)}…</span>
        </span>
        <span className="actions small">
          <span className="muted">recorded: {recorded?.verdict === 'PASS' ? 'compliant' : `${recorded?.checks.filter((c) => !c.passed).length ?? '?'} violated`}</span>
          <button className="btn ghost sm" onClick={run} disabled={state.busy}>
            {state.busy ? 'Solving…' : r ? 'Re-solve ↻' : 'Verify live →'}
          </button>
        </span>
      </div>
      <Pending busy={state.busy && !r} error={state.error} />
      {r && (
        <>
          <div style={{ height: 14 }} />
          <p className="small">
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <div style={{ height: 12 }} />
          <Checks checks={r.checks} rules={client.rules} />
          {r.verdict === 'VIOLATIONS_REPAIRED' && (
            <div style={{ marginTop: 20 }}>
              <Dumbbell before={draft} after={r.repaired_weights} />
            </div>
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
    <>
    <TopBar>
      <Link to="/#mandates">← Mandate book</Link>
    </TopBar>
    <main className="page">
      <div style={{ height: 48 }} />
      {!client ? (
        <Pending busy={!clients} error={clients ? `No mandate ${id}` : null} />
      ) : (
        <>
          <span className="kicker">Mandate {mandateId(id)} · synthetic</span>
          <h1 className="title" style={{ fontSize: 'clamp(32px, 5vw, 52px)' }}>
            {mandateName(client)}
          </h1>
          <p className="lede muted" style={{ marginTop: 16 }}>
            {client.story}
          </p>

          <h2 className="section-head" style={{ paddingTop: 64 }}>
            <span className="label">§ 1</span> <span>Constraints</span>
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
                    <td className="num faint">{r.id}</td>
                    <td>{r.source.replace(/\.$/, '')}</td>
                    <td className="nw num muted" style={{ fontSize: 12.5 }}>{formal(r)}</td>
                    <td className="r">{r.hard ? 'hard' : r.priority}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="section-head" style={{ paddingTop: 64 }}>
            <span className="label">§ 2</span> <span>Recorded AI drafts, verified live</span>
          </h2>
          <p className="muted">
            The allocator LLM's drafts for this mandate{demo.data?.extras?.model ? ` (${demo.data.extras.model})` : ''}{' '}
            were recorded on {demo.data?.extras?.saved_at?.slice(0, 10) ?? 'Oct 18, 2026'}. Each one is re-checked
            against the mandate by the verifier when you ask; the final round is checked on load.
          </p>
          <div style={{ height: 16 }} />
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

          <h2 className="section-head" style={{ paddingTop: 64 }}>
            <span className="label">§ 3</span> <span>Shadow cost of each constraint</span>
          </h2>
          <p className="muted">
            How much risk-adjusted return the best portfolio gives up because of each constraint: re-solve without
            it and compare. Constraints that never bind cost nothing.
          </p>
          <div style={{ height: 16 }} />
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
                      <td className="num faint">{p.rule_id}</td>
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
          <footer className="foot">
            <Link to="/">SwarmFolio Certus</Link>
            <a href="https://github.com/SwarmFolio-Labs/SwarmFolio---Referee">GitHub ↗</a>
          </footer>
        </>
      )}
    </main>
    </>
  )
}
