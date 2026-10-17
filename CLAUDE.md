# Instructions for the AI coding assistant

You are helping Samarth build **SwarmFolio Referee** at the LA Hacks AI Hackathon
(Sat Oct 17 12:00 PM → Sun Oct 18 12:00 PM PT). **`MASTER.md` is the source of truth** (split, contract, math, wiring, prompts).

## Saving usage (important: Claude Code limits are tight)
- **Read only the MASTER.md sections the current prompt names** (e.g. "MASTER 6.5"). Don't read the whole
  file, PLAN.md, or the other docs unless the prompt asks. Use search (grep) to jump to a section.
- **Never print or read `data/prices.csv`** or other big data files; load them in code and print only
  shapes, date ranges, or a few rows.
- Don't re-read files you just wrote. Keep answers short: what changed, test results, the commit command.
- Don't touch Devin's files (`api.py`, `frontend/`, `agents/*_agent.py`, `agents/transport.py`,
  `agents/run_all.py`, `eval/make_clients.py`, `README.md`) unless the prompt says so. `PLAN.md` has background (why, demo, judge Q&A). If files disagree, MASTER.md wins.

## Who you're working with
Samarth is a beginner programmer (UW-Madison freshman, interested in data science, stats and ML) and is relying
heavily on you. He understands the math ideas (optimization, Sharpe ratio, PSO) better than
the code. He has to explain the Referee to judges, so code must be readable and he must
understand it.

## Two builders
The work is split (MASTER.md Section 2): Claude Code owns `referee/`, `committee/`, `models.py`, `contract.py`, `fakes.py`, `agents/messages.py`, `tests/`, `eval/run_eval.py`;
another tool (Devin) owns `api.py`, `frontend/`, `agents/` (except `messages.py`), `eval/make_clients.py`, `README.md`.
Stay in your own files. Never change `contract.py`, `models.py` or `agents/messages.py` without saying so loudly,
because both halves depend on them.

## Hard rules
1. **Small steps.** Do exactly the step asked. Don't build ahead, don't add features that
   aren't in `PLAN.md`, don't refactor working code unless asked.
2. **Never rewrite a whole file to fix a bug.** Make the smallest edit that fixes it, and say what you changed.
3. **Every Referee feature gets a pytest test in the same step.** Run `pytest` before saying
   a step is done, and show the result. If a test fails, fix the code, not the test (unless the
   test is wrong, and then say why).
4. **After each working step, tell Samarth to commit**, and give the exact command:
   `git add -A && git commit -m "<what works now>"`.
5. **Don't touch Referee math without running its tests.** The Referee is the product.
6. **Explain like he's new** when he asks: plain English first, then the code line by line. For
   the Referee, end each step with a 2–3 sentence "how to explain this to a judge."
7. **Be honest.** If something didn't run, say so. Never claim tests pass without running them.
   If a library API is uncertain (especially Fetch.ai `uagents` / Agentverse), check the
   installed package or the official docs instead of guessing.
8. **Time awareness.** If a step is taking more than ~45 minutes, stop and suggest the cut from
   PLAN.md Section 8 ("Cut order").

## Tech conventions
- Python 3.14, virtualenv in `.venv`, dependencies in `requirements.txt` (pin nothing exotic).
- Optimization: `cvxpy`; solver `SCIP` for problems with yes/no (boolean) variables, `CLARABEL` for purely
  convex ones. Always pass the solver explicitly. Treat status `optimal`/`optimal_inaccurate`
  as solved; `infeasible` as infeasible; anything else → raise a clear error.
- Numerical conventions (MASTER 6.2): `TOL = 1e-6` for "rule passed"; weights below `DUST = 0.005`
  count as "not held" and are cleaned from proposals. Solver base constraints always include
  w_i <= z_i and w_i >= DUST * z_i.
- LLM: **LangChain** in `committee/llm.py` only (ChatOpenAI pointed at ASI:One by default, or Gemini /
  Anthropic), provider switch in `config.py` (`LLM_PROVIDER` = asi1 | gemini | anthropic), model ids only in
  `config.py`. Structured output via `with_structured_output`, falling back to a JSON parser (MASTER 8). Every LLM call returns JSON validated with Pydantic; on invalid JSON, retry once with
  the validation error appended. Cache responses in `cache/` keyed by a hash of
  (provider, model, prompt) so reruns are free and reproducible.
- API keys and agent seed phrases come from `.env` (loaded with `python-dotenv`). `.env` is in `.gitignore`. **Never
  print, log or commit a key.**
- Data: `data/refresh_data.py` downloads current prices with yfinance; SwarmFolio's `prices.csv` (MIT, credited in README) is the fallback.
  Sector map lives in `data/sectors.json`.
- Determinism: any randomness takes a `seed` argument.
- Agents are thin wrappers. All logic lives in `referee/` and `committee/` as plain functions;
  files in `agents/` only translate messages to function calls and back. The feedback loop
  takes a "transport" (LocalTransport = direct calls, AgentTransport = Fetch messages) and
  must work identically with both. Never put business logic in an agent file.
- `run_committee` and the Transport methods are **async** (uAgents' `send_and_receive` is await-only);
  all other brain functions are plain sync functions, called with `asyncio.to_thread` from async code.
- **uAgents `Model` is Pydantic v1; our models (`models.py`, `referee/schema.py`) are Pydantic v2.** Never nest
  them. Agent-to-agent messages carry JSON text (`agents/messages.py`, MASTER 5.5).
- uAgents facts come from Fetch's docs (summarized in MASTER 9.2). Don't guess the API: check the installed
  package or the docs.

## Project layout (create as needed, not all at once)
```
lahacks/
  PLAN.md  PROMPTS.md  CLAUDE.md  README.md  requirements.txt  config.py  .env (not committed)
  data/      refresh_data.py  prices.csv  fundamentals.json  sectors.json  clients/C01.json ...
  referee/   schema.py  check.py  solver.py  conflicts.py  relax.py  repair.py  receipt.py
  committee/ llm.py  analysts.py  chair.py  loop.py
  eval/      make_clients.py  run_eval.py  results/
  agents/    messages.py  transport.py  referee_agent.py  chair_agent.py
             macro_agent.py  fundamentals_agent.py  risk_agent.py   (Fetch.ai, Tier 2)
  contract.py  models.py  fakes.py   (signatures, shared Pydantic v2 models, fake brains; MASTER 5)
  api.py  frontend/  design/   (web app: FastAPI + React, styled from the Paper design)
  tests/     test_check.py  test_solver.py  test_conflicts.py  test_relax.py  test_repair.py
```

## Style
- Short functions with docstrings that say what the function does in plain English.
- Comments explain *why*, in the casual, clear style of the SwarmFolio repo.
- No clever one-liners in Referee code; clarity beats brevity.
