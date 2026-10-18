// Live committee run: POST /run/{client} starts it, GET /run/{job} is polled for progress events.
// Shows which agent is working and the round progress, then the debate and receipt when done.
import { useEffect, useMemo, useRef, useState } from 'react'
import { getRun, startRun } from '../api.js'
import { AGENTS, VERDICTS } from '../format.js'
import { buildSteps } from '../steps.js'
import DebateTimeline from './DebateTimeline.jsx'
import ReceiptCard from './ReceiptCard.jsx'
import StartingWeights from './StartingWeights.jsx'
import StanceBadge from './StanceBadge.jsx'
import { ErrorNote, SectionTitle } from './ui.jsx'

const POLL_MS = 600
const AGENT_ORDER = ['macro', 'fundamentals', 'risk', 'chair', 'referee']
const TASKS = { memo: 'writing a memo', stance: 'answering the Referee', draft: 'drafting the portfolio', revise: 'revising the portfolio', check: 'checking every rule' }

/** Per-agent status from the events: idle, working (with task), or done. */
function agentStates(events) {
  const s = Object.fromEntries(AGENT_ORDER.map((a) => [a, { status: 'idle' }]))
  for (const e of events) {
    if (!e.agent || !s[e.agent]) continue
    s[e.agent] = e.type === 'working' ? { status: 'working', task: e.task, round: e.round } : { status: 'done', last: e }
  }
  return s
}

function describe(e) {
  const who = AGENTS[e.agent]?.label ?? e.agent
  switch (e.type) {
    case 'started': return `Committee convened${e.fakes ? ' (scripted analysts, real Referee)' : ''}`
    case 'memo': return e.ok ? `${who} memo received` : `${who} did not answer`
    case 'chair_draft': return e.round === 1 ? 'Chair drafted the first portfolio' : `Chair revised the portfolio (draft ${e.round})`
    case 'referee': return `Referee round ${e.round}: ${VERDICTS[e.verdict]?.label ?? e.verdict} · ${e.passed} of ${e.total} rules pass${e.failed.length ? ` (broken: ${e.failed.join(', ')})` : ''}`
    case 'stance': return e.ok ? `${who} responded` : `${who} did not respond`
    case 'done': return `Done: ${VERDICTS[e.verdict]?.label ?? e.verdict} after ${e.rounds} round${e.rounds > 1 ? 's' : ''}`
    case 'error': return `Run failed: ${e.text}`
    default: return null
  }
}

function AgentTile({ agent, state }) {
  const working = state.status === 'working'
  return (
    <div
      data-component="agent-tile"
      data-agent={agent}
      data-status={state.status}
      className={`rounded-card border p-3 transition ${working ? 'border-accent bg-accent/5' : 'border-line bg-surface'}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${working ? 'bg-accent animate-pulse' : state.status === 'done' ? 'bg-pass' : 'bg-line'}`} />
        <span className="text-sm font-medium">{AGENTS[agent].label}</span>
      </div>
      <div className="text-xs text-muted mt-1">
        {working ? TASKS[state.task] ?? 'working' : state.status === 'done' ? 'waiting' : 'not started'}
      </div>
    </div>
  )
}

export default function LiveRun({ client, receiptVariant, onDisabled }) {
  const [useFakes, setUseFakes] = useState(true)
  const [job, setJob] = useState(null) // {job_id, status, max_rounds, result, error}
  const [events, setEvents] = useState([])
  const [startError, setStartError] = useState(null)
  const timer = useRef(null)

  const start = async () => {
    setStartError(null)
    setEvents([])
    setJob(null)
    try {
      const { job_id } = await startRun(client.client_id, { fakes: useFakes, stepDelay: useFakes ? 0.8 : 0 })
      setJob({ job_id, status: 'running' })
    } catch (e) {
      // 503: live runs are off in this deployment, so fall back to the saved committee run.
      if (e.status === 503 && onDisabled) onDisabled()
      else setStartError(e.message)
    }
  }

  useEffect(() => {
    if (!job || job.status !== 'running') return
    timer.current = setTimeout(async () => {
      try {
        const body = await getRun(job.job_id, events.length)
        setEvents((prev) => [...prev, ...body.events])
        setJob(body)
      } catch (e) {
        setJob((j) => ({ ...j, status: 'error', error: e.message }))
      }
    }, POLL_MS)
    return () => clearTimeout(timer.current)
  }, [job, events.length])

  const states = agentStates(events)
  const maxProposals = (job?.max_rounds ?? 3) + 1
  const round = Math.max(0, ...events.filter((e) => e.round != null).map((e) => e.round))
  const lastReferee = [...events].reverse().find((e) => e.type === 'referee')
  const running = job?.status === 'running'
  const progress = job?.status === 'done' ? 100 : Math.min(95, Math.round((round / maxProposals) * 100))
  const result = job?.status === 'done' ? job.result : null
  const resultWithDrafts = useMemo(
    () => result && { ...result, extras: { proposals: events.filter((e) => e.type === 'chair_draft').map((e) => e.weights) } },
    [result, events],
  )
  const steps = useMemo(() => (resultWithDrafts ? buildSteps(resultWithDrafts) : []), [resultWithDrafts])

  return (
    <div data-component="live-run" data-status={job?.status ?? 'idle'} className="grid gap-6">
      <div className="card p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm">
          {!job && 'Run the committee live: three analysts, the Chair and the Referee, round by round.'}
          {running && (
            <span className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              Committee in session · {round === 0 ? 'analyst memos' : `round ${round} of up to ${maxProposals}`}
            </span>
          )}
          {job?.status === 'done' && `Finished in ${result.rounds} round${result.rounds > 1 ? 's' : ''}`}
          {job?.status === 'error' && 'The live run failed.'}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={useFakes} disabled={running} onChange={(e) => setUseFakes(e.target.checked)} />
            Scripted analysts (no API key)
          </label>
          <button className="btn-primary" disabled={running} onClick={start}>
            {running ? 'Running…' : job ? 'Run again' : 'Start live run'}
          </button>
        </div>
      </div>

      {startError && <ErrorNote>{startError}</ErrorNote>}
      {job?.error && <ErrorNote>{job.error}</ErrorNote>}

      {job && (
        <div data-component="run-progress" className="card p-4 grid gap-4">
          <div>
            <div className="flex justify-between text-xs text-muted">
              <span className="label">Round progress</span>
              <span className="num">{round} / {maxProposals}</span>
            </div>
            <div className="mt-2 h-1.5 rounded-chip bg-sunken overflow-hidden">
              <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {AGENT_ORDER.map((a) => <AgentTile key={a} agent={a} state={states[a]} />)}
          </div>
          {lastReferee && (
            <div className="text-sm">
              <span className="label mr-2">Latest Referee result</span>
              {describe(lastReferee)}
            </div>
          )}
          <ol data-field="run-events" className="grid gap-1 text-xs text-muted max-h-64 overflow-auto">
            {events.filter((e) => e.type !== 'working').map((e) => (
              <li key={e.seq} data-event={e.type} className="flex gap-3 items-center">
                <span className="num w-10 shrink-0 text-right">{e.t.toFixed(1)}s</span>
                <span>{describe(e)}</span>
                {e.type === 'stance' && e.stance && <StanceBadge stance={e.stance} agent={e.agent} text="" />}
              </li>
            ))}
          </ol>
        </div>
      )}

      {result && (
        <div className="grid gap-8 animate-reveal">
          <DebateTimeline steps={steps} visible={steps.length} />
          <div>
            <SectionTitle eyebrow="Holdings" title="Starting → final" />
            <StartingWeights start={client.current_weights} final={result.final_proposal.weights} />
          </div>
          <ReceiptCard
            variant={receiptVariant}
            receipt={result.receipt}
            client={client}
            rules={client.rules}
            before={client.current_weights}
            after={result.final_proposal.weights}
            beforeLabel="Starting"
            afterLabel="Final"
          />
        </div>
      )}
    </div>
  )
}
