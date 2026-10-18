// One client in the picker. "featured" rows (demo clients) show the story and a few rules; compact rows are a table line.
import { Link } from 'react-router-dom'
import { displayName } from '../format.js'
import RuleChip from './RuleChip.jsx'
import StatusMark from './StatusMark.jsx'

function Chips({ rules, max }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {rules.slice(0, max).map((r) => (
        <RuleChip key={r.id} rule={r} />
      ))}
      {rules.length > max && <span className="px-1 text-ui text-muted">+ {rules.length - max} more</span>}
    </div>
  )
}

export default function ClientCard({ client, demo, primary = false, compact = false }) {
  const to = `/client/${client.client_id}`
  const n = client.rules.length
  if (compact) {
    return (
      <div data-component="client-card" data-variant="compact" className="flex items-center gap-10 border-b border-line py-3">
        <span className="num w-13 shrink-0 text-ui text-muted">{client.client_id}</span>
        <Link to={to} className="w-52 shrink-0 font-display text-lg font-semibold">{displayName(client.name)}</Link>
        <div className="min-w-0 flex-1"><Chips rules={client.rules} max={2} /></div>
        <span className="num w-20 shrink-0 text-right text-ui text-muted">{n} rules</span>
        <Link to={to} className="shrink-0 whitespace-nowrap text-right text-sm font-semibold underline underline-offset-4">Convene →</Link>
      </div>
    )
  }
  return (
    <div data-component="client-card" className="flex items-start gap-10 border-b border-line py-7">
      <span className="num w-13 shrink-0 text-ui leading-8 text-muted">{client.client_id}</span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <div className="flex flex-wrap items-baseline gap-3">
          <Link to={to} className="font-display text-h3 font-semibold">{displayName(client.name)}</Link>
          <StatusMark demo={demo} />
        </div>
        <p className="max-w-prose font-display text-prose text-prose">{client.story}</p>
        <Chips rules={client.rules} max={4} />
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2.5">
        <Link to={to} className={primary ? 'btn-primary' : 'btn-ghost'}>Convene the committee →</Link>
        <span className="num text-xs text-muted">{n} rules</span>
      </div>
    </div>
  )
}
