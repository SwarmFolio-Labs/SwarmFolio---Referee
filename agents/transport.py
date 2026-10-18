"""
AgentTransport: how the Chair's loop talks to the other agents over Fetch.ai (MASTER 4.5).

It has the same three async methods as the local transport, so run_committee works the same
with either. verify() always goes to the Referee Agent (local fallback if it's silent).
analyze() and review() go to the macro / fundamentals / risk agents when USE_ANALYST_AGENTS
is on (env var, default off); otherwise they call the local brains exactly as before.
"""

import asyncio
import os

from uagents_core.identity import Identity

import config
from agents import brains
from agents.messages import (AnalysisRequestMsg, ErrorMsg, MemoMsg, ReceiptMsg, ReviewRequestMsg,
                             StanceMsg, VerifyRequestMsg, pack, unpack)
from models import AnalysisRequest, Memo, Receipt, ReviewRequest, Stance, VerifyRequest

ANALYSTS = ("macro", "fundamentals", "risk")


def use_analyst_agents() -> bool:
    """USE_ANALYST_AGENTS from .env: "1" / "true" / "yes" sends analyst calls over Fetch (default: local)."""
    return os.getenv("USE_ANALYST_AGENTS", "false").strip().lower() in ("1", "true", "yes", "on")


def agent_address(name: str) -> str | None:
    """<NAME>_ADDRESS from .env, or worked out from <NAME>_SEED (an address is fixed by its seed)."""
    address = os.getenv(f"{name.upper()}_ADDRESS")
    if address:
        return address
    seed = os.getenv(f"{name.upper()}_SEED")
    if seed:
        return Identity.from_seed(seed, 0).address
    return None


class AgentTransport:
    """Talks to the other agents with ctx.send_and_receive.

    Silent Referee -> verify locally (never skipped). Silent analyst -> None (the loop goes on without it).
    """

    name = "agents"

    def __init__(self, ctx, referee_address: str | None,
                 analyst_addresses: dict[str, str | None] | None = None,
                 analyst_agents: bool | None = None):
        # ctx is the uAgents Context of the Chair's current message handler.
        self.ctx = ctx
        self.referee_address = referee_address
        self.analyst_agents = use_analyst_agents() if analyst_agents is None else analyst_agents
        if analyst_addresses is None:
            analyst_addresses = {a: agent_address(a) for a in ANALYSTS}
        self.analyst_addresses = analyst_addresses
        self.notes: list[str] = []

    async def _ask(self, address: str, msg, reply_type):
        """Send msg and wait for reply_type, with one retry. Returns (reply or None, what went wrong)."""
        problem = ""
        # 1 try + AGENT_RETRIES retries.
        for _attempt in range(1 + config.AGENT_RETRIES):
            reply, status = await self.ctx.send_and_receive(
                address, msg, response_type={reply_type, ErrorMsg}, timeout=config.AGENT_TIMEOUT_S,
            )
            if isinstance(reply, reply_type):
                return reply, ""
            if isinstance(reply, ErrorMsg):
                problem = f"it replied with an error ({reply.error})"
            else:
                problem = f"it did not answer ({getattr(status, 'detail', status)})"
        return None, problem

    async def _ask_analyst(self, agent: str, msg, reply_type, what: str):
        """Ask one analyst agent; on silence or error add a note and return None."""
        address = self.analyst_addresses.get(agent)
        if not address:
            self.notes.append(f"The {agent} analyst agent has no address ({agent.upper()}_ADDRESS or "
                              f"{agent.upper()}_SEED); skipped its {what}.")
            return None
        try:
            reply, problem = await self._ask(address, msg, reply_type)
        except Exception as e:  # a transport bug must not stop the committee
            reply, problem = None, f"sending failed ({e})"
        if reply is None:
            self.notes.append(f"The {agent} analyst agent is unavailable for its {what}: {problem}.")
        return reply

    async def analyze(self, agent: str, req: AnalysisRequest) -> Memo | None:
        """Ask one analyst for a memo. None if it fails, so the committee carries on without it (contract.py)."""
        if not self.analyst_agents:
            try:
                return await asyncio.to_thread(brains.analyze, agent, req)
            except Exception as e:
                self.notes.append(f"The {agent} analyst failed: {e}")
                return None
        reply = await self._ask_analyst(agent, AnalysisRequestMsg(agent=agent, payload=pack(req)), MemoMsg, "memo")
        return None if reply is None else unpack(Memo, reply.payload)

    async def review(self, agent: str, req: ReviewRequest) -> Stance | None:
        """Ask one analyst to respond to the Referee. None if it fails."""
        if not self.analyst_agents:
            try:
                return await asyncio.to_thread(brains.review, agent, req)
            except Exception as e:
                self.notes.append(f"The {agent} analyst failed to review: {e}")
                return None
        reply = await self._ask_analyst(agent, ReviewRequestMsg(agent=agent, payload=pack(req)), StanceMsg, "review")
        return None if reply is None else unpack(Stance, reply.payload)

    async def verify(self, req: VerifyRequest) -> Receipt:
        """Ask the Referee Agent to check a proposal. Verification is never skipped:
        if the agent doesn't answer after a retry, run the Referee locally and say so."""
        problem = "no REFEREE_ADDRESS set"
        if self.referee_address:
            reply, problem = await self._ask(self.referee_address, VerifyRequestMsg(payload=pack(req)), ReceiptMsg)
            if reply is not None:
                return unpack(Receipt, reply.payload)

        # Fallback: the same referee() function, called directly.
        note = f"Referee Agent unavailable: {problem}; verified locally instead."
        self.notes.append(note)
        receipt = await asyncio.to_thread(brains.referee, req.client, req.proposal)
        receipt.notes.append(note)
        return receipt
