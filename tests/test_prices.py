"""Tests for rule price tags (A11, MASTER 6.10)."""

import time

import pytest

from committee.analysts import load_client
from referee.prices import best_utility, rule_prices
from referee.schema import Rule

PATEL = load_client("C02")


def test_removing_a_rule_never_lowers_utility():
    """Fewer rules = more choice, so the best utility can only stay the same or go up."""
    all_ids = [r.id for r in PATEL.rules]
    u_all, _ = best_utility(PATEL, all_ids)
    for rid in all_ids:
        u_without, _ = best_utility(PATEL, [i for i in all_ids if i != rid])
        assert u_without >= u_all - 1e-4, rid


def test_a_rule_that_cannot_bind_costs_nothing():
    loose = PATEL.model_copy(deep=True)
    loose.rules.append(Rule(id="R99", type="max_weight", params={"ticker": "*", "max": 0.99}, priority=1,
                            hard=False, source="No single position above 99%."))
    r99 = next(p for p in rule_prices(loose) if p.rule_id == "R99")
    assert not r99.binds and r99.utility_cost_pts == pytest.approx(0, abs=0.01)
    assert "costs nothing" in r99.explain


def test_patel_prices_match_the_verified_numbers_and_are_fast():
    start = time.time()
    prices = {p.rule_id: p for p in rule_prices(PATEL)}
    assert time.time() - start < 5
    assert prices["R3"].utility_cost_pts == pytest.approx(0.85, abs=0.1)  # keep 30% JNJ
    assert prices["R7"].utility_cost_pts == pytest.approx(0.70, abs=0.1)  # volatility <= 18%
    assert prices["R7"].sharpe_with == pytest.approx(1.95, abs=0.05)
    assert prices["R7"].sharpe_without == pytest.approx(1.79, abs=0.05)
    for rid in ("R1", "R2", "R4", "R5", "R6"):
        assert not prices[rid].binds and prices[rid].utility_cost_pts < 0.1


def test_prices_are_sorted_most_expensive_first():
    costs = [p.utility_cost_pts for p in rule_prices(PATEL)]
    assert costs == sorted(costs, reverse=True)


def test_infeasible_client_is_priced_on_relaxed_rules():
    prices = rule_prices(load_client("C03"))
    assert len(prices) == 8
    assert all("relaxed rules" in p.explain for p in prices)
