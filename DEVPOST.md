# SwarmFolio Referee: Devpost draft

> Draft for the Devpost submission. Replace every `TODO` / `__` with real numbers and links before submitting. Don't round optimistically: the judges can rerun it.

**Tagline:** AI proposes. Math decides.

**Links:** GitHub `TODO` · Demo video `TODO` · ASI:One chat `TODO` · Agentverse: Chair `TODO`, Referee `TODO`, Macro `TODO`, Fundamentals `TODO`, Risk `TODO`

---

## Inspiration

Advisors are starting to let AI draft client portfolios, and the drafts break the client's rules. In the BiasMix-Finance study (ICLR 2026 workshop), 47.6–85.7% of AI first drafts violated the client's constraints. An advisor is a fiduciary and can't send a portfolio with 41% in one stock to a client who said "no single position above 35%". FINRA's 2026 report also expects firms using generative AI to have guardrails and audit trails.

I built SwarmFolio, a portfolio optimizer that used particle swarm optimization (PSO), before this hackathon. Its swarm-based rule check once called a perfectly feasible set of rules impossible. That's fine for a search heuristic, but not for something that has to *verify*. The idea behind this project is that the verifier, not the AI, is the product.

## What it does

SwarmFolio Referee is an investment committee made of five Fetch.ai agents, which you can chat with in ASI:One:

1. **Three analyst agents** (Macro, Fundamentals, Risk) study the market data and each write a memo.
2. **A Chair agent** turns the memos into a portfolio for the client.
3. **A Referee agent** checks the portfolio against the client's rules with an **exact optimization solver**. It reports:
   - which rules broke and by how much, quoting the client's own words;
   - whether the rules can be met at all;
   - if not, the **smallest set of rules that clash**, and the **cheapest fix**;
   - the **nearest compliant portfolio**.

   Everything goes into a reproducible **receipt**.
4. The analysts read the receipt and **concede, defend or modify**, and the Chair revises. This runs for up to 3 rounds, and you can watch who changes their mind.
5. **Price tags:** the Referee also says what each rule *costs* the client. For example, Dr. Patel's "Keep at least 30% in legacy JNJ" costs 0.85 points of risk-adjusted return a year, while her Healthcare cap costs nothing.

In ASI:One, the answers come with **Interactive Cards**: a receipt card, a client picker with a "Build portfolio" button for each client, and a price-tag card. The Referee is also a standalone agent, so any other AI can paste a portfolio and rules and get a receipt.

**Example:** an AI proposes NVDA 41%, JNJ 30%, GOOGL 15%, XOM 14% for Dr. Patel, a synthetic client.
- The Referee finds 3 broken rules: NVDA is over the 35% cap, XOM breaks "no fossil fuels", and volatility is 20.8% against an 18% limit.
- It repairs the portfolio while moving 20% of capital.
- Add "hold at least 10% UNH" and it proves the rules are impossible: 30% JNJ + 10% UNH = 40% Healthcare > 35%. The cheapest fix is to raise the Healthcare cap to 40%.

## How we built it

- **Referee (CVXPY + SCIP), no LLM:**
  - 10 rule types (single-name caps and floors, exclusions, sector caps and floors, max/min holdings, minimum position size, volatility cap, turnover cap).
  - These are modeled as a mixed-integer convex program: binary "held" variables, and a second-order cone for volatility.
  - A **deletion filter** finds a minimal conflicting rule set.
  - An **elastic program** finds the cheapest priority-weighted relaxation.
  - An **L1 projection** finds the nearest compliant portfolio.
  - Rule price tags re-solve a mean-variance utility problem without each rule.
- **Committee (LangChain):** the analysts and the Chair run on Fetch's **ASI:One** model by default, with a Gemini/Anthropic switch. Every response is validated with Pydantic, retried once on bad JSON, and cached for reproducibility.
- **Agents (Fetch.ai uAgents → Agentverse → ASI:One):** 5 agents with stable seeds, mailbox-connected to Agentverse. The Chair and Referee speak the Chat Protocol, and all 5 speak a committee protocol of JSON envelopes.
  - **Brains vs. phones:** every agent is a thin wrapper around plain Python functions. The committee loop takes either a local transport or a Fetch transport, so the whole system also runs without the network.
  - **Reliability:**
    - The Referee gets a timeout and one retry, then falls back to the local Referee.
    - The analysts are asked concurrently with a longer timeout and no retry on a timeout. A silent analyst is skipped and the reply says so.
    - Every handler failure becomes an error message instead of a crash.
- **Evaluation:**
  - 26 synthetic clients, including seeded "hard" clients whose volatility caps sit 0.5–1.0 points above the solver's minimum, and clients with planted conflicts.
  - A paired feedback experiment (self-check vs. bare verdict vs. the Referee's explanation) with bootstrap CIs and sign tests. The run reported here covers the 4 hard clients C91–C94 × 3 trials (12 client-trials, `asi1`). A larger run on C10–C24 with `asi1-mini` is in progress.
- **Web app:** FastAPI + React (Vite, Tailwind, Recharts), designed in Paper (**TODO-confirm**).
- **Tests:** `__` pytest tests (currently 210), covering the solver math, the Dr. Patel example, the generated clients, offline agent round trips, the cards and the eval.

## Challenges we ran into

- **Proving impossibility:** making the solver *prove* impossibility reliably. Tolerances matter, so we use a dust threshold, a tolerance for "passed", and a small volatility margin so repairs land under a cap and not 0.001 points over it.
- **Price-tag solve times:** strict solver tolerances made the utility problems hit the time limit every time. Tuned SCIP settings brought all 8 solves for a client down to about 0.1 s.
- **Generating "hard" clients:** a volatility cap that's barely feasible means computing the solver's minimum volatility first, then planting conflicts whose minimal set is *exactly* the intended rules.
- **Slow LLM agents:** an analyst can take minutes, and retrying after a timeout just runs the same LLM call twice. The analysts got their own timeout and are asked concurrently. uAgents tracks only one pending reply per destination, which shaped how requests are sent.
- **The Pydantic split:** uAgents models are Pydantic v1 and ours are v2, so agent messages carry JSON text instead of nested models.
- `TODO: anything from the live Agentverse / ASI:One testing`

## Accomplishments that we're proud of

- The Referee is exact and reproducible: the same input always gives the same receipt id. It can say "no portfolio exists, and here's the 3-rule reason" instead of silently drifting.
- A real 5-agent network where each agent has one job and its own address. The system keeps working when an agent is slow or down, and it says so.
- Rule price tags: "constraint attribution" of the kind institutional tools sell, explained in the client's words.
- An honest experiment with a fair, paired design.
- A real result, reported honestly. On realistic, tight clients the AI broke a rule in **83%** of first drafts (10 of 12).
  - After 3 rounds of feedback, compliance was 33% with self-check, 42% with a bare verdict and 50% with the Referee's explanation. The 95% CIs were [8, 58], [17, 67] and [25, 75].
  - That's a trend, not a statistically significant result with 12 trials: C vs. B p = 1.000, C vs. A p = 0.625.

## What we learned

- Keep the creative part (LLMs) and the part that must be right (the solver) separate. Then let the right part teach the creative part.
- Prompts are suggestions and constraints are guarantees. Explaining *why* a rule broke (actual vs. limit) helped more than saying *which* rule broke, and both helped more than self-checking, but only as a trend with 12 trials. Even with the best feedback, half the portfolios still broke a rule after 3 tries. Only the Referee's repair reached 100% compliance, which is why the Referee repairs portfolios as well as giving feedback.
- Agent networks need the boring parts: timeouts, retries, fallbacks, and saying out loud when something was skipped.
- uAgents, Agentverse mailboxes, the Chat Protocol and ASI:One Interactive Cards.

## What's next for SwarmFolio Referee

- **Pay per verification** with Fetch's Payment Protocol. The Referee is already a standalone service any wealthtech platform or AI agent can call.
- **Plain-English rules:** paste an investment policy statement and get the rule JSON, with the Referee confirming the result is feasible.
- **PSO searches, the Referee certifies:** use SwarmFolio's swarm to explore good portfolios and the Referee to certify them.
- More rule types (tax lots, ESG scores, factor exposures) and a larger universe than 19 tickers.

## Built with

`python` · `cvxpy` · `scip` / `pyscipopt` · `fetch.ai` · `uagents` · `agentverse` · `asi:one` · `langchain` · `pydantic` · `numpy` · `pandas` · `yfinance` · `fastapi` · `uvicorn` · `react` · `vite` · `tailwindcss` · `recharts` · `matplotlib` · `pytest` · `paper` (TODO-confirm) · `devin` · `claude-code`

## Built at LA Hacks vs. before

| Pre-existing (open source, MIT) | Built at LA Hacks |
|---|---|
| SwarmFolio: the price-download code and cached prices for 19 stocks, return and covariance math, a PSO optimizer, a backtest | Rule schema (10 rule types), the Referee (exact solver, conflict finder, cheapest relaxation, repair, receipt, rule price tags), the analyst and Chair logic, the feedback loop, the 5 Fetch agents and their messages, ASI:One Interactive Cards, the synthetic clients, the evaluation and feedback experiment, the web app (FastAPI + React; designed in Paper: **TODO-confirm**) |

*Design notes were written before the event; all code was written during it.*
