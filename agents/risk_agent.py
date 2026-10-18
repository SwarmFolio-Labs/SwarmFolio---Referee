"""
The Risk Agent (MASTER 9): "Risk analyst for the SwarmFolio committee."

All the logic is shared with the other analysts in agents/analyst_agent.py.
Run it with:  python -m agents.risk_agent
"""

from uagents import Agent

from agents.analyst_agent import build_analyst_agent, main

ROLE = "risk"


def build_agent(seed: str, port: int, mailbox: bool = True, publish: bool = True) -> Agent:
    """Make the Risk Agent. Tests pass mailbox=False/publish=False to stay offline."""
    return build_analyst_agent(ROLE, seed, port, mailbox=mailbox, publish=publish)


if __name__ == "__main__":
    main(ROLE)
