# The feedback experiment

*Provider: gemini, model: gemini-3.5-flash-lite (the only model: no fallback) (temperature 0.7). Clients: C10, C11, C12, C13, C17, C21, C23, C91, C93, C94. Feedback wording: Referee explain sentences use 'minimum'/'maximum' (fixed 2026-10-17; the earlier asi1 run on C91-C94 used 'limit').*

20 client-trials; 16 first drafts broke ≥1 rule. 95% bootstrap CIs in brackets.

| Condition | Round 0 | Round 1 | Round 2 | Round 3 | Capital moved |
|---|---|---|---|---|---|
| A. Self-check (compliance) | 20% [5, 40] | 20% [5, 40] | 20% [5, 40] | 20% [5, 40] | 14% [8, 20] |
| B. Bare verdict (compliance) | 20% [5, 40] | 25% [10, 45] | 25% [10, 45] | 25% [10, 45] | 22% [15, 29] |
| C. Explained (compliance) | 20% [5, 40] | 25% [10, 45] | 25% [10, 45] | 25% [10, 45] | 18% [12, 24] |

| Condition | Round 0 | Round 1 | Round 2 | Round 3 |
|---|---|---|---|---|
| A. Self-check | 1.10 broken, 10.4 pp | 1.00 broken, 8.9 pp | 1.10 broken, 9.8 pp | 1.10 broken, 10.4 pp |
| B. Bare verdict | 1.10 broken, 10.4 pp | 1.10 broken, 9.1 pp | 1.15 broken, 8.9 pp | 1.10 broken, 8.5 pp |
| C. Explained | 1.10 broken, 10.4 pp | 1.30 broken, 9.0 pp | 1.35 broken, 9.2 pp | 1.35 broken, 6.0 pp |

**C vs B** (rounds to compliance): C fewer 1, same 18, more 1; sign test p = 1.000

**C vs A** (rounds to compliance): C fewer 1, same 19, more 0; sign test p = 1.000

## Finding

Out of 20 client-trials, 16 first drafts broke at least one rule. After 3 rounds of revision, compliance was 20% with self-check, 25% with the bare verdict and 25% with the explained feedback. Explained feedback reached compliance in fewer rounds than bare in 1, the same in 18 and more in 1 client-trials (sign test p = 1.000); versus self-check: 1 / 19 / 0 (p = 1.000).

## Plain-English finding (written from the numbers above)

- **Complete, clean run:** all 20 client-trials finished; all 208 LLM calls were answered by
  gemini-3.5-flash-lite (no fallback, no failed calls; 38 rate-limit waits).
- **The AI almost never fixes its own rule breaks, whatever feedback it gets.** 16 of 20 first drafts
  broke a rule. After 3 rounds, only 2 of those 16 had become compliant: one with the explained
  feedback (C17 t2) and one with the bare verdict (C91 t2). Self-check fixed none.
- **Explained ≈ bare here.** Final compliance was 20% (self-check), 25% (bare), 25% (explained), with
  wide, overlapping confidence intervals. Rounds-to-compliance: explained vs bare 1 better / 18 same /
  1 worse (sign test p = 1.0). No significant difference between any two conditions.
- One possible pattern, too small to claim: with explained feedback the total size of the violations
  shrank the most by round 3 (6.0 pp vs 8.5 bare vs 10.4 self-check), but the number of broken rules
  went up (1.35 vs 1.10): the model fixed the big breach and broke smaller rules doing it.
- **What this means for SwarmFolio:** feedback alone did not make this model follow the rules, so the
  Referee's own repair (the nearest compliant portfolio) is what guarantees compliance.
