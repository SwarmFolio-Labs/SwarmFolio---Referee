"""Tests for referee/relax.py: the cheapest fix for impossible rules."""

import json
import os

import pytest

from referee.relax import apply_relaxations, cheapest_relaxation
from referee.schema import Client, Rule
from referee.solver import is_feasible

CLIENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")


def load(client_id: str) -> Client:
    with open(os.path.join(CLIENTS, f"{client_id}.json")) as f:
        return Client(**json.load(f))


def rule(id_, type_, params, priority=5, hard=False, source="Test rule.") -> Rule:
    return Rule(id=id_, type=type_, params=params, priority=priority, hard=hard, source=source)


def test_c03_cheapest_fix_raises_the_healthcare_cap():
    # Bending R4 (priority 4) by 5 points costs 20; R8 would cost 30 and R3 would cost 35.
    result = cheapest_relaxation(load("C03"))
    assert result.hard_conflict == []
    assert len(result.relaxations) == 1
    fix = result.relaxations[0]
    assert fix.rule_id == "R4"
    assert fix.old_limit == pytest.approx(0.35)
    assert fix.new_limit == pytest.approx(0.40)
    assert fix.cost == pytest.approx(20)
    assert "Healthcare at most 35%" in fix.explain and "35.0% to 40.0%" in fix.explain


def test_c03_fix_touches_no_hard_rule():
    c03 = load("C03")
    hard = {r.id for r in c03.rules if r.hard}
    relaxed = {r.rule_id for r in cheapest_relaxation(c03).relaxations}
    assert not relaxed & hard


def test_applying_the_fix_makes_c03_feasible():
    c03 = load("C03")
    fixed = apply_relaxations(c03, cheapest_relaxation(c03).relaxations)
    assert is_feasible(fixed)
    # The original client is untouched.
    assert not is_feasible(c03)


def test_feasible_client_needs_no_relaxation():
    assert cheapest_relaxation(load("C02")).relaxations == []


def test_holdings_rule_bends_by_whole_names():
    # At most 3 stocks, each at most 30%: impossible. Adding one name (cost 3) is far
    # cheaper than raising the 30% cap to 34% (4 points x priority 10 = 40).
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "max_holdings", {"k": 3}, priority=3),
        rule("R2", "max_weight", {"ticker": "*", "max": 0.30}, priority=10),
    ]})
    result = cheapest_relaxation(client)
    assert [r.rule_id for r in result.relaxations] == ["R1"]
    fix = result.relaxations[0]
    assert fix.new_limit == 4 and fix.cost == pytest.approx(3)
    fixed = apply_relaxations(client, result.relaxations)
    assert fixed.rules[0].params["k"] == 4
    assert is_feasible(fixed)


def test_hard_rules_that_clash_are_reported():
    # Two hard floors asking for 110% of the money: no soft rule can fix that.
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "min_weight", {"ticker": "AAPL", "min": 0.60}, hard=True),
        rule("R2", "min_weight", {"ticker": "MSFT", "min": 0.50}, hard=True),
        rule("R3", "max_holdings", {"k": 5}),
    ]})
    result = cheapest_relaxation(client)
    assert result.relaxations == []
    assert set(result.hard_conflict) == {"R1", "R2"}
