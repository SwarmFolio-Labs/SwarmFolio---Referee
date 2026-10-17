"""
The shapes of clients, rules and proposals (MASTER 5.1).

A client is one JSON file in data/clients/. The Referee reads the rules exactly
as written here; the LLMs only ever see the plain-English `source` text.
"""

from typing import Literal

from pydantic import BaseModel, Field

# The 10 rule types the Referee knows how to check and solve.
RuleType = Literal[
    "max_weight",
    "min_weight",
    "exclude",
    "sector_max",
    "sector_min",
    "max_holdings",
    "min_holdings",
    "buy_in",
    "max_volatility",
    "max_turnover",
]


class Rule(BaseModel):
    """One client rule.

    params by type:
      max_weight {ticker: str | "*", max}   min_weight {ticker, min}
      exclude {tickers: [...]}               sector_max / sector_min {sector, max | min}
      max_holdings / min_holdings {k}        buy_in {min}
      max_volatility {max}                   max_turnover {max}
    """

    id: str
    type: RuleType
    params: dict
    priority: int = Field(ge=1, le=10)  # cost per unit of relaxation; higher = more expensive
    hard: bool                          # hard rules can never be relaxed
    source: str                         # the client's own words


class Client(BaseModel):
    """A client: who they are, which stocks they can hold, and their rules."""

    client_id: str
    name: str
    story: str
    universe: list[str]
    current_weights: dict[str, float] = {}
    rules: list[Rule]
    planted_conflict: list[str] | None = None  # eval only: the rule ids we know clash


class Proposal(BaseModel):
    """A portfolio someone proposes: ticker -> fraction of capital, plus why."""

    weights: dict[str, float]
    thesis: str
    reasons: dict[str, str]
