"""
Start the Fetch.ai agents, one process each (MASTER 9.2).

All 5 agents: Referee, the three analysts, then the Chair (ports 8001-8005).
Prints each agent's address and Inspector link, then waits; Ctrl+C stops them all.
Run it from the project folder with:  python -m agents.run_all
"""

import os
import subprocess
import sys
from urllib.parse import quote

from uagents_core.identity import Identity

import config

# (name in AGENT_PORTS, seed variable in .env, module to run). The Chair goes last so the
# agents it calls are already up.
AGENTS = [
    ("referee", "REFEREE_SEED", "agents.referee_agent"),
    ("macro", "MACRO_SEED", "agents.macro_agent"),
    ("fundamentals", "FUNDAMENTALS_SEED", "agents.fundamentals_agent"),
    ("risk", "RISK_SEED", "agents.risk_agent"),
    ("chair", "CHAIR_SEED", "agents.chair_agent"),
]


def main() -> None:
    """Start every agent, print where to find it, and stop them all on Ctrl+C."""
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    procs = []
    for name, seed_var, module in AGENTS:
        seed = os.getenv(seed_var)
        if not seed:
            raise SystemExit(f"{seed_var} is missing from .env (any long random sentence; keep it stable).")
        port = config.AGENT_PORTS[name]
        address = Identity.from_seed(seed, 0).address  # same address the agent will have
        inspector = (f"https://agentverse.ai/inspect/?uri={quote(f'http://127.0.0.1:{port}')}"
                     f"&address={address}")
        print(f"{name:12} port {port}  {address}")
        print(f"             Inspector: {inspector}")
        procs.append(subprocess.Popen([sys.executable, "-m", module], cwd=project))

    print("\nAll agents started. Ctrl+C to stop.")
    if os.getenv("USE_ANALYST_AGENTS", "false").strip().lower() not in ("1", "true", "yes", "on"):
        print("Note: USE_ANALYST_AGENTS is off, so the Chair still calls the analyst brains locally."
              " Set USE_ANALYST_AGENTS=true in .env to route memos and stances through the analyst agents.")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
