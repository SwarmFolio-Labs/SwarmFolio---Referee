// Small formatting helpers shared by every screen.

export const pct = (x, digits = 1) => `${(x * 100).toFixed(digits)}%`

export const displayName = (name) => name.replace(/\s*\(synthetic\)\s*$/i, '')

export const isSynthetic = (name) => /\(synthetic\)/i.test(name)

const COUNT_TYPES = new Set(['max_holdings', 'min_holdings'])

/** Format a check's actual / limit: counts as integers, everything else as a percentage. */
export const fmtCheckValue = (type, x) => (COUNT_TYPES.has(type) ? `${Math.round(x)}` : pct(x))

// Rules whose limit is a floor (mirrors FLOOR_RULES in referee/check.py); every other limit is a cap.
const FLOOR_TYPES = new Set(['min_weight', 'sector_min', 'min_holdings', 'buy_in'])

/** A check's limit as the design shows it: "min 10.0%", "max 20.0%", or "none held" for exclusions. */
export const fmtLimit = (check) =>
  check.type === 'exclude' ? 'none held' : `${FLOOR_TYPES.has(check.type) ? 'min' : 'max'} ${fmtCheckValue(check.type, check.limit)}`

/** A check's actual value; for exclusions "none held" when nothing excluded is held. */
export const fmtActual = (check) =>
  check.type === 'exclude' && check.actual < 1e-9 ? 'none held' : fmtCheckValue(check.type, check.actual)

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

// The Referee ends conflict_explain with the proof in parentheses, e.g. "(30% + 10% = 40% > 35%)".
const ARITHMETIC = /\s*\(([^()]*[=<>][^()]*)\)\s*\.?\s*$/

export function splitConflict(explain = '') {
  const m = explain.match(ARITHMETIC)
  return m ? { sentence: explain.slice(0, m.index).trim(), arithmetic: m[1].trim() } : { sentence: explain, arithmetic: null }
}

/** "his" / "her" / "their" from the client's title, for headings like "His 8 rules". */
export function pronoun(name = '', story = '') {
  if (/^mr\.?\s/i.test(name)) return 'his'
  if (/^(ms|mrs|miss)\.?\s/i.test(name)) return 'her'
  // "Dr." and first names: fall back to how the client's story refers to them.
  const her = (story.match(/\b(her|she)\b/gi) ?? []).length
  const his = (story.match(/\b(his|he|him)\b/gi) ?? []).length
  return her > his ? 'her' : his > her ? 'his' : 'their'
}

const WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']

/** 3 → "three" (up to ten), for sentences like "Three of her rules can't all be true at once." */
export const numberWord = (n) => WORDS[n] ?? String(n)

/** What a rule is about, for the receipt's small print: "JNJ", "Healthcare", "XOM, CVX" (or null). */
export function ruleSubject(rule) {
  const p = rule?.params ?? {}
  if (p.ticker && p.ticker !== '*') return p.ticker
  if (p.sector) return p.sector
  if (p.tickers) return p.tickers.join(', ')
  return null
}
