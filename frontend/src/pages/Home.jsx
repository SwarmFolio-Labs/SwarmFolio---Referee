// The paper: abstract and Table 1, Fig. 1-2, three live exhibits, method, results, the mandate book.
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { verify, verifyRound } from '../api.js'
import { CIChart, ConflictBar, Dumbbell, FeasibleRegion, Pipeline } from '../components/Figures.jsx'
import { Certificate, Checks, LiveChip, Pending, useLive, Verdict } from '../components/Live.jsx'
import { TopBar } from '../components/TopBar.jsx'
import { formal, mandateId, mandateName, pct } from '../mandates.js'

const REPO = 'https://github.com/SwarmFolio-Labs/SwarmFolio---Referee'

function Section({ n, id, title, note, wide, children }) {
  return (
    <section className={`sec ${wide ? 'wide' : ''}`} id={id}>
      <aside className="rail">
        <b>§{n}</b>
        {note}
      </aside>
      <div>
        <h2>{title}</h2>
        {children}
      </div>
    </section>
  )
}

function Exhibit({ letter, id, title, live, children }) {
  return (
    <article className="exhibit" id={id}>
      <span className="tag tab">Exhibit {letter}</span>
      <div className="ex-head">
        <h3 className="ex-title">{title}</h3>
        {live}
      </div>
      {children}
    </article>
  )
}

const Head = ({ children }) => (
  <div className="u small muted" style={{ paddingBottom: 6 }}>
    {children}
  </div>
)

// ---------- Exhibit A: a recorded AI draft, re-verified live ----------

function ExhibitA({ client }) {
  const live = useLive(() => verifyRound('C04', 1), [])
  const r = live.data?.receipt
  return (
    <Exhibit
      letter="A"
      id="exhibit-a"
      title="An AI-drafted portfolio that violates its mandate"
      live={<LiveChip busy={live.busy} cert={live.data?.certificate} />}
    >
      <p className="muted" style={{ marginTop: 8, maxWidth: '72ch' }}>
        {mandateId('C04')} ({client && mandateName(client)}): 60% of the book in NVDA, MSFT and AAPL; cut risk without a
        large taxable sale. The allocator's first draft, recorded Oct 18, 2026 (asi1-mini), is re-checked against all
        eight constraints each time this page loads.
      </p>
      <div className="gap" />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <div className="stack">
          <p>
            <Verdict receipt={r} /> <span className="muted small">&nbsp;{r.summary}</span>
          </p>
          <Checks checks={r.checks} rules={client.rules} />
          <div className="split" style={{ marginTop: 24 }}>
            <div>
              <Head>Repair · min ½‖w − w_draft‖₁</Head>
              <Dumbbell before={live.data.weights} after={r.repaired_weights} />
            </div>
            <div>
              <Head>Cost of compliance</Head>
              <table className="tbl">
                <tbody>
                  <tr>
                    <td>capital moved</td>
                    <td className="r">{pct(r.capital_moved)}</td>
                  </tr>
                  <tr>
                    <td>Sharpe, ex-ante</td>
                    <td className="r">
                      {r.sharpe_before.toFixed(2)} → {r.sharpe_after.toFixed(2)}
                    </td>
                  </tr>
                  <tr>
                    <td>volatility after</td>
                    <td className="r">{pct(r.vol_after)}</td>
                  </tr>
                  <tr>
                    <td>violations</td>
                    <td className="r">{r.checks.filter((c) => !c.passed).length} → 0</td>
                  </tr>
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: 10 }}>
                The repair is the compliant portfolio closest to the draft, so as much of the model's view as possible
                survives.
              </p>
            </div>
          </div>
          <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />
        </div>
      )}
    </Exhibit>
  )
}

// ---------- Exhibit B: constraints that can't all hold, proven ----------

const limitFmt = (rule, x) => (rule && /holdings/.test(rule.type) ? `${Math.round(x)}` : pct(x))

function ExhibitB({ client }) {
  const live = useLive(() => verifyRound('C03', 1), [])
  const r = live.data?.receipt
  const byId = client ? Object.fromEntries(client.rules.map((x) => [x.id, x])) : {}
  return (
    <Exhibit
      letter="B"
      id="exhibit-b"
      title="A mandate no portfolio can satisfy, and the proof"
      live={<LiveChip busy={live.busy} cert={live.data?.certificate} />}
    >
      <p className="muted" style={{ marginTop: 8, maxWidth: '72ch' }}>
        {mandateId('C03')} ({client && mandateName(client)}). A language model still returns a confident portfolio here.
        Certus proves the constraints are infeasible, isolates the smallest conflicting set, and prices the cheapest
        relaxation.
      </p>
      <div className="gap" />
      <Pending busy={live.busy && !r} error={live.error} />
      {r && client && (
        <div className="stack">
          <p>
            <Verdict receipt={r} />
          </p>
          <ConflictBar conflictIds={r.conflict_set} rules={client.rules} />
          <div className="split">
            <div>
              <Head>Minimal conflicting set</Head>
              <table className="tbl">
                <tbody>
                  {r.conflict_set.map((id) => (
                    <tr key={id}>
                      <td className="faint">{id}</td>
                      <td>{byId[id]?.source.replace(/\.$/, '')}</td>
                      <td className="r nw muted hide-sm" style={{ fontSize: 12 }}>
                        {byId[id] && formal(byId[id])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: 8 }}>
                Deletion filter: drop each constraint and re-solve; whatever stays infeasible is the conflict. Removing
                any one of these makes the rest feasible.
              </p>
            </div>
            <div>
              <Head>Cheapest relaxation</Head>
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
              <p className="small muted" style={{ marginTop: 8 }}>
                One slack per soft constraint, minimize Σ priority·slack (eq. 10). Hard constraints and exclusions never
                bend.
              </p>
            </div>
          </div>
          <Certificate cert={live.data.certificate} receipt={r} onRerun={live.run} busy={live.busy} />
        </div>
      )}
    </Exhibit>
  )
}

// ---------- Exhibit C: verify your own weights ----------

function ExhibitC({ clients }) {
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
    <Exhibit
      letter="C"
      id="exhibit-c"
      title="Verify a portfolio of your own"
      live={<span className="livemark">Your input · solved on submit</span>}
    >
      <p className="muted" style={{ marginTop: 8, maxWidth: '72ch' }}>
        Choose a mandate, edit the weights (normalized to 100%) and submit. Nothing is cached: the server builds the
        mixed-integer model for your input and solves it.
      </p>
      <div className="gap" />
      <label>
        <span className="u small muted">Mandate&nbsp;&nbsp;</span>
        <select className="field" value={cid} onChange={(e) => choose(e.target.value)}>
          {clients.map((c) => (
            <option key={c.client_id} value={c.client_id}>
              {mandateId(c.client_id)} · {mandateName(c)}
            </option>
          ))}
        </select>
      </label>
      <div className="gap" />
      <div className="split">
        <div>
          <Head>Weights (%)</Head>
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
          <p className="links" style={{ marginTop: 12 }}>
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
          <Head>Mandate constraints</Head>
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
      <div className="gap" />
      <Pending busy={result.busy} error={result.error} />
      {r && (
        <div className="stack">
          <p>
            <Verdict receipt={r} /> <span className="muted small">&nbsp;{r.summary}</span>
          </p>
          <Checks checks={r.checks} rules={client.rules} />
          {r.verdict !== 'PASS' && Object.keys(r.repaired_weights).length > 0 && (
            <Dumbbell before={result.data.sent} after={r.repaired_weights} beforeLabel="Yours" />
          )}
          <Certificate cert={result.data.certificate} receipt={r} />
        </div>
      )}
    </Exhibit>
  )
}

// ---------- method: numbered equations ----------

const EQUATIONS = [
  ['minimize   ½ ‖w − w_draft‖₁', 'repair: least capital moved'],
  ['subject to Σ wᵢ = 1,  w ≥ 0', 'fully invested, long only'],
  ['           0.005·zᵢ ≤ wᵢ ≤ zᵢ,  zᵢ ∈ {0,1}', 'zᵢ = 1 if asset i is held'],
  ['           ‖Lᵀw‖₂ ≤ σ_max,  Σ = LLᵀ', 'volatility cap, a second-order cone'],
  ['           ‖w − w₀‖₁ ≤ τ_max', 'turnover from current holdings'],
  ['           l_S ≤ Σ_{i∈S} wᵢ ≤ u_S', 'sector floors and caps'],
  ['           k_min ≤ Σ zᵢ ≤ k_max', 'number of holdings'],
  ['           wᵢ ≥ m·zᵢ', 'minimum position size'],
  ['           w_E = 0', 'exclusions'],
  ['minimize   Σ_j p_j·s_j  (constraint j relaxed by s_j ≥ 0)', 'cheapest relaxation, when (1)-(9) is infeasible'],
]

function Equations() {
  return (
    <div className="fig scroll">
      {EQUATIONS.map(([e, note], i) => (
        <div className="eq" key={i} style={i === 9 ? { marginTop: 10, paddingTop: 10, borderTop: '1px dashed var(--rule)' } : undefined}>
          <span className="nw" style={{ whiteSpace: 'pre' }}>
            {e}
            <span className="note hide-sm">{'   '}# {note}</span>
          </span>
          <span className="no">({i + 1})</span>
        </div>
      ))}
    </div>
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
        <a href="#exhibit-a">Exhibits</a>
        <a href="#method">Method</a>
        <a href="#results">Results</a>
        <a href={REPO}>Code ↗</a>
      </TopBar>
      <main className="page">
        <div style={{ height: 48 }} />
        <p className="links">
          <span className="tag">Working paper · Nov 2026</span>
          <span className="tag line">Solved live</span>
        </p>
        <div className="gap" />
        <h1 className="title">Certus: exact verification for AI-drafted portfolios</h1>
        <div className="gap" />
        <p className="muted">Samarth Mukhi · University of Wisconsin–Madison · started at LA Hacks 2026</p>
        <div className="gap" />
        <p className="abstract">
          <b>Abstract.</b> Language models can draft an investment portfolio, but nothing guarantees the draft satisfies
          the client's mandate. In our runs, 26 of 32 first drafts violated at least one constraint, and feedback alone
          fixed 2 of 16. Certus separates proposing from deciding: it encodes the mandate as a mixed-integer second-order
          cone program, solves it with SCIP, reports every violation, proves when a mandate is infeasible, and repairs the
          draft to the nearest compliant portfolio. Every check on this page runs on the server as you read, and ships
          with a certificate of the solve.
        </p>
        <div className="gap" />
        <p className="links">
          <a href="#exhibit-a">Exhibits ↓</a>
          <a href={REPO}>Source ↗</a>
          <a href="https://youtu.be/ngHaVytPs6M">Demo video ↗</a>
          <a href="https://devpost.com/software/swarmfolio-referee">Devpost ↗</a>
        </p>
        <div className="gap" />
        <div className="gap" />
        <div className="scroll">
          <table className="tbl" style={{ maxWidth: 720 }}>
            <caption>Table 1. Headline results.</caption>
            <thead>
              <tr>
                <th>Measure</th>
                <th className="r">Value</th>
                <th className="r">n</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>LLM first drafts violating the mandate</td>
                <td className="r">
                  <b>81%</b>
                </td>
                <td className="r nw muted">26 / 32 · 2 models</td>
              </tr>
              <tr>
                <td>Violating drafts the LLM fixed from feedback</td>
                <td className="r">
                  <b>12.5%</b>
                </td>
                <td className="r nw muted">2 / 16 · 3 rounds</td>
              </tr>
              <tr>
                <td>Drafts compliant after Certus, or proven infeasible</td>
                <td className="r">
                  <b>100%</b>
                </td>
                <td className="r nw muted">by construction</td>
              </tr>
            </tbody>
          </table>
        </div>
        {error && <p style={{ color: 'var(--bad)', marginTop: 12 }}>✕ Could not reach the verifier API: {error}</p>}
        <div className="gap" />
        <div className="gap" />
        <div style={{ maxWidth: 680 }}>
          <FeasibleRegion />
        </div>

        <Section n={1} id="how" title="Models propose. A solver decides." note="The LLMs never see a pass/fail they can talk their way around.">
          <Pipeline />
        </Section>

        <Section
          n={2}
          wide
          id="exhibits"
          title="Exhibits"
          note="Each exhibit calls the verifier when the page loads. The certificate under it is the server's record of that solve."
        >
          <ExhibitA client={byId.C04} />
          <ExhibitB client={byId.C03} />
          {clients && <ExhibitC clients={clients} />}
        </Section>

        <Section n={3} id="method" title="Method" note="Feasibility is (2)-(9) with no objective. Conflicts: deletion filter.">
          <p style={{ maxWidth: '72ch' }}>
            Each mandate constraint becomes a constraint on weights w and binary holding indicators z. One model answers
            three questions: is the draft compliant, can any portfolio be compliant, and which compliant portfolio is
            nearest.
          </p>
          <div className="gap" />
          <Equations />
          <div className="gap" />
          <table className="tbl">
            <tbody>
              {[
                ['check', 'Evaluate each constraint on the draft directly; report actual vs limit.'],
                ['feasibility', 'Solve (2)-(9) with no objective. Infeasible: the mandate itself is contradictory.'],
                ['conflict set', 'Deletion filter, at most one solve per constraint; returns a minimal infeasible subset.'],
                ['relaxation', 'Solve (10); exclusions and hard limits never bend.'],
                ['repair', 'Solve (1)-(9), with any relaxed limits from (10).'],
                ['shadow cost', 'Re-solve the max-utility portfolio without each constraint; the gap is its cost.'],
              ].map(([k, v]) => (
                <tr key={k}>
                  <td className="nw u small" style={{ width: '15ch' }}>
                    {k}
                  </td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small muted" style={{ marginTop: 12 }}>
            Data: daily prices for 20 U.S. tickers through Oct 16, 2026; μ and Σ from the last 756 trading days;
            risk-free rate 4%; statistics are ex-ante. SCIP 1e-9 feasibility tolerance, 15 s limit per solve.
          </p>
        </Section>

        <Section n={4} id="results" title="Can feedback replace the verifier?" note="Same first draft in every condition; only the feedback differs.">
          <p style={{ maxWidth: '72ch' }}>
            If the model could repair its own drafts, a checker would be enough. We gave three kinds of feedback over three
            revision rounds.
          </p>
          <div className="gap" />
          <div className="fig">
            <CIChart runs={RUNS} />
          </div>
          <figcaption>
            <b>Fig. 3.</b> Share of trials fully compliant after round 3, with 95% bootstrap intervals. Richer feedback helps
            slightly but not significantly (sign test, explained vs. bare: p = 1.0 in both runs). Feedback is not a
            substitute for exact repair.
          </figcaption>
        </Section>

        <Section n={5} id="mandates" title="Mandate book" note="Open one to re-verify every recorded AI draft for it.">
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
        </Section>

        <Section n={6} id="reproduce" title="Reproduce" note="The API is public and the repo has the full test suite.">
          <pre className="diagram" style={{ background: 'var(--wash)', padding: 14 }}>
            <span className="faint"># the check Exhibit A runs</span>
            {'\n'}curl -s https://swarmfolio-api.onrender.com/api/verify/C04/round/1 | jq .certificate{'\n\n'}
            <span className="faint"># 298 tests: constraints, solver, conflicts, relaxation, repair, API</span>
            {'\n'}git clone {REPO}
            {'\n'}cd SwarmFolio---Referee && pip install -r requirements.txt && pytest -q
          </pre>
        </Section>

        <Section n={7} id="limits" title="Limitations">
          <table className="tbl">
            <tbody>
              {[
                'Mandates are synthetic; the universe is 20 large-cap U.S. tickers.',
                'Risk and return are historical estimates; Certus certifies constraints, not future performance.',
                'AI drafts are recorded runs (Oct 18, 2026). Their verification is live; the drafting is not.',
                'The feedback experiment is small (32 trials); its null result is suggestive, not conclusive.',
              ].map((x, i) => (
                <tr key={x}>
                  <td className="faint" style={{ width: '4ch' }}>
                    {i + 1}.
                  </td>
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
          <span className="faint">End of paper</span>
        </footer>
      </main>
    </>
  )
}
