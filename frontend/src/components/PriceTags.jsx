// Screen E: loads the rule prices for a client, shows them as a PriceTagChart, and turns the priciest rule into
// the conversation the advisor should have with the client.
import { useEffect, useState } from 'react'
import { getPrices } from '../api.js'
import { displayName, pronoun } from '../format.js'
import PriceTagChart from './PriceTagChart.jsx'
import { ErrorNote, Spinner } from './ui.jsx'

export default function PriceTags({ clientId, client, onBack }) {
  const [prices, setPrices] = useState(null)
  const [error, setError] = useState(null)
  const who = pronoun(displayName(client?.name ?? ''), client?.story ?? '')

  useEffect(() => {
    setPrices(null)
    setError(null)
    getPrices(clientId).then(setPrices).catch((e) => setError(e.message))
  }, [clientId])

  const top = prices && [...prices].sort((a, b) => b.utility_cost_pts - a.utility_cost_pts)[0]
  const topPaid = top && top.utility_cost_pts >= 0.005

  return (
    <div data-component="price-tags" className="grid gap-12">
      <div>
        <h2 className="font-display text-4xl font-semibold tracking-snug sm:text-6xl">What each of {who} rules costs</h2>
        <p className="mt-4 max-w-lede font-display text-lg text-prose">
          Risk-adjusted return (return minus a penalty for risk) the best portfolio gives up each year because of the rule,
          in percentage points. A rule that doesn't hold anything back is free.
        </p>
      </div>
      {error && <ErrorNote>{error}</ErrorNote>}
      {!prices && !error && <Spinner label="Solving the best portfolio with and without each rule…" />}
      {prices && (
        <div className="grid items-start gap-12 lg:grid-cols-conflict lg:gap-16">
          <PriceTagChart prices={prices} rules={client?.rules} who={who} />
          <aside className="grid gap-5 border-t-3 border-ink pt-6">
            <div className="label">The conversation to have</div>
            {topPaid ? (
              <p className="font-display text-2xl leading-snug">
                “Your rule ‘{top.source.replace(/\.$/, '')}’ is the one that costs you. Keeping it gives up about{' '}
                <span className="num font-semibold">{top.utility_cost_pts.toFixed(2)}</span> points of risk-adjusted return a
                year. Is it worth that?”
              </p>
            ) : (
              <p className="font-display text-2xl leading-snug">“None of your rules hold the portfolio back. Keep them all.”</p>
            )}
            <p className="text-ui text-muted">
              Each cost compares the best portfolio with the rule and without it. It's a guide for the conversation, not a
              promise. Ask before changing any rule.
            </p>
            {onBack && (
              <button className="btn-ghost justify-self-start" onClick={onBack}>Back to the committee run</button>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}
