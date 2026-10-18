// "From stock grants to a balanced book": before → after per ticker, as paired bars with the change.
import { pct } from '../format.js'

const signed = (d) => (Math.abs(d) < 5e-4 ? '0.0' : `${d > 0 ? '+' : '−'}${(Math.abs(d) * 100).toFixed(1)}`)

export default function StartingWeights({ start = {}, final = {}, compact = false }) {
  const tickers = [...new Set([...Object.keys(start), ...Object.keys(final)])]
    .filter((t) => (start[t] ?? 0) > 1e-9 || (final[t] ?? 0) > 1e-9)
    .sort((a, b) => (final[b] ?? 0) - (final[a] ?? 0) || (start[b] ?? 0) - (start[a] ?? 0))
  if (tickers.length === 0) return null
  const max = Math.max(...tickers.map((t) => Math.max(start[t] ?? 0, final[t] ?? 0)))
  const scale = Math.ceil((max * 100) / 5) * 5 // bar axis 0 – N%, rounded up to 5
  const w = (x) => ({ width: `${((x * 100) / scale) * 100}%` })
  return (
    <table data-component="starting-weights" data-variant={compact ? 'compact' : 'full'} className="w-full text-ui">
      <thead>
        <tr className="border-b border-ink text-left">
          <th className="label py-2 pr-2">Holding</th>
          {!compact && <th className="label w-16 py-2 pr-4 text-right">Before</th>}
          <th className="py-2 text-2xs font-normal text-muted">{compact ? 'before / after' : `0 – ${scale}%`}</th>
          <th className="label py-2 pl-4 text-right">{compact ? 'Weight' : 'After'}</th>
          {!compact && <th className="label w-14 py-2 text-right">Change</th>}
        </tr>
      </thead>
      <tbody>
        {tickers.map((t) => {
          const a = start[t] ?? 0
          const b = final[t] ?? 0
          const d = b - a
          return (
            <tr key={t} data-ticker={t} className="border-b border-line">
              <td className="num py-2 pr-2">{t}</td>
              {!compact && <td className="num py-2 pr-4 text-right text-muted">{a > 1e-9 ? pct(a) : <span className="font-sans text-xs">new</span>}</td>}
              <td className="w-full py-2">
                <div className="grid gap-0.5">
                  <div className="h-1 bg-before-bar" style={w(a)} />
                  <div className="h-1.5 bg-ink" style={w(b)} />
                </div>
              </td>
              {compact ? (
                <td className="num whitespace-nowrap py-2 pl-4 text-right">
                  {a > 1e-9 ? (a * 100).toFixed(1) : 'new'} → {(b * 100).toFixed(1)}
                </td>
              ) : (
                <td className="num py-2 pl-4 text-right font-semibold">{b > 1e-9 ? pct(b) : '–'}</td>
              )}
              {!compact && <td className={`num py-2 text-right ${Math.abs(d) >= 0.1 ? 'font-semibold text-ink' : 'text-muted'}`}>{signed(d)}</td>}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
