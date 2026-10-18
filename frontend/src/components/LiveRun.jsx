// Live committee run: POST /run/{client} starts it, GET /run/{job} is polled for progress events.
// Shows which agent is working and the round progress, then the debate and receipt when done.
import { useEffect, useMemo, useRef, useState } from 'react'
import { getRun, getRunCapabilities, startRun } from '../api.js'
import { AGENTS, VERDICTS } from '../format.js'
import { buildSteps } from '../steps.js'
import DebateTimeline from './DebateTimeline.jsx'
import ReceiptCard from './ReceiptCard.jsx'
import StartingWeights from './StartingWeights.jsx'
import StanceBadge from './StanceBadge.jsx'
import { ErrorNote } from './ui.jsx'
import ReadMore from './ReadMore.jsx'

const POLL_MS = 600

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

const SHAPES = {
  concede: 'h-2 w-2 rounded-full bg-concede',
  defend: 'h-2 w-2 bg-defend',
  modify: 'h-2 w-2 rotate-45 bg-modify',
}

/** One agent's line in "Who is working" for the current round: working / done / waiting, with real seconds. */
function workingRows(events, round, now) {
  const order = ['referee', 'macro', 'fundamentals', 'risk', 'chair']
  const inRound = events.filter((e) => e.round === round || (round <= 1 && e.round === 0))
  return order.map((agent) => {
    const mine = inRound.filter((e) => e.agent === agent)
    const start = [...mine].reverse().find((e) => e.type === 'working')
    const last = mine[mine.length - 1]
    if (!last) return { agent, status: 'waiting' }
    if (last.type === 'working') return { agent, status: 'working', task: last.task, secs: now - last.t }
    return { agent, status: 'done', event: last, secs: start ? last.t - start.t : null }
  })
}

function doneText(e) {
  if (e.type === 'referee') return e.failed.length ? `Checked the draft · ${e.failed.length} broken` : 'Checked the draft · all pass'
  if (e.type === 'stance') return e.ok ? `Answered · ${e.stance[0].toUpperCase()}${e.stance.slice(1)}` : 'Did not answer'
  if (e.type === 'memo') return e.ok ? 'Memo received' : 'Did not answer'
  if (e.type === 'chair_draft') return e.round === 1 ? 'Drafted the portfolio' : 'Revised the portfolio'
  return 'Done'
}

const WORKING_TEXT = { memo: 'Writing a memo…', stance: "Reading the Referee's findings…", draft: 'Drafting the portfolio…', revise: 'Revising the draft…', check: 'Checking every rule…' }

function WhoIsWorking({ rows }) {
  return (
    <div data-component="who-is-working" className="border border-line bg-surface">
      <div className="flex justify-between border-b border-line px-4 py-3">
        <span className="label">Who is working</span>
        <span className="text-xs text-muted">live</span>
      </div>
      <ul>
        {rows.map((r) => (
          <li
            key={r.agent}
            data-component="agent-tile"
            data-agent={r.agent}
            data-status={r.status}
            className={`grid grid-cols-who items-center gap-3 border-b border-line px-4 py-3 text-ui last:border-0 ${r.status === 'working' ? 'bg-warn-tint' : ''}`}
          >
            <span className="flex w-3 justify-center">
              {r.status === 'working' && <span className="h-2.5 w-2.5 animate-pulse rounded-full border-2 border-ink" />}
              {r.status === 'waiting' && <span className="h-2.5 w-2.5 rounded-full border border-dashed border-muted" />}
              {r.status === 'done' && (
                <span className={r.event.type === 'stance' && r.event.ok ? SHAPES[r.event.stance] : 'h-2 w-2 rounded-full bg-ink'} />
              )}
            </span>
            <span className={`font-semibold ${r.status === 'waiting' ? 'font-normal text-muted' : ''}`}>{AGENTS[r.agent]?.label ?? r.agent}</span>
            <span className="truncate text-muted">
              {r.status === 'working' ? WORKING_TEXT[r.task] ?? 'Working…' : r.status === 'done' ? doneText(r.event) : r.agent === 'chair' ? 'Revises once all three answer' : 'Waiting'}
            </span>
            <span className="num text-right text-xs text-muted">{r.secs != null ? `${r.secs.toFixed(1)} s` : '–'}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** One round as it happens: the Chair's draft, what the Referee found, the analysts' answers. */
function LiveRound({ round, events, rules, current, rows }) {
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const mine = events.filter((e) => e.round === round)
  const draft = mine.find((e) => e.type === 'chair_draft')
  const ref = mine.find((e) => e.type === 'referee')
  const stances = mine.filter((e) => e.type === 'stance')
  const rail = ref ? (ref.failed.length ? 'border-fail' : 'border-pass') : 'border-ink'
  return (
    <section data-round={round} className={`border-t-3 pt-5 ${rail}`}>
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-h3 font-semibold">Round {round}</h3>
        {ref && (
          <span className={`num text-xs font-semibold ${ref.failed.length ? 'text-fail' : 'text-pass'}`}>
            {ref.failed.length ? `${ref.failed.length} broken` : 'all pass'}
          </span>
        )}
      </div>
      {draft && (
        <div className="mt-5">
          <div className="label">{round === 1 ? "Chair's first draft" : "Chair's revision"}</div>
          <ReadMore text={draft.text} limit={160} label="Read full draft" className="mt-1 font-display text-lg" />
        </div>
      )}
      {ref && (
        <div className="mt-5">
          <div className="label">Referee found</div>
          {ref.failed.length === 0 ? (
            <p className="mt-1 text-ui text-pass">All {ref.total} rules hold.</p>
          ) : (
            <ul className="mt-1">
              {ref.failed.map((id) => (
                <li key={id} className="flex items-baseline gap-3 border-b border-line py-2">
                  <span className="h-2 w-2 shrink-0 self-center bg-fail" />
                  <span className="num text-xs text-fail">{id}</span>
                  <span className="font-display text-md italic">“{(ruleById[id]?.source ?? id).replace(/\.$/, '')}”</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {stances.length > 0 && (
        <div className="mt-5 grid gap-3">
          <div className="label">Committee answers</div>
          {stances.map((e) => (
            <StanceBadge key={e.seq} stance={e.ok ? e.stance : null} agent={e.agent} text={e.text ?? ''} />
          ))}
        </div>
      )}
      {current && (
        <div className="mt-5">
          <WhoIsWorking rows={rows} />
        </div>
      )}
    </section>
  )
}

function FutureRound({ round }) {
  return (
    <section data-round={round} className="border-t-3 border-dashed border-line pt-5 text-muted">
      <h3 className="font-display text-h3 font-semibold">Round {round}</h3>
      <p className="mt-4 font-display text-md italic">
        Only if round {round - 1} still breaks a rule. After the last round the Referee repairs the draft itself.
      </p>
    </section>
  )
}

// "Real committee · asi1-mini · fresh" / "Scripted analysts · real Referee": what this run actually uses.
const runLabel = (job) => {
  if (!job) return null
  if (job.fakes) return 'Scripted analysts · real Referee'
  const model = (job.model ?? '').split('/').pop() || 'live model'
  return `Real committee · ${model} · ${job.run_mode ?? 'cached'}`
}

const clock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

export default function LiveRun({ client, receiptVariant, onDisabled }) {
  // Scripted only when no LLM is available: the real committee is the default whenever the API reports a model.
  const [useFakes, setUseFakes] = useState(true)
  const [fresh, setFresh] = useState(false)
  const [job, setJob] = useState(null) // {job_id, status, max_rounds, result, error}
  const [events, setEvents] = useState([])
  const [startError, setStartError] = useState(null)
  const timer = useRef(null)
  const [now, setNow] = useState(0)

  useEffect(() => {
    getRunCapabilities()
      .then((c) => setUseFakes(!(c.live_runs && c.model)))
      .catch(() => setUseFakes(true))
  }, [])

  const start = async () => {
    setStartError(null)
    setEvents([])
    setJob(null)
    try {
      const { job_id, fakes, model, run_mode } = await startRun(client.client_id, { fakes: useFakes, fresh: fresh && !useFakes, stepDelay: useFakes ? 0.8 : 0 })
      setJob({ job_id, status: 'running', fakes, model, run_mode })
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

  useEffect(() => {
    if (job?.status !== 'running') return
    const startedAt = Date.now() - (events[events.length - 1]?.t ?? 0) * 1000
    const id = setInterval(() => setNow((Date.now() - startedAt) / 1000), 200)
    return () => clearInterval(id)
    // re-anchor the clock to the server's timestamps whenever new events arrive
  }, [job?.status, events])

  const maxProposals = (job?.max_rounds ?? 3) + 1
  const round = Math.max(0, ...events.filter((e) => e.round != null).map((e) => e.round))
  const running = job?.status === 'running'
  const current = Math.max(1, round)
  const elapsed = job?.status === 'running' ? Math.max(now, events[events.length - 1]?.t ?? 0) : events[events.length - 1]?.t ?? 0
  const rows = workingRows(events, current, elapsed)
  const lastRoundDone = events.some((e) => e.type === 'referee' && e.round === current && e.failed.length === 0)
  const shownRounds = Array.from({ length: Math.min(current + (lastRoundDone ? 0 : 1), maxProposals) }, (_, i) => i + 1).slice(-3)
  const result = job?.status === 'done' ? job.result : null
  const resultWithDrafts = useMemo(
    () => result && { ...result, extras: { proposals: events.filter((e) => e.type === 'chair_draft').map((e) => e.weights) } },
    [result, events],
  )
  const steps = useMemo(() => (resultWithDrafts ? buildSteps(resultWithDrafts) : []), [resultWithDrafts])

  return (
    <div data-component="live-run" data-status={job?.status ?? 'idle'} className="grid gap-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3 border-y border-line py-3">
        <div className="text-ui text-muted">
          {!job && 'Run the committee live: three analysts, the Chair and the Referee, round by round.'}
          {running && (
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-warn" />
              Committee in session · {round === 0 ? 'analyst memos' : `round ${round} of up to ${maxProposals}`}
            </span>
          )}
          {job?.status === 'done' && `Finished in ${result.rounds} round${result.rounds > 1 ? 's' : ''}`}
          {job?.status === 'error' && 'The live run failed.'}
          {job && <div data-component="run-label" className="mt-1 text-xs text-faint">{runLabel(job)}</div>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 whitespace-nowrap text-xs text-muted">
            <input type="checkbox" checked={useFakes} disabled={running} onChange={(e) => setUseFakes(e.target.checked)} />
            Scripted analysts (no API key)
          </label>
          <label
            data-component="fresh-run-toggle"
            title="Every LLM answers anew instead of replaying cached answers. Needs the real analysts, not the scripted ones."
            className={`flex items-center gap-2 whitespace-nowrap text-xs ${useFakes ? 'text-faint' : 'text-muted'}`}
          >
            <input type="checkbox" checked={fresh && !useFakes} disabled={running || useFakes} onChange={(e) => setFresh(e.target.checked)} />
            Fresh run (no cache)
          </label>
          <button className="btn-primary" disabled={running} onClick={start}>
            {running ? 'Running…' : job ? 'Run again' : 'Start live run'}
          </button>
        </div>
      </div>

      {startError && <ErrorNote>{startError}</ErrorNote>}
      {job?.error && <ErrorNote>{job.error}</ErrorNote>}

      {job && (
        <div data-component="run-progress" className="grid gap-8">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <p className="max-w-lede font-display text-lg text-prose">
              {running
                ? `The committee is working. Each round, the Referee checks the draft against ${client.rules.length} rules and the analysts answer.`
                : job.status === 'done'
                  ? `Finished: ${VERDICTS[result.receipt.verdict]?.label ?? result.receipt.verdict} after ${result.rounds} round${result.rounds > 1 ? 's' : ''}.`
                  : 'The live run stopped.'}
            </p>
            <div className="text-right">
              <div className="flex items-baseline justify-end gap-3">
                <span className="font-display text-3xl font-semibold">{round === 0 ? 'Memos' : `Round ${round}`}</span>
                <span className="text-sm text-muted">of up to <span className="num">{maxProposals}</span></span>
              </div>
              <div className="mt-2 flex justify-end gap-1">
                {Array.from({ length: maxProposals }, (_, i) => (
                  <span key={i} className={`h-1 w-16 ${i + 1 < round || (i + 1 === round && !running) ? 'bg-ink' : i + 1 === round ? 'bg-ink/70' : 'bg-line'}`} />
                ))}
              </div>
              <div className="mt-2 text-ui text-muted">
                <span className="num text-ink">{clock(elapsed)}</span> elapsed
              </div>
            </div>
          </div>
          {!result && (
            <div className="grid gap-10 md:grid-cols-3 md:gap-12">
              {shownRounds.map((r) =>
                r <= current ? (
                  <LiveRound key={r} round={r} events={events} rules={client.rules} current={running && r === current} rows={rows} />
                ) : (
                  <FutureRound key={r} round={r} />
                ),
              )}
            </div>
          )}
          <details className="text-xs text-muted">
            <summary className="cursor-pointer">Event log · {events.filter((e) => e.type !== 'working').length} events</summary>
            <ol data-field="run-events" className="mt-2 grid max-h-64 gap-1 overflow-auto">
              {events.filter((e) => e.type !== 'working').map((e) => (
                <li key={e.seq} data-event={e.type} className="flex items-center gap-3">
                  <span className="num w-10 shrink-0 text-right">{e.t.toFixed(1)}s</span>
                  <span>{describe(e)}</span>
                </li>
              ))}
            </ol>
          </details>
        </div>
      )}

      {result && (
        <div className="grid gap-8 animate-reveal">
          <DebateTimeline steps={steps} visible={steps.length} rules={client.rules} />
          <div>
            <h3 className="mb-4 font-display text-h3 font-semibold">From the starting book to the final one</h3>
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
