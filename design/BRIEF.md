# SwarmFolio Referee: Design Brief (Paper "Best Designed Hack")

You are the design session. Read this whole brief before designing anything, and come back to it
before every step. Work only in Paper (and export to `design/` when asked). Don't edit code, don't run
git, don't restart anything.

---

## 1. Why this design matters
Paper's prize: **$1,500 / $1,000 / $500**. Judges score three things, equally:

1. **Design fundamentals:** hierarchy, legibility, consistency, contrast, alignment, spacing.
2. **Ease of use:** the flow is obvious, every state gives clear feedback, nothing to learn.
3. **Personal craft and character:** it must feel *made by a person with taste*, not AI-generated.

Most teams will ship a default dashboard. We win by being **specific, restrained and crafted**: one
strong idea executed precisely everywhere.

---

## 2. The product in 30 seconds
**SwarmFolio Referee: "AI proposes. Math decides."**

- **Users:** financial advisors (and their compliance officers). Professionals who value trust,
  precision and clarity over flash. Secondary audience: the judges, who see it for ~2 minutes.
- **What happens:** three AI analysts (Macro, Fundamentals, Risk) and a Chair propose a portfolio for
  a client. A math **Referee** (an exact optimization solver, not an AI) checks it against the client's
  rules. If rules break, the analysts **concede, defend or modify** and the Chair revises, for up to
  3 rounds. The Referee then issues a **receipt**: an auditable record of what was checked, what
  broke, and how it was fixed with the fewest possible changes.
- **The emotional arc:** AI is creative but sloppy → the Referee is calm, exact and fair → the advisor
  ends up with something they can trust and sign.

**Design metaphor (use it everywhere):** *a referee's audit*. Think printed financial statements,
research reports, ledger paper, bank receipts, an official stamp. Authority through restraint, not
decoration.

---

## 3. Screens and their hierarchy (design these, in this priority order)

### Screen A: The committee run (THE hero screen, client C04 Mr. Alvarez)
The moment judges remember. Real content:
- **Client:** Mr. Alvarez (synthetic). 55-year-old tech executive; 60% of his money sits in NVDA, MSFT and
  AAPL from years of stock grants. Wants to de-risk before retiring without a big tax bill.
- **His 8 rules (always shown in his own words):** Annual volatility at most 14% · Turnover at most 45%
  from current holdings (taxes) · Tech at most 40% · No single position above 20% · At least 8 holdings ·
  No position under 4% · Financials at least 10% · No tobacco or energy companies (XOM, CVX).
- **The debate, round by round:**
  - Round 1: the first draft broke **turnover** and **minimum position size**. All 3 analysts proposed fixes.
  - Round 2: still broke **volatility, the Tech cap and turnover**. The analysts shifted from tech to
    defensive names.
  - Round 3: **✅ compliant with all 8 rules.** Sharpe 1.64, volatility 13.4%.
- **Final weights:** MSFT 16.9 · JNJ 13.5 · KO 13.5 · AAPL 11.2 · JPM 11.2 · NVDA 11.2 · AMZN 9.0 · PFE 6.7 · PG 6.7

Hierarchy, top to bottom:
1. The client (name, one-line story) and the run's status (round X of 3 / compliant / repaired).
2. A **timeline of rounds**: each round = the proposal → the Referee's findings (rules broken) → the
   3 analysts' stances. Stances are short (1–2 sentences) with a clear stance marker
   (concede / defend / modify).
3. The outcome: compliant, or repaired by the Referee, with a link to the receipt.

It must read like a story you can follow in 10 seconds: *"broke 2 → broke 3 → fixed."* Make the
**number of broken rules per round** visible at a glance (e.g. a small round-by-round tally).

### Screen B: The receipt (THE signature element)
Must feel like a **real printed audit receipt**: an official, trustworthy document. Content:
- Header: "Referee receipt · C02 · Dr. Patel (synthetic)", receipt id (e.g. `54411b07eaf4`), timestamp.
- **Verdict** + **stamp**: one of PASS (compliant) / REPAIRED / IMPOSSIBLE. The stamp is the signature
  detail: an ink stamp, slightly rotated, imperfect edge, in the meaning color.
- Summary sentence: "The proposal broke 2 of 7 rules. The nearest compliant portfolio moves 3.9% of
  capital and changes Sharpe from 1.72 to 1.74."
- **Broken rules:** for each, the client's own words in quotes + **Actual vs Minimum/Maximum**, e.g.
  "Keep at least 30% in legacy JNJ (tax reasons)": actual **26.7%**, minimum **30.0%**.
  "No position smaller than 5%": smallest is GS at **4.4%**, minimum **5.0%**.
- **Before → after holdings** (only changed rows highlighted), capital moved, Sharpe before → after.
- Footer: "Checked by an exact solver (CVXPY + SCIP). Same inputs → same receipt id."

Monospace for all numbers, tabular figures, dashed rule separators, perforated or torn edge, generous
margins. It should look printable.

### Screen C: The impossible client (C03, Dr. Patel with a UNH gift)
Content: "These rules can't all hold: 'Keep at least 30% in legacy JNJ (tax reasons)', 'Healthcare at most
35%', 'Hold at least 10% UNH (family shares)'  (30% + 10% = 40% > 35%)."
Cheapest fix: "Raise 'Healthcare at most 35%' from 35.0% to 40.0%."
Design goal: **calm, clear, helpful, not an error screen.** Show the 3 clashing rules as a visible
conflict (e.g. a simple bar showing 30% + 10% overflowing a 35% limit), then the suggested fix as the
obvious next action ("Ask the advisor to approve"). The stamp here: IMPOSSIBLE (or "NEEDS APPROVAL").

### Screen D: Client picker (the entry point)
26 synthetic clients. Each: name, one-line story, rule count, and rule chips in the client's own words.
Put the demo clients first: **C04 Mr. Alvarez**, C02 Dr. Patel, C03 Dr. Patel + UNH, C91 Ms. Okafor.
One clear primary action per client: "Convene the committee".

### Screen E: Price tags (what each rule costs)
Real data (C04): "Turnover at most 45% (taxes)" costs **4.23 points/yr** · "Annual volatility at most
14%" costs **2.43** · "Tech at most 40%" costs **0.04**. Others cost nothing (they don't bind).
A ranked horizontal bar list. Make "costs nothing / doesn't bind" feel like good news. Message: *now the
advisor can have this conversation with the client.*

### Screen F (if time): Experiment results
"On realistic, tight clients the AI broke a rule in 83% of first drafts. After 3 rounds of feedback:
self-check 33%, bare verdict 42%, the Referee's explanation 50% compliant (a trend, n = 12, not
statistically significant). Only the Referee's repair reached 100%." A simple learning-curve chart +
an honest caption. Honesty is part of the brand.

---

## 4. Visual system

### Typography (exactly 2 families + optional monospace for numbers)
Pick ONE pairing per direction; suggested pairings (all free on Google Fonts):
- **Research report:** *Newsreader* or *Source Serif 4* (headings) + *IBM Plex Sans* (UI) + *IBM Plex Mono* (numbers)
- **Trading terminal:** *IBM Plex Sans Condensed* or *Archivo* (UI/headings) + *JetBrains Mono* (numbers, lots of it)
- **Audit ledger:** *Instrument Serif* (display) + *Inter* (UI) + *Geist Mono* or *IBM Plex Mono* (numbers)

Rules: tabular/lining figures for every number; a clear type scale (e.g. 12 / 14 / 16 / 20 / 28 / 40);
headings tight letter-spacing, small caps or uppercase only for labels.

### Color: color means something, or it isn't used
- Neutrals: paper/off-white (e.g. #F6F3EC) and ink (e.g. #1B1B1A), or the dark inverse for the terminal
  direction. Hairline rules (1px) instead of heavy borders and shadows.
- **Meaning colors (muted, print-like, never neon):**
  - **pass / compliant:** moss/forest green (e.g. #2F6B3F)
  - **broken / impossible:** vermilion/brick (e.g. #B5432B)
  - **repaired / stance-modify:** ochre/amber (e.g. #B07A1A)
  - stances: concede = green tint, defend = brick tint, modify = ochre tint (always with a text label;
    never color alone)
- Contrast: body text ≥ WCAG AA (4.5:1). Check meaning colors on both backgrounds.

### Layout
12-column grid, max content width ~1200px, generous margins. Left-aligned editorial layout; avoid
centering everything. Consistent 4/8px spacing scale. Numbers right-aligned in tables.

### Signature details (personal craft: pick 2–3, do them well)
- The **ink stamp** on receipts (PASS / REPAIRED / IMPOSSIBLE), rotated ~4°, slightly rough edge.
  Build it as an SVG in Paper (Create SVG ⌘⇧J) and refine the paths by hand.
- **Perforated/torn receipt edge** and dashed separators.
- A small **"Referee" mark/logo**: e.g. a whistle, a balance, or a striped referee band, in one color.
- **Round tally** in the debate: e.g. ●●○ broken rules per round shrinking to 0.
- Subtle **paper texture or ledger lines** (very low contrast) on the receipt only.

### Motion (describe for the build; keep it subtle)
Debate rounds reveal step by step; the stamp "thunks" in at the end (scale 1.15 → 1, slight rotation).
No bouncy or flashy animation.

---

## 5. Avoid (instant "AI-generated" tells)
Purple/blue gradients · glassmorphism/blur · emoji as icons · neon accents · every element in identical
rounded cards with drop shadows · centered hero headline + subtitle + two buttons · stock KPI-tile
dashboards · more than 2 font families · generic icon sets everywhere · lorem ipsum (use the real
data above) · decoration without meaning.

---

## 6. States (ease of use)
Every screen needs: **loading** (committee is thinking: show which agent is working, e.g. "Risk analyst
reviewing…"), **empty**, **error** (calm, plain language, what to do next), and **success**. A run takes
~25 s live, so the loading state must feel alive and informative, not a spinner.

---

## 7. Process (stop at each checkpoint for the human)
1. Create Paper tokens from `frontend/src/index.css` + `frontend/tailwind.config.js`.
2. **3 style directions side by side** (one per pairing above), each showing: type scale, palette with
   meaning colors, a stance marker set, and a mini receipt for C02 with its stamp. **STOP for the human.**
3. The human picks and mixes; they edit tokens in the Theme tab and pin comments. Apply their comments.
4. Design screens A → B → C → D → E (→ F) at desktop width (1440), then a phone version of A and B (390).
   Bring the real app's structure in from http://localhost:5173 if useful. **STOP after A and B.**
5. Polish loop: human comments → apply → repeat.
6. When asked: export every final frame's HTML/CSS + PNG and `design/tokens.css` into `design/`.

Be lean with tool calls; reuse components (stamp, rule row, stance marker, number cell) across screens.

---

## 8. Self-check before calling anything done
- [ ] Can a stranger tell in 5 seconds what happened in the C04 run?
- [ ] Is every number in monospace, aligned, with the right unit?
- [ ] Is every color doing a job (pass / broken / repaired / stance), and is there always a text label?
- [ ] Are the client's own words always quoted for rules?
- [ ] Does the receipt look like something you could print and sign?
- [ ] Would anyone mistake this for a default AI template? If yes, push the signature details further.
- [ ] Hierarchy: one clear primary element per screen; consistent spacing; contrast AA.
