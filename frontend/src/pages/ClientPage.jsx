// Screen A: one client's committee run (replayed step by step), plus the receipt, price tags, the live Referee and live runs.
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getClients, getDemo, getSettings } from '../api.js'
import ConflictPanel from '../components/ConflictPanel.jsx'
import DebateTimeline from '../components/DebateTimeline.jsx'
import LiveRun from '../components/LiveRun.jsx'
import PriceTags from '../components/PriceTags.jsx'
import ReceiptCard from '../components/ReceiptCard.jsx'
import RuleCheckRow from '../components/RuleCheckRow.jsx'
import Stamp from '../components/Stamp.jsx'
import StartingWeights from '../components/StartingWeights.jsx'
import TryReferee from '../components/TryReferee.jsx'
import { ErrorNote, Spinner } from '../components/ui.jsx'
import { displayName, isSynthetic, pct, pronoun } from '../format.js'
import { buildSteps } from '../steps.js'

const STEP_MS = 900
const TABS = [
  { id: 'run', label: 'Committee run' },
  { id: 'receipt', label: 'Receipt' },
  { id: 'prices', label: 'Price tags' },
  { id: 'try', label: 'Try the Referee' },
  { id: 'live', label: 'Live run' },
]

/** Replays a saved run one step at a time; ?all=1 starts at the end. */
function useReplay(steps, startDone) {
  const [visible, setVisible] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  useEffect(() => {
    if (steps.length === 0) return
    if (startDone) setVisible(steps.length)
    else setPlaying(true)
  }, [steps.length, startDone])
  useEffect(() => {
    if (!playing) return
    if (visible >= steps.length) {
      setPlaying(false)
      return
    }
    timer.current = setTimeout(() => setVisible((v) => v + 1), visible === 0 ? 300 : STEP_MS)
    return () => clearTimeout(timer.current)
  }, [playing, visible, steps.length])
  return {
    visible,
    playing,
    done: steps.length > 0 && visible >= steps.length,
    toggle: () => setPlaying((p) => !p),
    skip: () => { setPlaying(false); setVisible(steps.length) },
    replay: () => { setVisible(0); setPlaying(true) },
  }
}

/** What the receipt's "holdings changed" table compares: proposal → repair, or starting book → final. */
function receiptChanges(client, demo) {
  if (demo.receipt.verdict === 'VIOLATIONS_REPAIRED') {
    return { before: demo.final_proposal.weights, after: demo.receipt.repaired_weights, beforeLabel: 'Proposed', afterLabel: 'Repaired' }
  }
  if (demo.receipt.verdict === 'RULES_INFEASIBLE') return {}
  const start = Object.keys(client.current_weights).length ? client.current_weights : demo.extras?.proposals?.[0]
  return { before: start, after: demo.final_proposal.weights, beforeLabel: 'Start', afterLabel: 'Final' }
}

const brokenCount = (r) => r.checks.filter((c) => !c.passed).length

function stampSub(demo) {
  const r = demo.receipt
  const n = r.checks.length
  if (r.verdict === 'PASS') return `${n - brokenCount(r)} of ${n} · round ${demo.rounds}`
  if (r.verdict === 'VIOLATIONS_REPAIRED') return `${brokenCount(r)} of ${n} · ${pct(r.capital_moved)}`
  if (r.verdict === 'RULES_INFEASIBLE') return `${r.conflict_set.length} rules clash`
  return null
}

/** "Broken rules per round": R1 ■■ 2 → R2 ■■■ 3 → R3 ○ 0, from the receipts revealed so far. */
function RoundTally({ steps, visible }) {
  const receipts = steps.slice(0, visible).filter((s) => s.kind === 'receipt' && s.receipt)
  if (receipts.length === 0) return null
  return (
    <div data-component="round-tally" className="flex flex-col gap-2">
      <span className="label">Broken rules per round</span>
      <div className="flex flex-wrap items-center gap-2.5">
        {receipts.map((s, i) => {
          const b = s.receipt.rules_feasible ? brokenCount(s.receipt) : null
          return (
            <span key={s.key} className="flex items-center gap-2.5">
              {i > 0 && <span className="text-muted">→</span>}
              <span className="num text-xs text-muted md:inline hidden">R{s.round}</span>
              <span className="hidden gap-0.5 md:flex">
                {b === 0 ? (
                  <span className="h-2 w-2 rounded-full border border-pass" />
                ) : (
                  Array.from({ length: Math.min(b ?? 1, 6) }, (_, k) => (
                    <span key={k} className={`h-2 w-2 ${b === null ? 'rotate-45 border border-warn' : 'bg-fail'}`} />
                  ))
                )}
              </span>
              <span className={`num text-lg font-semibold ${b === 0 ? 'text-pass' : b === null ? 'text-warn-text' : 'text-fail'}`}>
                {b ?? '×'}
              </span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

function FinalBox({ demo, onTab }) {
  const r = demo.receipt
  const vol = r.checks.find((c) => c.type === 'max_volatility')
  return (
    <div className="grid gap-4">
      {r.verdict !== 'RULES_INFEASIBLE' && (
        <div className="flex gap-8 border border-line bg-surface px-5 py-4">
          <div>
            <div className="label">Sharpe</div>
            <div className="num mt-1 text-3xl font-medium">{r.sharpe_after.toFixed(2)}</div>
          </div>
          <div>
            <div className="label">Volatility</div>
            <div className="num mt-1 text-3xl font-medium">
              {pct(r.vol_after)}
              {vol && <span className="ml-1.5 text-xs font-normal text-muted">max {pct(vol.limit)}</span>}
            </div>
          </div>
        </div>
      )}
      <div className="hidden flex-wrap gap-2.5 md:flex">
        <button className="btn-primary" onClick={() => onTab('receipt')}>
          {r.verdict === 'RULES_INFEASIBLE' ? 'See the conflict →' : 'Open the receipt →'}
        </button>
        <button className="btn-ghost" onClick={() => onTab('prices')}>See price tags</button>
      </div>
    </div>
  )
}

function RunView({ client, demo, demoError, steps, replay, onTab }) {
  if (demoError) {
    return (
      <div className="border border-line bg-surface p-6 text-sm">
        <div className="mb-1 font-semibold">No saved committee run for this client yet.</div>
        <p className="text-muted">
          Save one with <code className="num">python data/demo_runs/save_demo_run.py {client.client_id}</code> (needs
          ASI1_API_KEY). The price tags and the live Referee work without it.
        </p>
      </div>
    )
  }
  if (!demo) return <Spinner label="Loading the saved committee run…" />

  const start = Object.keys(client.current_weights).length ? client.current_weights : demo.extras?.proposals?.[0]
  const final = demo.final_proposal.weights
  const turnover = start
    ? Object.keys({ ...start, ...final }).reduce((s, t) => s + Math.abs((final[t] ?? 0) - (start[t] ?? 0)), 0) / 2
    : 0
  const ruleById = Object.fromEntries(client.rules.map((r) => [r.id, r]))
  const conflict = new Set(demo.receipt.conflict_set)
  const sectionTitle = !demo.receipt.rules_feasible
    ? "From the starting book to the committee's draft"
    : /stock grant/i.test(client.story)
    ? 'From stock grants to a balanced book'
    : Object.keys(client.current_weights).length
      ? 'From the starting book to a compliant one'
      : 'From the first draft to the final book'

  return (
    <div className="grid gap-12 pb-24 md:pb-0">
      {/* Impossible client: the conflict comes first, above the replayed rounds. */}
      {!demo.receipt.rules_feasible && (
        <div className="animate-reveal">
          <ConflictPanel
            layout="page"
            explain={demo.receipt.conflict_explain}
            relaxations={demo.receipt.cheapest_relaxation}
            conflictSet={demo.receipt.conflict_set}
            rules={client.rules}
            checks={demo.receipt.checks}
            clientName={displayName(client.name)}
            clientStory={client.story}
            onEdit={() => onTab('try')}
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-ui text-muted">
        <span className={`h-1.5 w-1.5 rounded-full ${replay.playing ? 'animate-pulse bg-warn' : 'bg-muted'}`} />
        {replay.playing
          ? `Replaying the saved run · step ${replay.visible} of ${steps.length}`
          : replay.done
            ? `Saved run · ${demo.rounds} round${demo.rounds > 1 ? 's' : ''} · ${steps.length} steps`
            : `Paused at step ${replay.visible} of ${steps.length}`}
        {demo.extras?.source === 'dev-fakes' && <span>· development run: scripted analysts, real Referee</span>}
        <span className="flex gap-3">
          {!replay.done && (
            <button className="underline underline-offset-4 hover:text-ink" onClick={replay.toggle}>
              {replay.playing ? 'Pause' : 'Resume'}
            </button>
          )}
          {!replay.done && (
            <button className="underline underline-offset-4 hover:text-ink" onClick={replay.skip}>Skip to the end</button>
          )}
          {replay.done && (
            <button className="underline underline-offset-4 hover:text-ink" onClick={replay.replay}>Replay</button>
          )}
        </span>
      </div>

      <DebateTimeline
        steps={steps}
        visible={replay.visible}
        rules={client.rules}
        final={<FinalBox demo={demo} onTab={onTab} />}
      />

      {replay.done && (
        <div className="-mx-6 grid animate-reveal gap-12 border-t border-line px-6 pt-10 md:grid-cols-2 xl:-mx-0 xl:px-0">
          {start && (
            <section>
              <h2 className="font-display text-2xl font-semibold">{sectionTitle}</h2>
              <p className="mb-4 mt-1 text-ui text-muted">
                {Object.keys(client.current_weights).length ? 'Starting holdings' : 'First draft'} → final ·{' '}
                <span className="num font-semibold text-ink">{pct(turnover)}</span> of the book changes hands
              </p>
              <div className="hidden md:block"><StartingWeights start={start} final={final} /></div>
              <div className="md:hidden"><StartingWeights start={start} final={final} compact /></div>
            </section>
          )}
          <section>
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-2xl font-semibold">Every rule, checked</h2>
              <span className="label">Actual · limit</span>
            </div>
            <p className="mb-4 mt-1 text-ui text-muted">{demo.receipt.summary}</p>
            <ul className="border-t border-ink">
              {demo.receipt.checks.map((c) => (
                <RuleCheckRow key={c.rule_id} check={c} rule={ruleById[c.rule_id]} inConflict={conflict.has(c.rule_id)} />
              ))}
            </ul>
          </section>
        </div>
      )}

      {replay.done && (
        <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-surface p-4 md:hidden">
          <button className="btn-primary w-full py-3" onClick={() => onTab('receipt')}>
            {demo.receipt.verdict === 'RULES_INFEASIBLE' ? 'See the conflict →' : 'Open the receipt →'}
          </button>
        </div>
      )}
    </div>
  )
}

// Keyed by id so switching clients starts from a clean slate (tab, replay, receipt).
export default function ClientPage() {
  const { id } = useParams()
  return <ClientDetail key={id} id={id} />
}

function ClientDetail({ id }) {
  // ?tab= picks the view, ?receipt=printed|card the receipt look, ?all=1 skips the replay.
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') ?? 'run'
  const receiptVariant = params.get('receipt') ?? 'printed'
  const [client, setClient] = useState(null)
  const [demo, setDemo] = useState(null)
  const [demoError, setDemoError] = useState(null)
  const [error, setError] = useState(null)
  // Hidden until the API says live runs are on (the public demo turns them off).
  const [liveRuns, setLiveRuns] = useState(false)
  const steps = useMemo(() => (demo ? buildSteps(demo) : []), [demo])
  const replay = useReplay(steps, params.get('all') === '1')
  // The tab bar scrolls sideways on phones; a right-edge fade shows there's more until the end is reached.
  const tabsRef = useRef(null)
  const [tabFade, setTabFade] = useState(false)
  useEffect(() => {
    const el = tabsRef.current
    if (!el) return
    const update = () => setTabFade(el.scrollLeft + el.clientWidth < el.scrollWidth - 2)
    const resize = new ResizeObserver(update)
    resize.observe(el)
    el.addEventListener('scroll', update, { passive: true })
    return () => {
      resize.disconnect()
      el.removeEventListener('scroll', update)
    }
  }, [client, demo, liveRuns])

  const setTab = (t) => {
    const next = new URLSearchParams(params)
    if (t === 'run') next.delete('tab')
    else next.set('tab', t)
    setParams(next, { replace: true })
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    getClients()
      .then((all) => {
        const c = all.find((x) => x.client_id === id)
        if (!c) throw new Error(`Unknown client ${id}`)
        setClient(c)
      })
      .catch((e) => setError(e.message))
    getDemo(id).then(setDemo).catch((e) => setDemoError(e.message))
    getSettings()
      .then((s) => setLiveRuns(Boolean(s.live_runs)))
      .catch(() => setLiveRuns(false))
  }, [id])

  const page = 'mx-auto max-w-page px-6 pb-16 pt-8 md:pt-10 xl:px-0'
  if (error) return <div className={page}><ErrorNote>{error}</ErrorNote></div>
  if (!client) return <div className={page}><Spinner label="Loading client…" /></div>

  const presets = [
    { label: 'Committee final', weights: demo?.final_proposal?.weights },
    { label: 'First draft', weights: demo?.extras?.proposals?.[0] },
    { label: "Client's current", weights: Object.keys(client.current_weights).length ? client.current_weights : null },
  ]
  const tabs = TABS.filter((t) => (t.id !== 'live' || liveRuns) && (t.id !== 'receipt' || demo))
  const current = tabs.find((t) => t.id === tab) ?? tabs[0]
  const showRules = current.id === 'run' && demo?.receipt?.rules_feasible !== false

  return (
    <div className={page}>
      <nav className={`items-center gap-2 text-ui text-muted ${current.id === 'receipt' ? 'hidden md:flex' : 'flex'}`}>
        <Link to="/" className="hover:text-ink">Clients</Link>
        <span>/</span>
        <span className="num">{client.client_id}</span>
        <span>/</span>
        <span className="text-ink">{current.label}</span>
      </nav>

      <div className={`mt-5 flex-wrap items-start justify-between gap-8 ${['receipt', 'prices'].includes(current.id) ? 'hidden' : 'flex'}`}>
        <div className="max-w-lede">
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="font-display text-4xl font-semibold tracking-tight md:text-6xl">{displayName(client.name)}</h1>
            {isSynthetic(client.name) && <span className="font-display text-lg italic text-muted">synthetic client</span>}
          </div>
          <p className="mt-3 font-display text-lead text-prose">{client.story}</p>
        </div>
        {demo && current.id === 'run' && (
          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-8">
            <RoundTally steps={steps} visible={replay.visible} />
            {replay.done && (
              <>
                <div className="pl-1 sm:hidden"><Stamp verdict={demo.receipt.verdict} sub={stampSub(demo)} size="sm" /></div>
                <div className="hidden sm:block"><Stamp verdict={demo.receipt.verdict} sub={stampSub(demo)} /></div>
              </>
            )}
          </div>
        )}
      </div>

      {showRules && (
        <section className="mt-10 hidden md:block">
          <div className="label border-b border-ink pb-2.5">
            {pronoun(displayName(client.name), client.story)} {client.rules.length} rules, in {pronoun(displayName(client.name), client.story)} own words
          </div>
          <ul className="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-4">
            {client.rules.map((r) => (
              <li key={r.id} title={`${r.type} · priority ${r.priority}${r.hard ? ' · hard rule' : ''}`} className="flex items-baseline gap-2.5 border-b border-line py-2.5">
                <span className="num w-6 shrink-0 text-xs text-muted">{r.id}</span>
                <span className="font-display text-md italic text-prose">“{r.source.replace(/\.$/, '')}”</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div data-component="tab-bar" className={`relative mt-8 mb-10 ${current.id === 'receipt' ? 'hidden md:block' : ''}`}>
      <div ref={tabsRef} className="no-scrollbar flex gap-6 overflow-x-auto overflow-y-hidden border-b border-line">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px whitespace-nowrap border-b-2 py-2.5 text-sm ${
              current.id === t.id ? 'border-ink font-medium text-ink' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tabFade && <span aria-hidden="true" data-component="tab-fade" className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-bg to-transparent" />}
      </div>

      {/* Keep tabs mounted so the replay and the editor keep their state when switching. */}
      <div className={current.id === 'run' ? '' : 'hidden'}>
        <RunView client={client} demo={demo} demoError={demoError} steps={steps} replay={replay} onTab={setTab} />
      </div>
      {demo && (
        <div className={current.id === 'receipt' ? '' : 'hidden'}>
          <ReceiptCard
            variant={receiptVariant}
            receipt={demo.receipt}
            rules={client.rules}
            client={client}
            {...receiptChanges(client, demo)}
            onBack={() => setTab('run')}
            onEdit={() => setTab('try')}
          />
        </div>
      )}
      {liveRuns && (
        <div className={current.id === 'live' ? '' : 'hidden'}>
          <LiveRun
            client={client}
            receiptVariant={receiptVariant}
            onDisabled={() => {
              setLiveRuns(false)
              setTab('run')
            }}
          />
        </div>
      )}
      <div className={current.id === 'prices' ? '' : 'hidden'}>
        <PriceTags clientId={client.client_id} client={client} onBack={() => setTab('run')} />
      </div>
      <div className={current.id === 'try' ? '' : 'hidden'}>
        {(demo || demoError) && <TryReferee key={demo ? 'demo' : 'nodemo'} client={client} presets={presets} receiptVariant={receiptVariant} />}
      </div>
    </div>
  )
}
