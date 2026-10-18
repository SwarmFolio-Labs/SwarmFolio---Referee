// One client rule, shown in the client's own words.
export default function RuleChip({ rule, state }) {
  const ring =
    state === 'fail'
      ? 'border-fail/40 bg-fail/5 text-fail'
      : state === 'pass'
        ? 'border-pass/40 bg-pass/5'
        : state === 'conflict'
          ? 'border-warn/50 bg-warn/10 text-warn'
          : 'border-line bg-surface'
  return (
    <span
      title={`${rule.id} · ${rule.type} · priority ${rule.priority}${rule.hard ? ' · hard rule (never relaxed)' : ''}`}
      className={`inline-flex items-center gap-1.5 rounded-chip border px-2.5 py-1 text-xs ${ring}`}
    >
      <span className="num text-3xs text-muted">{rule.id}</span>
      <span>{rule.source.replace(/\.$/, '')}</span>
      {rule.hard && <span className="text-3xs font-semibold uppercase text-muted">hard</span>}
    </span>
  )
}
