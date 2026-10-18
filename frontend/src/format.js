// Small formatting helpers shared by every screen.

export const pct = (x, digits = 1) => `${(x * 100).toFixed(digits)}%`

export const displayName = (name) => name.replace(/\s*\(synthetic\)\s*$/i, '')

export const isSynthetic = (name) => /\(synthetic\)/i.test(name)

const COUNT_TYPES = new Set(['max_holdings', 'min_holdings'])

/** Format a check's actual / limit: counts as integers, everything else as a percentage. */
export const fmtCheckValue = (type, x) => (COUNT_TYPES.has(type) ? `${Math.round(x)}` : pct(x))

/** Sorted [ticker, weight] pairs, biggest first, skipping zeros. */
export const sortedWeights = (weights = {}) =>
  Object.entries(weights)
    .filter(([, w]) => w > 1e-9)
    .sort((a, b) => b[1] - a[1])

export const AGENTS = {
  macro: { label: 'Macro', short: 'MA' },
  fundamentals: { label: 'Fundamentals', short: 'FU' },
  risk: { label: 'Risk', short: 'RI' },
  chair: { label: 'Chair', short: 'CH' },
  referee: { label: 'Referee', short: 'RF' },
}

export const VERDICTS = {
  PASS: { label: 'Pass', tone: 'pass', headline: 'Every rule passes' },
  VIOLATIONS_REPAIRED: { label: 'Violations repaired', tone: 'fail', headline: 'Rules broken — repaired' },
  RULES_INFEASIBLE: { label: 'Rules infeasible', tone: 'warn', headline: "These rules can't all hold" },
  ERROR: { label: 'Error', tone: 'fail', headline: 'The Referee could not check this' },
}
