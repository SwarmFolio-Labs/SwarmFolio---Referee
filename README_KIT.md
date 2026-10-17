# SwarmFolio Referee: LA Hacks kit

Open this folder in Claude Code. **`MASTER.md` is the source of truth.** Start with prompt **A0** in
MASTER.md Section 11.

| File | What it is | Who reads it |
|---|---|---|
| `MASTER.md` | Everything: the split (Claude Code / Devin / you), timeline + priority ladder, wiring, contract, verified math, LangChain layer, the uAgents recipe from Fetch's docs, Paper design plan, all prompts, rescue prompts, submissions | You, Claude Code, Devin |
| `CLAUDE.md` | Rules Claude Code follows automatically | Claude Code |
| `PLAN.md` | Background: why it wins, Fetch fit, demo script, judge Q&A, submission checklist | You |
| `PROMPTS.md`, `SPLIT.md` | Pointers into MASTER.md (old versions) | — |
| `data/prices.csv` | Fallback prices from SwarmFolio (MIT, up to Jul 1 2026) | Code |

**Stack:** LangChain brains (ASI:One model by default) · CVXPY + SCIP Referee · uAgents wrappers ·
Agentverse · ASI:One · FastAPI + React web app designed in Paper.

**Entered in:** Applied Intelligence + Agentverse tracks · Fetch.ai · Paper · Devin (+ Gemini if used).
