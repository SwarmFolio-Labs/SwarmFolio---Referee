"""
The committee Chair (MASTER 7.2): turns the analysts' memos into one portfolio, and
revises it after the Referee's findings.

The Chair sees the rules as text and the Referee's failed checks, but NEVER the
repaired weights. That keeps "did the committee fix itself?" an honest measurement.
"""

import json

from committee import llm
from committee.analysts import holdings_text
from committee.feedback import format_feedback
from models import Memo, Receipt, Stance
from referee.schema import Client, Proposal


def _system(client: Client) -> str:
    return ("You are the committee Chair. Combine the analysts' memos into one portfolio for this client, "
            f"over these tickers only: {', '.join(client.universe)}. Weights must be numbers from 0 to 1 that "
            "sum to 1. Give a one-paragraph thesis and one reason per position. "
            f"Reply with JSON: {json.dumps(Proposal.model_json_schema())}.")


def _client_text(client: Client) -> str:
    rules = "\n".join(f"- {r.source}" for r in client.rules)
    return f"Client story: {client.story}\nClient rules:\n{rules}\n{holdings_text(client)}"


def clean_proposal(client: Client, proposal: Proposal) -> Proposal:
    """
    Make the LLM's portfolio usable: drop tickers outside the universe (and say so in the thesis),
    drop zero/negative weights, and rescale so the weights sum to exactly 1.
    """
    universe = set(client.universe)
    outside = [t for t in proposal.weights if t not in universe]
    weights = {t: float(w) for t, w in proposal.weights.items() if t in universe and w > 0}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("The Chair's portfolio has no positive weights on allowed tickers.")
    weights = {t: w / total for t, w in weights.items()}

    thesis = proposal.thesis
    if outside:
        thesis += f" (Note: dropped {', '.join(outside)}, not in this client's universe.)"
    reasons = {t: r for t, r in proposal.reasons.items() if t in weights}
    return Proposal(weights=weights, thesis=thesis, reasons=reasons)


def failures_text(receipt: Receipt) -> list[str]:
    """The Referee's failed checks in plain English (what the Chair and analysts are shown)."""
    return [c.explain for c in receipt.checks if not c.passed]


def chair_propose(client: Client, memos: list[Memo]) -> Proposal:
    """The Chair turns the analysts' memos into a first portfolio."""
    memo_text = "\n".join(m.model_dump_json() for m in memos) or "(no memos arrived)"
    user = f"{_client_text(client)}\n\nAnalyst memos:\n{memo_text}"
    return clean_proposal(client, llm.complete_json("chair", _system(client), user, Proposal))


def chair_revise_with(client: Client, proposal: Proposal, feedback_text: str,
                      stances: list[Stance] | None = None) -> Proposal:
    """
    The Chair revises the portfolio given some feedback text (from committee/feedback.py).
    The experiment (A10) calls this directly with each feedback mode and no stances.
    """
    user = (f"{_client_text(client)}\n\n"
            f"Current portfolio: {json.dumps(proposal.weights)}\n"
            f"Revise the portfolio. Feedback:\n{feedback_text}\n")
    if stances:
        user += "Analyst stances:\n" + "\n".join(f"- {s.agent}: {s.stance}. {s.change} Why: {s.why}"
                                                 for s in stances) + "\n"
    user += "Fix every failed rule while keeping as much of the original idea as possible."
    return clean_proposal(client, llm.complete_json("chair", _system(client), user, Proposal))


def chair_revise(client: Client, proposal: Proposal, receipt: Receipt, stances: list[Stance]) -> Proposal:
    """The Chair fixes the portfolio using the Referee's explained findings and the analysts' stances."""
    feedback_text = format_feedback(receipt, client, "explained")
    return chair_revise_with(client, proposal, feedback_text, stances)
