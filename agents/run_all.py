"""
Start the Fetch.ai agents, one process each (MASTER 9.2).

Plan B step 2: only the Referee and the Chair for now (the analysts come later).
Prints each agent's address and Inspector link, then waits; Ctrl+C stops them all.
Run it from the project folder with:  python -m agents.run_all
"""

import os
import subprocess
import sys
from urllib.parse import quote

from uagents_core.identity import Identity

import config

# (name in AGENT_PORTS, seed variable in .env, module to run). Referee first so it's up when the Chair calls.
AGENTS = [
    ("referee", "REFEREE_SEED", "agents.referee_agent"),
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
        print(f"{name:8} port {port}  {address}")
        print(f"         Inspector: {inspector}")
        procs.append(subprocess.Popen([sys.executable, "-m", module], cwd=project))

    print("\nAll agents started. Ctrl+C to stop.")
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
