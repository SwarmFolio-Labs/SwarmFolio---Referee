"""
AgentTransport: how the Chair's loop talks to the other agents over Fetch.ai (MASTER 4.5).

It has the same three async methods as the local transport, so run_committee works the same
with either. For now (Plan B step 2) only verify() goes over the network; analyze() and review()
call the local brains until the analyst agents exist.
"""

import asyncio

import config
from agents import brains
from agents.messages import ErrorMsg, ReceiptMsg, VerifyRequestMsg, pack, unpack
from models import AnalysisRequest, Memo, Receipt, ReviewRequest, Stance, VerifyRequest


class AgentTransport:
    """Talks to the Referee Agent with ctx.send_and_receive; falls back to local calls if it's silent."""

    name = "agents"

    def __init__(self, ctx, referee_address: str | None):
        # ctx is the uAgents Context of the Chair's current message handler.
        self.ctx = ctx
        self.referee_address = referee_address
        self.notes: list[str] = []

    async def analyze(self, agent: str, req: AnalysisRequest) -> Memo | None:
        """Ask one analyst for a memo (local brain for now; analyst agents come in Plan B step 7).
        None if it fails, so the committee carries on without that analyst (contract.py)."""
        try:
            return await asyncio.to_thread(brains.analyze, agent, req)
        except Exception as e:
            self.notes.append(f"The {agent} analyst failed: {e}")
            return None

    async def review(self, agent: str, req: ReviewRequest) -> Stance | None:
        """Ask one analyst to respond to the Referee (local brain for now). None if it fails."""
        try:
            return await asyncio.to_thread(brains.review, agent, req)
        except Exception as e:
            self.notes.append(f"The {agent} analyst failed to review: {e}")
            return None

    async def verify(self, req: VerifyRequest) -> Receipt:
        """Ask the Referee Agent to check a proposal. Verification is never skipped:
        if the agent doesn't answer after a retry, run the Referee locally and say so."""
        problem = "no REFEREE_ADDRESS set"
        if self.referee_address:
            msg = VerifyRequestMsg(payload=pack(req))
            # 1 try + AGENT_RETRIES retries.
            for _attempt in range(1 + config.AGENT_RETRIES):
                reply, status = await self.ctx.send_and_receive(
                    self.referee_address, msg,
                    response_type={ReceiptMsg, ErrorMsg},
                    timeout=config.AGENT_TIMEOUT_S,
                )
                if isinstance(reply, ReceiptMsg):
                    return unpack(Receipt, reply.payload)
                if isinstance(reply, ErrorMsg):
                    problem = f"it replied with an error ({reply.error})"
                else:
                    problem = f"it did not answer ({status.detail})"

        # Fallback: the same referee() function, called directly.
        note = f"Referee Agent unavailable: {problem}; verified locally instead."
        self.notes.append(note)
        receipt = await asyncio.to_thread(brains.referee, req.client, req.proposal)
        receipt.notes.append(note)
        return receipt
