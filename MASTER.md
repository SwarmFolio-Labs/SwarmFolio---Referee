# SwarmFolio Referee: MASTER BUILD DOCUMENT

**AI proposes. Math decides.**

This is the single source of truth for the build. Where it disagrees with PLAN.md (or the old
PROMPTS.md and SPLIT.md pointers), **this file wins**. PLAN.md keeps the background (why, demo, judge Q&A).

Contents
0. PLAN B: Claude Code only (no Devin)
1. The project in 60 seconds
2. Who builds what (the split)
3. Today's timeline with owners
4. Wiring: files, flags, data flow, agent network
5. The contract: every data shape and function signature
6. The math: every formula the Referee uses
7. The committee: analysts, Chair, the loop
8. The LLM layer (ASI:One / Gemini / Anthropic, switchable)
9. The Fetch agents
10. The evaluation
11. Prompts for Claude Code (Part A)
12. Prompts for Devin (Part B)
13. Connecting everything (Part C)
13b. The Paper design (you, Part D)
14. Checkpoints, fallbacks, cut order
14b. Rescue prompts
15. Ship: README, video, the submissions

---

## 0. PLAN B: Claude Code only (no Devin)

If Devin credits aren't available, Claude Code builds everything, in this **leaner order** (the "B" prompts in
Section 12 are run in Claude Code instead; ignore "open a PR", just commit). **A0 is already done (commit 594733a).**

| # | Step | Prompt | Notes |
|---|---|---|---|
| 1 | Referee | **A1 → A5** | The core. Strongest model. Push at the end. |
| 2 | Referee + Chair agents on fakes | **B3, reduced**: only `referee_agent.py`, `chair_agent.py`, `transport.py`, `run_all.py` | Fetch checkpoint: chat with the Chair in ASI:One |
| 3 | Real Referee Agent | **A5b** | |
| 4 | AI brains + loop | **A6 → A8** (skip the "web app" sentence in A8) | |
| 5 | Connect real brains | **C1** | **Fetch-qualified: submit to the Fetch Submission Agent now** |
| 6 | Clients + **the feedback experiment** | **B2 with 18 clients** (15 feasible, 3 planted conflicts) → **A9 → A10** (MASTER 10.3) | ⭐ Depth: the headline *finding* |
| 7 | **Rule price tags** | **A11** (MASTER 6.10) | ⭐ Depth: "what each rule costs you" |
| 8 | Analyst agents | rest of **B3** (macro/fundamentals/risk agents) → **C2** | 5-agent bonus; stop at 4 AM |
| 9 | UI (only if usage remains) | **B1-lite**: `api.py` + ONE static `frontend/index.html` (no React build), showing the price tags and the learning-curve chart | Paper only if this exists by ~10 PM |
| 10 | README + submit | **B4/F1** | |

**Why steps 6–7 (technical depth):** judges know AI can write an agent wrapper in an hour. What they can't get
from "AI can code" is **insight**: a question answered with evidence (6) and an analysis advisors have never seen
(7). New pitch: *"AI proposes. Math decides. And when the math **explains** itself, the AI learns to follow the rules."*

**Dropped in Plan B:** the Devin prize, React, and Paper unless step 8 happens.
**Usage rules:** `/clear` before every step; strongest model only for A1–A5 and A8; a cheaper one for the rest.

---

## 1. The project in 60 seconds

A client (say, Dr. Patel) has investment rules: no oil companies, at most 35% in any one stock,
keep 30% in her legacy JNJ shares, and so on.

1. Three **analyst agents** (Macro, Fundamentals, Risk) each study the market and write a memo.
2. A **Chair agent** turns the memos into a portfolio proposal.
3. A **Referee agent** checks the proposal against the client's rules with an **exact math solver**
   (CVXPY + SCIP): which rules are broken, by how much, whether the rules are even possible, which
   rules clash, the cheapest fix, and the nearest compliant portfolio. It writes a **receipt**.
4. The analysts read the receipt and **concede, defend or modify**. The Chair revises. Up to 3 rounds.
5. The user gets the final portfolio + receipt + "who changed their mind", inside an **ASI:One chat**.

**Stack in one line:** analyst and Chair brains built with **LangChain** (default model: Fetch's **ASI:One**),
the Referee in **CVXPY + SCIP**, every agent wrapped with Fetch's **uAgents** layer, registered on
**Agentverse**, used through **ASI:One**. (Confirmed at the Fetch workshop: any framework for the brain,
uAgents as the wrapper that lets agents collaborate.)

Entered in: **Applied Intelligence track + Agentverse track + Fetch.ai challenge + Paper "Best Designed Hack"** (+ Devin, + Gemini if used).

The UI is a **custom web app** (FastAPI + React), **designed by you in Paper**, because Paper judges on design
fundamentals, ease of use and personal craft, and a stock Streamlit page looks generic.

---

## 2. Who builds what (the split)

| | **Part A: Brains** | **Part B: Shell** | **Part C: You** |
|---|---|---|---|
| Builder | **Claude Code** | **Devin** (free credits; counts for the Devin prize). Backup: teammate or another AI tool | **You, by hand** |
| Owns | `config.py`, `data/` (except clients C04+), `referee/`, `committee/`, `contract.py`, `models.py`, `fakes.py`, `agents/messages.py`, `eval/run_eval.py`, `tests/` | `api.py`, `frontend/`, `agents/*_agent.py`, `agents/transport.py`, `agents/run_all.py`, `eval/make_clients.py`, `data/clients/C04+`, `README.md` | **The Paper design** (`design/`), API keys in `.env`, Agentverse registration clicks, testing in ASI:One, merging Devin's pull requests, Fetch Submission Agent, Devpost, demo video |
| Works on | Real data | **Fakes** (`fakes.py`) until the connection step | |

**Golden rules**
1. Nobody edits a file owned by another part. That's what keeps the merge painless.
2. `contract.py`, `models.py` and `agents/messages.py` are frozen after A0. Changing them needs a loud note and both sides updated.
3. Everything is in one GitHub repo. Claude Code works on `main`. Devin works on branches and opens pull requests, which you merge.

---

## 3. Today's timeline with owners

| Time | Claude Code (A) | Devin (B) | You (C) |
|---|---|---|---|
| 11:00–12:00 | — | — | Opening. Keys ready: an LLM key (ASI:One or Gemini or Anthropic), Agentverse account, GitHub. Claim Devin credits. |
| 12:00–12:45 | **A0** setup + data + contract + fakes | — | Team formation; create the GitHub repo; push A0 |
| 12:45–1:00 | **A1** `check()` | **B3 first:** the 5 Fetch agents on fakes | Connect Devin to the repo |
| 1:00–2:00 | (paused or continue A1) | B3 continues | **Fetch workshop.** Ask: one orchestrator vs one agent per analyst? Ask for ASI:One API credits. |
| 2:00–5:00 | **A2–A5** solver, conflicts, relaxation, repair + receipt | B3 → PR, then **B2** 25 clients | Merge B3. **Register the fake agents on Agentverse and chat with the Chair in ASI:One** (fake answers are fine: this proves the Fetch plumbing early). **5 PM: Referee pushed** |
| 5:00–5:30 | **A5b** Referee Agent on the REAL referee | B2 continues | **Real Referee Agent answers in ASI:One** ✅ |
| 5:30–7:30 | **A6–A8** LLM layer, analysts + Chair, loop | **B1** web app on fakes | Merge B2. Fetch green? Then install Paper (**LAHACKS26**) and do the style guide (D1) |
| 7:30–9:30 | **A9** verify clients + web app switch to real | **B4** README draft | Design the 3 screens in Paper (D2). **9:30 PM: Tier 1 done** |
| 9:30–11:00 | **A10** evaluation | **B5** apply the Paper design (if exported) | Export the design (D3) by 10 PM, or skip Paper |
| 11:00 PM–1:00 AM | **C1** connect agents to real brains | — | Test in ASI:One; shared chat URL; **Fetch Submission Agent by 1 AM** |
| 1:00–4:00 AM | **C2** full 5-agent run + reliability, then Interactive Cards if time | — | Update the Fetch submission with the best chat URL |
| 4:00–7:00 AM | 😴 | 😴 | **Sleep** |
| 7:00–9:00 | One Tier 3 item or bug fixes | | |
| 9:00–11:30 | **F1** README final | | Video; **submit Devpost + Fetch** by 11:30 |
| 12:30 PM | | | Judging |

---

### Priority ladder (when time is short, protect from the top)
1. **Referee** (everything depends on it)
2. **Fetch.ai** (main prize): agents proven on fakes by 5 PM, real Referee Agent by 5:30, Fetch-qualified + submitted by 1 AM
3. **Applied Intelligence + Agentverse tracks** (same work as 1–2, plus the evaluation numbers)
4. **Paper** (only in time that doesn't touch 1–3; hard cutoff: design exported by 10 PM or skip)
5. **Devin / Gemini** (free side entries)

**Rule:** you only open Paper when the current Fetch checkpoint is green. If a Fetch step is
broken, all your attention goes there.

**Confirmed at the Fetch workshop:** an agent's brain can be built with any framework (LangChain,
CrewAI, Google ADK, plain Python); `uagents` is the wrapper layer that lets agents from different
frameworks talk to each other; then register on Agentverse and use them through ASI:One. That's
exactly this design (brains = plain functions, agents = thin wrappers).

**Optional booster (only if the workshop says judges value it, and only after the 1 AM checkpoint):**
rebuild ONE analyst brain in a different framework (e.g. Macro with Google ADK + Gemini, which also
counts for the Gemini prize), keeping the same `analyze()`/`review()` signatures. Pitch line: "three
frameworks, one committee, connected through uagents."

**Fetch score boosters (all cheap):** use the **ASI:One API** as the LLM if Fetch gives credits;
show 5 agents collaborating; timeouts and fallbacks (C2); the Referee Agent usable on its own;
ASI:One Interactive Cards for the receipt (listed as "recommended" in their requirements, so do it in C2 if time).

---

## 4. Wiring

### 4.1 Repository map (owner in brackets)
```
lahacks/
├── MASTER.md  PLAN.md  PROMPTS.md  SPLIT.md  CLAUDE.md          [docs]
├── config.py                         [A] all switches and constants
├── .env / .env.example               [C] keys (never committed)
├── requirements.txt                  [A]
├── contract.py                       [A] function signatures (frozen after A0)
├── models.py                         [A] shared Pydantic v2 models: MASTER 5.2–5.3 (frozen after A0)
├── fakes.py                          [A] fake brains with realistic sample outputs
├── data/
│   ├── refresh_data.py               [A] downloads prices + fundamentals
│   ├── prices.csv                    [A] daily prices, 19 stocks + SPY
│   ├── fundamentals.json             [A] P/E, revenue growth, margin per ticker
│   ├── sectors.json                  [A] ticker → sector
│   ├── samples/*.json                [A] one example of every message (for Devin)
│   └── clients/C01–C03.json [A], C04–C25.json [B]
├── referee/                          [A] the math (no LLM anywhere in here)
│   ├── schema.py   market.py   check.py   solver.py
│   ├── conflicts.py   relax.py   repair.py   receipt.py
├── committee/                        [A] the AI brains
│   ├── llm.py   analysts.py   chair.py   loop.py   transport_local.py
├── agents/
│   ├── messages.py                   [A] uAgents wire messages: JSON-string envelopes, MASTER 5.5 (frozen after A0)
│   ├── transport.py                  [B] AgentTransport (talks to agents over Fetch)
│   ├── referee_agent.py  chair_agent.py  macro_agent.py
│   ├── fundamentals_agent.py  risk_agent.py   [B]
│   └── run_all.py                    [B] starts all 5 agents
├── eval/
│   ├── make_clients.py               [B]
│   ├── run_eval.py                   [A]
│   └── results/                      [A] results.json, results.md, violations.png
├── api.py                            [B] FastAPI: /clients, /committee, /referee, /results
├── frontend/                         [B] React + Vite + Tailwind web app
├── design/                           [C] Paper exports: screens, style guide, HTML/CSS
├── tests/                            [A]
└── README.md                         [B draft, A final]
```

### 4.2 `config.py` switches
| Name | Default | Meaning |
|---|---|---|
| `USE_FAKES` | `True` until C1, then `False` | App and agents import brains from `fakes.py` instead of real modules |
| `USE_AGENT_NETWORK` | `False` | The Chair's loop uses LocalTransport (direct calls) or AgentTransport (Fetch messages) |
| `LLM_PROVIDER` | `"asi1"` (default) or `"gemini"` or `"anthropic"` | Which LLM the analysts and Chair use, via LangChain |
| `CHAIR_MODEL`, `ANALYST_MODEL` | per provider | asi1: `"asi1"` for both · anthropic: `claude-sonnet-5-5` / `claude-haiku-5-5` · gemini: set at the event |
| `ASI1_BASE_URL` | `https://api.asi1.ai/v1` | ASI:One's OpenAI-compatible endpoint (from Fetch's docs) |
| `AGENT_PORTS` | Chair 8001, Referee 8002, Macro 8003, Fundamentals 8004, Risk 8005 | One local port per agent |
| `DUST` | `0.005` | Weights below 0.5% count as "not held" (see 6.2) |
| `TOL` | `1e-6` | Tolerance for "rule passed" |
| `RISK_FREE` | `0.04` | For Sharpe |
| `LOOKBACK_DAYS` | `756` | 3 years of daily data for returns and risk |
| `MAX_ROUNDS` | `3` | Debate rounds |
| `AGENT_TIMEOUT_S`, `AGENT_RETRIES` | `45`, `1` | Agent reliability |

### 4.3 How a single function picks real vs fake
Every consumer (app, agents) imports brains through one place:
```
# brains.py pattern (inside api.py and each agent):
if config.USE_FAKES:  from fakes import referee, analyze, review, chair_propose, chair_revise, run_committee
else:                 real versions from referee/ and committee/
```
Switching from fake to real = flipping `USE_FAKES`. That's the whole connection step.

### 4.4 Data flow (brains only, LocalTransport)
```
prices.csv ─┐
fundamentals.json ─┤→ referee/market.py: mu (annual mean), Sigma (annual cov), per-stock stats
sectors.json ─┘                │
                               ▼
client C02.json ──→ committee/loop.py: run_committee(client, transport)
                      │
                      ├─ transport.analyze("macro" | "fundamentals" | "risk", AnalysisRequest) → Memo ×3
                      ├─ chair_propose(client, memos) → Proposal
                      ├─ transport.verify(VerifyRequest) → Receipt         (referee/receipt.py)
                      ├─ if violations: transport.review(name, ReviewRequest) → Stance ×3
                      │                 chair_revise(client, proposal, receipt, stances) → Proposal
                      │                 verify again … (max 3 rounds)
                      └─ CommitteeResult(final_proposal, receipt, debate_log, rounds, notes)
                                       │
                     api.py → frontend (web app)  /  chair_agent.py (ASI:One reply)
```

### 4.5 The agent network (AgentTransport)
```
ASI:One user ──chat──▶ CHAIR AGENT (runs committee/loop.py with AgentTransport)
                         │ AnalysisRequest ─▶ MACRO / FUNDAMENTALS / RISK AGENTS ─▶ Memo
                         │ VerifyRequest   ─▶ REFEREE AGENT ─▶ Receipt
                         │ ReviewRequest   ─▶ MACRO / FUNDAMENTALS / RISK AGENTS ─▶ Stance
                         ◀──chat── summary + final weights + receipt
Anyone else ──chat──▶ REFEREE AGENT (also speaks Chat Protocol on its own)
```
Every agent file follows the same 4-line idea: **receive message → call the brain function → wrap the
result in a message → send it back.** No business logic in agent files.

**Reliability inside AgentTransport:**
- Wait `AGENT_TIMEOUT_S` for a reply and retry `AGENT_RETRIES` times.
- If an analyst is still silent, return `None`. The loop continues without it and adds a note.
- If the Referee is still silent, call the local `referee()` and add a note. Verification is never skipped.

---

## 5. The contract (frozen after A0)

All models are Pydantic v2. Weights are always `dict[str, float]` (ticker → fraction of capital).

### 5.1 Clients and rules (`referee/schema.py`)
```
RuleType = "max_weight" | "min_weight" | "exclude" | "sector_max" | "sector_min"
         | "max_holdings" | "min_holdings" | "buy_in" | "max_volatility" | "max_turnover"

Rule:     id: str, type: RuleType, params: dict, priority: int (1–10),
          hard: bool, source: str   # source = the client's own words
          params by type:
            max_weight {ticker: str | "*", max: float}     min_weight {ticker: str, min: float}
            exclude {tickers: list[str]}                    sector_max/sector_min {sector: str, max|min: float}
            max_holdings/min_holdings {k: int}              buy_in {min: float}
            max_volatility {max: float}                     max_turnover {max: float}

Client:   client_id, name, story, universe: list[str],
          current_weights: dict[str,float] = {}, rules: list[Rule],
          planted_conflict: list[str] | None = None   # eval only

Proposal: weights: dict[str,float], thesis: str, reasons: dict[str,str]
```

### 5.2 Referee output (`models.py`)
```
CheckResult: rule_id, type, passed: bool, actual: float, limit: float,
             violation: float, explain: str

Relaxation:  rule_id, old_limit: float, new_limit: float, cost: float, explain: str

Receipt:     receipt_id: str, timestamp: str, client_id: str,
             verdict: "PASS" | "VIOLATIONS_REPAIRED" | "RULES_INFEASIBLE" | "ERROR",
             checks: list[CheckResult], dust_removed: list[str],
             rules_feasible: bool, conflict_set: list[str], conflict_explain: str,
             cheapest_relaxation: list[Relaxation],
             repaired_weights: dict[str,float], capital_moved: float,
             sharpe_before: float, sharpe_after: float, vol_after: float,
             summary: str, notes: list[str]
```

### 5.3 Committee models (`models.py`)
```
AnalysisRequest: client_id, client_story, rules_text: list[str], as_of: str
Memo:            agent: str, favor: list[str], avoid: list[str],
                 sector_views: dict[str,str],    # e.g. {"Tech": "overweight"}
                 reasons: dict[str,str], confidence: float (0–1)
ReviewRequest:   client_id, round: int, failures: list[str],    # plain-English failed checks
                 proposal: Proposal, conflict_explain: str
Stance:          agent: str, stance: "concede" | "defend" | "modify",
                 change: str, why: str
VerifyRequest:   client: Client, proposal: Proposal
DebateEntry:     round: int, agent: str, kind: "memo" | "proposal" | "receipt" | "stance" | "note",
                 text: str, stance: str | None
CommitteeResult: client_id, final_proposal: Proposal, receipt: Receipt,
                 first_receipt: Receipt, debate_log: list[DebateEntry],
                 rounds: int, self_corrected: bool, notes: list[str]
```

### 5.4 Function signatures (`contract.py`)
```
referee(client: Client, proposal: Proposal) -> Receipt
analyze(agent: str, req: AnalysisRequest) -> Memo                 # agent ∈ {"macro","fundamentals","risk"}
review(agent: str, req: ReviewRequest) -> Stance
chair_propose(client: Client, memos: list[Memo]) -> Proposal
chair_revise(client: Client, proposal: Proposal, receipt: Receipt, stances: list[Stance]) -> Proposal
async run_committee(client: Client, transport: Transport, max_rounds: int = 3) -> CommitteeResult

Transport (protocol, all async): async analyze(agent, req) -> Memo | None
                                 async review(agent, req) -> Stance | None
                                 async verify(req: VerifyRequest) -> Receipt
                                 name: str   # "local" or "agents"
```
**Why async:** inside a uAgent, asking another agent (`ctx.send_and_receive`) is `await`-only, so the loop
must be async. LocalTransport wraps the plain (sync) brain functions with `await asyncio.to_thread(...)`.
FastAPI awaits `run_committee` directly; the eval script uses `asyncio.run(...)`. All other brain functions
(`referee`, `analyze`, `review`, `chair_*`) stay normal sync functions.

### 5.5 Wire messages between agents (`agents/messages.py`)
**Verified on uagents 0.26.1:** a uAgents `Model` is a **Pydantic v1** model, while `models.py` uses Pydantic v2.
Never put v2 models inside a uAgents message. Instead, every wire message carries **JSON text**:
```
AnalysisRequestMsg(Model): agent: str, payload: str     # payload = AnalysisRequest.model_dump_json()
MemoMsg(Model):            payload: str                 # Memo as JSON
ReviewRequestMsg(Model):   agent: str, payload: str     # ReviewRequest as JSON
StanceMsg(Model):          payload: str                 # Stance as JSON
VerifyRequestMsg(Model):   payload: str                 # VerifyRequest as JSON
ReceiptMsg(Model):         payload: str                 # Receipt as JSON
ErrorMsg(Model):           error: str                   # sent back instead of crashing
```
Helpers in the same file: `pack(v2_model) -> str` and `unpack(cls, text) -> v2_model`. One-line conversions,
and both sides use the exact same shapes from `models.py`.

---

## 6. The math

### 6.1 Market estimates (`referee/market.py`)
From the last `LOOKBACK_DAYS` (756 ≈ 3 years) of daily prices:
- daily returns r_t = P_t / P_{t−1} − 1
- **μ** = mean(r) × 252 (annual expected return per stock)
- **Σ** = cov(r) × 252 (annual covariance), symmetrized: Σ ← (Σ + Σᵀ)/2
- **L** = Cholesky factor of Σ + 10⁻¹⁰·I (so ‖Lᵀw‖₂ = portfolio volatility)
- Portfolio: return μᵀw, volatility σ(w) = √(wᵀΣw), **Sharpe = (μᵀw − 0.04) / σ(w)**

Also computed for the analysts: 1/3/6-month return per stock and per sector, annual volatility,
max drawdown, correlation to SPY.

### 6.2 Conventions
- **Variables:** w ∈ ℝⁿ (weights, one per stock in the universe), z ∈ {0,1}ⁿ (held or not).
- **Base constraints (always on, never rules):** Σwᵢ = 1, wᵢ ≥ 0, wᵢ ≤ zᵢ, wᵢ ≥ DUST·zᵢ.
  Every position is either 0 or at least 0.5%. Every solver output already respects this.
- **Dust cleaning for proposals:** before checking an LLM proposal, positions below DUST are set to 0
  and the rest renormalized to sum to 1. Record the cleaned tickers in `dust_removed`.
  Weights for tickers outside the universe are an ERROR (say which).
- **Held** means wᵢ ≥ DUST. **Pass** means violation ≤ TOL (count rules: violation = 0).
- **Capital moved** between portfolios a and b = ½ Σ|aᵢ − bᵢ| (fraction of the money that changes hands).

### 6.3 The 10 rules: check, constraint, and relaxed form
For each rule: what `check()` computes (no solver), the exact solver constraint, and the
"elastic" version with a slack s ≥ 0 used only by the cheapest-fix step.

| Rule | check(): actual / violation | Solver constraint | Elastic form (slack s ≥ 0) |
|---|---|---|---|
| `max_weight` (ticker or `*`) | actual = wᵢ (or max over all i); viol = max(0, actual − max) | wᵢ ≤ max (for `*`: every i) | wᵢ ≤ max + s |
| `min_weight` | actual = wᵢ; viol = max(0, min − wᵢ) | wᵢ ≥ min | wᵢ ≥ min − s |
| `exclude` | actual = Σ_{excluded} wᵢ; viol = actual | wᵢ = 0 for each excluded i | wᵢ ≤ s (usually `hard`, so no slack) |
| `sector_max` | actual = Σ_{i∈sector} wᵢ; viol = max(0, actual − max) | Σ_{i∈S} wᵢ ≤ max | Σ ≤ max + s |
| `sector_min` | actual = Σ_{i∈sector} wᵢ; viol = max(0, min − actual) | Σ_{i∈S} wᵢ ≥ min | Σ ≥ min − s |
| `max_holdings` | actual = #{wᵢ ≥ DUST}; viol = max(0, actual − k) | Σzᵢ ≤ k | Σzᵢ ≤ k + s, s integer |
| `min_holdings` | actual = #{wᵢ ≥ DUST}; viol = max(0, k − actual) | Σzᵢ ≥ k | Σzᵢ ≥ k − s, s integer |
| `buy_in` | actual = smallest held weight; viol = Σ_{held, wᵢ<min} (min − wᵢ) | wᵢ ≥ min·zᵢ | wᵢ ≥ min·zᵢ − s (linear) |
| `max_volatility` | actual = √(wᵀΣw); viol = max(0, actual − max) | ‖Lᵀw‖₂ ≤ max (second-order cone) | ‖Lᵀw‖₂ ≤ max + s |
| `max_turnover` | actual = Σ\|wᵢ − cᵢ\|; viol = max(0, actual − max) | ‖w − c‖₁ ≤ max (c = current weights) | ‖w − c‖₁ ≤ max + s |

Every check also writes one plain-English sentence using the rule's `source`, e.g.
*"NVDA is 41.0% of the portfolio; the client said: 'No single position above 35%.'"*

### 6.4 Is it possible at all? (`solver.py`)
`build_problem(client, active_rule_ids, objective, elastic=False)` returns the cvxpy problem with the
base constraints plus the chosen rules. **is_feasible(client, rule_ids)**: objective = minimize 0,
solve with SCIP. Status `optimal`/`optimal_inaccurate` → feasible; `infeasible` → not feasible;
anything else → raise an error with the status.

### 6.5 Which rules clash? (deletion filter → minimal conflict set) (`conflicts.py`)
```
R = all rules                      # known infeasible
for each rule r in R (in order):
    if NOT is_feasible(R without r):     # still impossible without r → r isn't needed
        R = R without r
return R                           # minimal: removing ANY one rule in R makes it feasible
```
That's at most one solve per rule. Explanation sentence: *"These rules can't all hold: 'Keep at
least 30% in JNJ', 'Hold at least 10% UNH', 'Healthcare at most 35%' (30% + 10% = 40% > 35%)."*
Add the arithmetic when all clashing rules are linear weight rules. Otherwise just list them.

### 6.6 The cheapest fix (elastic program) (`relax.py`)
Elastic problem: base constraints + hard rules exactly + soft rules in elastic form (6.3).
```
minimize  Σ_rules priority_r × size_r
   size_r = 100 × s_r  for weight/sector/volatility/turnover rules (percentage points)
   size_r = s_r        for max_holdings/min_holdings (number of names)
```
Solve with SCIP. Every s_r > TOL is a relaxation: new_limit = old ± s_r (direction from the rule type).
If the elastic problem is itself infeasible, the **hard rules** clash: run the deletion filter on the
hard rules alone and report that set.
Test: applying the relaxations to the client must make `is_feasible` true.

### 6.7 Repair: nearest compliant portfolio (`repair.py`)
If the rules are feasible:
```
minimize ½ ‖w − p‖₁     subject to base constraints + all rules      (p = cleaned proposal)
```
If they're infeasible, repair against the **relaxed** client (after 6.6) and say so in the receipt.
Report repaired weights (drop entries < TOL), capital moved, Sharpe before/after, volatility after.

### 6.8 The receipt (`receipt.py`)
```
1. clean dust → p
2. checks = check(p, client)
3. feasible = is_feasible(client, all rules)
4. if not feasible: conflict_set = find_conflicts(); relax = cheapest_relaxation()
                    repaired = repair(p, relaxed client);  verdict = RULES_INFEASIBLE
   elif all checks pass: repaired = p;                     verdict = PASS
   else: repaired = repair(p, client);                     verdict = VIOLATIONS_REPAIRED
5. receipt_id = first 12 hex chars of sha256(canonical JSON of client + p)
6. summary = one sentence, e.g. "The proposal broke 2 of 7 rules. The nearest compliant portfolio
   moves 20% of capital and changes Sharpe from 1.74 to 1.81."
any exception → verdict ERROR with the message in notes (never crash the agent)
```

### 6.9 Verified example (checked with SCIP on real prices, Oct 17)
Dr. Patel's rules R1–R7 (PLAN.md Section 5) are **feasible**. Adding R8 "Hold at least 10% UNH"
makes them **infeasible**, and:
- deletion filter → **{R3 JNJ ≥ 30%, R4 Healthcare ≤ 35%, R8 UNH ≥ 10%}**
- cheapest fix → **raise R4 Healthcare cap from 35% to 40%** (cost 4 × 5 = 20)
- repairing "41% NVDA, 30% JNJ, 15% GOOGL, 14% XOM" under R1–R7 → NVDA cut to ~35%, XOM removed,
  KO/PG added; volatility lands exactly on the 18% cap.

Use these as integration tests (`tests/test_patel.py`). Exact repaired weights may differ slightly
with fresher prices; test the properties (rules pass, sums to 1), not exact numbers.

---

### 6.10 Rule price tags: what each rule costs (`referee/prices.py`)
Advisors and clients never see what a rule *costs*. Institutional tools (e.g. Axioma) sell this as
"constraint attribution". Here's our version:

1. **Best portfolio under all the rules.** Maximize mean-variance utility (concave, so exact with SCIP):
   ```
   maximize  U(w) = μᵀw − (γ/2)·‖Lᵀw‖²        γ = RISK_AVERSION = 3 (config)
   subject to base constraints + all rules
   ```
   Call the optimum U* and its Sharpe S*.
2. **Price of rule r.** Re-solve without rule r → U*₋ᵣ and S*₋ᵣ. Since removing a rule can only help,
   **price_r = U*₋ᵣ − U* ≥ 0** (up to solver tolerance; clip at 0). Report it in **percentage points of
   risk-adjusted return per year** (price × 100) together with the Sharpe change S*₋ᵣ − S*.
3. **binds** = price_r > 0.0001 (0.01 points). Non-binding rules "cost nothing": the client could keep or
   drop them freely. That's useful advice too.
4. If the client's rules are infeasible, compute the prices on the **relaxed** client (6.6) and say so.
5. **Solver settings (verified on C02 with real prices):** solve these utility problems with SCIP params
   `{"limits/time": 15, "limits/gap": 1e-3}` and SCIP's default feasibility tolerance. Do **not** use the strict
   `feastol 1e-9` first attempt from `solver.solve()`: with this quadratic objective it runs into the 15 s limit on
   every solve (2 minutes per client, unproven answers), while the settings above take ~0.1 s for all 8 solves with
   the same prices. Use `build_problem(client, ids)` for the constraints and your own objective + solve call.
   Verified result for Dr. Patel (C02): 'Keep at least 30% in legacy JNJ' costs **0.85 pts**, 'Annual volatility at
   most 18%' costs **0.70 pts** (Sharpe 1.95 → 1.79 without it, because it takes more risk), the other 5 rules
   cost ~0 (they don't bind). Use these as test expectations (±0.1).

**Output** (new model `RulePrice` in `models.py`, an additive change, announced loudly):
`rule_id, source, binds: bool, utility_cost_pts: float, sharpe_with: float, sharpe_without: float, explain: str`,
sorted by cost. Example sentence: *"'No fossil fuel companies' costs 0.8 points of risk-adjusted return a
year (Sharpe 1.21 → 1.29 without it)."* / *"'Healthcare at most 35%' costs nothing: it never binds."*

Function: `rule_prices(client) -> list[RulePrice]`. Not part of the receipt (the receipt stays frozen); the Chair
and the web app call it separately.

## 7. The committee

### 7.1 What each analyst sees (computed in Python, passed in the prompt)
| Analyst | Data block in its prompt | Must output (Memo) |
|---|---|---|
| **Macro** | 1/3/6-month return by sector and for SPY; best and worst 5 stocks over 3 months; as-of date | sector_views, favor/avoid, reasons |
| **Fundamentals** | Per ticker: trailing P/E, revenue growth, profit margin (missing → "n/a") | favor/avoid with reasons per ticker |
| **Risk** | Per ticker: annual volatility, max drawdown (3y), correlation to SPY; the 3 most correlated pairs | avoid/cap list, reasons, warnings |

All analysts also get the client's story and the rules **as text** (the `source` sentences).

### 7.2 Prompt skeletons (Claude Code fills in the details)
- **Analyst system prompt:** "You are the {Macro|Fundamentals|Risk} analyst on an investment committee
  for a financial advisor. Use ONLY the data provided. Be specific and brief. Reply with JSON matching
  this schema: {schema}."
- **Chair system prompt:** "You are the committee Chair. Combine the analysts' memos into one portfolio
  for this client, over these tickers only: {universe}. Weights must be numbers from 0 to 1 that sum
  to 1. Give a one-paragraph thesis and one reason per position. Reply with JSON: {schema}."
- **Review prompt (analyst):** "The independent Referee checked the committee's portfolio. These rules
  failed: {failures}. {conflict_explain}. Decide: concede (accept a change), defend (keep your view,
  explain why it doesn't break the rules), or modify (propose a different change). JSON: {schema}."
- **Revise prompt (Chair):** "Revise the portfolio. Referee findings: {failures}. Analyst stances:
  {stances}. Fix every failed rule while keeping as much of the original idea as possible. JSON: {schema}."

The Chair sees the rules as text and is **not** shown the repaired weights. That's why measuring
self-correction (M2) is honest.

### 7.3 The loop (`committee/loop.py`)
```
memos = [transport.analyze(a, req) for a in analysts]; drop None, add note
p = chair_propose(client, memos); first = r = transport.verify(VerifyRequest(client, p))
if r.verdict == RULES_INFEASIBLE:
    note = chair writes advisor note from r.conflict_explain + r.cheapest_relaxation
    return result(final = repaired weights under the relaxed rules, flagged as "needs advisor approval")
round = 1
while r.verdict != PASS and round <= max_rounds:
    stances = [transport.review(a, ReviewRequest(...)) for a in analysts]; drop None, add note
    p = chair_revise(client, p, r, stances); r = transport.verify(...); round += 1
if r.verdict != PASS: final = r.repaired_weights, note "committee could not self-correct; Referee repair applied"
else: final = p, self_corrected = True
log every memo, proposal, receipt summary, stance into debate_log
```

---

## 8. The LLM layer (`committee/llm.py`, built with LangChain)

`complete_json(role, system, user, schema) -> schema instance`   (role = "analyst" or "chair" picks the model)

**Chat models (LangChain), chosen by `config.LLM_PROVIDER`:**
| Provider | LangChain class | Settings |
|---|---|---|
| **asi1** (default) | `ChatOpenAI` from `langchain-openai` | `base_url=ASI1_BASE_URL`, `model="asi1"`, key `ASI1_API_KEY` (from asi1.ai/dashboard/api-keys). Fetch's own model: Fetch judges notice |
| **gemini** | `ChatGoogleGenerativeAI` from `langchain-google-genai` | key `GEMINI_API_KEY`; also counts for MLH "Best Use of Gemini" |
| **anthropic** | `ChatAnthropic` from `langchain-anthropic` | key `ANTHROPIC_API_KEY`; Haiku for analysts, Sonnet for the Chair |

**Structured output:** first try `model.with_structured_output(schema)`. If the provider doesn't support it
(possible on asi1), fall back to a prompt that ends with the schema's JSON format instructions
(`PydanticOutputParser`), strip code fences, validate with Pydantic, and retry once with the
validation error appended. Temperature 0.2 for analysts, 0 for the Chair.

**Cache:** our own disk cache: `cache/<sha256(provider+model+system+user)>.json`. A hit returns instantly,
so reruns and the evaluation are free and identical. **Keys** only from `.env`. Never print them.

Why LangChain: one interface for three providers (the switch is a single setting), structured output
built in, and a framework Fetch explicitly supports ("LangChain brains, wrapped with uAgents").
Only `committee/llm.py` imports LangChain. The loop, the Referee and the contract don't depend on it.

---

## 9. The Fetch agents (Part B builds, Part C connects)

| Agent | Handles | Calls | Agentverse description |
|---|---|---|---|
| **Chair** | Chat Protocol (user text) | `run_committee(client, AgentTransport)` | "Investment committee: builds a portfolio that follows your client's rules, with a debate log and a verification receipt." |
| **Referee** | `VerifyRequest`; also Chat Protocol (pasted JSON) | `referee()` | "Portfolio Referee: checks any AI-proposed portfolio against client rules, proves when rules are impossible, finds the clash and the cheapest fix." |
| **Macro** | `AnalysisRequest`, `ReviewRequest` | `analyze("macro")`, `review("macro")` | "Macro analyst for the SwarmFolio committee." |
| **Fundamentals** | same | `analyze/review("fundamentals")` | "Fundamentals analyst for the SwarmFolio committee." |
| **Risk** | same | `analyze/review("risk")` | "Risk analyst for the SwarmFolio committee." |

**Chair chat input it must understand:**
- "Build a portfolio for Dr. Patel" or "…for client C02" → load that client
- "list clients" → names + one-line stories
- Pasted client JSON (Tier 3: pasted plain-English rules)
- Anything else → a friendly help message with examples

**Chair chat reply format:**
1. **Verdict line**, e.g. "✅ Compliant after 2 rounds" or "⛔ These rules are impossible"
2. **Debate highlights:** who conceded, defended or modified, and what
3. **Final weights:** top holdings, sorted
4. **Receipt summary** + receipt_id
5. **Notes:** timeouts, fallbacks

### 9.2 How every agent is built (from Fetch's docs, checked against uagents 0.26.1 on Python 3.14)
Reference example: https://innovationlab.fetch.ai/resources/docs/examples/chat-protocol/asi-compatible-uagents
- `Agent(name=..., seed=<from .env>, port=<AGENT_PORTS>, mailbox=True, publish_agent_details=True)`
- **Chat Protocol** (Chair and Referee only): `from uagents_core.contrib.protocols.chat import ChatMessage,
  ChatAcknowledgement, TextContent, EndSessionContent, chat_protocol_spec` (AgentChatProtocol 0.3.0);
  `Protocol(spec=chat_protocol_spec)`; on every `ChatMessage`: **first send `ChatAcknowledgement`**, join
  the `TextContent` parts, do the work, reply with `ChatMessage(content=[TextContent(...), EndSessionContent(...)])`;
  also handle `ChatAcknowledgement` (do nothing). `agent.include(protocol, publish_manifest=True)`.
- **Committee protocol** (all 5): handlers for the JSON envelopes in MASTER 5.5, each replying with
  `ctx.send(sender, ...)`; on any exception reply with `ErrorMsg` instead of crashing.
- **Calling another agent and waiting:** `reply, status = await ctx.send_and_receive(address, msg,
  response_type={MemoMsg, ErrorMsg}, timeout=AGENT_TIMEOUT_S)`. `reply` is `None` on timeout → retry once → fallback.
- **Slow brains:** analyst/Referee handlers call the brain with `await asyncio.to_thread(fn, ...)` so the agent
  stays responsive (the mailbox keeps working while the LLM thinks).
- **The Chair takes 1–2 minutes:** acknowledge immediately, send a short "Convening the committee…"
  `ChatMessage`, then the final answer. Test early that ASI:One shows both (Fetch checkpoint, 5 PM).
- **Running:** `run_all.py` starts the 5 agents as 5 processes (ports 8001–8005) and prints each address.
  Agent addresses go into `.env` (`REFEREE_ADDRESS`, …) so the Chair knows whom to call.
- **Connecting to Agentverse:** open each agent's **Inspector** link from its startup log → **Connect** →
  **Mailbox**. Then edit the profile (name, handle, description from the table above). Look for
  "Successfully registered as mailbox agent in Agentverse" in the log.
- `ChatAgent` (`uagents.experimental.chat_agent`) exists but is **experimental** and LLM-tool-driven.
  Don't use it for the Chair, whose job is a precise multi-step loop.
- Fetch's example pins `uagents==0.25.5`; **0.26.1 works on Python 3.14** with Chat Protocol 0.3.0. Only
  downgrade if something specific breaks.

**Registration:** each agent gets a stable seed phrase from `.env` (so its address never changes)
and is connected to Agentverse the way the hackpack shows (typically a mailbox). Save all 5 profile URLs.

---

## 10. The evaluation

### 10.1 Clients (`eval/make_clients.py`, Part B; verified by Part A)
- C01 easy, C02 Dr. Patel, C03 Dr. Patel + "UNH ≥ 10%" (hand-made in A0)
- C04–C21: 18 feasible clients, 4–8 rules each, varied (exclusions, sector caps, legacy holdings, volatility caps)
- C22–C26 (5) with a **planted conflict** and a `planted_conflict` field (26 clients in total with C01–C03)
- 2 of the above with 9–10 rules
- Fixed random seed; each client has a one-sentence story

### 10.2 Metrics (`eval/run_eval.py`, Part A, brains + LocalTransport)
| # | Formula |
|---|---|
| M1 | share of feasible clients whose **first** proposal has ≥ 1 failed check; mean # failed checks |
| M2 | same for the Chair's **last own** proposal (before any Referee repair) |
| M3 | share of feasible clients whose **final** portfolio passes every check (target 100%) |
| M4 | median capital moved by repair; mean Sharpe change |
| M5 | infeasible clients detected / 5; conflict set == planted set / 5 |
| M6 | share of stances concede / defend / modify; mean rounds |

Outputs: `results.json`, `results.md` (table), `violations.png` (bar chart: M1 → M2 → M3).

---

### 10.3 The feedback experiment (`eval/experiment.py`): the headline *finding*
**Research question:** can math feedback teach an AI to follow a client's rules, and does it matter whether
the math *explains* itself?

**Design (paired, so the comparison is fair):**
- **Clients:** feasible clients only (C01, C02 + the 15 feasible generated ones). Infeasible clients can't
  comply, so they're judged separately by M5.
- **Trials:** T = 3 per client. The trial number goes into the prompt (so the cache key differs) and eval
  calls use temperature 0.7, so the trials are genuinely different samples.
- **Shared start:** per client-trial, the 3 memos and the Chair's **first draft** are made once and reused by all
  three conditions. Every condition starts from exactly the same draft.
- **Three conditions,** each = up to 3 rounds of *Chair-only* revision (no analyst stances, to isolate the
  effect of the feedback), checked by the Referee after every round, stopping early once compliant:
  | Condition | What the Chair is told each round |
  |---|---|
  | **A. Self-check** | "Re-check your portfolio against the client's rules and fix anything that breaks them." No Referee info. (What most AI products do today.) |
  | **B. Bare verdict** | The ids + client wording of the rules that failed. No numbers. |
  | **C. Explained** | The Referee's explain sentences (actual vs limit, e.g. "NVDA is 41.0%, limit 35%") + the conflict explanation if any. **Never the repaired weights** (that would just be copying). |
- **Budget:** 17 clients × 3 trials × (4 shared calls + 3 conditions × ≤3 revisions) ≈ 650 LLM calls, run with
  4 at a time. Add `--clients N --trials T` flags and smoke-test with `--clients 3 --trials 1` first.

**Metrics** for each condition at round 0, 1, 2, 3:
- **Compliance rate** (all checks pass), **mean # broken rules**, **mean total violation** (weight rules in
  percentage points; count rules reported separately)
- **Intent kept:** capital moved between the first draft and the final revision (lower = more of the AI's idea kept)
- **Uncertainty:** 95% bootstrap confidence intervals over client-trials
- **Paired test:** for C vs B and C vs A, the number of client-trials where C became compliant in fewer /
  the same / more rounds, plus a sign-test p-value

**Outputs:** `eval/results/experiment.json`, `experiment.md` (table + a 3-sentence plain-English finding) and
`learning_curves.png` (compliance rate vs round, one line per condition, shaded CIs).

**Honesty rule:** report whatever comes out. If B ≈ C, that's a finding too ("telling the AI *which* rule broke
is enough; the numbers don't help"). The finding just needs to be true and clearly stated.

## 11. Prompts for Claude Code (Part A)

Paste one at a time. Start a **fresh session** (`/clear`) for each to save usage. Commit after each.

**A0: Setup, data, contract, fakes (12:00)**
```
Read MASTER.md (the source of truth) and CLAUDE.md. Do the Part A setup:
1) git init; .gitignore (.venv, .env, cache/, __pycache__); requirements.txt (cvxpy, pyscipopt,
   numpy, pandas, yfinance, pydantic, python-dotenv, fastapi, uvicorn, pytest, matplotlib, uagents,
   langchain-core, langchain-openai, langchain-google-genai, langchain-anthropic); .env.example with ASI1_API_KEY, GEMINI_API_KEY,
   ANTHROPIC_API_KEY and agent seed phrases; config.py with every switch in MASTER 4.2.
2) data/prices.csv already exists (SwarmFolio's MIT data, up to Jul 1 2026): it's the fallback.
   Write data/refresh_data.py (MASTER 4.1): prices for the 19 tickers + SPY from 2015-01-01 to today
   via yfinance; save to a temp file and only replace data/prices.csv if the download is complete. Fundamentals snapshot to
   data/fundamentals.json. data/sectors.json by hand.
3) referee/schema.py (MASTER 5.1), models.py (5.2–5.3), agents/messages.py (the uAgents JSON
   envelopes + pack/unpack helpers, 5.5); contract.py with the
   signatures in MASTER 5.4 (docstrings + NotImplementedError); fakes.py returning realistic
   hard-coded outputs for every function (one violation in the first receipt, a concede and a
   defend, PASS after round 2; run_committee is async per 5.4); data/samples/ with one JSON per model.
4) data/clients/C01.json (easy), C02.json (Dr. Patel, PLAN.md Section 5), C03.json (C02 + rule R8
   "min_weight UNH 0.10", planted_conflict ["R3","R4","R8"]).
5) tests: every sample and client validates. Tell me the venv commands, run refresh_data.py, run pytest.
```
✅ pytest green, prices end near today. **Push to GitHub, then start Devin on B1.**

**A1: check() (12:45)**
```
Build referee/market.py (MASTER 6.1) and referee/check.py (MASTER 6.2 dust cleaning + every row of
the table in 6.3, check column). Tests: for each of the 10 rule types, one passing and one failing
case, plus dust cleaning. Run pytest.
```

**A2: solver + is_feasible (2:00)**
```
Build referee/solver.py: build_problem() and is_feasible() exactly per MASTER 6.2–6.4, with the
"Solver constraint" column of 6.3 and SCIP. Tests: C01, C02 feasible; C03 infeasible; the buy_in
5% + max_holdings 3 + min_holdings 3 + max_weight 30% case infeasible. Run pytest, then explain in
3 sentences how "at most 8 holdings" becomes math with z.
```

**A3: find_conflicts (3:00)**
```
Build referee/conflicts.py per MASTER 6.5 with the explanation sentence. Tests: C03 → exactly
{R3, R4, R8}; feasible clients → []. Run pytest.
```

**A4: cheapest_relaxation (3:30)**
```
Build referee/relax.py per MASTER 6.6 using the "Elastic form" column of 6.3. Tests: C03 → only
R4 relaxed, 35% → 40%, cost 20, no hard rule touched, and applying it makes is_feasible true.
Run pytest.
```

**A5: repair + receipt (4:00)**
```
Build referee/repair.py (MASTER 6.7) and referee/receipt.py (MASTER 6.8): referee(client, proposal)
-> Receipt. Tests (tests/test_patel.py, MASTER 6.9): the bad Patel proposal → VIOLATIONS_REPAIRED,
the repaired weights pass every check and sum to 1; C03 → RULES_INFEASIBLE with the right conflict
set; same inputs → same receipt_id; garbage input → verdict ERROR, no crash. Run pytest.
```
✅ **5 PM checkpoint: push. The Referee is done.**

**A5b: Referee Agent goes real (5:00, ~20 min)**
```
Devin's agents (agents/) are merged and run on fakes. Make ONLY the Referee Agent use the real
referee() from referee/receipt.py (leave the other agents on fakes). Run it, and give me a sample
chat message (Dr. Patel's client JSON + the bad proposal from MASTER 6.9) to paste into ASI:One.
```
✅ The real Referee answers in ASI:One. **Fetch's core is proven at 5:30 PM, not 1 AM.**

**A6: LLM layer with LangChain (5:30)**
```
Build committee/llm.py per MASTER 8 with LangChain: provider switch (asi1 via ChatOpenAI with the
ASI:One base URL, gemini, anthropic), with_structured_output with the PydanticOutputParser fallback,
one retry, and the disk cache. LLM_PROVIDER is "<asi1|gemini|anthropic>". Make one tiny test call
with a small schema and show the result; a second identical call must be instant. Never print keys.
```

**A7: analysts + Chair (6:00)**
```
Build committee/analysts.py (analyze + review for macro/fundamentals/risk, data blocks per MASTER 7.1,
prompts per 7.2) and committee/chair.py (chair_propose, chair_revise; renormalize weights, drop
tickers outside the universe and note it). Run on C02 and print the 3 memos and the proposal.
```

**A8: loop + LocalTransport (6:45)**
```
Build committee/transport_local.py (async LocalTransport using asyncio.to_thread) and committee/loop.py
with async run_committee per MASTER 5.4 and 7.3. Also committee/feedback.py: format_feedback(receipt, client,
mode) with the three modes of MASTER 10.3 ("self", "bare", "explained"), and in committee/chair.py a
chair_revise_with(client, proposal, feedback_text, stances=None) that chair_revise uses with mode "explained".
The experiment (A10) will call these directly. Run C01, C02, C03 and print readable transcripts. Then switch USE_FAKES to False only for
api.py and confirm the web app (built by Devin) runs on real brains.
```
✅ **Tier 1 done (~9:30 PM): push.**

**A9: verify Devin's clients (after B2 is merged)**
```
For every client in data/clients/: validate it, run is_feasible, and for clients with
planted_conflict check that find_conflicts returns exactly that set. Fix clients that don't match
(change the client file, not the Referee) and print a summary table.
```

**A10: evaluation + the feedback experiment (after A9)**
```
Read MASTER 10.2 and 10.3 only. 1) Build eval/run_eval.py for metrics M1–M6 (run_committee with
LocalTransport). 2) Build eval/experiment.py exactly per MASTER 10.3: paired design (shared memos and first
draft per client-trial), conditions self/bare/explained via format_feedback and chair_revise_with, Referee
check after every round, temperature 0.7 and the trial number in the prompt, 4 calls at a time,
--clients/--trials flags, bootstrap CIs, the paired sign test, and the outputs experiment.json,
experiment.md and learning_curves.png. Smoke-test with --clients 3 --trials 1, show me the table, then run
the full experiment in the background and tell me how to check on it. Finish with the plain-English
finding and the demo headline sentence, using only the real numbers.
```

**A11: rule price tags (after A10 starts running)**
```
Read MASTER 6.10 only. Add RulePrice to models.py (additive; say so loudly) and build referee/prices.py:
rule_prices(client) -> list[RulePrice] with the utility objective (RISK_AVERSION = 3 in config.py), one
re-solve per rule, price clipped at 0, binds threshold 0.0001, relaxed client if infeasible, sorted by cost.
Tests: removing a rule never lowers utility; a rule that can't bind (e.g. a 99% cap) costs ~0; C02's prices
are computed in under 5 s and match MASTER 6.10's verified C02 numbers (JNJ ~0.85, volatility ~0.70, others ~0). Then make the Chair Agent's reply include the top 3 price tags, and let it answer
"price tags for <client>". Run pytest, commit and push.
```

---

## 12. Prompts for Devin (Part B)

Connect Devin to the GitHub repo. Each task: its own branch + pull request. **Only edit the files
listed.** Use `fakes.py` for all brains (via `config.USE_FAKES`).

**Order for Devin: B3 (agents) → B2 (clients) → B1 (web app) → B4 (README) → B5 (Paper style).**

**B1: Web app on fakes (api.py + frontend/)**
```
Read MASTER.md sections 1, 4, 5 and 9. Build:
1) api.py (FastAPI): GET /clients (id, name, story, rules with source text); POST /committee
   {client_id} -> CommitteeResult; POST /referee {client, proposal} -> Receipt; GET /results ->
   eval/results/results.json if it exists. Brains imported via the USE_FAKES switch (MASTER 4.3).
   CORS open for local dev.
2) frontend/ (React + Vite + Tailwind) with 3 screens:
   (a) Client picker: cards with name, story, rule chips (each chip shows the client's own words).
   (b) Committee run: "Convene the committee" button, then the debate as a timeline by round:
       memos, proposal, Referee findings, stances with badges (concede / defend / modify),
       revealed step by step with a short animation so it feels live; a progress state while waiting.
   (c) Receipt: big verdict, every rule pass/fail with its explain sentence, conflict explanation
       and cheapest fix when present, before/after weights chart (first proposal vs final),
       receipt_id, "copy JSON" button.
   Plus a Results page showing results.json as a table and chart.
   Use a neutral placeholder style (system font, whitespace, one accent color): the final look
   comes from a Paper design in task B5, so keep styles in one place (Tailwind config + CSS
   variables) and components small.
Only edit api.py and frontend/. Open a PR with run steps (backend + frontend).
```

**B2: synthetic clients (eval/make_clients.py, data/clients/C04+)**
```
Read MASTER.md sections 5.1 and 10.1. Write eval/make_clients.py (fixed seed) generating C04
onward: 18 feasible clients and 5 clients with a planted conflict (set planted_conflict to the
clashing rule ids, and put the arithmetic that makes it impossible in a comment), 2 of them with
9–10 rules. Realistic stories and rule "source" sentences. Use only the 19 tickers and sectors in
data/sectors.json. Validate every client against referee/schema.py. Only edit
eval/make_clients.py and new files in data/clients/. Open a PR.
```

**B3: Fetch agents (agents/)**
```
Read MASTER.md sections 4.5, 5 (especially 5.4 async and 5.5 wire messages) and 9 (especially 9.2,
which summarizes Fetch's docs), plus https://innovationlab.fetch.ai/resources/docs/examples/chat-protocol/asi-compatible-uagents
and https://uagents.fetch.ai/docs/guides/send_receive. Use uagents 0.26.1 APIs exactly as there; don't guess.
Build referee_agent.py, chair_agent.py, macro_agent.py, fundamentals_agent.py, risk_agent.py,
transport.py (async AgentTransport: send_and_receive with timeout, one retry, fallbacks per MASTER 4.5)
and run_all.py (starts all 5 on ports 8001–8005 and prints their addresses). Wire messages are the
JSON envelopes in agents/messages.py (use pack/unpack; never put Pydantic v2 models inside a uAgents
Model). Brains come from the USE_FAKES switch (MASTER 4.3), called with asyncio.to_thread. The Chair
and Referee speak the Chat Protocol (acknowledge first, then reply with TextContent + EndSessionContent);
the Chair sends a "Convening the committee…" message before the final answer and uses the input and
reply formats in MASTER 9. Seeds and peer addresses from .env. Only edit those files in agents/.
Open a PR with exact steps: run locally, open each Inspector link → Connect → Mailbox, and test from ASI:One.
```

**B5: Apply the Paper design (after design/ is pushed)**
```
Read design/ (Paper exports: style guide, the 3 screens, their HTML/CSS). Restyle frontend/ to
match the design exactly: colors, typography, spacing, components, layout and motion. Keep all
behavior and data wiring unchanged. Put design tokens in the Tailwind config / CSS variables.
Check desktop and phone widths. Only edit frontend/. Open a PR with before/after screenshots.
```

**B4: README draft**
```
Draft README.md: tagline, problem, architecture and agent diagrams (MASTER 4.4–4.5), the "built
before vs at LA Hacks" table (PLAN.md Section 1) plus "Design notes were written before the event;
all code was written during it", how to run (brains only / with agents), placeholders for results,
Agentverse URLs and the ASI:One chat link, credits (SwarmFolio, MIT). Only edit README.md. Open a PR.
```

---

## 13. Connecting everything (Part C, Claude Code + you)

**C1: real brains into the agents (~11 PM)**
```
Read MASTER.md 4 and 13. Devin's agents (agents/) are merged. Set USE_FAKES = False. Run the
5 agents with run_all.py and, with USE_AGENT_NETWORK = False first, check the Chair Agent answers a
local test chat for C02 using real brains. Then set USE_AGENT_NETWORK = True and test again. Fix
mismatches with the smallest change, and tell me which file and which part (A or B) it belonged to.
Never change agents/messages.py or contract.py silently.
```
You: register / connect all 5 agents on Agentverse; save profile URLs.

**C2: full network in ASI:One (~1 AM)**
```
In ASI:One the Chair Agent should run the full 5-agent debate for Dr. Patel (C02) and the
impossible client (C03). Watch all 5 agents' logs while I test. Make timeouts, retries and
fallbacks behave per MASTER 4.5 (test by stopping the Macro agent mid-run). Report what you saw.
```
You: make a public **ASI:One shared chat URL** for C02 and C03. **Submit to the Fetch Submission Agent now.**

---

## 13b. The Paper design (you, Part D)

**Prize:** Best Designed Hack: $1,500 / $1,000 / $500. **Judged on:** design fundamentals (hierarchy,
legibility, consistency, contrast), ease of use, and **personal craft and character** (it must not
look AI-generated). Setup: Paper desktop app, redeem **LAHACKS26** for free Pro (cancel before it
renews in a month), visit their booth.

You own this, in the gaps while Claude Code and Devin build. The "personal craft" is literally yours.

**D1: Style guide (~30 min, afternoon).** A direction that fits "trustworthy math referee":
- Serious finance feel (a research report or trading terminal), not a generic SaaS dashboard
- Two typefaces: a strong one for headings, a clean monospace for numbers and receipts
- Mostly neutral colors + three meaning colors used everywhere: pass, fail, and the stance colors
- One signature element judges remember, e.g. the receipt drawn like a printed audit receipt with
  its ID and a "VERIFIED" stamp, or a referee's red card when a rule breaks

**D2: Three screens (~2 hours, evening)** matching B1: client picker, debate timeline, receipt (+ Results
if time). Design the *impossible client* state carefully (conflict + cheapest fix). It's the demo's best moment.

**D3: Export (~15 min).** Put screenshots, the style guide and the HTML/CSS Paper gives you into `design/`
and push. Ask at the Paper booth how best to hand a design to a coding agent that isn't connected to
Paper's MCP (Devin runs in the cloud). If Claude Code usage allows, Claude Code can read the canvas
over MCP instead.

**Devpost note:** add 2–3 screenshots of the Paper canvas (style guide + screens) and one sentence on
the design idea.

## 14. Checkpoints, fallbacks, cut order

| Checkpoint | Time | If missed |
|---|---|---|
| Fake agents chat in ASI:One | 5:00 PM | Stop everything else (Paper first) and fix the agent setup with Claude Code |
| Contract pushed, Devin started | 12:45 PM | Skip Devin; Part A continues; do B1 yourself later |
| Paper design exported to design/ | 10:00 PM | Skip B5; enter Paper with the clean default UI, or skip Paper |
| Referee done (A5) | 5:00 PM | Cut `max_turnover` and `sector_min`; keep the other 8 rules |
| Tier 1: loop + app on real brains | 9:30 PM | Use the terminal transcript as the demo |
| Eval headline number | 11:00 PM | Run eval on 10 clients |
| Fetch-qualified: Chair + Referee in ASI:One | 1:00 AM | Referee Agent alone in ASI:One |
| 5-agent network | 4:00 AM | Analysts back to LocalTransport inside the Chair (one setting) |

**Cut order:** Tier 3 → analyst agents → eval size → Chair Agent.
**Never cut:** Referee + tests, the loop, the headline number, the video, both submissions.

**Tier 3 (one, Sunday 7–9 AM):** plain-English rules → JSON (with source quotes); ASI:One Interactive
Cards for the receipt; Payment Protocol (testnet fee per verification); PSO explorer agent.

---

## 14b. Rescue prompts (paste when stuck)

**Error:**
```
Running <command> gives this error: <paste the FULL error>. Find the cause and make the smallest
fix. Don't rewrite the file. Explain what was wrong in one sentence.
```

**AI going in circles 3+ times:**
```
Stop. Explain what you think the problem is and list 2 different approaches. Don't change code yet.
```
Still stuck: `git stash` (or `git checkout .`) to return to the last commit, and retry the step with a smaller prompt.

**Agents not talking to each other:**
```
The <X> agent isn't receiving messages from the <Y> agent. Show both agents' addresses and logs,
check they use the same envelopes from agents/messages.py (MASTER 5.5), that addresses in .env match
the startup logs, that both show "Successfully registered as mailbox agent", and check the uagents
docs. Make the smallest fix.
```

**Understand before judging:**
```
Explain referee/<file>.py like I'm a beginner: first the idea in plain English, then each function
line by line. Then ask me 3 questions a judge might ask and check my answers.
```

**Running out of time:**
```
It's <time>. Look at MASTER.md Section 14 (checkpoints and cut order) and the priority ladder in
Section 3, and tell me what to cut so Fetch stays safe and I still submit by 11:30 AM.
```

---

## 15. Ship (Sunday)

- **F1 (Claude Code):** "Finalize README.md: fill in results from eval/results/results.md, the
  Agentverse URLs and the ASI:One chat URLs. Draft my Devpost description from PLAN.md Section 13."
- **Video (you):** 2–3 min, follow PLAN.md Section 11. Show ASI:One first, then the web app for the visual story (also the backup).
- **Submit by 11:30 AM:**
  - [ ] **Devpost:** both tracks (Applied Intelligence + Agentverse), challenges (Fetch.ai, **Paper**, Devin, Gemini if used), repo, video, results table, "built here" table
  - [ ] **Fetch Submission Agent:** https://asi1.ai/festival/lahacksai2026/dashboard, with the chat URLs + 5 Agentverse profile URLs
- **11:30–12:30:** rehearse 3×. Judge answers: PLAN.md Section 12.
