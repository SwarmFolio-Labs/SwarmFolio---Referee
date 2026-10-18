"""
One analyst agent (MASTER 9): a thin Fetch.ai wrapper around analyze() and review().

The macro, fundamentals and risk agents are the same code with a different role, so they
all use build_analyst_agent() from here. Two messages in, one reply out:
- AnalysisRequestMsg -> MemoMsg     (brains.analyze(role, request))
- ReviewRequestMsg   -> StanceMsg   (brains.review(role, request))
On any problem the agent replies ErrorMsg instead of crashing, so the Chair can move on.
"""

import asyncio
import os

from uagents import Agent, Context, Protocol

import config
from agents import brains, event_loop
from agents.messages import (AnalysisRequestMsg, ErrorMsg, MemoMsg, ReviewRequestMsg, StanceMsg,
                             pack, unpack)
from models import AnalysisRequest, ReviewRequest

ROLES = ("macro", "fundamentals", "risk")


def _check_role(role: str, asked_for: str) -> None:
    """The Chair says which analyst it means; refuse a message meant for someone else."""
    if asked_for != role:
        raise ValueError(f"this is the {role} analyst, but the message is for '{asked_for}'")


def build_analyst_agent(role: str, seed: str, port: int, mailbox: bool = True, publish: bool = True) -> Agent:
    """Make the analyst agent for `role`. Tests pass mailbox=False/publish=False to stay offline."""
    if role not in ROLES:
        raise ValueError(f"unknown analyst role '{role}' (expected one of {', '.join(ROLES)})")
    agent = Agent(name=f"swarmfolio-{role}", seed=seed, port=port, loop=event_loop(),
                  mailbox=mailbox, publish_agent_details=publish)
    committee = Protocol(name="swarmfolio-committee", version="0.1.0")

    @committee.on_message(AnalysisRequestMsg, replies={MemoMsg, ErrorMsg})
    async def on_analysis(ctx: Context, sender: str, msg: AnalysisRequestMsg):
        try:
            _check_role(role, msg.agent)
            req = unpack(AnalysisRequest, msg.payload)
            # brains.analyze is looked up at call time, so the USE_FAKES switch (and tests) decide which brain runs.
            memo = await asyncio.to_thread(brains.analyze, role, req)
            await ctx.send(sender, MemoMsg(payload=pack(memo)))
        except Exception as e:  # never crash: tell the Chair what went wrong
            ctx.logger.error(f"analysis failed: {e}")
            await ctx.send(sender, ErrorMsg(error=str(e)))

    @committee.on_message(ReviewRequestMsg, replies={StanceMsg, ErrorMsg})
    async def on_review(ctx: Context, sender: str, msg: ReviewRequestMsg):
        try:
            _check_role(role, msg.agent)
            req = unpack(ReviewRequest, msg.payload)
            stance = await asyncio.to_thread(brains.review, role, req)
            await ctx.send(sender, StanceMsg(payload=pack(stance)))
        except Exception as e:
            ctx.logger.error(f"review failed: {e}")
            await ctx.send(sender, ErrorMsg(error=str(e)))

    agent.include(committee, publish_manifest=publish)
    return agent


def main(role: str) -> None:
    """Run one analyst agent with its seed from .env (e.g. MACRO_SEED) on its port from config."""
    seed_var = f"{role.upper()}_SEED"
    seed = os.getenv(seed_var)
    if not seed:
        raise SystemExit(f"{seed_var} is missing from .env (any long random sentence; keep it stable).")
    build_analyst_agent(role, seed, config.AGENT_PORTS[role]).run()
