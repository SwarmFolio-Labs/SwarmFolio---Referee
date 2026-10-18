// An analyst's response to the Referee: concede / defend / modify (colors: --concede/--defend/--modify).
import { Badge } from './ui.jsx'

export default function StanceBadge({ stance }) {
  return <Badge tone={stance}>{stance}</Badge>
}
