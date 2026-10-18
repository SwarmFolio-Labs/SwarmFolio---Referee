# SwarmFolio Referee: design export

Final frames from the Paper file **"SwarmFolio Referee"** (Direction A, "Research report").
Brief: `design/BRIEF.md`. Tokens: `design/tokens.css`.

Each frame comes in two files in `frames/`:

- **`.png`**: the screenshot. Desktop frames are 1×; phone frames and the component are 2×.
- **`.html`**: static HTML with inline styles. It loads `../tokens.css` and the Google Fonts it needs, so you can open it in a browser. Treat it as a reference for spacing, type and color, not as production code.

## Frames → app

| Frame | Files (`frames/…`) | App screen / component | Notes |
|---|---|---|---|
| Screen A · Committee run (C04), 1440 | `screen-a-committee-run` | `pages/ClientPage.jsx` (run result): header, `DebateTimeline.jsx` (3 round columns), `WeightsChart.jsx` ("From stock grants to a balanced book", before → after), "Every rule, checked" list, COMPLIANT stamp | Hero screen. Round tally ●● → ●●● → ○ sits in the header. |
| Screen B · Receipt (C02), 1440 | `screen-b-receipt` | `components/ReceiptView.jsx` (the printed receipt) plus the side notes and actions on its page | Torn edge, dashed rules, REPAIRED stamp, broken rules as ACTUAL · LIMIT, passed rules with their actual value, changed rows highlighted. |
| Screen C · Impossible client (C03), 1440 | `screen-c-impossible` | `ReceiptView.jsx`, infeasible state (`conflict_set`, `cheapest_relaxation`) | Ochre NEEDS APPROVAL stamp (a pending decision, not an error). The conflict bar shows the 5.0% of room left and the 5.0 points over. Primary action: "Ask the advisor to approve". |
| Screen D · Client picker, 1440 | `screen-d-client-picker` | `pages/ClientsPage.jsx` + `components/RuleChip.jsx` | Demo clients first (C04, C02, C03, C91), then the rest. One action per client; only C04's is filled. **Build note in the frame:** rule chips must use each client's real `source` text from `data/clients/*.json`, word for word. |
| Screen E · Price tags (C04), 1440 | `screen-e-price-tags` | `components/PriceTags.jsx` (Price tags tab) | Ranked bars, and "5 of his 8 rules cost nothing" shown as good news. Units: points of **risk-adjusted** return (mean-variance utility) per year. |
| State · Committee thinking (C04), 1440 | `state-committee-thinking` | `ClientPage.jsx` while the run is in flight (`TryReferee.jsx` / run hook) | Round progress (round 2 of up to 3, a 3-segment bar, elapsed vs about 0:25) and a "Who is working" list: done ●, working (ring on an ochre row), waiting (dashed). Round 3 is shown as a dashed placeholder. |
| Component · Stance states | `component-stance-states` | Stance row inside `DebateTimeline.jsx` | Concede ● / Defend ■ / Modify ◆, always with a text label. Text wraps freely (up to about 240 characters, no clamping). Missing analyst: dashed hollow dot, muted italic. |
| Phone A · Committee run (C04), 390 | `phone-a-committee-run@2x` | `ClientPage.jsx` below the `md` breakpoint | Rounds stack vertically with a colored left rail. The action bar ("Open the receipt") sticks to the bottom. |
| Phone B · Receipt (C02), 390 | `phone-b-receipt@2x` | `ReceiptView.jsx` below `md` | Broken rules: quote on its own line, label plus values underneath. Sticky action bar: "Share receipt" / "Copy id". |

## System rules (from the brief, applied everywhere)

- **Type:** Newsreader for headings and client quotes (quotes in italic, *and numbers inside quotes stay in the serif*, because they're the client's voice). IBM Plex Sans for the UI. IBM Plex Mono for every measured value (actual, limit, Sharpe, weights, ids), including inside sentences.
- **Color means something or isn't used:** pass = moss, broken = brick, repaired / needs approval / modify = ochre. Color never stands alone: there's always a label, and stances also get a shape.
- **Limits** are written as `min 30.0%` / `max 14.0%` next to the actual value.
- **Contrast:** all small grey text is at least WCAG AA (`--color-muted` / `--color-faint`).
- **Motion (to build):** rounds reveal one after another, and the stamp "thunks" in at the end (scale 1.15 → 1, slight rotation). Nothing bouncy.

## Data caveats (to replace from live runs)

- Screen B / Phone B: the brief gives C02's receipt numbers (54411b07eaf4, 2 of 7 broken, 3.9% moved, Sharpe 1.72 → 1.74). The **passed-rule actuals** (Healthcare 34.1%, 8 holdings, volatility 15.8%) and the timestamp are placeholders, because no saved receipt for that run exists yet. "Others, pro rata −3.9" is inferred from the totals.
- Screen A: the Chair drafts and analyst stances are illustrative copy written to match the brief's round summary. Turnover 43.3% and Tech 39.3% were computed from C04's `current_weights` and the final weights, using the Referee's turnover formula and `data/sectors.json`.
- State · Committee thinking: the per-agent timings are illustrative.
