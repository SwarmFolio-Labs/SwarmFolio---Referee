"""Integration tests for the full Referee on Dr. Patel (MASTER 6.9).

Exact repaired weights can shift a little when prices are refreshed, so these
test properties (every rule passes, weights sum to 1) rather than exact numbers.
"""

import json
import os

import pytest

import config
from models import Receipt
from referee.check import check
from referee.receipt import referee
from referee.relax import apply_relaxations
from referee.schema import Client, Proposal

CLIENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")


def load(client_id: str) -> Client:
    with open(os.path.join(CLIENTS, f"{client_id}.json")) as f:
        return Client(**json.load(f))


def proposal(weights: dict[str, float]) -> Proposal:
    return Proposal(weights=weights, thesis="Test thesis.", reasons={t: "test" for t in weights})


BAD = {"NVDA": 0.41, "JNJ": 0.30, "GOOGL": 0.15, "XOM": 0.14}


@pytest.fixture(scope="module")
def patel_receipt() -> Receipt:
    return referee(load("C02"), proposal(BAD))


def test_bad_patel_proposal_is_repaired(patel_receipt):
    r = patel_receipt
    assert r.verdict == "VIOLATIONS_REPAIRED"
    assert r.rules_feasible
    failed = {c.rule_id for c in r.checks if not c.passed}
    assert failed == {"R1", "R2", "R7"}  # NVDA 41% > 35%, XOM held, volatility > 18%
    assert "broke 3 of 7 rules" in r.summary


def test_repaired_weights_pass_every_rule(patel_receipt):
    w = patel_receipt.repaired_weights
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-9)
    failed = [c.explain for c in check(w, load("C02")) if not c.passed]
    assert failed == []
    assert w.get("NVDA", 0) <= 0.35 + config.TOL
    assert "XOM" not in w
    assert patel_receipt.vol_after <= 0.18 + config.TOL


def test_repair_moves_some_but_not_all_capital(patel_receipt):
    # At least the 6 points of NVDA over the cap and the 14% XOM have to move.
    assert 0.20 - 1e-6 <= patel_receipt.capital_moved < 0.5


def test_c03_is_infeasible_with_conflict_and_fix():
    c03 = load("C03")
    r = referee(c03, proposal(BAD))
    assert r.verdict == "RULES_INFEASIBLE"
    assert not r.rules_feasible
    assert set(r.conflict_set) == {"R3", "R4", "R8"}
    assert "(30% + 10% = 40% > 35%)" in r.conflict_explain
    assert [x.rule_id for x in r.cheapest_relaxation] == ["R4"]
    assert r.cheapest_relaxation[0].new_limit == pytest.approx(0.40)
    # The repaired portfolio follows the RELAXED rules.
    relaxed = apply_relaxations(c03, r.cheapest_relaxation)
    assert all(c.passed for c in check(r.repaired_weights, relaxed))
    assert any("advisor approval" in n for n in r.notes)


def test_compliant_proposal_passes_unchanged(patel_receipt):
    good = patel_receipt.repaired_weights
    r = referee(load("C02"), proposal(good))
    assert r.verdict == "PASS"
    assert r.capital_moved == pytest.approx(0.0, abs=1e-9)
    assert r.sharpe_before == pytest.approx(r.sharpe_after)


def test_same_inputs_same_receipt_id():
    a = referee(load("C02"), proposal(BAD))
    b = referee(load("C02"), proposal(BAD))
    assert a.receipt_id == b.receipt_id
    assert len(a.receipt_id) == 12
    c = referee(load("C02"), proposal({**BAD, "NVDA": 0.40, "GOOGL": 0.16}))
    assert c.receipt_id != a.receipt_id


def test_dust_is_cleaned_and_reported():
    r = referee(load("C02"), proposal({**BAD, "PFE": 0.002}))
    assert r.dust_removed == ["PFE"]
    assert "PFE" not in r.repaired_weights or r.repaired_weights["PFE"] >= config.DUST


def test_ticker_outside_universe_is_an_error():
    r = referee(load("C02"), proposal({"NVDA": 0.5, "ZZZZ": 0.5}))
    assert r.verdict == "ERROR"
    assert "ZZZZ" in r.notes[0]


def test_garbage_input_never_crashes():
    r = referee(None, None)
    assert r.verdict == "ERROR"
    assert r.client_id == "unknown"


def test_receipt_round_trips_as_json(patel_receipt):
    again = Receipt.model_validate_json(patel_receipt.model_dump_json())
    assert again == patel_receipt
