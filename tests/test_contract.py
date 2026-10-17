"""
A0 tests: every sample and client file matches the contract, the wire
envelopes round-trip, and the fake committee tells the story Devin expects.
"""

import asyncio
import json
import os

import pandas as pd
import pytest

import fakes
import models
from agents.messages import ReceiptMsg, VerifyRequestMsg, pack, unpack
from referee.schema import Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SAMPLES = os.path.join(DATA, "samples")


def _load(path):
    with open(path) as f:
        return json.load(f)


def _model_for(sample_name: str):
    """Receipt_infeasible.json -> models.Receipt, Client.json -> models.Client, ..."""
    return getattr(models, sample_name.split("_")[0])


@pytest.mark.parametrize("name", sorted(f for f in os.listdir(SAMPLES) if f.endswith(".json")))
def test_every_sample_validates(name):
    cls = _model_for(name[:-5])
    cls.model_validate(_load(os.path.join(SAMPLES, name)))


@pytest.mark.parametrize("client_id", ["C01", "C02", "C03"])
def test_every_client_validates(client_id):
    client = Client.model_validate(_load(os.path.join(DATA, "clients", f"{client_id}.json")))
    sectors = _load(os.path.join(DATA, "sectors.json"))
    # Every stock in the universe needs a sector, or sector rules can't be checked.
    assert all(t in sectors for t in client.universe)
    # Rule ids must be unique so receipts can point at them.
    ids = [r.id for r in client.rules]
    assert len(ids) == len(set(ids))


def test_c03_is_c02_plus_unh_rule():
    c02 = fakes.load_client("C02")
    c03 = fakes.load_client("C03")
    assert c03.rules[:-1] == c02.rules
    assert c03.rules[-1].id == "R8" and c03.rules[-1].params == {"ticker": "UNH", "min": 0.10}
    assert c03.planted_conflict == ["R3", "R4", "R8"]


def test_prices_cover_universe():
    prices = pd.read_csv(os.path.join(DATA, "prices.csv"), index_col="Date")
    sectors = _load(os.path.join(DATA, "sectors.json"))
    for ticker in list(sectors) + ["SPY"]:
        assert ticker in prices.columns


def test_wire_envelope_round_trip():
    req = models.VerifyRequest.model_validate(_load(os.path.join(SAMPLES, "VerifyRequest.json")))
    msg = VerifyRequestMsg(payload=pack(req))
    assert unpack(models.VerifyRequest, msg.payload) == req
    receipt = fakes.referee(req.client, req.proposal)
    assert unpack(models.Receipt, ReceiptMsg(payload=pack(receipt)).payload) == receipt


def test_fake_weights_sum_to_one():
    assert sum(fakes.FIRST_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(fakes.REVISED_WEIGHTS.values()) == pytest.approx(1.0)


def test_fake_committee_story():
    result = asyncio.run(fakes.run_committee(fakes.load_client("C02"), fakes.FakeLocalTransport()))
    failed = [c.rule_id for c in result.first_receipt.checks if not c.passed]
    assert failed == ["R4"]                       # one violation in the first receipt
    stances = {e.stance for e in result.debate_log if e.kind == "stance"}
    assert {"concede", "defend"} <= stances       # a concede and a defend
    assert result.receipt.verdict == "PASS" and result.rounds == 2
    assert result.self_corrected


def test_fake_committee_infeasible():
    result = asyncio.run(fakes.run_committee(fakes.load_client("C03"), fakes.FakeLocalTransport()))
    assert result.receipt.verdict == "RULES_INFEASIBLE"
    assert result.receipt.conflict_set == ["R3", "R4", "R8"]
