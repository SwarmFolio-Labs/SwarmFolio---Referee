// The paper: what Certus does (Fig. 1-2), three live cases, the method, results, the mandate book.
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { verify, verifyRound } from '../api.js'
import { CIChart, ConflictBar, Dumbbell, FeasibleRegion, Pipeline } from '../components/Figures.jsx'
import { Certificate, Checks, LiveChip, Pending, useLive, Verdict } from '../components/Live.jsx'
import { TopBar } from '../components/TopBar.jsx'
import { formal, mandateId, mandateName, pct } from '../mandates.js'

const REPO = 'https://github.com/SwarmFolio-Labs/SwarmFolio---Referee'

function Section({ n, id, title, children }) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        <span className="label">§ {n}</span>
        <h2>{title}</h2>
      </div>
      <div className="section-body">{children}</div>
    </section>
  )
}

function CaseHead({ n, title, live }) {
  return (
    <>
      <div className="case-head">
        <span className="label">Case {n}</span>
        <LiveChip busy={live.busy} cert={live.data?.certificate} />
      </div>
      <h3 className="case-title">{title}</h3>
    </>
  )
}

// ---------- Case 1: a recorded AI draft, re-verified live ----------

function CaseViolation({ client }) {
  const live = useLive(() => verifyRound('C04', 1), [])
  const r = live.data?.receipt
  return (
    <article className="case" id="case-1">
      <CaseHead n={1} title="An AI-drafted portfolio that violates its mandate" live={live} />
      <p className="muted" style={{ marginTop: 8, maxWidth: '70ch' }}>
        {mandateId('C04')} · <b style={{ color: 'var(--ink)' }}>{client && mandateName(client)}</b>. 60% of the book in
        NVDA, MSFT and AAPL; cut risk without a large taxable sale. The allocator's first draft (recorded Oct 18, 2026,
        asi1-mini) is re-checked against all eight constraints each time this page loads.
      </p>
      <div style={{ height: 20 }} />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <div className="stack">
          <p className="small">
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <Checks checks={r.checks} rules={client.rules} />
          <div className="split" style={{ marginTop: 28 }}>
            <div>
              <div className="label" style={{ paddingBottom: 6 }}>
                Repair · minimize ½‖w − w_draft‖₁
              </div>
              <Dumbbell before={live.data.weights} after={r.repaired_weights} />
            </div>
            <div>
              <div className="label" style={{ paddingBottom: 6 }}>
                Cost of compliance
              </div>
              <table className="tbl">
                <tbody>
                  <tr>
                    <td>Capital moved</td>
                    <td className="r num">{pct(r.capital_moved)}</td>
                  </tr>
                  <tr>
                    <td>Sharpe (ex-ante)</td>
                    <td className="r num">
                      {r.sharpe_before.toFixed(2)} → {r.sharpe_after.toFixed(2)}
                    </td>
                  </tr>
                  <tr>
                    <td>Volatility after repair</td>
                    <td className="r num">{pct(r.vol_after)}</td>
                  </tr>
                  <tr>
                    <td>Constraints violated → after</td>
                    <td className="r num">{r.checks.filter((c) => !c.passed).length} → 0</td>
                  </tr>
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: 12 }}>
                The repair is the closest compliant portfolio to the AI's draft, so as much of the model's view as
                possible survives.
              </p>
            </div>
          </div>
          <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />
        </div>
      )}
    </article>
  )
}

// ---------- Case 2: constraints that can't all hold, proven ----------

const limitFmt = (rule, x) => (rule && /holdings/.test(rule.type) ? `${Math.round(x)}` : pct(x))

function CaseInfeasible({ client }) {
  const live = useLive(() => verifyRound('C03', 1), [])
  const r = live.data?.receipt
  const byId = client ? Object.fromEntries(client.rules.map((x) => [x.id, x])) : {}
  return (
    <article className="case" id="case-2">
      <CaseHead n={2} title="A mandate no portfolio can satisfy, and the proof" live={live} />
      <p className="muted" style={{ marginTop: 8, maxWidth: '70ch' }}>
        {mandateId('C03')} · <b style={{ color: 'var(--ink)' }}>{client && mandateName(client)}</b>. A language model
        still returns a confident portfolio here. Certus proves infeasibility, isolates the smallest conflicting set,
        and prices the cheapest relaxation.
      </p>
      <div style={{ height: 20 }} />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <div className="stack">
          <p className="small">
            <Verdict receipt={r} />
          </p>
          <ConflictBar conflictIds={r.conflict_set} rules={client.rules} />
          <div className="split">
            <div>
              <div className="label" style={{ paddingBottom: 6 }}>
                Minimal conflicting set
              </div>
              <table className="tbl">
                <tbody>
                  {r.conflict_set.map((id) => (
                    <tr key={id}>
                      <td className="num faint">{id}</td>
                      <td>{byId[id]?.source.replace(/\.$/, '')}</td>
                      <td className="r nw num muted" style={{ fontSize: 12.5 }}>
                        {byId[id] && formal(byId[id])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: 10 }}>
                Deletion filter: drop each constraint and re-solve; whatever stays infeasible is the conflict. Removing
                any one of these makes the rest feasible.
              </p>
            </div>
            <div>
              <div className="label" style={{ paddingBottom: 6 }}>
                Cheapest relaxation
              </div>
              <table className="tbl">
                <tbody>
                  {r.cheapest_relaxation.map((x) => (
                    <tr key={x.rule_id}>
                      <td className="num faint">{x.rule_id}</td>
                      <td>{byId[x.rule_id]?.source.replace(/\.$/, '')}</td>
                      <td className="r nw num">
                        {limitFmt(byId[x.rule_id], x.old_limit)} → <b>{limitFmt(byId[x.rule_id], x.new_limit)}</b>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: 10 }}>
                One slack per soft constraint, minimize Σ priority·slack. Hard constraints and exclusions never bend.
              </p>
            </div>
          </div>
          <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />
        </div>
      )}
    </article>
  )
}

// ---------- Case 3: verify your own weights ----------

function CaseYours({ clients }) {
  const [cid, setCid] = useState('C04')
  const client = clients.find((c) => c.client_id === cid)
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
    <article className="case" id="case-3">
      <div className="case-head">
        <span className="label">Case 3</span>
        <span className="chip accent">Your input · solved on submit</span>
      </div>
      <h3 className="case-title">Verify a portfolio of your own</h3>
      <p className="muted" style={{ marginTop: 8, maxWidth: '70ch' }}>
        Choose a mandate, edit the weights (normalized to 100%) and submit. Nothing is cached: the server builds the
        mixed-integer model for your input and solves it.
      </p>
      <div style={{ height: 16 }} />
      <label className="small">
        <span className="label">Mandate&nbsp;&nbsp;</span>
        <select className="field" value={cid} onChange={(e) => choose(e.target.value)}>
          {clients.map((c) => (
            <option key={c.client_id} value={c.client_id}>
              {mandateId(c.client_id)} · {mandateName(c)}
            </option>
          ))}
        </select>
      </label>
      <div style={{ height: 16 }} />
      <div className="split">
        <div>
          <div className="label" style={{ paddingBottom: 6 }}>
            Weights (%)
          </div>
          <table className="tbl">
            <tbody>
              {client.universe.map((t) => (
                <tr key={t}>
                  <td className="num">{t}</td>
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
          <div className="actions" style={{ marginTop: 14 }}>
            <button className="btn" onClick={run} disabled={result.busy || total <= 0}>
              {result.busy ? 'Solving…' : 'Verify →'}
            </button>
            <button className="btn ghost" onClick={() => setWeights(null)}>
              Reset
            </button>
            <span className="small muted num">sum {(total * 100).toFixed(1)}%</span>
          </div>
        </div>
        <div>
          <div className="label" style={{ paddingBottom: 6 }}>
            Mandate constraints
          </div>
          <table className="tbl">
            <tbody>
              {client.rules.map((x) => (
                <tr key={x.id}>
                  <td className="num faint">{x.id}</td>
                  <td>{x.source.replace(/\.$/, '')}</td>
                  <td className="r nw num muted hide-sm" style={{ fontSize: 12.5 }}>
                    {formal(x)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div style={{ height: 16 }} />
      <Pending busy={result.busy} error={result.error} />
      {r && (
        <div className="stack" style={{ marginTop: 12 }}>
          <p className="small">
            <Verdict receipt={r} /> <span className="muted">&nbsp;{r.summary}</span>
          </p>
          <Checks checks={r.checks} rules={client.rules} />
          {r.verdict !== 'PASS' && Object.keys(r.repaired_weights).length > 0 && (
            <Dumbbell before={result.data.sent} after={r.repaired_weights} beforeLabel="Yours" />
          )}
          <Certificate cert={result.data.certificate} receipt={r} />
        </div>
      )}
    </article>
  )
}

// ---------- method ----------

// [expression, what it encodes]. A table, not a <pre>: subscript glyphs fall back to another
// font and would break column alignment.
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
    <figure>
      <div className="fig scroll">
        <table className="tbl num" style={{ fontSize: 13.5 }}>
          <tbody>
            {FORMULATION.map(([expr, note], i) => (
              <tr key={expr}>
                <td className="nw" style={{ borderBottom: 0, paddingLeft: i === 0 ? 0 : '11ch' }}>
                  {expr}
                </td>
                <td className="faint nw" style={{ borderBottom: 0 }}>
                  # {note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption>
        <b>Fig. 3.</b> The repair model, a mixed-integer second-order cone program solved by SCIP. Feasibility is the same
        model with no objective.
      </figcaption>
    </figure>
  )
}

const RUNS = [
  {
    model: 'asi1-mini',
    n: 12,
    broken: '10 / 12',
    rows: [
      { name: 'Self-check', mean: 33, lo: 8, hi: 58 },
      { name: 'Which rule failed', mean: 42, lo: 17, hi: 67 },
      { name: 'Actual vs limit', mean: 50, lo: 25, hi: 75 },
    ],
  },
  {
    model: 'gemini-3.5-flash-lite',
    n: 20,
    broken: '16 / 20',
    rows: [
      { name: 'Self-check', mean: 20, lo: 5, hi: 40 },
      { name: 'Which rule failed', mean: 25, lo: 10, hi: 45 },
      { name: 'Actual vs limit', mean: 25, lo: 10, hi: 45 },
    ],
  },
]

// ---------- the page ----------

export default function Home({ clients, error }) {
  const nav = useNavigate()
  const byId = useMemo(() => Object.fromEntries((clients ?? []).map((c) => [c.client_id, c])), [clients])
  return (
    <>
      <TopBar>
        <a href="#cases">Cases</a>
        <a href="#method" className="opt">
          Method
        </a>
        <a href="#results" className="opt">
          Results
        </a>
        <a href="#mandates" className="opt">
          Mandates
        </a>
        <a href={REPO}>Code ↗</a>
      </TopBar>
      <main className="page">
        <div className="hero">
          <div>
            <span className="kicker">
              <span className="dot" /> Working paper · Nov 2026 · solved live
            </span>
            <h1 className="title">
              Certainty for <em>AI-drafted</em> portfolios.
            </h1>
            <p className="lede" style={{ marginTop: 20 }}>
              Language models can draft a portfolio, but nothing guarantees the draft satisfies the client's mandate.
              Certus encodes the mandate as a mixed-integer second-order cone program and solves it with SCIP: it reports
              every violated constraint, proves when a mandate is infeasible, and repairs the draft to the nearest
              compliant portfolio. Each answer ships with a certificate of the solve.
            </p>
            <p className="byline" style={{ marginTop: 16 }}>
              Samarth Mukhi · University of Wisconsin–Madison · started at LA Hacks 2026
            </p>
            <div className="actions" style={{ marginTop: 22 }}>
              <a className="btn" href="#case-1">
                See it solve live ↓
              </a>
              <a className="btn ghost" href={REPO}>
                Source ↗
              </a>
              <a href="https://youtu.be/ngHaVytPs6M" className="small">
                Demo video ↗
              </a>
            </div>
          </div>
          <FeasibleRegion />
        </div>

        <div className="stats">
          <div>
            <div className="label">LLM drafts violating the mandate</div>
            <div className="stat">81%</div>
            <div className="small muted">26 of 32 first drafts, two models</div>
          </div>
          <div>
            <div className="label">Fixed by the LLM from feedback</div>
            <div className="stat">2 / 16</div>
            <div className="small muted">within three revision rounds</div>
          </div>
          <div>
            <div className="label">After Certus repair</div>
            <div className="stat" style={{ color: 'var(--accent)' }}>
              100%
            </div>
            <div className="small muted">compliant, or infeasibility proven</div>
          </div>
        </div>
        {error && (
          <p className="status" style={{ marginTop: 16 }}>
            <span className="dot bad" /> Could not reach the verifier API: {error}
          </p>
        )}

        <Section n={1} id="how" title="Models propose. A solver decides.">
          <Pipeline />
        </Section>

        <Section n={2} id="cases" title="Three cases, solved as you read">
          <CaseViolation client={byId.C04} />
          <CaseInfeasible client={byId.C03} />
          {clients && <CaseYours clients={clients} />}
        </Section>

        <Section n={3} id="method" title="Method">
          <p className="lede" style={{ fontSize: 16, lineHeight: '26px' }}>
            Every mandate constraint becomes a constraint on weights w and binary holding indicators z. One model answers
            three questions: is this draft compliant, can any portfolio be compliant, and which compliant portfolio is
            nearest.
          </p>
          <div style={{ height: 20 }} />
          <Formulation />
          <div style={{ height: 20 }} />
          <table className="tbl">
            <tbody>
              {[
                ['Check', 'Evaluate each constraint on the draft directly; report actual vs limit.'],
                ['Feasibility', 'Solve with no objective. Infeasible means the mandate itself is contradictory.'],
                ['Conflict set', 'Deletion filter: at most one solve per constraint; returns a minimal infeasible subset.'],
                ['Relaxation', 'Slack per soft constraint, minimize Σ priority·slack; exclusions and hard limits never bend.'],
                ['Repair', 'Minimize capital moved, ½‖w − w_draft‖₁, subject to every (relaxed) constraint.'],
                ['Shadow cost', 'Re-solve the max-utility portfolio without each constraint; the gap is its cost.'],
              ].map(([k, v]) => (
                <tr key={k}>
                  <td className="nw label" style={{ width: '15ch', color: 'var(--ink)' }}>
                    {k}
                  </td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small muted" style={{ marginTop: 14 }}>
            Data: daily prices for 20 U.S. tickers through Oct 16, 2026; μ and Σ from the last 756 trading days; risk-free
            rate 4%; statistics are ex-ante. SCIP runs with a 1e-9 feasibility tolerance and a 15 s limit per solve.
          </p>
        </Section>

        <Section n={4} id="results" title="Can feedback replace the verifier?">
          <p className="lede" style={{ fontSize: 16, lineHeight: '26px' }}>
            If the model could fix its own drafts from feedback, a checker would be enough. We gave three kinds of
            feedback over three revision rounds, every condition starting from the same first draft.
          </p>
          <div style={{ height: 20 }} />
          <div className="fig">
            <CIChart runs={RUNS} />
          </div>
          <figcaption>
            <b>Fig. 4.</b> Share of trials fully compliant after round 3, with 95% bootstrap intervals. Richer feedback helps
            slightly but not significantly (sign test, explained vs. bare: p = 1.0 in both runs). In the larger run the
            model fixed 2 of 16 violating drafts. Feedback is not a substitute for exact repair.
          </figcaption>
        </Section>

        <Section n={5} id="mandates" title="Mandate book">
          <p className="muted">
            {clients ? clients.length : '—'} synthetic mandates, written in plain language and mapped to formal
            constraints. Open one to re-verify every recorded AI draft live.
          </p>
          <div style={{ height: 16 }} />
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
                      <td className="nw num faint">{mandateId(c.client_id)}</td>
                      <td>
                        <Link to={`/m/${c.client_id}`} style={{ textDecoration: 'none' }}>
                          {mandateName(c)}
                        </Link>
                      </td>
                      <td className="r num">{c.rules.length}</td>
                      <td className="r num hide-sm">{c.universe.length}</td>
                      <td className="r faint">→</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section n={6} id="reproduce" title="Reproduce it">
          <div className="fig scroll">
            <pre className="num" style={{ margin: 0, fontSize: 13, lineHeight: '22px' }}>
              <span className="faint"># the check Case 1 runs, from your terminal</span>
              {'\n'}curl -s https://swarmfolio-api.onrender.com/api/verify/C04/round/1 | jq .certificate{'\n\n'}
              <span className="faint"># 298 tests: constraints, solver, conflicts, relaxation, repair, API</span>
              {'\n'}git clone {REPO} && cd SwarmFolio---Referee{'\n'}pip install -r requirements.txt && pytest -q
            </pre>
          </div>
        </Section>

        <Section n={7} id="limits" title="Limitations">
          <table className="tbl">
            <tbody>
              {[
                'Mandates are synthetic; the universe is 20 large-cap U.S. tickers.',
                'Risk and return are historical estimates; Certus certifies constraints, not future performance.',
                'AI drafts are recorded runs (Oct 18, 2026). Their verification is live; the drafting is not.',
                'The feedback experiment is small (32 trials); its null result is suggestive, not conclusive.',
              ].map((x) => (
                <tr key={x}>
                  <td>{x}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <footer className="foot">
          <span>SwarmFolio Certus · Samarth Mukhi</span>
          <a href="https://samarthmukhi.com">samarthmukhi.com ↗</a>
          <a href={REPO}>GitHub ↗</a>
          <a href="https://devpost.com/software/swarmfolio-referee">Devpost (LA Hacks 2026) ↗</a>
        </footer>
      </main>
    </>
  )
}
