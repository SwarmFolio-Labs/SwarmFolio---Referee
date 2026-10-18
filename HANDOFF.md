# HANDOFF: coordinator state (Sat Oct 17 2026, ~10:55 PM PT)

Read this first if you're a new coordinator session. MASTER.md = the original plan; this file = what's
actually true now. Samarth is a beginner who relies on AI builders; the coordinator reviews every PR on
his Mac before he merges, and gives him paste-ready prompts.

## Repo / setup
- Folder: `~/SwarmFolio LaHacks AI Hackathon` · GitHub: `github.com/SwarmFolio-Labs/SwarmFolio---Referee`
  (moved to the org for Devin). Python 3.14 venv `.venv`. ~257 tests pass.
- `.env` (git-ignored, never print it): ASI1_API_KEY, GEMINI_API_KEY, 5 agent seeds, CHAIR/REFEREE
  addresses, USE_ANALYST_AGENTS=true, LLM_PROVIDER=asi1, STRIPE test keys, REFEREE_PAYMENTS=true.
  Warning: an ASI1 key screenshot was shared in chat, so rotate it after the hackathon.
- PR review method: git worktree in the scratchpad → run the suite with the main `.venv` → merge-test
  with other open PRs → `npm run build` for frontend PRs.

## Builders
- **Main Claude Code session:** brains, referee, experiment, agents restarts.
- **Design Claude session (Paper MCP):** works only in Paper. Brief is in `design/BRIEF.md`.
- **Devin session 1:** backend/docs/packaging. **Devin session 2:** web app (frontend + api.py).

## Done (on main)
Referee (exact CVXPY+SCIP: check, feasibility, minimal conflict set, cheapest relaxation, L1 repair,
receipt, price tags, stress-tested) · LangChain brains (asi1 / gemini / anthropic) · loop with 3 feedback
modes · 26 clients (C01–C04, C10–C27, C91–C94) · 5 Fetch agents live (Chair 8001, Referee 8002, Macro
8003, Fund 8004, Risk 8005, mailboxes connected, run under nohup, log cache/run_all.log) · ASI:One
Interactive Cards working · Stripe pay-per-check (test mode, $0.50, Chair exempt) tested by Samarth ·
demo speed (LIVE_MODEL asi1-mini, parallel analysts, warm cache for C02/C03/C04/C91) · live-demo fixes
(min/max wording, 2-decimals near limit, receipt before/after, short stances) · web app (FastAPI + React,
tokens + named components, PR #10) · README + DEVPOST drafts (PRs #6/#7/#9) · experiment #1: asi1, C91–C94
× 3 = 12 trials: 83% first drafts broke a rule; compliance after 3 rounds self 33% / bare 42% /
explained 50% (trend, p = 0.63, not significant); only the Referee's repair reaches 100%.
Best live demo: **C04 Mr. Alvarez**: broke 2 → broke 3 → compliant in round 3 (Sharpe 1.64, vol 13.4%);
price tags: turnover 4.23, vol cap 2.43, tech 0.04 points/yr of RISK-ADJUSTED return.

## In flight
- **Experiment #2 (Gemini):** restarted on gemini-3.5-flash-lite only (flash out of quota), 10 clients × 2
  trials, nohup, main session. Report honestly when done and add to the README/Devpost.
- **asi1-mini:** hit the ASI:One rate limit earlier (resets in minutes). Keep ASI:One quota for live
  agents and judging; don't run experiments on it.
- **PR #11** (Devin 2: live-run progress API, starting→final holdings, every-rule-checked, Screen C data,
  print CSS): passes alone. Samarth to merge. Then Devin 2 must make `committee` a LAZY import in api.py
  + an ENABLE_LIVE_RUNS flag, because otherwise **PR #12** (Devin 1: demo.sh, LLM-free Dockerfile,
  render.yaml, DEPLOY.md) fails tests/test_public_api.py. Merge #12 after that fix.
- **Paper design:** Direction A (Research Report) + C's table/stance shapes. Screens done: A (C04 run),
  B (C02 receipt), the stance component, the thinking/loading state, C (C03 impossible, ochre NEEDS
  APPROVAL stamp), D (client picker), E (C04 price tags). Pending: the Screen E copy fix (risk-adjusted,
  not expected return), D chips from real data, 390px phone A+B, Samarth hand-edits the stamps, then
  EXPORT to design/ (HTML/CSS + PNG + design/tokens.css), then Devin 2 implements it (prompt below).

## Still to do (priority)
1. 🔒 **Fetch submission** (NOT done): ASI:One shared chat of the C04 run + 5 Agentverse profile URLs →
   https://asi1.ai/festival/lahacksai2026/dashboard. Can be updated later.
2. Main session: save real demo runs `data/demo_runs/save_demo_run.py C04 C02 C91 C03` (C04 missing).
3. Main session: a "fresh run (no cache)" option (Chair "… fresh" + a UI toggle) so judges can see a
   live uncached run. Devin 2: let "Try the Referee" edit RULES too, plus a "Make it impossible" button.
4. Paper export → Devin 2 implements: "Implement the Paper design in design/ (tokens + named
   components exist). Update frontend/src/index.css from design/tokens.css, restyle each component to
   match the screenshots exactly, keep the data wiring, attach design-vs-app screenshots."
5. Sunday AM: final README/Devpost numbers (incl. Gemini run; delete any "in progress" lines), optional
   deploy (Render + Vercel + swarmfolio.biz; Render free tier sleeps, so wake it before the demo), demo
   video (show ASI:One C04 + web app + a live "break it" moment), rehearse 3×, **submit Devpost + update
   the Fetch submission by 11:30 AM** (hacking ends 12:00, judging 12:30).

## Submissions / prizes
Tracks: Applied Intelligence + Agentverse. Challenges: Fetch.ai (main), Paper (Best Designed Hack), Devin
(Cognition), MLH Gemini (experiment #2 uses Gemini), MLH GoDaddy domain (`aisaidtrustmebro.biz`, funny)
+ formal `swarmfolio.biz`. Solo team.

## Judge Q&A notes
Cached ≠ hardcoded: the Referee is live; the AI answers are cached for reproducibility and rate limits;
offer "try to break it" live (Try the Referee, impossible rules pasted into the Referee chat, a fresh
uncached run on C13/C17). Payments = "we sell verification, not advice." Experiment = trend, honestly
reported. PSO searches, the exact solver judges.
