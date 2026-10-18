"""
Start the Fetch.ai agents, one process each (MASTER 9.2).

All 5 agents: Referee, the three analysts, then the Chair (ports 8001-8005).
Prints each agent's address and Inspector link, then waits. Ctrl+C, `kill <pid>` (SIGTERM) or
closing the terminal (SIGHUP) stops them all.
Run it from the project folder with:  python -m agents.run_all
"""

import os
import signal
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


STOP_SIGNALS = ("SIGTERM", "SIGHUP")  # SIGHUP doesn't exist on Windows, so look them up by name


def _stop(signum, frame):
    """Treat `kill <pid>` (SIGTERM) and a closed terminal (SIGHUP) exactly like Ctrl+C."""
    raise KeyboardInterrupt


def stop_all(procs: list[subprocess.Popen], grace_s: float = 10) -> None:
    """Ask every agent to stop, wait a little, then force-kill any that are still running."""
    # A second Ctrl+C or kill while we clean up must not leave agents behind.
    for name in ("SIGINT", *STOP_SIGNALS):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), signal.SIG_IGN)
    for p in procs:
        if p.poll() is None:
            p.terminate()
    for p in procs:
        try:
            p.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def main() -> None:
    """Start every agent, print where to find it, and stop them all on Ctrl+C, SIGTERM or SIGHUP."""
    for name in STOP_SIGNALS:
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    procs = []
    try:
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

        print("\nAll agents started. Ctrl+C (or kill this process) to stop.", flush=True)
        if os.getenv("USE_ANALYST_AGENTS", "false").strip().lower() not in ("1", "true", "yes", "on"):
            print("Note: USE_ANALYST_AGENTS is off, so the Chair still calls the analyst brains locally."
                  " Set USE_ANALYST_AGENTS=true in .env to route memos and stances through the analyst agents.")
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        stop_all(procs)


if __name__ == "__main__":
    main()
