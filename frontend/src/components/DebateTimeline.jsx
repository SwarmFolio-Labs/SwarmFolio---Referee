// The committee's debate, grouped by round and revealed one step at a time.
import { AGENTS } from '../format.js'
import StanceBadge from './StanceBadge.jsx'
import { AgentAvatar, Badge, PassMark, VerdictBadge, WeightPills } from './ui.jsx'

const ROUND_TITLES = (round, last) => {
  if (round === 0) return 'Analyst memos'
  if (round === 1) return "Round 1 · Chair's first draft"
  return `Round ${round} · Revision${round === last ? ' (final)' : ''}`
}

function ReceiptStep({ receipt, text }) {
  if (!receipt) return <p className="text-sm">{text}</p>
  const failed = receipt.checks.filter((c) => !c.passed)
  return (
    <div className="grid gap-2">
      <div className="flex items-center gap-2">
        <VerdictBadge verdict={receipt.verdict} />
        <span className="num text-2xs text-muted">#{receipt.receipt_id}</span>
      </div>
      <p className="text-sm">{receipt.summary}</p>
      {failed.length > 0 && (
        <ul className="grid gap-1.5">
          {failed.map((c) => (
            <li key={c.rule_id} className="flex gap-2 text-sm">
              <PassMark passed={false} />
              <span className="text-fail">{c.explain}</span>
            </li>
          ))}
        </ul>
      )}
      {!receipt.rules_feasible && receipt.conflict_explain && (
        <p className="text-sm text-warn">{receipt.conflict_explain}</p>
      )}
    </div>
  )
}

function Step({ step }) {
  const agent = AGENTS[step.agent]?.label ?? step.agent
  const kindLabel = { memo: 'memo', proposal: 'proposal', receipt: 'findings', stance: 'response', note: 'note' }[step.kind]
  return (
    <li className="flex gap-3 animate-reveal">
      <AgentAvatar agent={step.agent} />
      <div className="flex-1 min-w-0 card px-4 py-3">
        <div className="flex flex-wrap items-center gap-2 mb-1.5">
          <span className="text-sm font-semibold">{agent}</span>
          <span className="label">{kindLabel}</span>
          {step.kind === 'stance' && step.stance && <StanceBadge stance={step.stance} />}
          {step.kind === 'note' && <Badge tone="warn">advisor needed</Badge>}
        </div>
        {step.kind === 'receipt' ? (
          <ReceiptStep receipt={step.receipt} text={step.text} />
        ) : (
          <>
            <p className="text-sm">{step.text}</p>
            {step.weights && (
              <div className="mt-2">
                <WeightPills weights={step.weights} />
              </div>
            )}
          </>
        )}
      </div>
    </li>
  )
}

export default function DebateTimeline({ steps, visible }) {
  const shown = steps.slice(0, visible)
  const lastRound = Math.max(...steps.map((s) => s.round))
  const rounds = [...new Set(shown.map((s) => s.round))]
  return (
    <div className="grid gap-6" data-component="debate-timeline">
      {rounds.map((round) => (
        <section key={round}>
          <div className="flex items-center gap-3 mb-3">
            <span className="num text-xs rounded bg-ink text-bg px-1.5 py-0.5">R{round}</span>
            <h3 className="text-sm font-semibold">{ROUND_TITLES(round, lastRound)}</h3>
            <div className="h-px flex-1 bg-line" />
          </div>
          <ol className="grid gap-3">
            {shown
              .filter((s) => s.round === round)
              .map((s) => (
                <Step key={s.key} step={s} />
              ))}
          </ol>
        </section>
      ))}
    </div>
  )
}
