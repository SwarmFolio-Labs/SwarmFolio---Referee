// Screen B: the Referee's receipt, printed on receipt paper with the ink stamp. Broken rules first (the client's
// words, actual vs limit), then every passed rule, the holdings that changed, capital moved and Sharpe.
// The side panel explains it and holds the actions; on phones the actions become a sticky bar.
import { useRef, useState } from 'react'
import { displayName, fmtActual, fmtLimit, isSynthetic, numberWord, pct, ruleSubject } from '../format.js'
import ConflictPanel from './ConflictPanel.jsx'
import Stamp from './Stamp.jsx'

const broken = (r) => r.checks.filter((c) => !c.passed)

function stampSub(r) {
  const n = r.checks.length
  if (r.verdict === 'PASS') return `${n} of ${n} hold`
  if (r.verdict === 'VIOLATIONS_REPAIRED') return `${broken(r).length} of ${n} · ${pct(r.capital_moved)} moved`
  if (r.verdict === 'RULES_INFEASIBLE') return `${r.conflict_set.length} rules can't all hold`
  return null
}

function Summary({ r }) {
  const b = (x, tone = '') => <span className={`num font-semibold ${tone}`}>{x}</span>
  if (r.verdict === 'VIOLATIONS_REPAIRED') {
    return (
      <>
        The proposal broke {b(`${broken(r).length} of ${r.checks.length}`, 'text-fail')} rules. The nearest compliant
        portfolio moves {b(pct(r.capital_moved))} of capital and changes Sharpe from {b(r.sharpe_before.toFixed(2))} to{' '}
        {b(r.sharpe_after.toFixed(2))}.
      </>
    )
  }
  if (r.verdict === 'PASS') {
    return (
      <>
        The proposal follows all {b(r.checks.length, 'text-pass')} rules. Sharpe {b(r.sharpe_after.toFixed(2))}, volatility{' '}
        {b(pct(r.vol_after))}. Nothing had to move.
      </>
    )
  }
  return r.summary
}

function Head({ tone, title, right = 'Actual · limit' }) {
  return (
    <div className={`flex items-baseline justify-between border-b border-ink pb-2 ${tone}`}>
      <span className="label !text-current">{title}</span>
      <span className="label hidden sm:inline">{right}</span>
    </div>
  )
}

function Changes({ before, after, beforeLabel, afterLabel }) {
  const rows = [...new Set([...Object.keys(before), ...Object.keys(after)])]
    .map((t) => ({ t, a: before[t] ?? 0, b: after[t] ?? 0 }))
    .filter((x) => x.a > 1e-9 || x.b > 1e-9)
    .sort((x, y) => Math.abs(y.b - y.a) - Math.abs(x.b - x.a))
  const changed = rows.filter((x) => Math.abs(x.b - x.a) >= 5e-4)
  if (changed.length === 0) return null
  const unchanged = rows.length - changed.length
  return (
    <table data-field="holdings-changed" className="w-full text-sm">
      <thead>
        <tr className="border-b border-ink text-right">
          <th className="label py-2 text-left">Holdings changed</th>
          <th className="label py-2">{beforeLabel}</th>
          <th className="label py-2">{afterLabel}</th>
          <th className="label py-2">Change</th>
        </tr>
      </thead>
      <tbody>
        {changed.map(({ t, a, b }) => (
          <tr key={t} data-ticker={t} className="border-b border-line bg-warn-tint text-right">
            <td className="num px-2 py-2 text-left">{t}</td>
            <td className="num py-2 text-muted">{a > 1e-9 ? pct(a) : 'new'}</td>
            <td className="num py-2 font-semibold">{b > 1e-9 ? pct(b) : 'sold'}</td>
            <td className="num px-2 py-2 text-warn-text">{`${b > a ? '+' : '−'}${(Math.abs(b - a) * 100).toFixed(1)}`}</td>
          </tr>
        ))}
        {unchanged > 0 && (
          <tr className="border-b border-line">
            <td colSpan={4} className="px-2 py-2 text-ui text-muted">{unchanged} other holding{unchanged > 1 ? 's' : ''} unchanged</td>
          </tr>
        )}
      </tbody>
    </table>
  )
}

/**
 * receipt: a Receipt from the API. rules/client: for the client's own words and name.
 * before/after: the weights the "holdings changed" table compares (default after: the Referee's repair).
 * variant: "printed" (default, torn receipt paper) or "card"; rendered as data-variant.
 */
export default function ReceiptCard({
  receipt,
  rules = [],
  client,
  before,
  after,
  beforeLabel = 'Before',
  afterLabel = 'After',
  headline,
  onBack,
  onEdit,
  variant = 'printed',
}) {
  const [copied, setCopied] = useState(false)
  const paper = useRef(null)
  const r = receipt
  const ruleById = Object.fromEntries(rules.map((x) => [x.id, x]))
  const conflict = new Set(r.conflict_set)
  const failed = broken(r)
  const passed = r.checks.filter((c) => c.passed)
  const changesAfter = after ?? r.repaired_weights
  const name = client ? displayName(client.name) : r.client_id
  const quote = (id) => `“${(ruleById[id]?.source ?? id).replace(/\.$/, '')}”`
  const time = r.timestamp.replace('T', ' ').replace(/:\d\dZ$/, ' UTC')

  const copy = async () => {
    await navigator.clipboard.writeText(r.receipt_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  const share = async () => {
    const text = `Referee receipt ${r.receipt_id}: ${r.summary}`
    if (navigator.share) await navigator.share({ title: `Referee receipt ${r.receipt_id}`, text, url: window.location.href }).catch(() => {})
    else await copy()
  }

  // Print only the paper: mark it, hide everything else via the print stylesheet in index.css.
  const print = () => {
    const el = paper.current
    const path = []
    for (let p = el.parentElement; p; p = p.parentElement) path.push(p)
    el.setAttribute('data-print-target', '')
    path.forEach((p) => p.setAttribute('data-print-path', ''))
    document.body.classList.add('printing-receipt')
    const done = () => {
      el.removeAttribute('data-print-target')
      path.forEach((p) => p.removeAttribute('data-print-path'))
      document.body.classList.remove('printing-receipt')
      window.removeEventListener('afterprint', done)
    }
    window.addEventListener('afterprint', done)
    window.print()
  }

  const title =
    headline ??
    (r.verdict === 'VIOLATIONS_REPAIRED'
      ? `The Referee fixed ${numberWord(failed.length)} broken rule${failed.length === 1 ? '' : 's'} with the smallest change it could find.`
      : r.verdict === 'PASS'
        ? 'Every rule holds. The Referee signed off without moving a thing.'
        : r.verdict === 'RULES_INFEASIBLE'
          ? "These rules can't all hold, so the Referee stops instead of guessing."
          : 'The Referee could not check this proposal.')

  return (
    <div data-component="receipt" data-variant={variant} data-verdict={r.verdict} className="grid items-start gap-10 pb-28 md:pb-0 lg:grid-cols-receipt lg:gap-20">
      <div
        ref={paper}
        data-component="receipt-paper"
        data-variant={variant}
        className="relative -mx-6 border border-line bg-surface px-6 pb-8 pt-8 sm:mx-0 sm:px-12 sm:pt-11"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="label">Referee receipt</div>
            <div className="mt-1 font-display text-2xl font-semibold sm:text-5xl">
              {r.client_id} · {name}
            </div>
            {client && isSynthetic(client.name) && <div className="mt-1 font-display text-md italic text-muted">synthetic client</div>}
            <div className="num mt-3 flex flex-col gap-x-6 text-xs text-muted sm:flex-row">
              <span>No. {r.receipt_id}</span>
              <span>{time}</span>
            </div>
          </div>
          <Stamp verdict={r.verdict} sub={stampSub(r)} />
        </div>

        <div className="my-6 border-t border-dashed border-perforation" />
        <p className="font-display text-xl">
          <Summary r={r} />
        </p>

        {!r.rules_feasible && (
          <div className="mt-8">
            <ConflictPanel
              explain={r.conflict_explain}
              relaxations={r.cheapest_relaxation}
              conflictSet={r.conflict_set}
              rules={rules}
              checks={r.checks}
              clientName={client?.name}
              clientStory={client?.story}
            />
          </div>
        )}

        {failed.length > 0 && r.rules_feasible && (
          <section className="mt-8">
            <Head tone="text-fail" title={`Broken · ${failed.length}`} />
            <ul>
              {failed.map((c) => (
                <li key={c.rule_id} data-component="rule-check" data-passed="false" data-rule-type={c.type} title={c.explain} className="grid gap-1 border-b border-line py-4 sm:grid-cols-receipt-row sm:items-baseline">
                  <div>
                    <div className="font-display text-lg italic">{quote(c.rule_id)}</div>
                    {ruleSubject(ruleById[c.rule_id]) && <div className="mt-1 text-xs text-muted">{ruleSubject(ruleById[c.rule_id])}</div>}
                  </div>
                  <div className="num flex items-baseline justify-end gap-6 text-right">
                    <span data-field="actual" className="text-lg font-semibold text-fail">{fmtActual(c)}</span>
                    <span data-field="limit" className="text-ui text-muted">{fmtLimit(c)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {passed.length > 0 && (
          <section className="mt-8">
            <Head tone="text-pass" title={`Passed · ${passed.length}`} right="" />
            <ul>
              {passed.map((c) => (
                <li key={c.rule_id} data-component="rule-check" data-passed="true" data-rule-type={c.type} title={c.explain} className="flex flex-col gap-0.5 border-b border-line py-2 sm:flex-row sm:items-baseline sm:gap-3">
                  <span className="flex items-baseline gap-3">
                    <span className="h-1.5 w-1.5 shrink-0 self-center rounded-full bg-pass" />
                    <span className={`font-display text-md italic ${conflict.has(c.rule_id) ? 'text-warn-text' : ''}`}>{quote(c.rule_id)}</span>
                  </span>
                  <span className="num pl-4 text-xs text-muted sm:ml-auto sm:pl-0">
                    {c.type === 'exclude' ? 'none held' : <>{fmtActual(c)} · {fmtLimit(c)}</>}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {before && changesAfter && (
          <section className="mt-8">
            <Changes before={before} after={changesAfter} beforeLabel={beforeLabel} afterLabel={afterLabel} />
          </section>
        )}

        {r.rules_feasible && (
          <dl className="mt-2 border-b-3 border-double border-ink px-2 text-sm">
            <div className="flex justify-between py-2">
              <dt className="font-semibold">Capital moved</dt>
              <dd className="num text-lg font-semibold">{pct(r.capital_moved)}</dd>
            </div>
            <div className="flex justify-between py-2">
              <dt className="font-semibold">Sharpe ratio</dt>
              <dd className="num text-lg font-semibold">
                {r.sharpe_before.toFixed(2)} → {r.sharpe_after.toFixed(2)}
              </dd>
            </div>
          </dl>
        )}

        {(r.dust_removed.length > 0 || r.notes.length > 0) && (
          <ul className="mt-4 grid gap-1 text-xs text-muted">
            {r.dust_removed.length > 0 && <li>Dust removed (under 0.5%): {r.dust_removed.join(', ')}</li>}
            {r.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}

        <div className="mt-10 flex items-end justify-between gap-6">
          <p className="num text-2xs text-muted">
            Checked by an exact solver (CVXPY + SCIP).
            <br />
            Same inputs → same receipt id.
          </p>
          <div className="hidden w-40 border-t border-ink pt-1 text-right text-2xs text-muted sm:block">Advisor signature</div>
        </div>
      </div>

      <aside className="no-print grid gap-8">
        <h2 className="hidden font-display text-4xl font-semibold tracking-snug md:block">{title}</h2>
        <ol className="hidden border-t border-ink md:block">
          {[
            ['In the client\'s own words', `Every rule is quoted exactly as ${name} said it, next to the actual value and the limit.`],
            r.verdict === 'RULES_INFEASIBLE'
              ? ['The cheapest way out', 'The solver finds the smallest change to one rule that makes the rest possible. A person has to approve it.']
              : ['The nearest compliant portfolio', 'An exact solver moved as little money as possible. Only the highlighted rows changed.'],
            ['Reproducible', 'The receipt id is a fingerprint of the inputs. Run it again and you get the same id.'],
          ].map(([h, t], i) => (
            <li key={h} className="flex gap-6 border-b border-line py-5">
              <span className="num text-xs text-muted">{String(i + 1).padStart(2, '0')}</span>
              <div>
                <div className="text-md font-semibold">{h}</div>
                <p className="mt-1 text-ui text-muted">{t}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="hidden flex-wrap gap-2.5 md:flex">
          <button className="btn-primary" onClick={print}>Print receipt</button>
          <button className="btn-ghost border-line bg-surface" onClick={copy}>
            {copied ? 'Copied' : 'Copy id'} <span className="num text-xs text-muted">{r.receipt_id}</span>
          </button>
          {onEdit && r.verdict === 'RULES_INFEASIBLE' && <button className="btn-ghost" onClick={onEdit}>Edit the rules</button>}
        </div>
        {onBack && (
          <button className="hidden text-left text-sm underline underline-offset-4 md:block" onClick={onBack}>
            ← Back to the committee run
          </button>
        )}
        <div className="fixed inset-x-0 bottom-0 z-10 flex gap-2.5 border-t border-line bg-surface p-4 md:hidden">
          <button className="btn-primary flex-1 py-3" onClick={share}>Share receipt</button>
          <button className="btn-ghost border-line py-3" onClick={copy}>{copied ? 'Copied' : 'Copy id'}</button>
        </div>
      </aside>
    </div>
  )
}
