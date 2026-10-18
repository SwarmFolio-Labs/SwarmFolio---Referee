// Turn a saved CommitteeResult into timeline steps.

/** Pair each log entry with the proposal weights / receipt it refers to, when we have them. */
export function buildSteps(result) {
  const extras = result.extras ?? {}
  const lastRound = Math.max(...result.debate_log.map((e) => e.round))
  return result.debate_log.map((entry, i) => {
    const step = { ...entry, key: i }
    if (entry.kind === 'proposal') {
      step.weights = extras.proposals?.[entry.round - 1]
    }
    if (entry.kind === 'receipt') {
      step.receipt =
        extras.receipts?.[entry.round - 1] ??
        (entry.round === 1 ? result.first_receipt : entry.round === lastRound ? result.receipt : null)
    }
    return step
  })
}
