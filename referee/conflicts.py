"""
Which rules clash? (MASTER 6.5)

When is_feasible says "impossible", the client deserves to know WHY. We find a
minimal conflict set: a small group of rules that can't all hold together, where
removing any single one of them makes the rest possible again.

The method is a "deletion filter": try throwing each rule away. If the rules are
still impossible without it, that rule wasn't part of the problem, so drop it for
good. Whatever survives is the clash. That's at most one solver call per rule.
"""

from referee.market import load_sectors
from referee.schema import Client, Rule
from referee.solver import is_feasible

FLOOR_TYPES = {"min_weight", "sector_min"}  # "at least X%" rules
CAP_TYPES = {"max_weight", "sector_max"}    # "at most X%" rules


def find_conflicts(client: Client, rule_ids: list[str] | None = None) -> list[str]:
    """Return a minimal set of rule ids that can't all hold ([] if the rules are feasible).

    rule_ids: which rules to look at (None = all of the client's rules). The
    cheapest-fix step uses this to search only the hard rules.
    """
    remaining = [r.id for r in client.rules] if rule_ids is None else list(rule_ids)
    if is_feasible(client, remaining):
        return []

    for rule_id in list(remaining):  # copy, because we shrink `remaining` as we go
        without_it = [r for r in remaining if r != rule_id]
        if not is_feasible(client, without_it):
            # Still impossible without this rule, so it isn't needed to explain the clash.
            remaining = without_it
    return remaining


# ---------- The explanation sentence ----------

def _pct(x: float) -> str:
    """0.3 -> "30%", 0.125 -> "12.5%"."""
    return f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"


def _scope(rule: Rule, client: Client) -> set[str] | None:
    """The tickers a weight rule covers (None for max_weight "*", which covers each stock separately)."""
    if rule.type in ("min_weight", "max_weight"):
        return None if rule.params["ticker"] == "*" else {rule.params["ticker"]}
    sectors = load_sectors()
    return {t for t in client.universe if sectors.get(t) == rule.params["sector"]}


def _limit(rule: Rule) -> float:
    return rule.params["min"] if rule.type in FLOOR_TYPES else rule.params["max"]


def _arithmetic(rules: list[Rule], client: Client) -> str | None:
    """Show the sum that breaks, when the clash is simple floors against one cap.

    Example: JNJ >= 30% and UNH >= 10% are both inside "Healthcare <= 35%",
    so the floors need 30% + 10% = 40% > 35%. Returns None when the clash
    involves other kinds of rules; then we just list them.
    """
    floors = [r for r in rules if r.type in FLOOR_TYPES]
    caps = [r for r in rules if r.type in CAP_TYPES]
    if not floors or len(floors) + len(caps) != len(rules) or len(caps) > 1:
        return None

    # The floors must cover separate stocks, or adding them up would double-count.
    scopes = [_scope(f, client) for f in floors]
    covered: set[str] = set()
    for s in scopes:
        if s & covered:
            return None
        covered |= s

    total = sum(_limit(f) for f in floors)
    parts = " + ".join(_pct(_limit(f)) for f in floors)
    if not caps:
        # Floors alone: they ask for more than all the money.
        return f"{parts} = {_pct(total)} > 100%" if len(floors) > 1 else None

    cap = caps[0]
    cap_scope = _scope(cap, client)
    if cap_scope is None:
        # "No single stock above X": only explains a single-stock floor above X.
        if len(floors) != 1 or floors[0].type != "min_weight":
            return None
    elif not covered <= cap_scope:
        return None

    if len(floors) == 1:
        return f"{_pct(total)} > {_pct(_limit(cap))}"
    return f"{parts} = {_pct(total)} > {_pct(_limit(cap))}"


def explain_conflict(client: Client, conflict_ids: list[str]) -> str:
    """One plain-English sentence naming the clashing rules in the client's words."""
    if not conflict_ids:
        return ""
    rules = [r for r in client.rules if r.id in conflict_ids]
    quoted = ", ".join(f"'{r.source.rstrip('.')}'" for r in rules)
    sentence = f"These rules can't all hold: {quoted}"
    math = _arithmetic(rules, client)
    if math:
        sentence += f" ({math})"
    return sentence + "."
