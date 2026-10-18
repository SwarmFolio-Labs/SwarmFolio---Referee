// One client in the picker: story, demo badge, and every rule in the client's own words.
import { Link } from 'react-router-dom'
import { displayName, isSynthetic } from '../format.js'
import RuleChip from './RuleChip.jsx'
import { Badge } from './ui.jsx'

export default function ClientCard({ client }) {
  return (
    <Link
      to={`/client/${client.client_id}`}
      data-component="client-card"
      className="card p-5 flex flex-col gap-3 transition hover:border-ink/30 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="num text-xs text-muted">{client.client_id}</span>
            {isSynthetic(client.name) && <span className="text-3xs uppercase tracking-wide text-muted">synthetic</span>}
          </div>
          <h2 className="font-display text-lg font-semibold tracking-tight">{displayName(client.name)}</h2>
        </div>
        {client.has_demo ? <Badge tone="accent">committee run</Badge> : <Badge>referee only</Badge>}
      </div>
      <p className="text-sm text-muted">{client.story}</p>
      <div className="flex flex-wrap gap-1.5">
        {client.rules.map((r) => (
          <RuleChip key={r.id} rule={r} />
        ))}
      </div>
    </Link>
  )
}
