// An analyst's answer to the Referee: shape + "Stance · Analyst" label, then the text (wraps freely, no clamping).
// Concede ● moss, defend ■ brick, modify ◆ ochre; a missing analyst gets a dashed hollow dot and muted italics.
import { AGENTS } from '../format.js'

const STANCES = {
  concede: { tone: 'text-concede', shape: 'h-2 w-2 rounded-full bg-concede' },
  defend: { tone: 'text-defend', shape: 'h-2 w-2 bg-defend' },
  modify: { tone: 'text-warn-text', shape: 'h-2 w-2 rotate-45 bg-modify' },
}

export default function StanceBadge({ stance, agent, text }) {
  const s = STANCES[stance]
  const who = AGENTS[agent]?.label ?? agent
  return (
    <div data-component="stance-badge" data-stance={stance ?? 'missing'} className="grid grid-cols-stance gap-x-2.5 gap-y-0.5">
      <span className="flex h-4 items-center justify-center">
        <span className={s ? s.shape : 'h-2 w-2 rounded-full border border-dashed border-muted'} />
      </span>
      <span className={`text-xs font-semibold ${s ? s.tone : 'text-muted'}`}>
        {s ? stance[0].toUpperCase() + stance.slice(1) : 'No answer'}
        {who ? ` · ${who}` : ''}
      </span>
      <span />
      <p className={`font-display text-base ${s ? 'text-ink' : 'italic text-muted'}`}>{text}</p>
    </div>
  )
}
