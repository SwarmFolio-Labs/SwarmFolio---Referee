// Screen E: "What each rule costs" as ranked bars. Rules that hold something back get a bar scaled to the priciest
// one; rules that cost nothing are listed together underneath. Values are the API's utility cost in points / yr.
import { numberWord } from '../format.js'

const PAID = 0.005 // below this the rule prints as 0.00: free

export default function PriceTagChart({ prices, rules = [], who = 'their' }) {
  const ruleById = Object.fromEntries(rules.map((r) => [r.id, r]))
  const quote = (p) => `“${(ruleById[p.rule_id]?.source ?? p.source).replace(/\.$/, '')}”`
  const paid = prices.filter((p) => p.utility_cost_pts >= PAID).sort((a, b) => b.utility_cost_pts - a.utility_cost_pts)
  const free = prices.filter((p) => p.utility_cost_pts < PAID)
  const scale = Math.max(1, Math.ceil(paid[0]?.utility_cost_pts ?? 1))
  const Who = who[0].toUpperCase() + who.slice(1)

  return (
    <div data-component="price-tag-chart" className="grid gap-10">
      {paid.length > 0 && (
        <table className="w-full border-b border-ink">
          <thead>
            <tr className="border-b border-ink text-left">
              <th className="label w-2/5 pb-2">{who} rule</th>
              <th className="hidden pb-2 text-2xs font-normal text-muted sm:table-cell">0 – {scale} points / yr</th>
              <th className="label pb-2 text-right">Cost / yr</th>
            </tr>
          </thead>
          <tbody>
            {paid.map((p, i) => (
              <tr key={p.rule_id} data-rule-id={p.rule_id} title={p.explain} className="border-b border-line last:border-0">
                <td className="py-5 pr-6 align-middle">
                  <div className="font-display text-lg italic">{quote(p)}</div>
                  {i === 0 && paid.length > 1 && <div className="mt-1 text-xs text-muted">The most expensive rule</div>}
                </td>
                <td className="hidden py-5 pr-12 align-middle sm:table-cell">
                  <div className="h-3.5 bg-sunken">
                    <div className="h-full bg-ink" style={{ width: `${Math.max((p.utility_cost_pts / scale) * 100, 0.6)}%` }} />
                  </div>
                </td>
                <td className="num py-5 text-right align-middle text-2xl font-semibold">{p.utility_cost_pts.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {free.length > 0 && (
        <div>
          <p className="flex items-baseline gap-3 font-display text-2xl font-semibold text-pass">
            <span className="h-2.5 w-2.5 shrink-0 self-center rounded-full bg-pass" />
            {free.length === prices.length
              ? `All ${numberWord(free.length)} of ${who} rules cost nothing.`
              : `${free.length} of ${who} ${prices.length} rules cost nothing.`}
          </p>
          <p className="mt-2 text-ui text-muted">
            The best portfolio already meets them, so keeping them is free. {Who === 'Their' ? 'They' : Who === 'His' ? 'He' : 'She'} can hold on to every one.
          </p>
          <ul className="mt-3 grid gap-x-6 sm:grid-cols-2">
            {free.map((p) => (
              <li key={p.rule_id} data-rule-id={p.rule_id} title={p.explain} className="flex items-baseline justify-between gap-4 border-b border-line py-2.5">
                <span className="font-display text-md italic">{quote(p)}</span>
                <span className="num text-xs text-pass">0.00</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
