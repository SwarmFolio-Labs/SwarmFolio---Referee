// The Referee's receipt: verdict, every rule with its sentence, conflict + cheapest fix, weights chart, id.
import { useState } from 'react'
import { VERDICTS, fmtCheckValue, pct } from '../format.js'
import { Badge, PassMark } from './ui.jsx'
import WeightsChart from './WeightsChart.jsx'

const VERDICT_STYLE = {
  pass: 'border-pass/40 bg-pass/5 text-pass',
  fail: 'border-fail/40 bg-fail/5 text-fail',
  warn: 'border-warn/50 bg-warn/10 text-warn',
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="num text-sm mt-0.5">{value}</div>
    </div>
  )
}

function CheckRow({ check, rule, inConflict }) {
  return (
    <li className="flex gap-3 py-3 border-b border-line last:border-0">
      <PassMark passed={check.passed} />
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="num text-xs text-muted">{check.rule_id}</span>
          <span className="font-medium text-sm">{rule?.source ?? check.type}</span>
          {inConflict && <Badge tone="warn">in conflict</Badge>}
        </div>
        <p className="text-sm text-muted mt-0.5">{check.explain}</p>
      </div>
      <div className="text-right shrink-0">
        <div className={`num text-sm ${check.passed ? '' : 'text-fail font-semibold'}`}>
          {fmtCheckValue(check.type, check.actual)}
        </div>
        <div className="num text-[11px] text-muted">limit {fmtCheckValue(check.type, check.limit)}</div>
      </div>
    </li>
  )
}

/**
 * receipt: a Receipt from the API. rules: the client's rules (for their own words).
 * before/after: weights for the chart (defaults: nothing / the Referee's repaired weights).
 */
export default function ReceiptView({ receipt, rules = [], before, after, beforeLabel, afterLabel, headline }) {
  const [copied, setCopied] = useState(false)
  const v = VERDICTS[receipt.verdict] ?? VERDICTS.ERROR
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const failed = receipt.checks.filter((c) => !c.passed).length
  const conflict = new Set(receipt.conflict_set)
  const chartAfter = after ?? receipt.repaired_weights
  const showChart = before && chartAfter && Object.keys(chartAfter).length > 0

  const copy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(receipt, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="card overflow-hidden">
      {/* Verdict */}
      <div className={`border-b px-6 py-5 ${VERDICT_STYLE[v.tone]}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="label !text-current opacity-80">Referee verdict</div>
            <div className="font-display text-3xl font-bold tracking-tight mt-1">{headline ?? v.headline}</div>
            <div className="text-sm mt-1 text-ink/80">
              {receipt.checks.length - failed} of {receipt.checks.length} rules pass
              {receipt.verdict === 'VIOLATIONS_REPAIRED' &&
                ` · nearest compliant portfolio moves ${pct(receipt.capital_moved, 0)} of capital`}
            </div>
          </div>
          <div className="text-right">
            <div className="label">Receipt</div>
            <div className="num text-lg font-semibold text-ink">#{receipt.receipt_id}</div>
            <div className="num text-[11px] text-muted">{receipt.timestamp}</div>
          </div>
        </div>
      </div>

      <div className="px-6 py-5 grid gap-6">
        <p className="text-sm">{receipt.summary}</p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Sharpe before" value={receipt.sharpe_before.toFixed(2)} />
          <Stat label="Sharpe after" value={receipt.sharpe_after.toFixed(2)} />
          <Stat label="Volatility after" value={pct(receipt.vol_after)} />
          <Stat label="Capital moved" value={pct(receipt.capital_moved)} />
        </div>

        {/* Conflict + cheapest fix */}
        {!receipt.rules_feasible && (
          <div className="rounded-card border border-warn/50 bg-warn/5 p-4">
            <div className="label !text-warn">Conflict</div>
            <p className="text-sm mt-1">{receipt.conflict_explain}</p>
            {receipt.cheapest_relaxation.length > 0 && (
              <div className="mt-4">
                <div className="label">Cheapest fix (needs advisor approval)</div>
                <ul className="mt-2 grid gap-2">
                  {receipt.cheapest_relaxation.map((r) => (
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
        )}

        {/* Every rule */}
        <div>
          <div className="label mb-1">Every rule</div>
          <ul>
            {receipt.checks.map((c) => (
              <CheckRow key={c.rule_id} check={c} rule={ruleById[c.rule_id]} inConflict={conflict.has(c.rule_id)} />
            ))}
          </ul>
        </div>

        {showChart && (
          <div>
            <div className="label mb-2">Weights</div>
            <WeightsChart before={before} after={chartAfter} beforeLabel={beforeLabel} afterLabel={afterLabel} />
          </div>
        )}

        {(receipt.dust_removed.length > 0 || receipt.notes.length > 0) && (
          <ul className="text-xs text-muted grid gap-1">
            {receipt.dust_removed.length > 0 && <li>Dust removed (under 0.5%): {receipt.dust_removed.join(', ')}</li>}
            {receipt.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}

        <div className="flex justify-end">
          <button className="btn-ghost" onClick={copy}>
            {copied ? 'Copied' : 'Copy JSON'}
          </button>
        </div>
      </div>
    </div>
  )
}
