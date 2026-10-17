"""Tests for referee/solver.py: is_feasible on real clients and a hand-made impossible case."""

import json
import os

import pytest

import config
from referee.check import check
from referee.schema import Client, Rule
from referee.solver import build_problem, is_feasible, solve

CLIENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")


def load(client_id: str) -> Client:
    with open(os.path.join(CLIENTS, f"{client_id}.json")) as f:
        return Client(**json.load(f))


def rule(id_, type_, params) -> Rule:
    return Rule(id=id_, type=type_, params=params, priority=5, hard=False, source="Test rule.")


def test_easy_client_is_feasible():
    assert is_feasible(load("C01"))


def test_dr_patel_is_feasible():
    assert is_feasible(load("C02"))


def test_dr_patel_plus_unh_is_infeasible():
    # JNJ >= 30% plus UNH >= 10% is 40% of Healthcare, but Healthcare is capped at 35%.
    assert not is_feasible(load("C03"))


def test_dropping_one_clashing_rule_makes_c03_feasible():
    c03 = load("C03")
    all_but_r8 = [r.id for r in c03.rules if r.id != "R8"]
    assert is_feasible(c03, all_but_r8)


def test_too_few_too_small_positions_is_infeasible():
    # Exactly 3 holdings, each at most 30%: the most you can invest is 90%, not 100%.
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "buy_in", {"min": 0.05}),
        rule("R2", "max_holdings", {"k": 3}),
        rule("R3", "min_holdings", {"k": 3}),
        rule("R4", "max_weight", {"ticker": "*", "max": 0.30}),
    ]})
    assert not is_feasible(client)
    # Allow 34% per stock instead and 3 x 34% = 102% >= 100%, so it becomes possible.
    client.rules[3] = rule("R4", "max_weight", {"ticker": "*", "max": 0.34})
    assert is_feasible(client)


@pytest.mark.parametrize("client_id", ["C01", "C02"])
def test_solver_portfolio_passes_check(client_id):
    # The solver and check() must agree: whatever the solver finds, check() should pass.
    client = load(client_id)
    problem, v = build_problem(client)
    assert solve(problem)
    weights = {t: float(x) for t, x in zip(v.tickers, v.w.value) if x > config.TOL}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    failed = [r.explain for r in check(weights, client) if not r.passed]
    assert failed == []


def test_turnover_and_sector_min_constraints():
    client = load("C02").model_copy(update={"rules": [
        rule("R1", "sector_min", {"sector": "Tech", "min": 0.50}),
        rule("R2", "max_turnover", {"max": 0.80}),
    ]})
    # Current: JNJ 40 / TLT 30 / KO 30, no Tech. Getting to 50% Tech means at least
    # 50% bought + 50% sold = 1.0 turnover, more than the 0.80 allowed.
    assert not is_feasible(client)
    client.rules[1] = rule("R2", "max_turnover", {"max": 1.0})
    assert is_feasible(client)


def test_unknown_rule_id_is_an_error():
    with pytest.raises(ValueError, match="R99"):
        is_feasible(load("C02"), ["R1", "R99"])
