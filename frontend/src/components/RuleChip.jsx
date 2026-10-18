// One client rule, quoted in the client's own words (the rule's `source`, word for word).
export default function RuleChip({ rule, state }) {
  const tone =
    state === 'fail' ? 'border-fail/40 text-fail' : state === 'conflict' ? 'border-warn/50 text-warn-text' : 'border-line'
  return (
    <span
      data-component="rule-chip"
      title={`${rule.id} · ${rule.type} · priority ${rule.priority}${rule.hard ? ' · hard rule (never relaxed)' : ''}`}
      className={`inline-flex items-baseline border bg-surface px-2 py-0.5 font-display text-md italic text-prose ${tone}`}
    >
      “{rule.source.replace(/\.$/, '')}”
    </span>
  )
}
