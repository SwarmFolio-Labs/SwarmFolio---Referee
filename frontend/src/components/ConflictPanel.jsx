// Screen C: the client's rules can't all hold. Which rules clash (in the client's words), an overflow bar and the
// arithmetic that proves it, and the cheapest way to loosen them. Everything comes from the receipt.
// layout="page" is the full two-column screen; layout="receipt" is the stacked version inside a receipt.
import { useState } from 'react'
import { fmtLimit, numberWord, pct, pronoun, ruleSubject, splitConflict } from '../format.js'

const FLOORS = new Set(['min_weight', 'sector_min', 'buy_in'])

/** "30% + 10% > 35%" as bars: the floors stacked left to right against the cap, the overflow in brick. */
function OverflowBar({ conflictChecks, ruleById }) {
  const floors = conflictChecks.filter((c) => FLOORS.has(c.type)).sort((a, b) => b.limit - a.limit)
  const caps = conflictChecks.filter((c) => c.type === 'sector_max' || c.type === 'max_weight')
  if (floors.length < 1 || caps.length !== 1) return null
  const cap = caps[0]
  const total = floors.reduce((s, c) => s + c.limit, 0)
  if (total <= cap.limit) return null
  const scale = Math.ceil((total * 100 + 5) / 10) * 10 // axis 0 – N%, a little past the total
  const w = (x) => ({ width: `${((x * 100) / scale) * 100}%` })
  const last = floors[floors.length - 1]
  const before = total - last.limit
  const room = Math.max(cap.limit - before, 0)
  const over = total - cap.limit
  const subject = ruleSubject(ruleById[cap.rule_id])
  return (
    <div data-field="conflict-bar" className="grid gap-2">
      <div className="label">{subject ? `${subject} share of the portfolio` : 'Combined share of the portfolio'}</div>
      <div className="relative">
        <div className="flex text-xs">
          {floors.map((c, i) => (
            <span key={c.rule_id} className="num shrink-0" style={w(c.limit)}>
              {i === floors.length - 1 ? '' : `${ruleSubject(ruleById[c.rule_id]) ?? c.rule_id} ${pct(c.limit)}`}
            </span>
          ))}
        </div>
        <div className="num absolute top-0 flex gap-1 text-xs" style={{ left: `${((before * 100) / scale) * 100}%` }}>
          <span>{ruleSubject(ruleById[last.rule_id]) ?? last.rule_id} {pct(last.limit)}</span>
          <span className="font-semibold text-fail">cap {pct(cap.limit)}</span>
        </div>
      </div>
      <div className="relative flex h-9 bg-sunken">
        {floors.map((c, i) => (
          <div key={c.rule_id} className={`h-full ${i === floors.length - 1 ? 'border-l border-surface bg-muted' : 'bg-ink'}`} style={w(c.limit)} />
        ))}
        <div className="absolute inset-y-0 bg-fail/90" style={{ left: `${((cap.limit * 100) / scale) * 100}%`, ...w(over) }} />
        <div className="absolute -inset-y-1 w-0.5 bg-fail" style={{ left: `${((cap.limit * 100) / scale) * 100}%` }} />
      </div>
      <div className="relative h-8 text-xs">
        <div className="absolute top-0 h-1.5 border-x border-b border-ink" style={{ left: `${((before * 100) / scale) * 100}%`, ...w(room) }} />
        <div className="absolute top-0 h-1.5 border-x border-b border-fail" style={{ left: `${((cap.limit * 100) / scale) * 100}%`, ...w(over) }} />
        <div className="num absolute top-3 flex gap-3 whitespace-nowrap" style={{ right: `${100 - (((cap.limit + over) * 100) / scale) * 100}%` }}>
          <span>only {pct(room)} room left for {ruleSubject(ruleById[last.rule_id]) ?? last.rule_id}</span>
          <span className="font-semibold text-fail">{(over * 100).toFixed(1)} points over</span>
        </div>
      </div>
      <div className="num flex justify-between text-2xs text-muted">
        <span>0%</span>
        <span>{scale}%</span>
      </div>
    </div>
  )
}

function Arithmetic({ arithmetic, n }) {
  const m = arithmetic.match(/^(.*?)(\s*>\s*.*)$/)
  return (
    <div data-field="conflict-arithmetic" className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
      <span className="num text-lg">
        {m ? m[1] : arithmetic}
        {m && <span className="font-semibold text-fail">{m[2]}</span>}
      </span>
      <span className="text-ui text-muted">
        No portfolio can satisfy all {numberWord(n)}, so the Referee stops instead of guessing.
      </span>
    </div>
  )
}

function CheapestFix({ relaxations, ruleById, conflictSet, who, onEdit, compact }) {
  const [asked, setAsked] = useState(false)
  const ask = async () => {
    const text = relaxations.map((r) => r.explain).join('\n')
    try {
      await navigator.clipboard.writeText(`Approval needed: ${text}`)
    } catch {
      /* clipboard can be blocked; the button still confirms */
    }
    setAsked(true)
  }
  return (
    <div data-field="cheapest-fix">
      <div className={`label ${compact ? 'mb-2' : 'border-t-3 border-ink pt-6 mb-5'}`}>The cheapest way out</div>
      <div className={compact ? 'grid gap-4' : 'grid gap-5 border border-line bg-surface p-6'}>
        {relaxations.map((r) => {
          const rule = ruleById[r.rule_id]
          return (
            <div key={r.rule_id} data-rule-id={r.rule_id}>
              <div className="font-display text-lg text-prose">{r.new_limit > r.old_limit ? 'Raise' : 'Lower'} {who} rule</div>
              <div className="font-display text-2xl italic">“{(rule?.source ?? r.rule_id).replace(/\.$/, '')}”</div>
              <div className="mt-3 flex items-baseline gap-3 text-sm text-muted">
                from <span className="num text-2xl text-muted line-through">{pct(r.old_limit)}</span>
                to <span className="num text-4xl font-semibold text-ink">{pct(r.new_limit)}</span>
              </div>
              <p className="mt-3 text-ui text-muted">
                The smallest single change that makes every other rule possible.
                {conflictSet.length > 1 && ` The other ${numberWord(conflictSet.length - 1)} rule${conflictSet.length > 2 ? 's' : ''} stay as ${who === 'their' ? 'they' : who === 'his' ? 'he' : 'she'} said them.`}
                <span className="num ml-1 text-xs">(cost {r.cost.toFixed(0)})</span>
              </p>
            </div>
          )
        })}
        {!compact && (
          <div className="no-print grid gap-2.5">
            <button className="btn-primary py-3" onClick={ask}>
              {asked ? 'Approval request copied' : 'Ask the advisor to approve →'}
            </button>
            {onEdit && (
              <button className="btn-ghost border-line bg-surface py-3" onClick={onEdit}>Edit {who} rules instead</button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ConflictPanel({ explain, relaxations = [], conflictSet = [], rules = [], checks = [], clientName = '', clientStory = '', onEdit, layout = 'receipt' }) {
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const checkById = Object.fromEntries(checks.map((c) => [c.rule_id, c]))
  const { sentence, arithmetic } = splitConflict(explain)
  const who = pronoun(clientName, clientStory)
  const n = conflictSet.length
  const conflictChecks = conflictSet.map((id) => checkById[id]).filter(Boolean)
  const others = checks.length - n
  const page = layout === 'page'

  const list = (
    <ul data-field="conflict-rules" className="border-t border-ink">
      {conflictSet.map((id) => {
        const c = checkById[id]
        const subject = ruleSubject(ruleById[id])
        return (
          <li key={id} data-rule-id={id} className="flex items-baseline gap-4 border-b border-line py-3">
            <span className="num w-6 shrink-0 text-xs text-fail">{id}</span>
            <span className={`min-w-0 flex-1 font-display italic ${page ? 'text-xl' : 'text-lg'}`}>“{(ruleById[id]?.source ?? id).replace(/\.$/, '')}”</span>
            {c && <span className="num shrink-0 text-xs text-muted">{subject ? `${subject} ` : ''}{fmtLimit(c)}</span>}
          </li>
        )
      })}
    </ul>
  )

  return (
    <div data-component="conflict-panel" data-layout={layout} className={page ? 'grid gap-12 lg:grid-cols-conflict' : 'grid gap-6'}>
      <div className={page ? 'grid gap-8 border-t-3 border-fail pt-6' : 'grid gap-5'}>
        <div>
          <h2 className={`font-display font-semibold ${page ? 'text-4xl' : 'text-2xl'}`}>
            {n > 0 ? `${numberWord(n)[0].toUpperCase()}${numberWord(n).slice(1)} of ${who} rules can't all be true at once.` : "These rules can't all hold."}
          </h2>
          <p data-field="conflict-explain" className="sr-only">{sentence}</p>
        </div>
        {list}
        <OverflowBar conflictChecks={conflictChecks} ruleById={ruleById} />
        {arithmetic && <Arithmetic arithmetic={arithmetic} n={n} />}
      </div>
      {relaxations.length > 0 && (
        <div className="grid content-start gap-5">
          <CheapestFix relaxations={relaxations} ruleById={ruleById} conflictSet={conflictSet} who={who} onEdit={onEdit} compact={!page} />
          {page && others > 0 && (
            <p className="flex items-baseline gap-2.5 text-ui text-muted">
              <span className="h-2 w-2 shrink-0 rounded-full bg-pass" />
              {who[0].toUpperCase() + who.slice(1)} other {others} rules can all be met. Nothing changes until someone approves.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
