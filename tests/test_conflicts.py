"""Tests for referee/conflicts.py: the deletion filter and its explanation sentence."""

import json
import os

import pytest

from referee.conflicts import explain_conflict, find_conflicts
from referee.schema import Client, Rule
from referee.solver import is_feasible

CLIENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")


def load(client_id: str) -> Client:
    with open(os.path.join(CLIENTS, f"{client_id}.json")) as f:
        return Client(**json.load(f))


def rule(id_, type_, params, source="Test rule.") -> Rule:
    return Rule(id=id_, type=type_, params=params, priority=5, hard=False, source=source)


def test_c03_conflict_is_exactly_r3_r4_r8():
    c03 = load("C03")
    conflict = find_conflicts(c03)
    assert set(conflict) == {"R3", "R4", "R8"}
    assert set(conflict) == set(c03.planted_conflict)


def test_conflict_set_is_minimal():
    # Removing any ONE rule from the conflict set must make it possible again.
    c03 = load("C03")
    conflict = find_conflicts(c03)
    assert not is_feasible(c03, conflict)
    for r in conflict:
        assert is_feasible(c03, [x for x in conflict if x != r])


@pytest.mark.parametrize("client_id", ["C01", "C02"])
def test_feasible_clients_have_no_conflict(client_id):
    assert find_conflicts(load(client_id)) == []


def test_c03_explanation_shows_the_arithmetic():
    c03 = load("C03")
    text = explain_conflict(c03, find_conflicts(c03))
    assert text.startswith("These rules can't all hold:")
    assert "Keep at least 30% in legacy JNJ" in text
    assert "Healthcare at most 35%" in text
    assert "(30% + 10% = 40% > 35%)" in text


def test_holdings_clash_is_listed_without_arithmetic():
    # At most 3 stocks, each at most 30%: 90% is the most you can invest.
    # buy_in and min_holdings aren't needed for the clash, so the filter drops them.
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "buy_in", {"min": 0.05}),
        rule("R2", "max_holdings", {"k": 3}, "At most 3 stocks."),
        rule("R3", "min_holdings", {"k": 3}),
        rule("R4", "max_weight", {"ticker": "*", "max": 0.30}, "Nothing above 30%."),
    ]})
    conflict = find_conflicts(client)
    assert set(conflict) == {"R2", "R4"}
    text = explain_conflict(client, conflict)
    assert text == "These rules can't all hold: 'At most 3 stocks', 'Nothing above 30%'."


def test_floors_above_100_percent():
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "min_weight", {"ticker": "AAPL", "min": 0.60}, "At least 60% Apple."),
        rule("R2", "min_weight", {"ticker": "MSFT", "min": 0.50}, "At least 50% Microsoft."),
    ]})
    conflict = find_conflicts(client)
    assert set(conflict) == {"R1", "R2"}
    assert "(60% + 50% = 110% > 100%)" in explain_conflict(client, conflict)


def test_single_floor_above_single_cap():
    client = load("C01").model_copy(update={"rules": [
        rule("R1", "min_weight", {"ticker": "NVDA", "min": 0.25}, "At least 25% NVDA."),
        rule("R2", "max_weight", {"ticker": "*", "max": 0.20}, "No stock above 20%."),
    ]})
    conflict = find_conflicts(client)
    assert "(25% > 20%)" in explain_conflict(client, conflict)


def test_no_conflict_means_empty_explanation():
    assert explain_conflict(load("C02"), []) == ""
