"""
LocalTransport: the committee talks to the analysts and the Referee by plain function calls.

It has the same async methods as the Fetch AgentTransport, so the loop works the same with both.
The brain functions are normal (blocking) functions, so we run them in a worker thread with
asyncio.to_thread; that way the event loop (and the web app) never freezes while an LLM thinks.
"""

import asyncio

from committee.analysts import analyze, review
from models import AnalysisRequest, Memo, Receipt, ReviewRequest, Stance, VerifyRequest
from referee.receipt import referee


class LocalTransport:
    """Direct calls to the real brains. A failed analyst returns None (the loop notes it and moves on)."""

    name = "local"

    async def analyze(self, agent: str, req: AnalysisRequest) -> Memo | None:
        try:
            return await asyncio.to_thread(analyze, agent, req)
        except Exception:
            return None

    async def review(self, agent: str, req: ReviewRequest) -> Stance | None:
        try:
            return await asyncio.to_thread(review, agent, req)
        except Exception:
            return None

    async def verify(self, req: VerifyRequest) -> Receipt:
        # referee() never raises: bad input comes back as an ERROR receipt.
        return await asyncio.to_thread(referee, req.client, req.proposal)
