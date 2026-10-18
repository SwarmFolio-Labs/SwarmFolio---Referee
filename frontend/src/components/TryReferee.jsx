// "Try the Referee": edit weights, get a real receipt back from the solver.
import { useMemo, useState } from 'react'
import { checkProposal } from '../api.js'
import ReceiptCard from './ReceiptCard.jsx'
import { ErrorNote, SectionTitle, Spinner } from './ui.jsx'

const toPercents = (weights = {}) =>
  Object.fromEntries(Object.entries(weights).map(([t, w]) => [t, +(w * 100).toFixed(1)]))

export default function TryReferee({ client, presets, receiptVariant }) {
  const firstPreset = presets.find((p) => p.weights && Object.keys(p.weights).length)
  const [inputs, setInputs] = useState(() => toPercents(firstPreset?.weights))
  const [receipt, setReceipt] = useState(null)
  const [checkedWeights, setCheckedWeights] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const total = useMemo(() => Object.values(inputs).reduce((s, x) => s + (Number(x) || 0), 0), [inputs])
  const totalOk = Math.abs(total - 100) < 0.05

  const setWeight = (t, value) => setInputs((prev) => ({ ...prev, [t]: value === '' ? '' : Number(value) }))

  const check = async () => {
    const weights = Object.fromEntries(
      Object.entries(inputs)
        .filter(([, x]) => Number(x) > 0)
        .map(([t, x]) => [t, Number(x) / 100]),
    )
    setLoading(true)
    setError(null)
    try {
      setReceipt(await checkProposal(client.client_id, weights))
      setCheckedWeights(weights)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-6">
      <SectionTitle eyebrow="Live" title="Try the Referee">
        Change the weights and check them. This calls the real Referee (exact math, no AI): every rule, the clash if the
        rules can't all hold, and the nearest compliant portfolio.
      </SectionTitle>

      <div className="card p-5 grid gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="label mr-1">Start from</span>
          {presets.map((p) => (
            <button
              key={p.label}
              className="btn-ghost !py-1 !px-2.5 !text-xs"
              disabled={!p.weights}
              onClick={() => setInputs(toPercents(p.weights))}
            >
              {p.label}
            </button>
          ))}
          <button className="btn-ghost !py-1 !px-2.5 !text-xs" onClick={() => setInputs({})}>
            Clear
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {client.universe.map((t) => (
            <label
              key={t}
              className={`flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 ${
                Number(inputs[t]) > 0 ? 'border-accent/40 bg-accent/5' : 'border-line'
              }`}
            >
              <span className="num text-xs font-semibold">{t}</span>
              <span className="flex items-center gap-0.5">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  value={inputs[t] ?? ''}
                  placeholder="0"
                  onChange={(e) => setWeight(t, e.target.value)}
                  className="num w-14 bg-transparent text-right text-sm outline-none"
                />
                <span className="text-xs text-muted">%</span>
              </span>
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm">
            Total <span className={`num font-semibold ${totalOk ? 'text-pass' : 'text-fail'}`}>{total.toFixed(1)}%</span>
            {!totalOk && <span className="text-muted"> · weights must add up to 100%</span>}
          </div>
          <button className="btn-primary" onClick={check} disabled={loading || total <= 0}>
            {loading ? 'Checking…' : 'Check with the Referee'}
          </button>
        </div>
      </div>

      {loading && <Spinner label="The solver is checking every rule and searching for the nearest compliant portfolio…" />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {receipt && !loading && (
        <ReceiptCard
          variant={receiptVariant}
          receipt={receipt}
          rules={client.rules}
          before={checkedWeights}
          beforeLabel="Your weights"
          afterLabel={receipt.verdict === 'PASS' ? 'Unchanged' : 'Referee repair'}
        />
      )}
    </div>
  )
}
