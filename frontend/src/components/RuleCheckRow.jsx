// One line of "Every rule, checked": ● pass / ■ broken, the rule, and actual · limit ("min X" / "max X";
// exclusions read "none held"). The full sentence from the Referee is the row's tooltip.
import { fmtActual, fmtLimit } from '../format.js'

export default function RuleCheckRow({ check, rule, inConflict }) {
  const exclusionClear = check.type === 'exclude' && check.passed
  return (
    <li
      data-component="rule-check"
      data-passed={check.passed}
      data-rule-type={check.type}
      title={check.explain}
      className="flex items-baseline gap-3 border-b border-line py-1.5 text-ui"
    >
      <span aria-label={check.passed ? 'passed' : 'broken'} className={`h-1.5 w-1.5 shrink-0 self-start mt-2 md:mt-0 md:self-center ${check.passed ? 'rounded-full bg-pass' : 'bg-fail'}`} />
      <span className="num w-6 shrink-0 text-xs text-muted">{check.rule_id}</span>
      <span className="min-w-0 flex-1 md:flex md:items-baseline md:gap-3">
      <span className={`block font-display text-md italic md:min-w-0 md:flex-1 ${inConflict ? 'text-warn-text' : 'text-prose'}`}>
        “{(rule?.source ?? check.type).replace(/\.$/, '')}”
      </span>
      <span className="num block text-xs md:shrink-0 md:text-right md:text-ui">
        {exclusionClear ? (
          <span data-field="limit">none held</span>
        ) : (
          <>
            <span data-field="actual" className={check.passed ? '' : 'font-semibold text-fail'}>{fmtActual(check)}</span>
            <span className="text-muted"> · </span>
            <span data-field="limit">{fmtLimit(check)}</span>
          </>
        )}
      </span>
      </span>
    </li>
  )
}
