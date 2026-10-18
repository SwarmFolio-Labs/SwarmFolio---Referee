# ABORTED run: not a result

asi1-mini experiment on C10–C24 + C91–C94 (3 trials, concurrency 6), started 2026-10-17 21:04 PT.
ASI:One returned "rate limit exceeded" (asi1-mini, limit 100) after 274 successful calls.
48 of 57 client-trials failed; of the 9 that finished, one had a failed revision that the code
(at the time) wrongly scored as "no progress". **Do not use these numbers.** Kept only as a record.
Fixed afterwards: any failed LLM call now fails the whole client-trial, so it is excluded, never scored.
