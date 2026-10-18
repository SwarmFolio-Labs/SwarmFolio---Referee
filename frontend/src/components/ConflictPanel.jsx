// Screen C: the client's rules can't all hold. Which rules clash (in the client's words), the
// arithmetic that proves it, and the cheapest way to loosen them (all from the receipt).
import { pct, splitConflict } from '../format.js'

export default function ConflictPanel({ explain, relaxations = [], conflictSet = [], rules = [] }) {
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const { sentence, arithmetic } = splitConflict(explain)
  return (
    <div data-component="conflict-panel" className="rounded-card border border-warn/50 bg-warn/5 p-4 grid gap-4">
      <div>
        <div className="label !text-warn">Conflict</div>
        <p data-field="conflict-explain" className="text-sm mt-1">{sentence}</p>
      </div>

      {conflictSet.length > 0 && (
        <div data-field="conflict-rules">
          <div className="label">These rules clash</div>
          <ul className="mt-2 grid gap-1.5">
            {conflictSet.map((id) => (
              <li key={id} data-rule-id={id} className="flex items-baseline gap-3 text-sm">
                <span className="num text-xs text-muted">{id}</span>
                <span className="font-medium">“{ruleById[id]?.source ?? id}”</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {arithmetic && (
        <div data-field="conflict-arithmetic">
          <div className="label">The arithmetic</div>
          <div className="num text-lg font-semibold mt-1">{arithmetic}</div>
        </div>
      )}

      {relaxations.length > 0 && (
        <div data-field="cheapest-fix">
          <div className="label">Cheapest fix (needs advisor approval)</div>
          <ul className="mt-2 grid gap-2">
            {relaxations.map((r) => (
              <li key={r.rule_id} className="flex flex-wrap items-center gap-3 text-sm">
                <span className="num text-xs text-muted">{r.rule_id}</span>
                {ruleById[r.rule_id] && <span className="font-medium">“{ruleById[r.rule_id].source}”</span>}
                <span className="num">
                  {pct(r.old_limit)} <span className="text-muted">→</span>{' '}
                  <span className="font-semibold">{pct(r.new_limit)}</span>
                </span>
                <span className="num text-xs text-muted">cost {r.cost.toFixed(1)}</span>
                <span className="text-muted basis-full">{r.explain}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
