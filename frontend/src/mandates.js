// Display vocabulary. The data files keep their original ids (C04 ...) so receipts and tests stay stable;
// the site presents each synthetic client as a mandate, named by what makes it hard to satisfy.

const NAMES = {
  C01: 'Retirement saver with a tech tilt',
  C02: 'Fossil-fuel exclusion, legacy JNJ',
  C03: 'Fossil-fuel exclusion, two inherited blocks',
  C04: 'Concentrated tech executive',
  C10: 'Low-volatility healthcare tilt',
  C11: 'Tech tilt over existing NVDA exposure',
  C12: 'Short list of banks and household brands',
  C13: 'Concentrated, with risk guardrails',
  C14: 'Ten-constraint values mandate',
  C15: 'Big-tech holder, tax-constrained exit',
  C16: 'Financials-heavy, no investment banks',
  C17: 'Four-sector balance, compact book',
  C18: 'Inherited energy book, staged exit',
  C19: 'Income retiree, staples and bonds',
  C20: 'Equal-sized conviction book',
  C21: 'Consolidate ten small positions',
  C22: 'Healthcare exclusion (conflict of interest)',
  C23: 'Pension rebalance under a trading budget',
  C24: 'Gold required, no Treasuries',
  C25: 'Heavy tech under a volatility cap',
  C26: 'Broad diversification, minimum position size',
  C27: 'Tech de-concentration with a tax budget',
  C91: 'Low volatility, tech and healthcare required',
  C92: 'Concentrated ex-Google holder, taxed exit',
  C93: 'Old-economy balance, at most six names',
  C94: 'Family trust with a JNJ/UNH block',
}

/** "C04" -> "M-04" */
export const mandateId = (clientId) => `M-${clientId.slice(1)}`

export const mandateName = (client) =>
  NAMES[client.client_id] ?? client.name.replace(/\s*\(synthetic\)\s*$/i, '')

// pct: tables (always one decimal, so columns line up); lim: limits in formal notation ("40%", "10.5%")
const pct = (x) => `${(x * 100).toFixed(1)}%`
const lim = (x) => `${+(x * 100).toFixed(1)}%`

/** A constraint in formal notation, e.g. "Σ w[Tech] ≤ 40%". */
export function formal(rule) {
  const p = rule.params
  switch (rule.type) {
    case 'max_weight':
      return p.ticker === '*' ? `wᵢ ≤ ${lim(p.max)}  ∀i` : `w[${p.ticker}] ≤ ${lim(p.max)}`
    case 'min_weight':
      return `w[${p.ticker}] ≥ ${lim(p.min)}`
    case 'sector_max':
      return `Σ w[${p.sector}] ≤ ${lim(p.max)}`
    case 'sector_min':
      return `Σ w[${p.sector}] ≥ ${lim(p.min)}`
    case 'max_volatility':
      return `‖Lᵀw‖₂ ≤ ${lim(p.max)}`
    case 'max_turnover':
      return `‖w − w₀‖₁ ≤ ${lim(p.max)}`
    case 'min_holdings':
      return `Σ zᵢ ≥ ${p.k}`
    case 'max_holdings':
      return `Σ zᵢ ≤ ${p.k}`
    case 'buy_in':
      return `wᵢ ≥ ${lim(p.min)}·zᵢ`
    case 'exclude':
      return `w[${p.tickers.join(', ')}] = 0`
    default:
      return rule.type
  }
}

const COUNT = new Set(['max_holdings', 'min_holdings'])
const FLOOR = new Set(['min_weight', 'sector_min', 'min_holdings', 'buy_in'])

/** A check's actual value as shown in tables. */
export const fmtActual = (c) =>
  c.type === 'exclude' ? (c.actual < 1e-9 ? 'none' : pct(c.actual)) : COUNT.has(c.type) ? `${Math.round(c.actual)}` : pct(c.actual)

/** A check's limit with its direction, e.g. "≤ 40%". */
export const fmtLimit = (c) =>
  c.type === 'exclude' ? '= 0' : `${FLOOR.has(c.type) ? '≥' : '≤'} ${COUNT.has(c.type) ? Math.round(c.limit) : pct(c.limit)}`

export const VERDICT = {
  PASS: 'COMPLIANT',
  VIOLATIONS_REPAIRED: 'VIOLATED · REPAIRED',
  RULES_INFEASIBLE: 'INFEASIBLE · PROVEN',
  ERROR: 'ERROR',
}

export { pct }
