"""Offline tests for the analysts and the Chair (A7). The LLM is replaced by a stub."""

import pytest

from committee import analysts, chair, llm
from models import AnalysisRequest, Memo, ReviewRequest, Stance
from referee.receipt import referee
from referee.schema import Proposal

PATEL = analysts.load_client("C02")


@pytest.fixture
def stub(monkeypatch):
    """Replace complete_json with a stub that records the prompt and returns a canned answer."""
    seen = {}

    def make(answer):
        def fake(role, system, user, schema):
            seen.update(role=role, system=system, user=user, schema=schema)
            return answer
        monkeypatch.setattr(llm, "complete_json", fake)
        return seen
    return make


def _request() -> AnalysisRequest:
    return AnalysisRequest(client_id="C02", client_story=PATEL.story,
                           rules_text=[r.source for r in PATEL.rules], as_of="2026-10-16")


def test_data_blocks_have_the_promised_numbers():
    u = PATEL.universe
    assert "SPY" in analysts.macro_data(u) and "Best 5 over 3 months" in analysts.macro_data(u)
    fund = analysts.fundamentals_data(u)
    assert "- GLD: P/E n/a" in fund  # ETFs have no P/E
    risk = analysts.risk_data(u)
    assert "Most correlated pairs" in risk and "- NVDA: vol" in risk


def test_analyze_stamps_agent_and_drops_outside_tickers(stub):
    seen = stub(Memo(agent="wrong", favor=["JNJ", "TSLA"], avoid=["XOM"], sector_views={},
                     reasons={}, confidence=0.6))
    memo = analysts.analyze("fundamentals", _request())
    assert memo.agent == "fundamentals"
    assert memo.favor == ["JNJ"]  # TSLA isn't in Dr. Patel's universe
    assert seen["role"] == "analyst"
    assert "No fossil fuel companies." in seen["user"]  # the client's own words reach the LLM


def test_unknown_analyst_is_an_error():
    with pytest.raises(ValueError):
        analysts.analyze("astrology", _request())


def test_review_stamps_agent(stub):
    stub(Stance(agent="x", stance="concede", change="Sell XOM.", why="Rule R2."))
    req = ReviewRequest(client_id="C02", round=1, failures=["XOM is held."],
                        proposal=Proposal(weights={"JNJ": 1.0}, thesis="t", reasons={}), conflict_explain="")
    assert analysts.review("risk", req).agent == "risk"


def test_chair_propose_cleans_the_portfolio(stub):
    seen = stub(Proposal(weights={"JNJ": 0.4, "MSFT": 0.4, "TSLA": 0.2, "KO": 0.0},
                         thesis="Quality.", reasons={"JNJ": "a", "MSFT": "b", "TSLA": "c"}))
    p = chair.chair_propose(PATEL, [])
    assert p.weights == pytest.approx({"JNJ": 0.5, "MSFT": 0.5})  # TSLA and the 0 weight dropped, rescaled
    assert "dropped TSLA" in p.thesis
    assert set(p.reasons) == {"JNJ", "MSFT"}
    assert seen["role"] == "chair"


def test_chair_with_nothing_allowed_is_an_error(stub):
    stub(Proposal(weights={"TSLA": 1.0}, thesis="t", reasons={}))
    with pytest.raises(ValueError):
        chair.chair_propose(PATEL, [])


def test_chair_revise_sees_failures_but_not_repaired_weights(stub):
    bad = Proposal(weights={"NVDA": 0.41, "JNJ": 0.30, "GOOGL": 0.15, "XOM": 0.14}, thesis="t", reasons={})
    receipt = referee(PATEL, bad)
    seen = stub(Proposal(weights={"JNJ": 0.5, "MSFT": 0.5}, thesis="t", reasons={}))
    chair.chair_revise(PATEL, bad, receipt, [])
    assert "XOM" in seen["user"] and "BROKEN" in seen["user"]
    for t, w in receipt.repaired_weights.items():
        assert f'"{t}": {w}' not in seen["user"]  # the answer key is never shown (honest M2)
