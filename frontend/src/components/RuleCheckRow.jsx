// One line of the receipt: pass/fail mark, the rule in the client's words, the Referee's sentence, actual vs limit.
import { fmtCheckValue } from '../format.js'
import { Badge, PassMark } from './ui.jsx'

export default function RuleCheckRow({ check, rule, inConflict }) {
  return (
    <li data-component="rule-check" data-passed={check.passed} className="flex gap-3 py-3 border-b border-line last:border-0">
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
        <div className="num text-2xs text-muted">limit {fmtCheckValue(check.type, check.limit)}</div>
      </div>
    </li>
  )
}
