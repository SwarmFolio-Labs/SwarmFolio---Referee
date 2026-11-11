// Building blocks for anything the verifier computes live: the request hook, the solver
// certificate, the verdict chip and the constraint table.
import { useCallback, useEffect, useState } from 'react'
import { fmtActual, fmtLimit, formal, VERDICT } from '../mandates.js'
import { Gauge } from './Figures.jsx'

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

/** While a request is in flight: a status line that admits when the free server is waking. */
export function Pending({ busy, error }) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!busy) return
    const t = setTimeout(() => setSlow(true), 4000)
    return () => {
      clearTimeout(t)
      setSlow(false)
    }
  }, [busy])
  if (error)
    return (
      <p className="status">
        <span className="dot bad" /> Verifier unreachable: {error}
      </p>
    )
  if (!busy) return null
  return (
    <p className="status muted">
      <span className="dot busy" />
      {slow ? 'Waking the solver server (free hosting tier, up to ~50 s)…' : 'Solving…'}
    </p>
  )
}

/** "Solved live 2.1 s ago" style indicator for a case header. */
export function LiveChip({ busy, cert }) {
  return (
    <span className="chip accent">
      <span className={`dot ${busy ? 'busy' : ''}`} />
      {busy ? 'Solving' : cert ? `Solved live · ${cert.solver_ms} ms` : 'Live'}
    </span>
  )
}

export function Verdict({ receipt }) {
  const ok = receipt.verdict === 'PASS'
  return (
    <span className="chip" style={{ borderColor: ok ? 'var(--good)' : 'var(--bad)' }}>
      <span className={`dot ${ok ? '' : 'bad'}`} />
      {VERDICT[receipt.verdict] ?? receipt.verdict}
    </span>
  )
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
      download: `certus-${receipt.client_id}-${cert.input_sha256.slice(0, 8)}.json`,
    })
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const rows = [
    ['computed', `${cert.verified_at.replace('T', ' ').replace('Z', ' UTC')} · ${cert.wall_ms} ms on the server`],
    [
      'solver',
      `SCIP ${cert.versions.scip} via CVXPY ${cert.versions.cvxpy} · ${cert.solves.length} solve${cert.solves.length === 1 ? '' : 's'} · ${cert.solver_ms} ms`,
    ],
    ['model', m ? `${m.variables} variables (${m.binaries} binary) · ${m.constraints} constraint blocks` : '—'],
    ['status', statuses],
    ['input', `sha256 ${short(cert.input_sha256)}`],
    ['output', `sha256 ${short(cert.output_sha256)}`],
    ['code', cert.commit === 'local' ? 'local build' : <a href={`${REPO}/commit/${cert.commit}`}>commit {cert.commit} ↗</a>],
  ]
  return (
    <div className="cert">
      <div className="cert-head">
        <span className="label" style={{ color: 'var(--accent)' }}>
          Certus · solver certificate
        </span>
        <span style={{ display: 'flex', gap: 8 }}>
          {onRerun && (
            <button className="btn sm" onClick={onRerun} disabled={busy}>
              {busy ? 'Solving…' : 'Re-solve now ↻'}
            </button>
          )}
          <button className="btn ghost sm" onClick={download}>
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
            <th className="hide-sm" />
            <th className="r">Actual</th>
            <th className="r">Limit</th>
            <th className="r">Result</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((c) => (
            <tr key={c.rule_id}>
              <td className="num faint">{c.rule_id}</td>
              <td>{byId[c.rule_id]?.source.replace(/\.$/, '')}</td>
              <td className="hide-sm nw num muted" style={{ fontSize: 12.5 }}>
                {byId[c.rule_id] && formal(byId[c.rule_id])}
              </td>
              <td className="hide-sm">
                <Gauge check={c} />
              </td>
              <td className="r nw num" style={c.passed ? undefined : { fontWeight: 600 }}>
                {fmtActual(c)}
              </td>
              <td className="r nw num muted">{fmtLimit(c)}</td>
              <td className="r">
                <span className="status">
                  <i style={{ color: c.passed ? 'var(--good)' : 'var(--bad)' }}>{c.passed ? '✓' : '✕'}</i>
                  {c.passed ? 'OK' : 'VIOLATED'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
