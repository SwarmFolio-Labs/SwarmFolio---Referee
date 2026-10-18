// The experiment's three feedback conditions (MASTER 10.3). Colors are --chart-* tokens.
export const CONDITIONS = [
  { id: 'self', label: 'A. Self-check', blurb: '"Re-check your portfolio against the rules." No Referee info.', color: 'var(--chart-self)' },
  { id: 'bare', label: 'B. Bare verdict', blurb: 'Which rules failed, in the client\'s words. No numbers.', color: 'var(--chart-bare)' },
  { id: 'explained', label: 'C. Explained', blurb: 'The Referee\'s sentences: actual vs limit, plus any conflict.', color: 'var(--chart-explained)' },
]
