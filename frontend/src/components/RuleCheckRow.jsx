// One line of "Every rule, checked": pass/fail mark, the rule in the client's words, the Referee's
// sentence, and actual vs limit ("min X" / "max X"; exclusions read "none held").
import { fmtActual, fmtLimit } from '../format.js'
import { Badge, PassMark } from './ui.jsx'

export default function RuleCheckRow({ check, rule, inConflict }) {
  return (
    <li
      data-component="rule-check"
      data-passed={check.passed}
      data-rule-type={check.type}
      className="flex gap-3 py-3 border-b border-line last:border-0"
    >
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
        <div data-field="actual" className={`num text-sm ${check.passed ? '' : 'text-fail font-semibold'}`}>
          {fmtActual(check)}
        </div>
        <div data-field="limit" className="num text-2xs text-muted">{fmtLimit(check)}</div>
      </div>
    </li>
  )
}
