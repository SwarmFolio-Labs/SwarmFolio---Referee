// The feedback experiment (MASTER 10.3): can math feedback teach an AI to follow a client's rules?
import { useEffect, useState } from 'react'
import { getExperiment } from '../api.js'
import ExperimentChart from '../components/ExperimentChart.jsx'
import { CONDITIONS } from '../experiment.js'
import { ErrorNote, SectionTitle, Spinner } from '../components/ui.jsx'


const ci = ([m, lo, hi], scale = 100, digits = 0) =>
  `${(m * scale).toFixed(digits)}${scale === 100 ? '%' : ''} [${(lo * scale).toFixed(digits)}, ${(hi * scale).toFixed(digits)}]`

function PairedCard({ title, p }) {
  return (
    <div className="card p-5">
      <div className="label">{title}</div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[['fewer', 'C faster'], ['same', 'same'], ['more', 'C slower']].map(([k, l]) => (
          <div key={k} className="rounded-md bg-sunken py-2">
            <div className="num text-xl font-semibold">{p[k]}</div>
            <div className="text-2xs text-muted">{l}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 text-sm text-muted">
        Sign test <span className="num text-ink">p = {p.p_value.toFixed(3)}</span>
      </div>
    </div>
  )
}

export default function ExperimentPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getExperiment().then(setData).catch((e) => setError(e))
  }, [])

  if (error)
    return error.status === 404 ? (
      <div className="card p-6 text-sm">
        <div className="font-semibold mb-1">No experiment results yet.</div>
        <p className="text-muted">
          Run <code className="num bg-sunken px-1 rounded">python -m eval.experiment</code> to create eval/results/experiment.json.
        </p>
      </div>
    ) : (
      <ErrorNote>{error.message}</ErrorNote>
    )
  if (!data) return <Spinner label="Loading experiment results…" />

  const s = data.summary
  const last = (m) => s[m].per_round[s[m].per_round.length - 1].compliance[0]
  const rounds = s.self.per_round.length

  return (
    <div className="grid gap-10">
      <div className="max-w-prose">
        <div className="label mb-2">The feedback experiment</div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Can math feedback teach an AI to follow a client's rules?</h1>
        <p className="mt-3 text-muted">
          Every condition starts from the same first draft, then the Chair revises up to {rounds - 1} times with different
          feedback. {s.n_trials} client-trials; {s.n_draft_violates} first drafts broke at least one rule. Brackets are 95%
          bootstrap confidence intervals.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {CONDITIONS.map((c) => (
          <div key={c.id} className="card p-5">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
              <span className="font-semibold text-sm">{c.label}</span>
            </div>
            <p className="text-xs text-muted mt-1">{c.blurb}</p>
            <div className="num text-3xl font-bold mt-3">{(last(c.id) * 100).toFixed(0)}%</div>
            <div className="text-xs text-muted">compliant after round {rounds - 1}</div>
          </div>
        ))}
      </div>

      <section>
        <SectionTitle title="Learning curve">Share of client-trials that follow every rule, after each round of revision.</SectionTitle>
        <div className="card p-4">
          <ExperimentChart summary={s} />
        </div>
      </section>

      <section>
        <SectionTitle title="By round" />
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th className="px-4 py-3 label">Condition</th>
                {Array.from({ length: rounds }, (_, r) => (
                  <th key={r} className="px-4 py-3 label">Round {r}</th>
                ))}
                <th className="px-4 py-3 label">Capital moved</th>
              </tr>
            </thead>
            <tbody>
              {CONDITIONS.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0 align-top">
                  <td className="px-4 py-3 font-medium whitespace-nowrap">{c.label}</td>
                  {s[c.id].per_round.map((pr, r) => (
                    <td key={r} className="px-4 py-3">
                      <div className="num">{ci(pr.compliance)}</div>
                      <div className="num text-xs text-muted">
                        {pr.n_broken[0].toFixed(2)} broken · {(pr.violation_pp[0] ?? 0).toFixed(1)} pp
                      </div>
                    </td>
                  ))}
                  <td className="px-4 py-3 num">{ci(s[c.id].capital_moved)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <SectionTitle title="Paired comparison">Rounds needed to reach compliance, per client-trial.</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2">
          <PairedCard title="C. Explained vs B. Bare verdict" p={s.C_vs_B} />
          <PairedCard title="C. Explained vs A. Self-check" p={s.C_vs_A} />
        </div>
      </section>

      {data.trials?.length > 0 && (
        <section>
          <SectionTitle title="Every client-trial">Rounds to compliance per condition (— = never within the budget).</SectionTitle>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left">
                  <th className="px-4 py-2 label">Client</th>
                  <th className="px-4 py-2 label">Trial</th>
                  {CONDITIONS.map((c) => (
                    <th key={c.id} className="px-4 py-2 label">{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.trials.map((t, i) => (
                  <tr key={i} className="border-b border-line last:border-0">
                    <td className="px-4 py-2 num">{t.client_id}</td>
                    <td className="px-4 py-2 num">{t.trial}</td>
                    {CONDITIONS.map((c) => {
                      const r = t.conditions?.[c.id]?.rounds_to_comply
                      return (
                        <td key={c.id} className="px-4 py-2 num">
                          {r === null || r === undefined ? '—' : r}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
