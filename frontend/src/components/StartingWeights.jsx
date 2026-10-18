// "Starting → final" per ticker: the client's current holdings vs the committee's final portfolio.
import { pct } from '../format.js'

export default function StartingWeights({ start = {}, final = {}, startLabel = 'Starting', finalLabel = 'Final' }) {
  const tickers = [...new Set([...Object.keys(start), ...Object.keys(final)])]
    .filter((t) => (start[t] ?? 0) > 1e-9 || (final[t] ?? 0) > 1e-9)
    .sort((a, b) => (final[b] ?? 0) - (final[a] ?? 0) || (start[b] ?? 0) - (start[a] ?? 0))
  if (tickers.length === 0) return null
  return (
    <div data-component="starting-weights" className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            <th className="label px-4 py-2">Ticker</th>
            <th className="label px-4 py-2 text-right">{startLabel}</th>
            <th className="px-2 py-2" />
            <th className="label px-4 py-2 text-right">{finalLabel}</th>
            <th className="label px-4 py-2 text-right">Change</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => {
            const a = start[t] ?? 0
            const b = final[t] ?? 0
            const d = b - a
            return (
              <tr key={t} data-ticker={t} className="border-b border-line last:border-0">
                <td className="num px-4 py-1.5 font-medium">{t}</td>
                <td className="num px-4 py-1.5 text-right text-muted">{a > 1e-9 ? pct(a) : '–'}</td>
                <td className="px-2 py-1.5 text-muted">→</td>
                <td className="num px-4 py-1.5 text-right">{b > 1e-9 ? pct(b) : '–'}</td>
                <td className={`num px-4 py-1.5 text-right ${Math.abs(d) < 5e-4 ? 'text-muted' : d > 0 ? 'text-pass' : 'text-fail'}`}>
                  {Math.abs(d) < 5e-4 ? '0.0%' : `${d > 0 ? '+' : '−'}${pct(Math.abs(d))}`}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
