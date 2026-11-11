// The paper: what the verifier does, three live exhibits, the method, the results, the mandate book.
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { verify, verifyRound } from '../api.js'
import { Certificate, Checks, Pending, useLive, Verdict, WeightsDiff } from '../components/Live.jsx'
import { formal, mandateId, mandateName, pct } from '../mandates.js'

function Sec({ n, id, children }) {
  return (
    <h2 id={id} className="sec small">
      <b>§{n}</b> {children}
    </h2>
  )
}

function ExhibitHead({ letter, title, busy }) {
  return (
    <>
      <div className="ex-head">
        <span className="tag">Exhibit {letter}</span>
        <span className={`live small u ${busy ? 'busy' : ''}`}>{busy ? 'Solving' : 'Solved live on load'}</span>
      </div>
      <h3 className="ex-title">{title}</h3>
    </>
  )
}

// ---------- Exhibit A: a recorded AI draft, re-verified live ----------

function ExhibitA({ client }) {
  const live = useLive(() => verifyRound('C04', 1), [])
  const r = live.data?.receipt
  return (
    <section className="exhibit" id="exhibit-a">
      <ExhibitHead letter="A" title="An AI-drafted portfolio that violates its mandate" busy={live.busy} />
      <div className="gap" />
      <p className="lede muted">
        Mandate {mandateId('C04')}, <span style={{ color: 'var(--ink)' }}>{client && mandateName(client)}</span>: 60% of
        the book in NVDA, MSFT and AAPL; reduce risk without a large taxable sale. The allocator LLM's first draft
        (recorded Oct 18, 2026, asi1-mini) is re-checked by the verifier each time this page loads.
      </p>
      <div className="gap" />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <>
          <p>
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <div className="gap" />
          <Checks checks={r.checks} rules={client.rules} />
          <div className="gap2" />
          <p className="u small">Repair · nearest compliant portfolio</p>
          <p className="muted small">
            minimize ½‖w − w_draft‖₁ subject to every constraint · moves {pct(r.capital_moved)} of capital · Sharpe{' '}
            {r.sharpe_before.toFixed(2)} → {r.sharpe_after.toFixed(2)}
          </p>
          <div className="gap" />
          <WeightsDiff before={live.data.weights} after={r.repaired_weights} beforeLabel="AI draft" />
          <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />
        </>
      )}
    </section>
  )
}

// ---------- Exhibit B: constraints that can't all hold, proven ----------

const limitFmt = (rule, x) => (rule && /holdings/.test(rule.type) ? `${Math.round(x)}` : pct(x))

function ExhibitB({ client }) {
  const live = useLive(() => verifyRound('C03', 1), [])
  const r = live.data?.receipt
  const byId = client ? Object.fromEntries(client.rules.map((x) => [x.id, x])) : {}
  return (
    <section className="exhibit" id="exhibit-b" style={{ marginTop: 0, borderTop: '1px solid var(--rule)' }}>
      <ExhibitHead letter="B" title="A mandate that no portfolio can satisfy, and the proof" busy={live.busy} />
      <div className="gap" />
      <p className="lede muted">
        Mandate {mandateId('C03')}, <span style={{ color: 'var(--ink)' }}>{client && mandateName(client)}</span>. An LLM
        will still produce a confident portfolio here. The verifier instead proves infeasibility, isolates the smallest
        set of constraints that conflict, and prices the cheapest way to relax them.
      </p>
      <div className="gap" />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <div className="grid2">
          <div>
            <p className="u small">Minimal conflicting set</p>
            <table className="tbl">
              <tbody>
                {r.conflict_set.map((id) => (
                  <tr key={id}>
                    <td className="faint">{id}</td>
                    <td>{byId[id]?.source.replace(/\.$/, '')}</td>
                    <td className="r nw bad">{byId[id] && formal(byId[id])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="gap" />
            <p className="muted small">{r.conflict_explain}</p>
            <p className="muted small">
              Found with a deletion filter: drop each constraint in turn and re-solve; whatever stays infeasible is
              the conflict. Removing any one of these makes the rest feasible.
            </p>
          </div>
          <div>
            <p className="u small">Cheapest relaxation</p>
            <table className="tbl">
              <tbody>
                {r.cheapest_relaxation.map((x) => (
                  <tr key={x.rule_id}>
                    <td className="faint">{x.rule_id}</td>
                    <td>{byId[x.rule_id]?.source.replace(/\.$/, '')}</td>
                    <td className="r nw">
                      {limitFmt(byId[x.rule_id], x.old_limit)} → <b>{limitFmt(byId[x.rule_id], x.new_limit)}</b>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="gap" />
            <p className="muted small">
              Each soft constraint gets a slack sᵢ ≥ 0; the solver minimizes Σ priorityᵢ·sᵢ so that a feasible
              portfolio exists. Hard constraints get no slack.
            </p>
          </div>
        </div>
      )}
      {r && <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />}
    </section>
  )
}

// ---------- Exhibit C: verify your own weights ----------

function ExhibitC({ clients }) {
  const pickable = clients.filter((c) => c.universe.length <= 20)
  const [cid, setCid] = useState('C04')
  const client = pickable.find((c) => c.client_id === cid)
  const [weights, setWeights] = useState(null)
  const [result, setResult] = useState({ data: null, error: null, busy: false })
  const w = weights ?? Object.fromEntries((client?.universe ?? []).map((t) => [t, client.current_weights[t] ?? 0]))
  const total = Object.values(w).reduce((a, b) => a + b, 0)

  const choose = (id) => {
    setCid(id)
    setWeights(null)
    setResult({ data: null, error: null, busy: false })
  }
  const set = (t, v) => setWeights({ ...w, [t]: Math.max(0, Number(v) || 0) / 100 })
  const run = () => {
    const sent = Object.fromEntries(Object.entries(w).filter(([, x]) => x > 0).map(([t, x]) => [t, x / total]))
    setResult((s) => ({ ...s, busy: true, error: null }))
    verify(cid, sent)
      .then((data) => setResult({ data: { ...data, sent }, error: null, busy: false }))
      .catch((e) => setResult({ data: null, error: e.message, busy: false }))
  }
  if (!client) return null
  const r = result.data?.receipt
  return (
    <section className="exhibit" id="exhibit-c" style={{ marginTop: 0, borderTop: '1px solid var(--rule)' }}>
      <div className="ex-head">
        <span className="tag">Exhibit C</span>
        <span className="small u muted">Your input · solved on submit</span>
      </div>
      <h3 className="ex-title">Verify a portfolio of your own</h3>
      <div className="gap" />
      <p className="lede muted">
        Pick a mandate, edit the weights (they are normalized to 100%), and submit. Nothing here is cached: the
        server builds the mixed-integer model for your input and solves it.
      </p>
      <div className="gap" />
      <p>
        <span className="u small muted">Mandate&nbsp;&nbsp;</span>
        <select className="field" value={cid} onChange={(e) => choose(e.target.value)}>
          {pickable.map((c) => (
            <option key={c.client_id} value={c.client_id}>
              {mandateId(c.client_id)} · {mandateName(c)}
            </option>
          ))}
        </select>
      </p>
      <div className="gap" />
      <div className="grid2">
        <div>
          <p className="u small">Weights (%)</p>
          <table className="tbl">
            <tbody>
              {client.universe.map((t) => (
                <tr key={t}>
                  <td>{t}</td>
                  <td className="r">
                    <input
                      className="field"
                      inputMode="decimal"
                      aria-label={`${t} weight in percent`}
                      value={+(w[t] * 100).toFixed(1)}
                      onChange={(e) => set(t, e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="gap" />
          <p className="links">
            <button className="btn" onClick={run} disabled={result.busy || total <= 0}>
              {result.busy ? 'Solving…' : 'Verify →'}
            </button>
            <button className="btn ghost" onClick={() => setWeights(null)}>
              Reset
            </button>
            <span className="small muted">sum {(total * 100).toFixed(1)}%</span>
          </p>
        </div>
        <div>
          <p className="u small">Mandate constraints</p>
          <table className="tbl">
            <tbody>
              {client.rules.map((x) => (
                <tr key={x.id}>
                  <td className="faint">{x.id}</td>
                  <td>{x.source.replace(/\.$/, '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <Pending busy={result.busy} error={result.error} />
      {r && (
        <>
          <div className="gap2" />
          <p>
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <div className="gap" />
          <Checks checks={r.checks} rules={client.rules} />
          {r.verdict !== 'PASS' && Object.keys(r.repaired_weights).length > 0 && (
            <>
              <div className="gap" />
              <WeightsDiff before={result.data.sent} after={r.repaired_weights} beforeLabel="Yours" />
            </>
          )}
          <Certificate cert={result.data.certificate} receipt={r} />
        </>
      )}
    </section>
  )
}

// ---------- the page ----------

// [expression, what it encodes]. A table, not a <pre>: subscript glyphs fall back to another font
// and would break column alignment.
const FORMULATION = [
  ['minimize   ½ ‖w − w_draft‖₁', 'repair: least capital moved'],
  ['subject to   Σ wᵢ = 1,  w ≥ 0', 'fully invested, long only'],
  ['0.005·zᵢ ≤ wᵢ ≤ zᵢ,  zᵢ ∈ {0,1}', 'zᵢ = 1 if asset i is held'],
  ['‖Lᵀw‖₂ ≤ σ_max,  Σ = LLᵀ', 'volatility cap (second-order cone)'],
  ['‖w − w₀‖₁ ≤ τ_max', 'turnover from current holdings'],
  ['l_S ≤ Σ_{i∈S} wᵢ ≤ u_S', 'sector floors and caps'],
  ['k_min ≤ Σ zᵢ ≤ k_max', 'number of holdings'],
  ['wᵢ ≥ m·zᵢ', 'minimum position size'],
  ['w_E = 0', 'exclusions'],
]

function Formulation() {
  return (
    <div className="scroll" style={{ border: '1px solid var(--rule)', padding: '8px 16px' }}>
      <table className="tbl">
        <tbody>
          {FORMULATION.map(([expr, note], i) => (
            <tr key={expr}>
              <td className="nw" style={{ borderBottom: 0, paddingLeft: i === 0 ? 0 : '11ch' }}>
                {expr}
              </td>
              <td className="faint" style={{ borderBottom: 0 }}>
                # {note}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const RUNS = [
  { model: 'asi1-mini', n: 12, broken: '10 / 12', self: '33% [8, 58]', bare: '42% [17, 67]', expl: '50% [25, 75]', p: '1.000' },
  { model: 'gemini-3.5-flash-lite', n: 20, broken: '16 / 20', self: '20% [5, 40]', bare: '25% [10, 45]', expl: '25% [10, 45]', p: '1.000' },
]

export default function Home({ clients, error }) {
  const nav = useNavigate()
  const byId = useMemo(() => Object.fromEntries((clients ?? []).map((c) => [c.client_id, c])), [clients])
  return (
    <main className="page">
      <header className="bar">
        <span>
          <b>SwarmFolio Verify</b>
        </span>
        <nav>
          <a href="#exhibit-a">Exhibits</a>
          <a href="#method">Method</a>
          <a href="#results">Results</a>
          <a href="#mandates">Mandates</a>
          <a href="https://github.com/SwarmFolio-Labs/SwarmFolio---Referee">Code ↗</a>
        </nav>
      </header>

      <div className="gap2" />
      <span className="tag">Working paper · November 2026</span>
      <div className="gap" />
      <h1 className="title">Exact verification for AI-drafted portfolios</h1>
      <div className="gap" />
      <p className="muted">Samarth Mukhi · University of Wisconsin–Madison · started at LA Hacks 2026</p>
      <div className="gap" />
      <p className="lede">
        Language models can draft an investment portfolio, but nothing guarantees the draft satisfies the client's
        mandate. SwarmFolio Verify separates the two jobs: LLM agents propose weights, and a deterministic verifier
        encodes the mandate as a mixed-integer second-order cone program and solves it with SCIP. It reports every
        violated constraint and by how much, proves when a mandate is infeasible, and repairs the draft to the nearest
        compliant portfolio. Every verification on this page runs live on the server and comes with a certificate of
        the solve.
      </p>
      <div className="gap" />
      <p className="links">
        <a href="#exhibit-a">Exhibits ↓</a>
        <a href="https://github.com/SwarmFolio-Labs/SwarmFolio---Referee">Source ↗</a>
        <a href="https://devpost.com/software/swarmfolio-referee">Devpost ↗</a>
        <a href="https://youtu.be/ngHaVytPs6M">Demo video ↗</a>
      </p>
      <div className="gap2" />
      <div className="stats">
        <div>
          <div className="small u muted">LLM drafts violating the mandate</div>
          <div className="stat">81%</div>
          <div className="small muted">26 of 32 first drafts, two models</div>
        </div>
        <div>
          <div className="small u muted">Fixed by the LLM from feedback</div>
          <div className="stat">2 / 16</div>
          <div className="small muted">within three revision rounds</div>
        </div>
        <div>
          <div className="small u muted">After exact repair</div>
          <div className="stat">100%</div>
          <div className="small muted">compliant, or infeasibility proven</div>
        </div>
      </div>
      {error && <p className="bad">Could not reach the verifier API: {error}</p>}

      <ExhibitA client={byId.C04} />
      <ExhibitB client={byId.C03} />
      {clients && <ExhibitC clients={clients} />}

      <Sec n={1} id="method">Method</Sec>
      <p className="lede">
        Each mandate constraint becomes a constraint on weights w and binary holding indicators z. One model answers
        three questions: is this draft compliant (direct evaluation), can any portfolio be compliant (feasibility), and
        what is the nearest compliant portfolio (the objective below).
      </p>
      <div className="gap" />
      <Formulation />
      <div className="gap" />
      <table className="tbl">
        <tbody>
          {[
            ['Check', 'Evaluate each constraint on the draft directly; report actual vs limit.'],
            ['Feasibility', 'Solve the model with no objective. Infeasible → the mandate itself is contradictory.'],
            ['Conflict set', 'Deletion filter: at most one solve per constraint, returns a minimal infeasible subset.'],
            ['Relaxation', 'Slack per soft constraint, minimize Σ priority·slack; exclusions and hard limits never bend.'],
            ['Repair', 'Minimize capital moved, ½‖w − w_draft‖₁, subject to every (relaxed) constraint.'],
            ['Shadow cost', 'Re-solve the max-utility portfolio without each constraint; the gap is that constraint’s cost.'],
          ].map(([k, v]) => (
            <tr key={k}>
              <td className="nw u small" style={{ width: '16ch' }}>
                {k}
              </td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="gap" />
      <p className="small muted">
        Data: daily prices for 20 U.S. tickers through Oct 16, 2026; μ and Σ estimated from the last 756 trading days;
        risk-free rate 4%. Statistics are ex-ante. SCIP runs with a 1e-9 feasibility tolerance and a 15 s limit per
        solve.
      </p>

      <Sec n={2} id="results">Results: can feedback replace the verifier?</Sec>
      <p className="lede">
        If the LLM could fix its own drafts from feedback, the verifier would only need to check. We tested three kinds
        of feedback over three revision rounds, starting every condition from the same first draft.
      </p>
      <div className="gap" />
      <div className="scroll">
        <table className="tbl">
          <thead>
            <tr>
              <th>Model</th>
              <th className="r">Trials</th>
              <th className="r">Drafts violating</th>
              <th className="r">Self-check</th>
              <th className="r">Which rule failed</th>
              <th className="r">Actual vs limit</th>
              <th className="r">p</th>
            </tr>
          </thead>
          <tbody>
            {RUNS.map((x) => (
              <tr key={x.model}>
                <td className="nw">{x.model}</td>
                <td className="r">{x.n}</td>
                <td className="r">{x.broken}</td>
                <td className="r nw">{x.self}</td>
                <td className="r nw">{x.bare}</td>
                <td className="r nw">{x.expl}</td>
                <td className="r">{x.p}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="gap" />
      <p className="small muted">
        Share of trials fully compliant after round 3, with 95% bootstrap intervals; p is a sign test, explained vs.
        bare verdict. Richer feedback helps slightly but not significantly at this sample size, and in the larger run
        the LLM fixed only 2 of 16 violating drafts. Conclusion: feedback is not a substitute for exact repair.
      </p>

      <Sec n={3} id="mandates">Mandate book</Sec>
      <p className="lede">
        {clients ? clients.length : '—'} synthetic mandates, each written in plain language and mapped to formal
        constraints. Open one to re-verify every recorded AI draft live.
      </p>
      <div className="gap" />
      <Pending busy={!clients && !error} error={null} />
      {clients && (
        <div className="scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th>ID</th>
                <th>Mandate</th>
                <th className="r">Constraints</th>
                <th className="r hide-sm">Universe</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.client_id} className="link" onClick={() => nav(`/m/${c.client_id}`)}>
                  <td className="nw faint">{mandateId(c.client_id)}</td>
                  <td>
                    <Link to={`/m/${c.client_id}`} style={{ textDecoration: 'none' }}>
                      {mandateName(c)}
                    </Link>
                  </td>
                  <td className="r">{c.rules.length}</td>
                  <td className="r hide-sm">{c.universe.length}</td>
                  <td className="r">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Sec n={4} id="reproduce">Reproduce</Sec>
      <pre className="math">{`# the same check Exhibit A runs, from your terminal
curl -s https://swarmfolio-api.onrender.com/api/verify/C04/round/1 | jq .certificate

# the test suite (298 tests: rules, solver, conflicts, relaxation, repair, API)
git clone https://github.com/SwarmFolio-Labs/SwarmFolio---Referee && cd SwarmFolio---Referee
pip install -r requirements.txt && pytest -q`}</pre>

      <Sec n={5} id="limits">Limitations</Sec>
      <table className="tbl">
        <tbody>
          {[
            'Mandates are synthetic; the universe is 20 large-cap U.S. tickers.',
            'Risk and return are historical estimates; the verifier certifies constraints, not future performance.',
            'AI drafts are recorded runs (Oct 18, 2026). The verification of them is live; the drafting is not.',
            'The feedback experiment is small (32 trials); its null result is suggestive, not conclusive.',
          ].map((x) => (
            <tr key={x}>
              <td>{x}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <footer className="foot links muted">
        <span>SwarmFolio Verify · Samarth Mukhi</span>
        <a href="https://samarthmukhi.com">samarthmukhi.com ↗</a>
        <a href="https://github.com/SwarmFolio-Labs/SwarmFolio---Referee">GitHub ↗</a>
      </footer>
    </main>
  )
}
