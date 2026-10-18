// One client: the committee run (replayed step by step), the receipt, rule prices, and the live Referee.
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getClients, getDemo, getSettings } from '../api.js'
import DebateTimeline from '../components/DebateTimeline.jsx'
import LiveRun from '../components/LiveRun.jsx'
import PriceTags from '../components/PriceTags.jsx'
import ReceiptCard from '../components/ReceiptCard.jsx'
import RuleChip from '../components/RuleChip.jsx'
import StartingWeights from '../components/StartingWeights.jsx'
import TryReferee from '../components/TryReferee.jsx'
import { ErrorNote, SectionTitle, Spinner } from '../components/ui.jsx'
import { displayName } from '../format.js'
import { buildSteps } from '../steps.js'

const STEP_MS = 900
const TABS = [
  { id: 'run', label: 'Committee run' },
  { id: 'live', label: 'Live run' },
  { id: 'prices', label: 'What each rule costs' },
  { id: 'try', label: 'Try the Referee' },
]

function RunView({ client, demo, demoError, receiptVariant }) {
  const steps = useMemo(() => (demo ? buildSteps(demo) : []), [demo])
  const [visible, setVisible] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  const done = steps.length > 0 && visible >= steps.length

  useEffect(() => {
    if (!playing) return
    if (visible >= steps.length) {
      setPlaying(false)
      return
    }
    timer.current = setTimeout(() => setVisible((v) => v + 1), visible === 0 ? 300 : STEP_MS)
    return () => clearTimeout(timer.current)
  }, [playing, visible, steps.length])

  if (demoError) {
    return (
      <div className="card p-6 text-sm">
        <div className="font-semibold mb-1">No saved committee run for this client yet.</div>
        <p className="text-muted">
          Save one with <code className="num bg-sunken px-1 rounded">python data/demo_runs/save_demo_run.py {client.client_id}</code>{' '}
          (needs ASI1_API_KEY). The rule prices and the live Referee work without it.
        </p>
      </div>
    )
  }
  if (!demo) return <Spinner label="Loading the saved committee run…" />

  const firstDraft = demo.extras?.proposals?.[0]
  const finalHeadline =
    demo.receipt.verdict === 'PASS' && demo.self_corrected
      ? `Self-corrected in ${demo.rounds} rounds`
      : demo.receipt.verdict === 'PASS'
        ? 'Every rule passes'
        : undefined

  return (
    <div className="grid gap-8">
      <div className="card p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm">
          {visible === 0 && !playing && 'Replay the committee: memos → proposal → Referee findings → analyst responses.'}
          {playing && (
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              Committee in session · step {visible} of {steps.length}
            </span>
          )}
          {!playing && visible > 0 && !done && `Paused at step ${visible} of ${steps.length}`}
          {done && `${demo.rounds} round${demo.rounds > 1 ? 's' : ''} · ${steps.length} steps`}
          {demo.extras?.source === 'dev-fakes' && (
            <span className="ml-2 text-2xs text-muted">(development run: scripted analysts, real Referee)</span>
          )}
        </div>
        <div className="flex gap-2">
          {!done && (
            <button
              className="btn-primary"
              onClick={() => setPlaying((p) => !p)}
            >
              {playing ? 'Pause' : visible === 0 ? 'Convene the committee' : 'Resume'}
            </button>
          )}
          {!done && (
            <button className="btn-ghost" onClick={() => { setPlaying(false); setVisible(steps.length) }}>
              Show all
            </button>
          )}
          {done && (
            <button className="btn-ghost" onClick={() => { setVisible(0); setPlaying(true) }}>
              Replay
            </button>
          )}
        </div>
      </div>

      {visible > 0 && <DebateTimeline steps={steps} visible={visible} />}

      {done && (
        <div className="animate-reveal">
          <SectionTitle eyebrow="Final" title="The receipt">
            {demo.receipt.verdict === 'RULES_INFEASIBLE'
              ? "No debate can fix rules that contradict each other. The Referee proves which rules clash and the cheapest way to loosen them."
              : 'What the Referee certified for the committee\'s final portfolio.'}
          </SectionTitle>
          {Object.keys(client.current_weights).length > 0 && (
            <div className="mb-6">
              <div className="label mb-2">Starting → final holdings</div>
              <StartingWeights start={client.current_weights} final={demo.final_proposal.weights} />
            </div>
          )}
          {demo.notes.length > 0 && (
            <ul className="mb-3 text-sm text-muted">{demo.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
          )}
          <ReceiptCard
            variant={receiptVariant}
            receipt={demo.receipt}
            rules={client.rules}
            headline={finalHeadline}
            before={firstDraft}
            after={demo.final_proposal.weights}
            beforeLabel="First draft"
            afterLabel="Final"
          />
        </div>
      )}
    </div>
  )
}

// Keyed by id so switching clients starts from a clean slate (tab, replay, receipt).
export default function ClientPage() {
  const { id } = useParams()
  // ?receipt=printed previews the printed-receipt variant (see index.css).
  const [params] = useSearchParams()
  return <ClientDetail key={id} id={id} receiptVariant={params.get('receipt') ?? 'card'} />
}

function ClientDetail({ id, receiptVariant }) {
  const [client, setClient] = useState(null)
  const [demo, setDemo] = useState(null)
  const [demoError, setDemoError] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('run')
  // Hidden until the API says live runs are on (the public demo turns them off).
  const [liveRuns, setLiveRuns] = useState(false)

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

  if (error) return <ErrorNote>{error}</ErrorNote>
  if (!client) return <Spinner label="Loading client…" />

  const presets = [
    { label: 'Committee final', weights: demo?.final_proposal?.weights },
    { label: 'First draft', weights: demo?.extras?.proposals?.[0] },
    { label: "Client's current", weights: Object.keys(client.current_weights).length ? client.current_weights : null },
  ]

  return (
    <div className="grid gap-8">
      <div>
        <Link to="/" className="text-sm text-muted hover:text-ink">
          ← All clients
        </Link>
        <div className="mt-3 flex flex-wrap items-baseline gap-3">
          <h1 className="font-display text-3xl font-bold tracking-tight">{displayName(client.name)}</h1>
          <span className="num text-sm text-muted">{client.client_id}</span>
        </div>
        <p className="mt-2 text-muted max-w-prose">{client.story}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {client.rules.map((r) => (
            <RuleChip key={r.id} rule={r} />
          ))}
        </div>
      </div>

      <div className="border-b border-line flex gap-1">
        {TABS.filter((t) => t.id !== 'live' || liveRuns).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-sm -mb-px border-b-2 transition ${
              tab === t.id ? 'border-ink text-ink font-medium' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Keep tabs mounted so the replay and the editor keep their state when switching. */}
      <div className={tab === 'run' ? '' : 'hidden'}>
        <RunView client={client} demo={demo} demoError={demoError} receiptVariant={receiptVariant} />
      </div>
      {liveRuns && (
        <div className={tab === 'live' ? '' : 'hidden'}>
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
      <div className={tab === 'prices' ? '' : 'hidden'}>
        <PriceTags clientId={client.client_id} />
      </div>
      <div className={tab === 'try' ? '' : 'hidden'}>
        {(demo || demoError) && <TryReferee key={demo ? 'demo' : 'nodemo'} client={client} presets={presets} receiptVariant={receiptVariant} />}
      </div>
    </div>
  )
}
