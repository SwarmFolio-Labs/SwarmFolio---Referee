"""
The Referee: one function that checks a proposal and writes the receipt (MASTER 6.8).

    referee(client, proposal) -> Receipt

Steps:
  1. clean dust from the proposal
  2. check every rule (plain arithmetic)
  3. ask the solver whether the rules are possible at all
  4. impossible  -> find the clash, the cheapest fix, and repair under the fixed rules
     all pass    -> nothing to do
     some broken -> repair to the nearest compliant portfolio
  5. stamp a receipt id that depends only on the inputs (same inputs, same id)
  6. write a one-sentence summary

The Referee never crashes: any error becomes a receipt with verdict ERROR, so an
agent calling it always gets an answer back.
"""

import hashlib
import json
from datetime import datetime, timezone

import config
from models import Receipt
from referee.check import check, clean_dust
from referee.conflicts import explain_conflict, find_conflicts
from referee.market import get_market, portfolio_volatility, sharpe
from referee.relax import apply_relaxations, cheapest_relaxation
from referee.repair import capital_moved, repair
from referee.schema import Client, Proposal
from referee.solver import is_feasible


def _now() -> str:
    """Current time in UTC, e.g. "2026-10-17T21:30:00Z"."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_receipt_id(client: Client, weights: dict[str, float]) -> str:
    """First 12 hex characters of sha256(client + cleaned proposal), as canonical JSON.

    Canonical = sorted keys, no extra spaces, so the same inputs always give the
    same text and therefore the same id. Anyone can recompute it to audit us.
    """
    payload = {"client": client.model_dump(mode="json"), "proposal": weights}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _error_receipt(client, proposal, message: str) -> Receipt:
    """A receipt for inputs the Referee couldn't process. Never raises."""
    client_id = getattr(client, "client_id", "unknown")
    raw = f"{client!r}|{proposal!r}"
    return Receipt(
        receipt_id=hashlib.sha256(raw.encode()).hexdigest()[:12],
        timestamp=_now(),
        client_id=str(client_id),
        verdict="ERROR",
        checks=[],
        dust_removed=[],
        rules_feasible=False,
        conflict_set=[],
        conflict_explain="",
        cheapest_relaxation=[],
        repaired_weights={},
        capital_moved=0.0,
        sharpe_before=0.0,
        sharpe_after=0.0,
        vol_after=0.0,
        summary=f"The Referee could not check this proposal: {message}",
        notes=[message],
    )


def referee(client: Client, proposal: Proposal) -> Receipt:
    """Check a proposal against the client's rules and return the full receipt."""
    try:
        return _referee(client, proposal)
    except Exception as e:  # never crash an agent: report the problem instead
        return _error_receipt(client, proposal, f"{type(e).__name__}: {e}")


def _referee(client: Client, proposal: Proposal) -> Receipt:
    notes: list[str] = []

    # 1. Clean dust.
    p, dust_removed = clean_dust(proposal.weights, client.universe)
    if dust_removed:
        notes.append(f"Positions below {config.DUST * 100:.1f}% were treated as not held: {', '.join(dust_removed)}.")

    # 2. Check every rule.
    checks = check(p, client)
    failed = [c for c in checks if not c.passed]

    # 3. Are the rules possible at all?
    rules_feasible = is_feasible(client)

    conflict_set: list[str] = []
    conflict_explain = ""
    relaxations = []
    market = get_market(client.universe)

    # 4. Decide what to do.
    if not rules_feasible:
        verdict = "RULES_INFEASIBLE"
        fix = cheapest_relaxation(client)
        if fix.hard_conflict:
            # Even bending every soft rule can't help: the hard rules clash.
            conflict_set = fix.hard_conflict
            conflict_explain = explain_conflict(client, conflict_set)
            repaired = {}
            notes.append("The client's hard rules clash, so no portfolio is possible until they change.")
        else:
            conflict_set = find_conflicts(client)
            conflict_explain = explain_conflict(client, conflict_set)
            relaxations = fix.relaxations
            repaired = repair(p, apply_relaxations(client, relaxations))
            notes.append("Repaired under the relaxed rules (cheapest fix): needs advisor approval.")
    elif not failed:
        verdict = "PASS"
        repaired = p
    else:
        verdict = "VIOLATIONS_REPAIRED"
        repaired = repair(p, client)

    # 5. Numbers before and after.
    moved = capital_moved(p, repaired) if repaired else 0.0
    sharpe_before = sharpe(market, p)
    sharpe_after = sharpe(market, repaired) if repaired else 0.0
    vol_after = portfolio_volatility(market, repaired) if repaired else 0.0

    # 6. One-sentence summary.
    n = len(checks)
    if verdict == "PASS":
        summary = (f"The proposal follows all {n} rules. Sharpe {sharpe_before:.2f}, "
                   f"volatility {vol_after * 100:.1f}%.")
    elif verdict == "VIOLATIONS_REPAIRED":
        summary = (f"The proposal broke {len(failed)} of {n} rules. The nearest compliant portfolio "
                   f"moves {_pct(moved)} of capital and changes Sharpe from {sharpe_before:.2f} to {sharpe_after:.2f}.")
    elif not repaired:
        summary = f"The client's hard rules can't all hold ({', '.join(conflict_set)}); no portfolio is possible."
    else:
        fixes = " ".join(r.explain for r in relaxations)
        summary = (f"These rules can't all hold ({', '.join(conflict_set)}). Cheapest fix: {fixes} "
                   f"Under the relaxed rules, the nearest portfolio moves {_pct(moved)} of capital.")

    return Receipt(
        receipt_id=make_receipt_id(client, p),
        timestamp=_now(),
        client_id=client.client_id,
        verdict=verdict,
        checks=checks,
        dust_removed=dust_removed,
        rules_feasible=rules_feasible,
        conflict_set=conflict_set,
        conflict_explain=conflict_explain,
        cheapest_relaxation=relaxations,
        repaired_weights=repaired,
        capital_moved=moved,
        sharpe_before=sharpe_before,
        sharpe_after=sharpe_after,
        vol_after=vol_after,
        summary=summary,
        notes=notes,
    )
