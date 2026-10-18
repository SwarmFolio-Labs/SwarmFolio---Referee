"""
What the Chair is told after the Referee checks a portfolio (MASTER 10.3).

Three modes, so the experiment can ask "does it matter HOW the math explains itself?":
- "self":      no Referee info at all, just "re-check your work" (what most AI products do today).
- "bare":      which rules failed (id + the client's own words), but no numbers.
- "explained": the Referee's sentences with actual vs limit, plus the conflict explanation.
No mode ever shows the repaired weights: that would just be copying the answer.
"""

from models import Receipt
from referee.schema import Client

MODES = ("self", "bare", "explained")


def format_feedback(receipt: Receipt, client: Client, mode: str) -> str:
    """Turn a receipt into the feedback text for the Chair, in one of the three modes."""
    failed = [c for c in receipt.checks if not c.passed]

    if mode == "self":
        return "Re-check your portfolio against the client's rules and fix anything that breaks them."

    if mode == "bare":
        source = {r.id: r.source for r in client.rules}
        if not failed:
            return "The independent Referee found no broken rules."
        lines = ["The independent Referee says these rules failed:"]
        for c in failed:
            lines.append(f"- {c.rule_id}: '{source.get(c.rule_id, c.type)}'")
        return "\n".join(lines)

    if mode == "explained":
        if not failed:
            lines = ["The independent Referee found no broken rules."]
        else:
            lines = ["The independent Referee checked the portfolio. These rules failed:"]
            lines += [f"- {c.explain}" for c in failed]
        if receipt.conflict_explain:
            lines.append(receipt.conflict_explain)
        return "\n".join(lines)

    raise ValueError(f"Unknown feedback mode {mode!r} (use one of {MODES})")
