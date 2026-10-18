// "What each rule costs": how much better the best portfolio gets if one rule is dropped.
import { useEffect, useState } from 'react'
import { getPrices } from '../api.js'
import { Badge, ErrorNote, SectionTitle, Spinner } from './ui.jsx'

export default function PriceTags({ clientId }) {
  const [prices, setPrices] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setPrices(null)
    setError(null)
    getPrices(clientId).then(setPrices).catch((e) => setError(e.message))
  }, [clientId])

  const max = prices ? Math.max(...prices.map((p) => p.utility_cost_pts), 0.01) : 1

  return (
    <div>
      <SectionTitle eyebrow="Constraint attribution" title="What each rule costs">
        For each rule, the solver finds the best possible portfolio with and without it. The gap is the rule's price, in
        points of risk-adjusted return per year. Rules that never bind cost nothing.
      </SectionTitle>
      {error && <ErrorNote>{error}</ErrorNote>}
      {!prices && !error && <Spinner label="Solving the best portfolio with and without each rule…" />}
      {prices && (
        <ul className="card divide-y divide-line">
          {prices.map((p) => (
            <li key={p.rule_id} className="px-5 py-4 grid gap-2 sm:grid-cols-[1fr_220px] sm:items-center">
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
                  <span className="text-[11px] text-muted">pts / yr</span>
                </div>
                <div className="h-1.5 rounded-full bg-sunken mt-1 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${p.binds ? 'bg-accent' : 'bg-line'}`}
                    style={{ width: `${Math.max((p.utility_cost_pts / max) * 100, p.binds ? 3 : 0)}%` }}
                  />
                </div>
                <div className="num text-[11px] text-muted mt-1">
                  Sharpe {p.sharpe_with.toFixed(2)} → {p.sharpe_without.toFixed(2)} without
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
