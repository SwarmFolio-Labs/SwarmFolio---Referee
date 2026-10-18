// "What each rule costs" panel: loads the rule prices for a client and shows them as a PriceTagChart.
import { useEffect, useState } from 'react'
import { getPrices } from '../api.js'
import PriceTagChart from './PriceTagChart.jsx'
import { ErrorNote, SectionTitle, Spinner } from './ui.jsx'

export default function PriceTags({ clientId }) {
  const [prices, setPrices] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setPrices(null)
    setError(null)
    getPrices(clientId).then(setPrices).catch((e) => setError(e.message))
  }, [clientId])

  return (
    <div>
      <SectionTitle eyebrow="Constraint attribution" title="What each rule costs">
        For each rule, the solver finds the best possible portfolio with and without it. The gap is the rule's price, in
        points of risk-adjusted return per year. Rules that never bind cost nothing.
      </SectionTitle>
      {error && <ErrorNote>{error}</ErrorNote>}
      {!prices && !error && <Spinner label="Solving the best portfolio with and without each rule…" />}
      {prices && <PriceTagChart prices={prices} />}
    </div>
  )
}
