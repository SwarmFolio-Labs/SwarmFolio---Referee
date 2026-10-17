# SwarmFolio Referee — LA Hacks AI Hackathon 2026 (Plan v2)

> **Superseded by `MASTER.md`** for the split, contract, math, wiring and prompts. Keep this file for background.

**AI proposes. Math decides.**

A network of **five AI agents on Fetch.ai** builds an investment portfolio for a client.
Three analyst agents (Macro, Fundamentals, Risk) each research the market from their own
angle. A Chair agent combines their views into a proposal. A **Referee agent** checks it
against the client's rules with an exact math solver. When the proposal breaks a rule, the
Referee says which rules were violated, by how much, which rules contradict each other,
and the cheapest fix. The verdict goes back to the analysts, who **concede, defend or
modify**, and we log who changed their mind. Everything runs inside an ASI:One chat and
ends in an auditable **Feasibility Receipt**.

> This file is a design document written before the hackathon. All code is written during
> the event (Sat Oct 17, 12:00 PM to Sun Oct 18, 12:00 PM PT).

**Splitting the work:** to save Claude usage, see MASTER.md Section 2. Claude Code builds the Brains, Devin builds the Shell, you design in Paper, and everything connects at night.

**What changed in v2:** the analysts are now their own Fetch agents (5 agents total, not 2),
to score on Fetch's "multi-agent collaboration" bonus. Prices are refreshed to the current
date at the start. The design stays safe: every agent is a thin wrapper around plain Python
functions that work on their own, and a single switch falls back to the simpler version.

---

## 0. Why this wins

| Judging criterion | How this project scores |
|---|---|
| Technical depth | An exact optimization solver (mixed-integer programming), a minimal conflicting set of rules found with a deletion filter, an elastic relaxation, a projection onto the nearest valid portfolio, and a **5-agent network** with timeouts, retries and graceful failure. Clearly more than an API wrapper. |
| Product thinking & impact | Built on 9 days of Priority Labs market research. Real gap: AI drafts portfolios that break client rules (47.6–85.7% of first drafts in BiasMix-Finance, ICLR 2026 workshop). FINRA's 2026 report expects guardrails and audit trails for AI. |
| Execution & polish | Tiered plan: Tier 1 alone is a complete, demoable product. |
| Originality & insight | "Watch who changes their mind": an AI debate held accountable by math. The insight is that the verifier, not the AI, is the product. |

**Fetch.ai challenge fit, criterion by criterion:**

| Fetch criterion | This project |
|---|---|
| Real-world problem | AI-drafted portfolios that break client rules |
| Multi-step planning / orchestration | Analysts → Chair → Referee → revise loop, up to 3 rounds |
| Tools, APIs, other agents | Exact solver, market data, LLMs, agent-to-agent messages |
| Registered on Agentverse, Chat Protocol, works fully in ASI:One | All 5 agents registered; the Chair is the chat entry point |
| ⭐ Bonus: multi-agent collaboration | 5 agents, each with its own job and address |
| ⭐ Bonus: reliability and error handling | Timeouts, one retry, continue without a silent agent and say so |
| ⭐ Bonus: real-time data | Prices refreshed to the current date; live fundamentals |
| ⭐ Bonus: could keep operating | The Referee Agent is a standalone service any AI can call |
| ⭐ Bonus: Payment Protocol, Interactive Cards | Tier 3: pay per verification; receipt as a card |

**Where to submit:**
- **Tracks:** Applied Intelligence **and** Agentverse (confirmed at the event: one project can enter both).
- **Main sponsor challenge:** Fetch.ai ASI:One Agent Challenge.
- **Free extra:** Cognition "Best Use of Devin". Use the free credits for a few steps and screenshot what Devin did.
- **Design challenge:** Paper "Best Designed Hack" ($1,500 / $1,000 / $500). You design the web app in Paper (MASTER 13b).
- **Optional:** MLH Best Use of Gemini, if one analyst uses Gemini.

**Priority if time is short:** Referee → Fetch → the two tracks → Paper → Devin/Gemini (MASTER 3).

---

## 1. What exists before the event vs. what is built at the event

| Pre-existing (open source, MIT) | Built at LA Hacks (what gets judged) |
|---|---|
| SwarmFolio: the price-download code and cached prices for 19 stocks, return and covariance math, a PSO optimizer, a backtest | Rule schema (10 rule types), the Referee (exact solver, conflict finder, cheapest relaxation, repair, receipt), the analyst and Chair logic, the feedback loop, the 5 Fetch agents and their messages, the evaluation, the web app (FastAPI + React, designed in Paper) |

Put this table in the README and on Devpost (the rules require it), plus one line:
*"Design notes were written before the event; all code was written during it."*

---

## 2. Architecture

### Two layers: "brains" and "phones"

1. **Brains (plain Python, built Saturday afternoon).** Analysts, Chair, Referee and the feedback
   loop are ordinary functions. They pass JSON to each other and work with **no Fetch at all**.
   The web app (FastAPI + React) runs on this layer.
2. **Phones (Fetch agents, built Saturday night).** Each brain gets wrapped in a small Fetch
   agent with its own address. Agents send messages instead of calling functions.

A switch in `config.py`, `USE_AGENT_NETWORK = True / False`, picks which one the Chair uses.
**If the network breaks at 3 AM, flip the switch and everything still works.**

### The agent network
```
      You, in ASI:One: "Build a portfolio for Dr. Patel"
                         │  (Chat Protocol)
                         ▼
              ┌─────────────────────┐
              │  🤖 CHAIR AGENT      │  entry point; orchestrates everything
              └──┬─────┬─────┬───┬──┘
     1. analyze  │     │     │   │ 3. verify
        ▼        ▼     ▼     │   ▼
   🤖 MACRO  🤖 FUNDAMENTALS  🤖 RISK      ⚖️ REFEREE AGENT
    memo ↑      memo ↑      memo ↑         receipt ↑
                         │
     2. Chair writes the proposal from the 3 memos
     4. Violations? Chair sends the receipt to each analyst →
        each replies concede / defend / modify → Chair revises → verify again
        (max 3 rounds; the debate log records every stance)
     5. Reply in chat: debate summary + final portfolio + receipt
```

### Agent roster

| Agent | Brain inside | Receives | Sends back |
|---|---|---|---|
| **Chair Agent** | Chair LLM (LangChain) + loop logic | Chat message from the user (ASI:One) | Chat reply with summary, weights, receipt |
| **Macro Agent** | Macro analyst (LangChain) + sector/trend data | `AnalysisRequest` | `Memo` |
| **Fundamentals Agent** | Fundamentals analyst (LangChain) + yfinance data | `AnalysisRequest` | `Memo` |
| **Risk Agent** | Risk analyst (LangChain) + volatility/drawdown data | `AnalysisRequest`, `ReviewRequest` | `Memo`, `Stance` |
| **Referee Agent** | The CVXPY + SCIP Referee (no LLM) | `VerifyRequest`, or a chat message with JSON from anyone | `Receipt` |

All three analysts handle both `AnalysisRequest` and `ReviewRequest`.

**The Referee Agent also speaks the Chat Protocol on its own**, so anyone (a person in ASI:One,
or someone else's AI agent) can send it a portfolio plus rules and get a receipt. That makes it
a standalone service, not just a part of this demo.

### Messages (one Pydantic model each, in `agents/messages.py`)
- `AnalysisRequest`: client_id, client story, rules as text, market snapshot date
- `Memo`: agent name, views (overweight/underweight with reasons), tickers to favor or avoid
- `VerifyRequest`: client (full JSON), proposal (weights + thesis + reasons)
- `Receipt`: the Feasibility Receipt (Section 5)
- `ReviewRequest`: round number, the receipt's plain-English failures, the current proposal
- `Stance`: agent name, `concede | defend | modify`, change, why

### Reliability (a Fetch bonus criterion)
- Each request waits at most **45 seconds**, then retries once.
- If an analyst still doesn't answer, the Chair **continues without it** and says so in the reply
  ("Macro analyst timed out; proceeding with 2 of 3 memos").
- If the Referee Agent doesn't answer, the Chair calls the local Referee function directly, so
  verification is never skipped.
- LLM answers are cached, so a retry doesn't cost extra and gives the same answer.

**Key design decision (judges will ask):** the Referee uses an *exact* solver (CVXPY + SCIP), not
PSO or an LLM. A verifier must give the same answer every time and must be able to prove that no
valid portfolio exists. The LLM agents are creative but unreliable, and PSO is a random search.
**PSO searches, the exact solver judges.** (PSO from SwarmFolio is a Tier 3 add-on that searches
for good portfolios; the Referee then certifies them.)

---

## 3. Tech stack

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.14 (already on your Mac) | Verified: cvxpy, SCIP, HiGHS, uagents 0.26.1 (Chat Protocol 0.3.0), LangChain all install and import on it |
| Optimization | `cvxpy` with the `SCIP` solver (yes/no rules plus a volatility cap); `CLARABEL`/`HIGHS` as fallbacks | Free and exact |
| LLM | **LangChain** in `committee/llm.py`. Default: Fetch's **ASI:One** model (`asi1`, OpenAI-compatible). Switchable to Gemini or Claude with one setting | One interface, structured output, a framework Fetch supports |
| Agents | Fetch.ai `uagents` as the wrapper layer, mailbox to Agentverse, Agent Chat Protocol 0.3.0, ASI:One. Recipe in MASTER 9.2 | Sponsor challenge. Agents exchange JSON text (uAgents uses Pydantic v1) |
| Market data | Prices refreshed with `yfinance` on Saturday (falls back to SwarmFolio's cached `prices.csv`); fundamentals snapshot from `yfinance`; hand-written sector map | Current data, but still works offline |
| UI | ASI:One chat (required by Fetch) + a web app: FastAPI + React, designed in Paper (for judges, the video, and the Paper prize) | |
| Tests | `pytest` | AI-written math must be verified |

---

## 4. Data: where every number comes from

| Data | Source | Saved to | Used by |
|---|---|---|---|
| Daily prices, 19 stocks + SPY, 2015 → today | `yfinance`, downloaded once on Saturday (fallback: SwarmFolio's `prices.csv`, which ends Jul 1 2026) | `data/prices.csv` | Everyone |
| Returns, volatility, correlations, drawdowns | Computed in Python from prices | in memory | Risk Agent, Referee |
| Recent performance by stock and sector (1, 3, 6 months) | Computed from prices | in memory | Macro Agent |
| P/E, revenue growth, profit margins | `yfinance`, one snapshot on Saturday | `data/fundamentals.json` | Fundamentals Agent |
| Sector of each stock | Written by hand | `data/sectors.json` | Referee (sector rules), analysts |
| Client rules and story | Written by hand / generated | `data/clients/C01.json …` | Referee (exact JSON), Chair + analysts (rules as text) |
| LLM answers | The chosen model (ASI:One by default), saved after the first call | `cache/` | Makes reruns free and identical |

**Analysts never browse the internet.** Python hands them the numbers inside their prompt. That
keeps results reliable, repeatable and cheap.

---

## 5. The rule schema (the contract everything depends on)

A **client** is one JSON file in `data/clients/`:

```json
{
  "client_id": "C07",
  "name": "Dr. Patel (synthetic)",
  "story": "Retired surgeon, wants growth but no fossil fuels; holds legacy JNJ stock from her career.",
  "universe": ["AAPL","MSFT","GOOGL","NVDA","AMZN","META","JPM","GS","BAC","JNJ","UNH","PFE","PG","KO","WMT","XOM","CVX","GLD","TLT"],
  "current_weights": {"JNJ": 0.40, "TLT": 0.30, "KO": 0.30},
  "rules": [
    {"id": "R1", "type": "max_weight",   "params": {"ticker": "*", "max": 0.35}, "priority": 5, "hard": false, "source": "No single position above 35%."},
    {"id": "R2", "type": "exclude",      "params": {"tickers": ["XOM","CVX"]},   "priority": 10, "hard": true, "source": "No fossil fuel companies."},
    {"id": "R3", "type": "min_weight",   "params": {"ticker": "JNJ", "min": 0.30}, "priority": 7, "hard": false, "source": "Keep at least 30% in legacy JNJ (tax reasons)."},
    {"id": "R4", "type": "sector_max",   "params": {"sector": "Healthcare", "max": 0.35}, "priority": 4, "hard": false, "source": "Healthcare at most 35%."},
    {"id": "R5", "type": "max_holdings", "params": {"k": 8}, "priority": 3, "hard": false, "source": "At most 8 holdings."},
    {"id": "R6", "type": "buy_in",       "params": {"min": 0.05}, "priority": 3, "hard": false, "source": "No position smaller than 5%."},
    {"id": "R7", "type": "max_volatility","params": {"max": 0.18}, "priority": 6, "hard": false, "source": "Annual volatility at most 18%."}
  ]
}
```

> Verified with SCIP on Oct 15: this client is feasible but tight. JNJ ≥ 30% (R3) fits under the
> 35% single-name cap (R1) and the 35% Healthcare cap (R4), leaving at most 5% for other Healthcare
> names. Add "hold at least 10% UNH" and the rules become impossible: JNJ 30% + UNH 10% = 40% > 35%.
> The Referee should then report exactly {R3, R4, new rule} as the conflict.
> **Design clients so conflicts are realistic, like this.**

**The 10 rule types** (each needs a checker, a solver constraint, and a plain-English template):

| type | params | math | solver form |
|---|---|---|---|
| `max_weight` | ticker or `*`, max | w_i ≤ max | linear |
| `min_weight` | ticker, min | w_i ≥ min | linear |
| `exclude` | tickers | w_i = 0 | linear |
| `sector_max` | sector, max | Σ sector ≤ max | linear |
| `sector_min` | sector, min | Σ sector ≥ min | linear |
| `max_holdings` | k | # held ≤ k | binary vars z_i, w_i ≤ z_i |
| `min_holdings` | k | # held ≥ k | binaries (with w_i ≥ DUST·z_i always on; see MASTER 6.2) |
| `buy_in` | min | w_i = 0 or w_i ≥ min | binaries: min·z_i ≤ w_i ≤ z_i |
| `max_volatility` | max | √(wᵀΣw) ≤ max | second-order cone |
| `max_turnover` | max | Σ\|w_i − current_i\| ≤ max | linear with helper vars |

Always present (not rules): long-only, weights sum to 1.

**Priority & hard:** `hard: true` means it can never be relaxed (regulatory/values).
Priority 1–10 is the cost per unit of relaxation; higher means more expensive to relax.

---

## 6. The Referee spec (`referee/`)

### Input
`client` (the JSON above) + `proposal` = `{"weights": {...}, "thesis": "...", "reasons": {...}}`

### Output: the Feasibility Receipt
```json
{
  "receipt_id": "sha256 of inputs, first 12 chars",
  "timestamp": "...",
  "client_id": "C07",
  "verdict": "VIOLATIONS_REPAIRED",
  "checks": [
    {"rule_id": "R1", "passed": false, "actual": 0.41, "limit": 0.35, "violation": 0.06,
     "explain": "NVDA is 41% of the portfolio; the client allows at most 35% in one name."}
  ],
  "rules_feasible": true,
  "conflict_set": [],
  "cheapest_relaxation": [],
  "repaired_weights": {"...": 0.0},
  "repair_distance": 0.14,
  "sharpe_before": 1.21,
  "sharpe_after": 1.17,
  "summary": "The proposal broke 2 of 7 rules. The nearest compliant portfolio moves 14% of capital and costs 0.04 Sharpe."
}
```

**Verdicts:** `PASS` | `VIOLATIONS_REPAIRED` | `RULES_INFEASIBLE` (no portfolio can satisfy all rules) | `ERROR`.

### The five algorithms

1. **check(weights, rules)**: plain Python, no solver. For every rule: actual value, limit, passed, violation size, plain-English sentence. *Easiest piece; build first.*
2. **is_feasible(rules)**: build the cvxpy problem with all rules as constraints and a dummy objective; solve with SCIP. Feasible if the status is optimal.
3. **find_conflicts(rules)** (deletion filter, gives an Irreducible Infeasible Subset): start with all rules (known infeasible). For each rule in order: remove it; if still infeasible, leave it out for good; otherwise put it back. What remains is a *minimal* set of rules that can't all hold, where dropping any one fixes it. Explain it in one sentence ("R3, R4 and R8 can't all hold: …").
4. **cheapest_relaxation(rules)** (elastic program): give every soft rule a slack variable s ≥ 0 (for example, `w_i ≤ max + s`), keep hard rules exact, minimize Σ priority × s. The nonzero slacks are the cheapest fix: "Raise the Healthcare cap from 35% to 40% (cost 20)." If even that is infeasible, the hard rules conflict with each other; report that set.
5. **repair(proposal, rules)**: if feasible, minimize Σ|w − proposal| (L1 = capital moved) subject to all rules. That is the valid portfolio closest to what the AI intended. Report the distance and the Sharpe before/after.

### Required tests (`tests/`). Write each with its feature.
- A proposal that obeys every rule → `PASS`, all checks pass.
- NVDA at 31% with a 25% cap → the max_weight rule fails with violation 0.06.
- Rules `min JNJ 0.40` + `Healthcare max 0.30` → infeasible; conflict set is exactly those two.
- Same conflict, cheapest relaxation changes only one of them, and never touches a hard rule.
- Repair output passes `check` on every rule and sums to 1.
- `buy_in` 5% + `max_holdings` 3 + `min_holdings` 3 + `max_weight` 0.30 → infeasible (3 × 30% = 90% < 100%).
- Same inputs → same receipt id (deterministic).

---

## 7. The analysts, the Chair and the feedback loop (`committee/`)

| Brain | Model | Data it gets (computed by Python) | Produces |
|---|---|---|---|
| **Macro analyst** | analyst model | 1/3/6-month returns per stock and sector, a short macro brief (Tier 3: live news) | Sector overweights/underweights + 2-sentence reasons |
| **Fundamentals analyst** | analyst model | `fundamentals.json`: P/E, revenue growth, margins per ticker | Top picks / avoids + reasons |
| **Risk analyst** | analyst model | Volatility, correlation, max drawdown per ticker | Risk warnings, names to cap |
| **Chair** | chair model | The three memos + client story + rule *text* | `proposal`: weights (sum to 1) + thesis + one reason per position |

**Important:** analysts and Chair see the rules as text only, the way a human advisor reads an
investment policy. That is realistic, and it is *why* they break rules, which is what the
evaluation measures.

### The feedback loop (the "watch who changes their mind" moment)
1. Chair proposes → Referee receipt.
2. If violations: each analyst receives the receipt's plain-English failures and must reply
   `{"stance": "concede" | "defend" | "modify", "change": "...", "why": "..."}`.
3. Chair revises using those replies → Referee again. Max 3 rounds.
4. Log every stance into `debate_log`. Shown as a timeline, e.g. "Round 2: Risk analyst
   conceded NVDA 41% → 35%; Fundamentals defended GOOGL."
5. If still violating after 3 rounds → the Referee's `repair` becomes final, and the receipt
   says the committee could not self-correct.
6. If the *rules themselves* are infeasible → no portfolio is possible; the Chair writes a note to
   the advisor with the conflict and the cheapest fix. (This is the "honest referee" from the
   original SwarmFolio pitch.)

The loop is one function, `run_committee(client)`. It takes "how to talk to the analysts and the
Referee" as an input: direct function calls (`USE_AGENT_NETWORK = False`) or Fetch messages
(`True`). Same logic, two transports.

All LLM calls return strict JSON (validated with Pydantic; on bad JSON, retry once with the error).

---

## 8. The evaluation (the data-science edge; gives judges a real number)

`eval/` runs everything on **25 synthetic clients** (`data/clients/C01..C25.json`):
- 18 feasible clients with varied rules (some easy, some tight).
- 5 clients with a **planted conflict** (we know the exact conflict set).
- 2 clients with 9–10 rules (stress test).

Generate clients with a script and a fixed random seed. The evaluation calls the brains directly
(no agent network), so it's fast and doesn't depend on Fetch.

| # | Metric | Question it answers |
|---|---|---|
| M1 | % of first-draft proposals violating ≥1 rule; mean # violations | How often does AI break client rules? |
| M2 | Same, after the feedback loop (before repair) | Does Referee feedback make the AI self-correct? |
| M3 | % of final portfolios that comply (should be 100% for feasible clients) | Does the system guarantee compliance? |
| M4 | Mean capital moved by repair (L1) and Sharpe change | What does compliance cost the AI's intent? |
| M5 | Planted conflicts: all 5 flagged? Found conflict set = planted one? | Is the Referee right? |
| M6 | % of stances concede / defend / modify; rounds to converge | Who changes their mind, and how fast? |
| M7 (Tier 3) | Rule extraction accuracy from plain-English instructions | Can AI turn a document into rules reliably? |

**Baseline:** "LLM alone with rules in the prompt" (M1) vs "LLM + Referee" (M3).
**Headline sentence for the demo:** *"Our AI committee broke at least one client rule in X% of
first drafts. With the Referee, 100% of final portfolios comply, at a median cost of Y% of
capital moved, and it caught 5 out of 5 impossible clients."*

---

## 9. Tiers (build in order; never start a tier until the previous one demos)

### Tier 1: the complete product, brains only (target: Sat 9:30 PM)
- [ ] Prices refreshed + fundamentals snapshot + sector map + 3 hand-made clients (easy, tight, infeasible)
- [ ] Referee: check → is_feasible → find_conflicts → cheapest_relaxation → repair → receipt, all tested
- [ ] Analysts + Chair producing a valid proposal
- [ ] Feedback loop with debate log
- [ ] Web app: pick client → "Convene committee" → debate timeline → receipt card → before/after chart
- [ ] `git commit` + push. **This alone is a submittable project (Applied Intelligence).**

### Tier 2: the winning version, the agent network (target: Sun 4 AM)
- [ ] 25 synthetic clients + evaluation + results table + 1 chart
- [ ] **Referee Agent** on Agentverse, Chat Protocol, works alone in ASI:One
- [ ] **Chair Agent** in ASI:One, calling the Referee Agent (the 2-agent version: qualifies for Fetch)
- [ ] **Macro, Fundamentals, Risk Agents**, so the Chair runs the full debate over the network (the 5-agent version: the Fetch bonus)
- [ ] Timeouts, retry, graceful fallback; `USE_AGENT_NETWORK` switch tested both ways
- [ ] ASI:One shared chat URL of a full run + all Agentverse profile URLs saved
- [ ] README with "built at LA Hacks" table, architecture diagram, results

### Tier 3: the ambitious version (only with time left; pick ONE)
- [ ] Plain-English instructions → rules: paste a paragraph; LLM extracts rule JSON *with the source quote for each rule*; Referee validates it; eval M7
- [ ] ASI:One Interactive Cards for the receipt (Fetch bonus)
- [ ] Fetch Payment Protocol: a tiny testnet fee per verification (matches the research's per-check business model; Fetch bonus)
- [ ] SwarmFolio PSO as an "explorer" agent: maximizes Sharpe under the rules, certified by the Referee
- [ ] Live news for the Macro analyst

### Cut order if behind (cut from the top)
Tier 3 → analyst agents (keep the 2-agent Fetch version) → eval down to 10 clients → Chair Agent (keep the Referee Agent alone in ASI:One).
**Never cut:** Referee tests, the feedback loop, the eval headline number, the demo video, both submissions.

---

## 10. Timeline (24 hours)

**The up-to-date, hour-by-hour timeline with owners (Claude Code / Devin / you) is in MASTER.md Section 3.**
Key checkpoints: Referee pushed 5 PM · fake agents chat in ASI:One 5 PM · real Referee Agent 5:30 PM ·
Tier 1 9:30 PM · Paper design exported 10 PM (or skip) · Fetch-qualified + submitted 1 AM · sleep 4–7 AM ·
both submissions by 11:30 AM Sunday.

---

## 11. Demo script (2.5 minutes; rehearse 3×)

1. **Hook (15s):** "Anyone can ask an AI for an investment thesis. In a recent study, AI-drafted
   portfolios broke a client's rules in up to 86% of first drafts. Advisors can't send that to clients."
2. **Show it in ASI:One (60s):** "Build a portfolio for Dr. Patel." Five agents get to work: Macro,
   Fundamentals and Risk send memos, the Chair proposes, the Referee flags "NVDA 41% breaks the 35% cap."
   Round 2: the Risk agent concedes, Fundamentals defends GOOGL. Final receipt: compliant, 6% of capital moved.
3. **The twist (30s):** the impossible client. "No portfolio exists. These 3 rules can't all hold.
   Cheapest fix: raise the Healthcare cap to 40%." "Most systems silently drift. We tell the advisor why."
4. **Proof (30s):** eval chart: X% violation rate → 100% compliant; 5/5 impossible clients caught exactly.
5. **Close (15s):** "The Referee is its own agent on Agentverse. Any AI that drafts portfolios can call it.
   AI proposes. Math decides."

Have the web app open in a second tab: it's the visual story for judges and the backup if ASI:One is slow.

---

## 12. Judge Q&A, prepared answers

- **Why not just put the rules in the prompt?** We did; that's the baseline. It still breaks rules X% of the time (M1). Prompts are suggestions; constraints are guarantees.
- **Isn't this just an AI wrapper?** The AI is the easy part. Remove Claude and the Referee still works on any portfolio from any source: it checks, proves impossibility, finds the clash, computes the smallest fix. Remove the Referee and you'd have a wrapper; that's why it's the product.
- **Why a solver and not PSO or the LLM?** A verifier must be reproducible and able to *prove* that no valid portfolio exists. PSO is random and can only say "didn't find one." My SwarmFolio repo showed exactly this: the old swarm check called a feasible rule set impossible.
- **How do you find the conflicting rules?** Deletion filter: remove rules one at a time; if the problem stays infeasible without a rule, that rule wasn't needed for the conflict. What's left is minimal.
- **Why five separate agents?** Each has one job and its own address, so they can run, fail and be replaced independently, and the Referee is a reusable service any other agent can call. If an analyst times out, the Chair continues and says so.
- **Isn't this investment advice?** It's a tool for advisors, who are fiduciaries, and it uses synthetic clients. The Referee only checks rules; humans decide.
- **Who pays?** My research says the best fit is per-verification pricing for wealthtech platforms and AI-agent builders, not standalone software for advisors (StratiFi, the closest comparable, is ~$4M revenue). Fetch's Payment Protocol makes per-check payment natural.
- **Competitors?** Vestmark Pulse (May 2026) screens trades against investment policies; Gurobi can find conflicting constraints. Nobody publicly connects AI proposals → conflict explanation → cheapest fix → audit receipt.
- **What did you build here vs. before?** Point to the table in Section 1 and the commit history.

---

## 13. Submission checklist
**Devpost**
- [ ] Title, tagline "AI proposes. Math decides.", 2–3 min video
- [ ] Tracks: Applied Intelligence + Agentverse (both allowed); challenges: Fetch.ai, Paper, Cognition (Devin), Gemini if used
- [ ] Paper: 2–3 screenshots of the Paper canvas (style guide + screens) + one sentence on the design idea
- [ ] Public GitHub repo (MIT) with README, run instructions, "built at LA Hacks" table
- [ ] Results table (M1–M6), screenshots: debate timeline, receipt, conflict explanation
- [ ] Team members' names; be present in person for judging

**Fetch.ai (separate, required for the Fetch prize)**
- [ ] ASI:One shared chat URL of a full run
- [ ] Agentverse profile URL for every agent (up to 5)
- [ ] **Submit through the ASI:One Submission Agent** (https://asi1.ai/festival/lahacksai2026/dashboard). Process doc: https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0

---

## 14. Before hacking starts (learning only, no project code)
- [x] Library check: `cvxpy`, `pyscipopt`, `highspy`, `uagents` 0.26.1, LangChain install on your Python 3.14; SCIP solved a test problem with yes/no rules plus a volatility cap; the Referee math was verified on Dr. Patel (MASTER 6.9).
- [ ] **ASI:One API key** (asi1.ai/dashboard/api-keys); backup: Gemini key (free) or Anthropic; Agentverse account; Paper desktop + code LAHACKS26
- [ ] Fetch hackpack: https://www.fetch.ai/events/hackathons/la-hacks-ai-hackathon-2026/hackpack and resources doc: https://docs.google.com/document/d/10w0c9L1GL8FkeciTGyBzUCWUgrEsKJgZh4hxG_96XLs
- [ ] Fetch hello-world in a *throwaway* folder: one agent on Agentverse you can chat with in ASI:One. Then delete it.
- [ ] Post the teammate message on Discord; claim Devin credits at the event
- [ ] Pack: laptop + charger, phone charger, power strip, headphones, hoodie, water bottle, toothbrush, student ID
