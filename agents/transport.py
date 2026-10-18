"""
AgentTransport: how the Chair's loop talks to the other agents over Fetch.ai (MASTER 4.5).

It has the same three async methods as the local transport, so run_committee works the same
with either. verify() always goes to the Referee Agent (local fallback if it's silent).
analyze() and review() go to the macro / fundamentals / risk agents when USE_ANALYST_AGENTS
is on (env var, default off); otherwise they call the local brains exactly as before.

Analysts think for minutes (LLM calls), the Referee answers in about a second, so they get
different timeouts: ANALYST_TIMEOUT_S (env, default 240 s) vs config.AGENT_TIMEOUT_S.
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
DEFAULT_ANALYST_TIMEOUT_S = 240
# What uAgents' send_and_receive puts in MsgStatus.detail when the message was delivered
# but no reply came back in time (uagents/context.py).
NO_REPLY_DETAIL = "Timeout waiting for response"


def use_analyst_agents() -> bool:
    """USE_ANALYST_AGENTS from .env: "1" / "true" / "yes" sends analyst calls over Fetch (default: local)."""
    return os.getenv("USE_ANALYST_AGENTS", "false").strip().lower() in ("1", "true", "yes", "on")


def analyst_timeout_s() -> int:
    """ANALYST_TIMEOUT_S from .env: how long to wait for one analyst's memo or stance (default 240 s)."""
    raw = os.getenv("ANALYST_TIMEOUT_S", "").strip()
    try:
        return int(float(raw)) if raw else DEFAULT_ANALYST_TIMEOUT_S
    except ValueError:
        return DEFAULT_ANALYST_TIMEOUT_S


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
        # Analyst calls already running, keyed by (memo/review, request JSON) then analyst name.
        self._running: dict[tuple[str, str], dict[str, asyncio.Task]] = {}

    async def _ask(self, address: str, msg, reply_type, timeout: int, retry_on_timeout: bool = True):
        """Send msg and wait up to `timeout` s for reply_type, with AGENT_RETRIES retries.
        Returns (reply or None, what went wrong).

        An error reply or a failed send is always retried. A timeout is retried only if
        retry_on_timeout: for an analyst, a timeout means it's still thinking, and asking
        again would just run the same LLM call twice."""
        problem = ""
        for _attempt in range(1 + config.AGENT_RETRIES):
            try:
                reply, status = await self.ctx.send_and_receive(
                    address, msg, response_type={reply_type, ErrorMsg}, timeout=timeout,
                )
            except Exception as e:
                problem = f"sending failed ({e})"
                continue
            if isinstance(reply, reply_type):
                return reply, ""
            if isinstance(reply, ErrorMsg):
                problem = f"it replied with an error ({reply.error})"
                continue
            detail = getattr(status, "detail", status)
            if detail == NO_REPLY_DETAIL:
                problem = f"it did not answer within {timeout} s"
                if not retry_on_timeout:
                    break
            else:
                problem = f"sending failed ({detail})"
        return None, problem

    async def _ask_analyst(self, agent: str, msg, reply_type, what: str):
        """Ask one analyst agent; on silence or error add a note and return None."""
        address = self.analyst_addresses.get(agent)
        if not address:
            self.notes.append(f"The {agent} analyst agent has no address ({agent.upper()}_ADDRESS or "
                              f"{agent.upper()}_SEED); skipped its {what}.")
            return None
        try:
            reply, problem = await self._ask(address, msg, reply_type, timeout=analyst_timeout_s(),
                                             retry_on_timeout=False)
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
        return await self._all_analysts_at_once("memo", agent, req)

    async def review(self, agent: str, req: ReviewRequest) -> Stance | None:
        """Ask one analyst to respond to the Referee. None if it fails."""
        if not self.analyst_agents:
            try:
                return await asyncio.to_thread(brains.review, agent, req)
            except Exception as e:
                self.notes.append(f"The {agent} analyst failed to review: {e}")
                return None
        return await self._all_analysts_at_once("review", agent, req)

    async def _ask_one_analyst(self, kind: str, agent: str, req):
        """One memo or review request to one analyst agent, unpacked. None if it fails."""
        if kind == "memo":
            reply = await self._ask_analyst(agent, AnalysisRequestMsg(agent=agent, payload=pack(req)), MemoMsg, "memo")
            return None if reply is None else unpack(Memo, reply.payload)
        reply = await self._ask_analyst(agent, ReviewRequestMsg(agent=agent, payload=pack(req)), StanceMsg, "review")
        return None if reply is None else unpack(Stance, reply.payload)

    async def _all_analysts_at_once(self, kind: str, agent: str, req):
        """run_committee asks the analysts one after another with the same request. Over the network
        each answer can take minutes, so the first call sends the request to all three analysts at
        once (like asyncio.gather), and each call then just waits for its own analyst's answer."""
        key = (kind, pack(req))
        running = self._running.setdefault(key, {})
        if agent not in running:
            for name in dict.fromkeys((agent, *ANALYSTS)):
                if name not in running:
                    running[name] = asyncio.create_task(self._ask_one_analyst(kind, name, req))
        task = running.pop(agent)
        if not running:
            del self._running[key]
        return await task

    async def verify(self, req: VerifyRequest) -> Receipt:
        """Ask the Referee Agent to check a proposal. Verification is never skipped:
        if the agent doesn't answer after a retry, run the Referee locally and say so."""
        problem = "no REFEREE_ADDRESS set"
        if self.referee_address:
            reply, problem = await self._ask(self.referee_address, VerifyRequestMsg(payload=pack(req)), ReceiptMsg,
                                             timeout=config.AGENT_TIMEOUT_S)
            if reply is not None:
                return unpack(Receipt, reply.payload)

        # Fallback: the same referee() function, called directly.
        note = f"Referee Agent unavailable: {problem}; verified locally instead."
        self.notes.append(note)
        receipt = await asyncio.to_thread(brains.referee, req.client, req.proposal)
        receipt.notes.append(note)
        return receipt
