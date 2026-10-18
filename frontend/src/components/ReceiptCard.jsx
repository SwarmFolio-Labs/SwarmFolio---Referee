// The Referee's receipt: verdict, every rule with its sentence, conflict + cheapest fix, weights chart, id.
import { useState } from 'react'
import { VERDICTS, pct } from '../format.js'
import ConflictPanel from './ConflictPanel.jsx'
import RuleCheckRow from './RuleCheckRow.jsx'
import WeightsChart from './WeightsChart.jsx'

const VERDICT_STYLE = {
  pass: 'border-pass/40 bg-pass/5 text-pass',
  fail: 'border-fail/40 bg-fail/5 text-fail',
  warn: 'border-warn/50 bg-warn/10 text-warn',
}

function VerdictBanner({ receipt, verdict, headline }) {
  const failed = receipt.checks.filter((c) => !c.passed).length
  return (
    <div data-component="verdict-banner" className={`border-b px-6 py-5 ${VERDICT_STYLE[verdict.tone]}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="label !text-current opacity-80">Referee verdict</div>
          <div className="font-display text-3xl font-bold tracking-tight mt-1">{headline ?? verdict.headline}</div>
          <div className="text-sm mt-1 text-ink/80">
            {receipt.checks.length - failed} of {receipt.checks.length} rules pass
            {receipt.verdict === 'VIOLATIONS_REPAIRED' &&
              ` · nearest compliant portfolio moves ${pct(receipt.capital_moved, 0)} of capital`}
          </div>
        </div>
        <div className="text-right">
          <div className="label">Receipt</div>
          <div className="num text-lg font-semibold text-ink">#{receipt.receipt_id}</div>
          <div className="num text-2xs text-muted">{receipt.timestamp}</div>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="num text-sm mt-0.5">{value}</div>
    </div>
  )
}

/**
 * receipt: a Receipt from the API. rules: the client's rules (for their own words).
 * before/after: weights for the chart (defaults: nothing / the Referee's repaired weights).
 * variant: "card" (default) or "printed"; rendered as data-variant so index.css can restyle it.
 */
export default function ReceiptCard({ receipt, rules = [], before, after, beforeLabel, afterLabel, headline, variant = 'card' }) {
  const [copied, setCopied] = useState(false)
  const v = VERDICTS[receipt.verdict] ?? VERDICTS.ERROR
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const conflict = new Set(receipt.conflict_set)
  const chartAfter = after ?? receipt.repaired_weights
  const showChart = before && chartAfter && Object.keys(chartAfter).length > 0

  const copy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(receipt, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div data-component="receipt" data-variant={variant} data-verdict={receipt.verdict} className="card overflow-hidden">
      <VerdictBanner receipt={receipt} verdict={v} headline={headline} />

      <div className="px-6 py-5 grid gap-6">
        <p className="text-sm">{receipt.summary}</p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Sharpe before" value={receipt.sharpe_before.toFixed(2)} />
          <Stat label="Sharpe after" value={receipt.sharpe_after.toFixed(2)} />
          <Stat label="Volatility after" value={pct(receipt.vol_after)} />
          <Stat label="Capital moved" value={pct(receipt.capital_moved)} />
        </div>

        {!receipt.rules_feasible && (
          <ConflictPanel explain={receipt.conflict_explain} relaxations={receipt.cheapest_relaxation} />
        )}

        <div>
          <div className="label mb-1">Every rule</div>
          <ul>
            {receipt.checks.map((c) => (
              <RuleCheckRow key={c.rule_id} check={c} rule={ruleById[c.rule_id]} inConflict={conflict.has(c.rule_id)} />
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
