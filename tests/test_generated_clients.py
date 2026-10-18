"""The generated hard clients C10-C27 (eval/make_clients.py, MASTER 10.1).

Checks the promises the generator makes: 15 feasible + 3 planted conflicts, the
Referee agrees with every label, volatility caps sit 0.5-1.0 point above the
solver's floor, and the hard rule mixes are actually there.
"""

import json
import os

import pytest

from eval.make_clients import ARCHETYPES, min_volatility
from referee.conflicts import find_conflicts
from referee.schema import Client
from referee.solver import is_feasible

CLIENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")
IDS = [f"C{i}" for i in range(10, 28)]


def load(client_id: str) -> Client:
    with open(os.path.join(CLIENTS_DIR, f"{client_id}.json")) as f:
        return Client.model_validate(json.load(f))


CLIENTS = {cid: load(cid) for cid in IDS}
FEASIBLE = [c for c in CLIENTS.values() if c.planted_conflict is None]
PLANTED = [c for c in CLIENTS.values() if c.planted_conflict is not None]


def types(client: Client) -> set[str]:
    return {r.type for r in client.rules}


def test_generator_only_makes_c10_to_c27():
    assert [a[0] for a in ARCHETYPES] == IDS


def test_counts_ids_and_names():
    assert len(FEASIBLE) == 15 and len(PLANTED) == 3
    for cid, client in CLIENTS.items():
        assert client.client_id == cid
        assert client.name.endswith("(synthetic)") and client.story
        assert [r.id for r in client.rules] == [f"R{i}" for i in range(1, len(client.rules) + 1)]
        assert all(r.source and "{" not in r.source for r in client.rules)
    assert len({c.name for c in CLIENTS.values()}) == len(CLIENTS)


@pytest.mark.parametrize("client", FEASIBLE, ids=lambda c: c.client_id)
def test_feasible_clients_are_feasible(client):
    assert is_feasible(client)


@pytest.mark.parametrize("client", PLANTED, ids=lambda c: c.client_id)
def test_planted_conflict_is_exactly_what_the_referee_finds(client):
    assert not is_feasible(client)
    assert sorted(find_conflicts(client)) == sorted(client.planted_conflict)


VOL_CLIENTS = [c for c in FEASIBLE if "max_volatility" in types(c)]


@pytest.mark.parametrize("client", VOL_CLIENTS, ids=lambda c: c.client_id)
def test_vol_cap_is_half_to_one_point_above_the_floor(client):
    cap = next(r.params["max"] for r in client.rules if r.type == "max_volatility")
    gap = cap - min_volatility(client)
    # 0.5-1.0 point, plus 0.05 point of slack for rounding the cap to 0.1 point and SCIP's 0.1% gap.
    assert 0.0045 <= gap <= 0.0105, f"{client.client_id}: cap {cap} is {gap * 100:.2f} points above the floor"


def test_the_hard_rule_mixes_are_all_there():
    interlocking = [c for c in FEASIBLE
                    if types(c) & {"sector_min", "sector_max"} and types(c) & {"max_weight", "min_weight"}]
    holdings_buy_in = [c for c in FEASIBLE if {"max_holdings", "buy_in"} <= types(c)]
    turnover = [c for c in FEASIBLE if "max_turnover" in types(c)]
    assert len(VOL_CLIENTS) >= 6
    assert len(interlocking) >= 6
    assert len(holdings_buy_in) >= 3
    assert len(turnover) >= 3
    assert all(c.current_weights and abs(sum(c.current_weights.values()) - 1) < 1e-9 for c in turnover)
    assert any(len(c.rules) >= 9 for c in FEASIBLE)
