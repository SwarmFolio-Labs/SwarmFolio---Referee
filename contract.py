"""
The function signatures both halves of the project agree on (MASTER 5.4).

FROZEN after A0. The real versions live in referee/ and committee/; the fake
versions live in fakes.py. Both must match these signatures exactly.
"""

from typing import Protocol

from models import (
    AnalysisRequest,
    CommitteeResult,
    Memo,
    Receipt,
    ReviewRequest,
    Stance,
    VerifyRequest,
)
from referee.schema import Client, Proposal


class Transport(Protocol):
    """How the Chair's loop talks to the analysts and the Referee.

    "local" = direct function calls; "agents" = Fetch.ai messages.
    All methods are async because uAgents' send_and_receive is await-only.
    """

    name: str  # "local" or "agents"

    async def analyze(self, agent: str, req: AnalysisRequest) -> Memo | None:
        """Ask one analyst for a memo. None if it timed out or failed."""
        ...

    async def review(self, agent: str, req: ReviewRequest) -> Stance | None:
        """Ask one analyst to respond to the Referee's findings. None if it failed."""
        ...

    async def verify(self, req: VerifyRequest) -> Receipt:
        """Ask the Referee to check a proposal."""
        ...


def referee(client: Client, proposal: Proposal) -> Receipt:
    """Check a proposal against the client's rules and return the full receipt."""
    raise NotImplementedError


def analyze(agent: str, req: AnalysisRequest) -> Memo:
    """One analyst ("macro", "fundamentals" or "risk") writes a memo for this client."""
    raise NotImplementedError


def review(agent: str, req: ReviewRequest) -> Stance:
    """One analyst responds to the Referee's failed checks: concede, defend or modify."""
    raise NotImplementedError


def chair_propose(client: Client, memos: list[Memo]) -> Proposal:
    """The Chair turns the analysts' memos into a first portfolio."""
    raise NotImplementedError


def chair_revise(client: Client, proposal: Proposal, receipt: Receipt, stances: list[Stance]) -> Proposal:
    """The Chair fixes the portfolio using the receipt and the analysts' stances."""
    raise NotImplementedError


async def run_committee(client: Client, transport: Transport, max_rounds: int = 3) -> CommitteeResult:
    """Run the whole committee: memos -> proposal -> Referee -> debate rounds -> result."""
    raise NotImplementedError
