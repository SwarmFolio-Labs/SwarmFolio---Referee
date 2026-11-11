// Building blocks for anything the verifier computes live: the request hook, the solver
// certificate, the constraint table and the before -> after weights.
import { useCallback, useEffect, useState } from 'react'
import { fmtActual, fmtLimit, formal, pct, VERDICT } from '../mandates.js'

const REPO = 'https://github.com/SwarmFolio-Labs/SwarmFolio---Referee'

/** Run `fn` on mount and on demand; {data, error, busy, run}. */
export function useLive(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, busy: true })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const call = useCallback(fn, deps)
  const run = useCallback(() => {
    setState((s) => ({ ...s, busy: true, error: null }))
    return call()
      .then((data) => setState({ data, error: null, busy: false }))
      .catch((e) => setState((s) => ({ ...s, error: e.message, busy: false })))
  }, [call])
  useEffect(() => {
    run()
  }, [run])
  return { ...state, run }
}

/** While a request is in flight: a plain status line that admits when the free server is waking. */
export function Pending({ busy, error }) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!busy) return
    setSlow(false)
    const t = setTimeout(() => setSlow(true), 4000)
    return () => clearTimeout(t)
  }, [busy])
  if (error) return <p className="bad">Verifier unreachable: {error}</p>
  if (!busy) return null
  return (
    <p className="live busy muted">
      {slow ? 'Waking the solver server (free hosting tier, up to ~50 s)…' : 'Solving…'}
    </p>
  )
}

export function Verdict({ receipt }) {
  const tone = receipt.verdict === 'PASS' ? 'good' : receipt.verdict === 'ERROR' ? 'bad' : ''
  return <span className={`tag ${tone}`}>{VERDICT[receipt.verdict] ?? receipt.verdict}</span>
}

const short = (h) => `${h.slice(0, 10)}…${h.slice(-6)}`

/** What the solver actually did for this answer, with hashes anyone can recompute. */
export function Certificate({ cert, receipt, onRerun, busy }) {
  const statuses = [...new Set(cert.solves.map((s) => s.status))].join(', ') || 'no solve needed'
  const m = cert.largest_model
  const download = () => {
    const blob = new Blob([JSON.stringify({ receipt, certificate: cert }, null, 2)], { type: 'application/json' })
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: `certificate-${receipt.client_id}-${cert.input_sha256.slice(0, 8)}.json`,
    })
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const rows = [
    ['computed', `${cert.verified_at.replace('T', ' ').replace('Z', ' UTC')} · ${cert.wall_ms} ms on the server`],
    ['solver', `SCIP ${cert.versions.scip} via CVXPY ${cert.versions.cvxpy} · ${cert.solves.length} solve${cert.solves.length === 1 ? '' : 's'} · ${cert.solver_ms} ms`],
    ['model', m ? `${m.variables} variables (${m.binaries} binary) · ${m.constraints} constraint blocks` : '—'],
    ['status', statuses],
    ['input', `sha256 ${short(cert.input_sha256)}`],
    ['output', `sha256 ${short(cert.output_sha256)}`],
    [
      'code',
      cert.commit === 'local' ? (
        'local build'
      ) : (
        <a href={`${REPO}/commit/${cert.commit}`}>commit {cert.commit} ↗</a>
      ),
    ],
  ]
  return (
    <div className="cert">
      <div className="ex-head" style={{ borderBottomColor: 'var(--rule)', paddingBottom: 8, marginBottom: 8 }}>
        <span className="u">Solver certificate</span>
        <span className="links">
          {onRerun && (
            <button className="btn ghost" onClick={onRerun} disabled={busy}>
              {busy ? 'Solving…' : 'Re-solve now ↻'}
            </button>
          )}
          <button className="btn ghost" onClick={download}>
            JSON ↓
          </button>
        </span>
      </div>
      {rows.map(([k, v]) => (
        <div key={k} className="cert-row">
          <span className="faint">{k}</span>
          <span>{v}</span>
        </div>
      ))}
    </div>
  )
}

/** Every constraint of the mandate: plain wording, formal form, actual vs limit, result. */
export function Checks({ checks, rules }) {
  const byId = Object.fromEntries(rules.map((r) => [r.id, r]))
  return (
    <div className="scroll">
      <table className="tbl">
        <thead>
          <tr>
            <th>ID</th>
            <th>Constraint</th>
            <th className="hide-sm">Formal</th>
            <th className="r">Actual</th>
            <th className="r">Limit</th>
            <th className="r">Result</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((c) => (
            <tr key={c.rule_id}>
              <td className="faint">{c.rule_id}</td>
              <td>{byId[c.rule_id]?.source.replace(/\.$/, '')}</td>
              <td className="hide-sm nw muted">{byId[c.rule_id] && formal(byId[c.rule_id])}</td>
              <td className={`r nw ${c.passed ? '' : 'bad'}`}>{fmtActual(c)}</td>
              <td className="r nw muted">{fmtLimit(c)}</td>
              <td className={`r nw ${c.passed ? 'good' : 'bad'}`}>{c.passed ? 'OK' : 'VIOLATED'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Before -> after weights, sorted by how much each position moved. */
export function WeightsDiff({ before, after, beforeLabel = 'Draft', afterLabel = 'Repaired' }) {
  const tickers = [...new Set([...Object.keys(before), ...Object.keys(after)])]
  const rows = tickers
    .map((t) => ({ t, a: before[t] ?? 0, b: after[t] ?? 0 }))
    .filter((r) => r.a > 1e-4 || r.b > 1e-4)
    .sort((x, y) => Math.abs(y.b - y.a) - Math.abs(x.b - x.a))
  const max = Math.max(...rows.map((r) => Math.max(r.a, r.b)), 0.01)
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Ticker</th>
          <th className="r">{beforeLabel}</th>
          <th className="r">{afterLabel}</th>
          <th className="r">Δ</th>
          <th className="hide-sm" style={{ width: '30%' }} />
        </tr>
      </thead>
      <tbody>
        {rows.map(({ t, a, b }) => (
          <tr key={t}>
            <td>{t}</td>
            <td className="r muted">{a > 1e-4 ? pct(a) : '—'}</td>
            <td className="r">{b > 1e-4 ? pct(b) : '—'}</td>
            <td className="r nw">{`${b - a >= 0 ? '+' : '−'}${(Math.abs(b - a) * 100).toFixed(1)}`}</td>
            <td className="hide-sm">
              <div className="wbar">
                <i style={{ width: `${(a / max) * 100}%` }} />
                <i style={{ width: `${(b / max) * 100}%` }} />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
