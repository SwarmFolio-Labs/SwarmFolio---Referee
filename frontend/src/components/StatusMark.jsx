// A run's outcome as a shape + label (color only reinforces it): ● compliant, ◆ repaired, ◇ needs approval.
const OUTCOMES = {
  PASS: { mark: '●', tone: 'text-pass', label: (d) => `Compliant after ${d.rounds} round${d.rounds === 1 ? '' : 's'}` },
  VIOLATIONS_REPAIRED: { mark: '◆', tone: 'text-warn-text', label: () => 'Repaired by the Referee' },
  RULES_INFEASIBLE: { mark: '◇', tone: 'text-warn-text', label: () => 'Rules conflict · needs approval' },
  ERROR: { mark: '■', tone: 'text-fail', label: () => 'The Referee could not check this' },
}

export default function StatusMark({ demo }) {
  if (!demo) {
    return (
      <span data-component="status-mark" className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted">
        <span className="h-2 w-2 rounded-full border border-muted" />
        Not run yet
      </span>
    )
  }
  const o = OUTCOMES[demo.receipt.verdict] ?? OUTCOMES.ERROR
  return (
    <span data-component="status-mark" className={`inline-flex items-center gap-1.5 text-xs font-semibold ${o.tone}`}>
      <span aria-hidden className="text-2xs">{o.mark}</span>
      {o.label(demo)}
    </span>
  )
}
