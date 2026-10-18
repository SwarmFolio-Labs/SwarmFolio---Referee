// When the client's rules can't all hold: which rules clash, and the cheapest way to loosen them.
import { pct } from '../format.js'

export default function ConflictPanel({ explain, relaxations = [] }) {
  return (
    <div data-component="conflict-panel" className="rounded-card border border-warn/50 bg-warn/5 p-4">
      <div className="label !text-warn">Conflict</div>
      <p className="text-sm mt-1">{explain}</p>
      {relaxations.length > 0 && (
        <div className="mt-4">
          <div className="label">Cheapest fix (needs advisor approval)</div>
          <ul className="mt-2 grid gap-2">
            {relaxations.map((r) => (
              <li key={r.rule_id} className="flex flex-wrap items-center gap-3 text-sm">
                <span className="num text-xs text-muted">{r.rule_id}</span>
                <span className="num">
                  {pct(r.old_limit)} <span className="text-muted">→</span>{' '}
                  <span className="font-semibold">{pct(r.new_limit)}</span>
                </span>
                <span className="text-muted">{r.explain}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
