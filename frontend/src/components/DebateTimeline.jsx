// The committee's debate as round columns (stacked with a colored left rail on phones), revealed step by step.
// Each round: the Chair's draft → what the Referee found → the committee's answers. All text is the saved run's.
import { AGENTS, sortedWeights } from '../format.js'
import StanceBadge from './StanceBadge.jsx'
import ReadMore from './ReadMore.jsx'

const ANALYSTS = ['macro', 'fundamentals', 'risk']
const NO_ANSWER = "Didn't reply in time. The Chair went ahead with the other answers; the Referee's check is unaffected."

const chairLabel = (round, last, done) =>
  round === 1 ? "Chair's first draft" : round === last && done ? "Chair's final" : "Chair's revision"

function Label({ children }) {
  return <div className="label mb-2.5">{children}</div>
}

function Findings({ receipt, rules, text }) {
  if (!receipt) return <p className="font-display text-base">{text}</p>
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const failed = receipt.checks.filter((c) => !c.passed)
  if (!receipt.rules_feasible) {
    return <p className="font-display text-base text-warn-text">{receipt.conflict_explain || receipt.summary}</p>
  }
  if (failed.length === 0) {
    return (
      <p className="font-display text-base text-pass">
        All {receipt.checks.length} rules hold. No repair needed.
      </p>
    )
  }
  return (
    <ul className="border-t border-line">
      {failed.map((c) => (
        <li key={c.rule_id} title={c.explain} className="flex items-baseline gap-2.5 border-b border-line py-1.5">
          <span className="h-1.5 w-1.5 shrink-0 self-center bg-fail" aria-label="broken" />
          <span className="num w-6 shrink-0 text-xs text-fail">{c.rule_id}</span>
          <span className="font-display text-md italic">“{(ruleById[c.rule_id]?.source ?? c.explain).replace(/\.$/, '')}”</span>
        </li>
      ))}
    </ul>
  )
}

function Round({ round, steps, rules, last, done, final }) {
  const proposal = steps.find((s) => s.kind === 'proposal')
  const receiptStep = steps.find((s) => s.kind === 'receipt')
  const stances = steps.filter((s) => s.kind === 'stance')
  const notes = steps.filter((s) => s.kind === 'note' || (s.kind !== 'proposal' && s.kind !== 'receipt' && s.kind !== 'stance'))
  const receipt = receiptStep?.receipt
  const broken = receipt ? receipt.checks.filter((c) => !c.passed).length : null
  const clean = receipt && broken === 0 && receipt.rules_feasible
  const rail = !receipt ? 'border-line' : clean ? 'border-pass' : receipt.rules_feasible ? 'border-fail' : 'border-warn'
  const answered = new Set(stances.map((s) => s.agent))
  // Only flag a missing analyst once the round's answers are in (the next round started or the run is over).
  const missing = stances.length > 0 && (done || round < last) ? ANALYSTS.filter((a) => !answered.has(a)) : []
  return (
    <section
      data-round={round}
      className={`animate-reveal border-l-3 pl-4 md:border-l-0 md:border-t-3 md:pl-0 md:pt-5 ${rail}`}
    >
      <div className="mb-5 flex items-baseline justify-between">
        <h3 className="font-display text-3xl font-semibold">Round {round}</h3>
        {receipt && (
          <span className={`num text-ui font-medium ${clean ? 'text-pass' : receipt.rules_feasible ? 'text-fail' : 'text-warn-text'}`}>
            {receipt.rules_feasible ? `${broken} broken` : 'rules conflict'}
          </span>
        )}
      </div>
      <div className="grid gap-6">
        {proposal && (
          <div className="hidden md:block">
            <Label>{chairLabel(round, last, done)}</Label>
            <ReadMore text={proposal.text} limit={160} label="Read full draft" className="font-display text-base" />
            {proposal.weights && (
              <p className="num mt-2 text-xs text-muted">
                {sortedWeights(proposal.weights).map(([t, w]) => `${t} ${(w * 100).toFixed(0)}`).join(' · ')}
              </p>
            )}
          </div>
        )}
        {receiptStep && (
          <div>
            <div className="hidden md:block"><Label>Referee found</Label></div>
            <Findings receipt={receipt} rules={rules} text={receiptStep.text} />
          </div>
        )}
        {(stances.length > 0 || missing.length > 0) && (
          <div>
            <div className="hidden md:block"><Label>Committee answers</Label></div>
            <div className="grid gap-4">
              {stances.map((s) => (
                <StanceBadge key={s.key} stance={s.stance} agent={s.agent} text={s.text} />
              ))}
              {missing.map((a) => (
                <div key={a} className="border-t border-dashed border-perforation pt-3">
                  <StanceBadge agent={a} text={NO_ANSWER} />
                </div>
              ))}
            </div>
          </div>
        )}
        {notes.map((n) => (
          <p key={n.key} className="font-display text-base italic text-muted">
            {AGENTS[n.agent]?.label ?? n.agent}: {n.text}
          </p>
        ))}
        {final}
      </div>
    </section>
  )
}

/** steps from buildSteps(); visible = how many are revealed; final = extra content under the last round. */
export default function DebateTimeline({ steps, visible, rules = [], final }) {
  const shown = steps.slice(0, visible)
  const done = visible >= steps.length
  const memos = shown.filter((s) => s.round === 0)
  const rounds = [...new Set(shown.filter((s) => s.round > 0).map((s) => s.round))]
  const last = Math.max(0, ...steps.map((s) => s.round))
  return (
    <div className="grid gap-10" data-component="debate-timeline">
      {memos.length > 0 && (
        <details className="group border-b border-line pb-4" open={rounds.length === 0}>
          <summary className="label cursor-pointer list-none">
            Analyst memos <span className="font-normal normal-case tracking-normal">· {memos.length} received before round 1</span>
          </summary>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            {memos.map((m) => (
              <div key={m.key} className="animate-reveal">
                <div className="mb-1 text-xs font-semibold">{AGENTS[m.agent]?.label ?? m.agent}</div>
                <ReadMore text={m.text} className="font-display text-md text-prose" />
              </div>
            ))}
          </div>
        </details>
      )}
      {rounds.length > 0 && (
        <div className="grid gap-10 md:grid-cols-3 md:gap-12">
          {rounds.map((r) => (
            <Round
              key={r}
              round={r}
              steps={shown.filter((s) => s.round === r)}
              rules={rules}
              last={last}
              done={done}
              final={done && r === last ? final : null}
            />
          ))}
        </div>
      )}
    </div>
  )
}

