// Tiny shared building blocks. Colors come from the tokens in index.css.
import { AGENTS, VERDICTS } from '../format.js'

const TONES = {
  pass: 'bg-pass/10 text-pass border-pass/30',
  fail: 'bg-fail/10 text-fail border-fail/30',
  warn: 'bg-warn/10 text-warn border-warn/30',
  concede: 'bg-concede/10 text-concede border-concede/30',
  defend: 'bg-defend/10 text-defend border-defend/30',
  modify: 'bg-modify/10 text-modify border-modify/30',
  neutral: 'bg-sunken text-muted border-line',
  accent: 'bg-accent/10 text-accent border-accent/30',
}

export function Badge({ tone = 'neutral', children, className = '', ...rest }) {
  return (
    <span
      {...rest}
      className={`inline-flex items-center gap-1 rounded-chip border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

export function VerdictBadge({ verdict }) {
  const v = VERDICTS[verdict] ?? VERDICTS.ERROR
  return <Badge tone={v.tone}>{v.label}</Badge>
}

export function AgentAvatar({ agent }) {
  const a = AGENTS[agent] ?? { short: agent.slice(0, 2).toUpperCase() }
  const dark = agent === 'referee' || agent === 'chair'
  return (
    <span
      className={`h-8 w-8 shrink-0 rounded-full grid place-items-center font-mono text-2xs font-bold border ${
        dark ? 'bg-ink text-bg border-ink' : 'bg-surface text-ink border-line'
      }`}
    >
      {a.short}
    </span>
  )
}

export function PassMark({ passed }) {
  return (
    <span
      className={`h-5 w-5 shrink-0 rounded-full grid place-items-center text-2xs font-bold text-on-accent ${
        passed ? 'bg-pass' : 'bg-fail'
      }`}
      aria-label={passed ? 'passed' : 'failed'}
    >
      {passed ? '✓' : '✕'}
    </span>
  )
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted">
      <span className="h-4 w-4 rounded-full border-2 border-line border-t-accent animate-spin" />
      {label}
    </div>
  )
}

export function ErrorNote({ children }) {
  return <div className="card border-fail/30 bg-fail/5 p-4 text-sm text-fail">{children}</div>
}

export function SectionTitle({ eyebrow, title, children }) {
  return (
    <div className="mb-4">
      {eyebrow && <div className="label mb-1">{eyebrow}</div>}
      <h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>
      {children && <p className="mt-1 text-sm text-muted max-w-prose">{children}</p>}
    </div>
  )
}

export function WeightPills({ weights }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(weights)
        .filter(([, w]) => w > 1e-9)
        .sort((a, b) => b[1] - a[1])
        .map(([t, w]) => (
          <span key={t} className="num text-xs rounded border border-line bg-sunken px-1.5 py-0.5">
            {t} <span className="text-muted">{(w * 100).toFixed(1)}%</span>
          </span>
        ))}
    </div>
  )
}
