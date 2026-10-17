"""Stress test: the Referee on 30 random clients (fixed seed, so it's reproducible).

Random rules from all 10 types, random limits, ~15% hard rules, random proposals
with some dust. Whatever comes out, the Referee's promises must hold:
  - it never returns ERROR
  - PASS / VIOLATIONS_REPAIRED: the repaired weights pass every rule and sum to 1
  - RULES_INFEASIBLE: the conflict set is minimal (drop any one rule -> possible),
    and the cheapest fix makes the client possible, with the repair passing every relaxed rule
"""

import numpy as np
import pytest

from referee.check import check
from referee.market import load_sectors
from referee.receipt import referee
from referee.relax import apply_relaxations
from referee.schema import Client, Proposal, Rule
from referee.solver import is_feasible

SEED = 20261017
N_CLIENTS = 30
RULE_TYPES = [
    "max_weight", "min_weight", "exclude", "sector_max", "sector_min",
    "max_holdings", "min_holdings", "buy_in", "max_volatility", "max_turnover",
]


def _random_weights(rng, tickers: list[str], k: int) -> dict[str, float]:
    """k random tickers with random weights that sum to 1."""
    picked = rng.choice(tickers, size=k, replace=False)
    w = rng.dirichlet(np.ones(k))
    return {str(t): float(x) for t, x in zip(picked, w)}


def _random_params(rng, rule_type: str, tickers: list[str], sectors: list[str]) -> dict:
    u = lambda lo, hi: round(float(rng.uniform(lo, hi)), 3)  # noqa: E731
    ticker = lambda: str(rng.choice(tickers))  # noqa: E731
    if rule_type == "max_weight":
        return {"ticker": "*" if rng.random() < 0.5 else ticker(), "max": u(0.15, 0.5)}
    if rule_type == "min_weight":
        return {"ticker": ticker(), "min": u(0.02, 0.3)}
    if rule_type == "exclude":
        return {"tickers": [str(t) for t in rng.choice(tickers, size=int(rng.integers(1, 3)), replace=False)]}
    if rule_type == "sector_max":
        return {"sector": str(rng.choice(sectors)), "max": u(0.1, 0.6)}
    if rule_type == "sector_min":
        return {"sector": str(rng.choice(sectors)), "min": u(0.05, 0.4)}
    if rule_type == "max_holdings":
        return {"k": int(rng.integers(3, 11))}
    if rule_type == "min_holdings":
        return {"k": int(rng.integers(2, 9))}
    if rule_type == "buy_in":
        return {"min": u(0.02, 0.1)}
    if rule_type == "max_volatility":
        return {"max": u(0.10, 0.30)}
    return {"max": u(0.3, 1.5)}  # max_turnover


def make_random_cases(seed: int = SEED, n: int = N_CLIENTS) -> list[tuple[Client, Proposal]]:
    """n random (client, proposal) pairs from one fixed seed."""
    rng = np.random.default_rng(seed)
    sector_map = load_sectors()
    tickers = sorted(sector_map)
    sectors = sorted(set(sector_map.values()))

    cases = []
    for i in range(n):
        rules = []
        for j in range(int(rng.integers(3, 8))):
            rule_type = str(rng.choice(RULE_TYPES))
            rules.append(Rule(
                id=f"R{j + 1}",
                type=rule_type,
                params=_random_params(rng, rule_type, tickers, sectors),
                priority=int(rng.integers(1, 11)),
                hard=bool(rng.random() < 0.15),
                source=f"Random {rule_type} rule.",
            ))
        current = _random_weights(rng, tickers, int(rng.integers(2, 6))) if rng.random() < 0.6 else {}
        client = Client(
            client_id=f"S{i + 1:02d}",
            name=f"Stress client {i + 1}",
            story="Randomly generated for the stress test.",
            universe=tickers,
            current_weights=current,
            rules=rules,
        )
        weights = _random_weights(rng, tickers, int(rng.integers(3, 9)))
        if rng.random() < 0.4:
            # Sprinkle in a dust position the Referee should clean away.
            dust_ticker = str(rng.choice([t for t in tickers if t not in weights]))
            weights[dust_ticker] = 0.002
        cases.append((client, Proposal(weights=weights, thesis="Random.", reasons={})))
    return cases


CASES = make_random_cases()


@pytest.mark.parametrize("client,proposal", CASES, ids=[c.client_id for c, _ in CASES])
def test_referee_keeps_its_promises(client: Client, proposal: Proposal):
    r = referee(client, proposal)
    assert r.verdict != "ERROR", r.notes

    if r.verdict in ("PASS", "VIOLATIONS_REPAIRED"):
        w = r.repaired_weights
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)
        failed = [c.explain for c in check(w, client) if not c.passed]
        assert failed == []
        return

    assert r.verdict == "RULES_INFEASIBLE"
    conflict = r.conflict_set
    assert conflict, "an infeasible client must name its clashing rules"
    assert not is_feasible(client, conflict)
    for rule_id in conflict:
        assert is_feasible(client, [x for x in conflict if x != rule_id]), f"{rule_id} isn't needed"

    if not r.cheapest_relaxation:
        # Hard rules clash: no fix is allowed, so there's no repaired portfolio.
        assert r.repaired_weights == {}
        return

    relaxed = apply_relaxations(client, r.cheapest_relaxation)
    assert is_feasible(relaxed)
    assert sum(r.repaired_weights.values()) == pytest.approx(1.0, abs=1e-6)
    failed = [c.explain for c in check(r.repaired_weights, relaxed) if not c.passed]
    assert failed == []
