"""
The Fundamentals Agent (MASTER 9): "Fundamentals analyst for the SwarmFolio committee."

All the logic is shared with the other analysts in agents/analyst_agent.py.
Run it with:  python -m agents.fundamentals_agent
"""

from uagents import Agent

from agents.analyst_agent import build_analyst_agent, main

ROLE = "fundamentals"


def build_agent(seed: str, port: int, mailbox: bool = True, publish: bool = True) -> Agent:
    """Make the Fundamentals Agent. Tests pass mailbox=False/publish=False to stay offline."""
    return build_analyst_agent(ROLE, seed, port, mailbox=mailbox, publish=publish)


if __name__ == "__main__":
    main(ROLE)
