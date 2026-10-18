"""
Shared Pydantic v2 models for the Referee and the committee (MASTER 5.2-5.3).

FROZEN after A0: both halves of the project (brains and app/agents) depend on
these exact shapes. Changing anything here needs a loud note to everyone.
"""

from typing import Literal

from pydantic import BaseModel, Field

from referee.schema import Client, Proposal, Rule  # noqa: F401  (re-exported for convenience)


# ---------- Referee output (MASTER 5.2) ----------

class CheckResult(BaseModel):
    """The result of checking one rule against one portfolio."""

    rule_id: str
    type: str
    passed: bool
    actual: float     # what the portfolio has (e.g. 0.42 = 42% in JNJ)
    limit: float      # what the rule allows
    violation: float  # how far past the limit (0 if passed)
    explain: str      # plain English


class Relaxation(BaseModel):
    """One rule loosened as part of the cheapest fix for impossible rules."""

    rule_id: str
    old_limit: float
    new_limit: float
    cost: float       # priority x how much it was loosened
    explain: str


class Receipt(BaseModel):
    """Everything the Referee found, in one auditable record."""

    receipt_id: str
    timestamp: str
    client_id: str
    verdict: Literal["PASS", "VIOLATIONS_REPAIRED", "RULES_INFEASIBLE", "ERROR"]
    checks: list[CheckResult]
    dust_removed: list[str]
    rules_feasible: bool
    conflict_set: list[str]
    conflict_explain: str
    cheapest_relaxation: list[Relaxation]
    repaired_weights: dict[str, float]
    capital_moved: float
    sharpe_before: float
    sharpe_after: float
    vol_after: float
    summary: str
    notes: list[str]


# ---------- Committee models (MASTER 5.3) ----------

class AnalysisRequest(BaseModel):
    """What the Chair sends each analyst at the start."""

    client_id: str
    client_story: str
    rules_text: list[str]
    as_of: str


class Memo(BaseModel):
    """One analyst's view: what to favor, what to avoid, and why."""

    agent: str
    favor: list[str]
    avoid: list[str]
    sector_views: dict[str, str]  # e.g. {"Tech": "overweight"}
    reasons: dict[str, str]
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewRequest(BaseModel):
    """What the Chair sends analysts after the Referee finds problems."""

    client_id: str
    round: int
    failures: list[str]  # plain-English failed checks
    proposal: Proposal
    conflict_explain: str


class Stance(BaseModel):
    """An analyst's answer to a review: give in, push back, or adjust."""

    agent: str
    stance: Literal["concede", "defend", "modify"]
    change: str
    why: str


class VerifyRequest(BaseModel):
    """Ask the Referee to check a proposal for a client."""

    client: Client
    proposal: Proposal


class DebateEntry(BaseModel):
    """One line in the debate log shown in the app."""

    round: int
    agent: str
    kind: Literal["memo", "proposal", "receipt", "stance", "note"]
    text: str
    stance: str | None = None


class CommitteeResult(BaseModel):
    """The full outcome of one committee run."""

    client_id: str
    final_proposal: Proposal
    receipt: Receipt
    first_receipt: Receipt
    debate_log: list[DebateEntry]
    rounds: int
    self_corrected: bool
    notes: list[str]
    # Added after the freeze (optional, additive): the dust-cleaned weights of the last proposal the
    # Referee checked. When the Referee repairs, final_proposal holds the repaired weights instead,
    # so this is the "before" in "before -> after".
    checked_weights: dict[str, float] = {}


# ---------- Rule price tags (MASTER 6.10; additive, not part of the frozen receipt) ----------

class RulePrice(BaseModel):
    """What one client rule costs: how much better the best portfolio gets if the rule is dropped."""

    rule_id: str
    source: str              # the client's own words
    binds: bool              # False = the rule costs nothing (it never limits the best portfolio)
    utility_cost_pts: float  # points of risk-adjusted return per year lost to this rule (>= 0)
    sharpe_with: float       # Sharpe of the best portfolio with all rules
    sharpe_without: float    # Sharpe of the best portfolio without this rule
    explain: str
