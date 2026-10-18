// "What each rule costs" as a list of price tags: the rule, its cost in pts/yr, and a bar scaled to the priciest rule.
import { Badge } from './ui.jsx'

export default function PriceTagChart({ prices }) {
  const max = Math.max(...prices.map((p) => p.utility_cost_pts), 0.01)
  return (
    <ul data-component="price-tag-chart" className="card divide-y divide-line">
      {prices.map((p) => (
        <li key={p.rule_id} className="px-5 py-4 grid gap-2 sm:grid-cols-price-tag sm:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="num text-xs text-muted">{p.rule_id}</span>
              <span className="font-medium text-sm">{p.source}</span>
              {p.binds ? <Badge tone="accent">binds</Badge> : <Badge>free</Badge>}
            </div>
            <p className="text-xs text-muted mt-1">{p.explain}</p>
          </div>
          <div>
            <div className="flex items-baseline justify-between">
              <span className="num text-lg font-semibold">{p.utility_cost_pts.toFixed(2)}</span>
              <span className="text-2xs text-muted">pts / yr</span>
            </div>
            <div className="h-1.5 rounded-full bg-sunken mt-1 overflow-hidden">
              <div
                className={`h-full rounded-full ${p.binds ? 'bg-accent' : 'bg-line'}`}
                style={{ width: `${Math.max((p.utility_cost_pts / max) * 100, p.binds ? 3 : 0)}%` }}
              />
            </div>
            <div className="num text-2xs text-muted mt-1">
              Sharpe {p.sharpe_with.toFixed(2)} → {p.sharpe_without.toFixed(2)} without
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}
