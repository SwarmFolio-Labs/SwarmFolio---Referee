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


def test_analyze_pulls_tickers_out_of_described_items(stub):
    """LLMs write 'GOOGL: cheap at 17 P/E' instead of 'GOOGL'; the tickers must survive, the text becomes a reason."""
    stub(Memo(agent="fundamentals",
              favor=["GOOGL: cheap at 17 P/E", "MSFT", "GOOGL (again)", "TSLA: not ours"],
              avoid=["XOM/CVX: prohibited", "UNH — shrinking revenue", "the energy names like XOM"],
              sector_views={}, reasons={"MSFT": "Strong margins."}, confidence=0.7))
    memo = analysts.analyze("fundamentals", _request())
    assert memo.favor == ["GOOGL", "MSFT"]  # deduped, TSLA dropped (not in the universe)
    assert memo.avoid == ["XOM", "CVX", "UNH"]  # last item: no ticker before a separator, falls back to the whole text
    assert memo.reasons["GOOGL"] == "GOOGL: cheap at 17 P/E"  # first explanation wins
    assert memo.reasons["CVX"] == "XOM/CVX: prohibited"
    assert memo.reasons["MSFT"] == "Strong margins."  # an existing reason is never overwritten


def test_analyst_prompt_asks_for_bare_tickers(stub):
    seen = stub(Memo(agent="macro", favor=[], avoid=[], sector_views={}, reasons={}, confidence=0.5))
    analysts.analyze("macro", _request())
    assert "bare ticker symbols" in seen["system"]


ALVAREZ = analysts.load_client("C04")


def test_holdings_text_shows_holdings_and_turnover_definition():
    text = analysts.holdings_text(ALVAREZ)
    assert "NVDA 25.0%" in text and "MSFT 20.0%" in text
    assert "|new weight - current weight|" in text and "20% turnover" in text
    # Dr. Patel has holdings but no turnover rule: holdings yes, definition no.
    patel_text = analysts.holdings_text(PATEL)
    assert "JNJ 40.0%" in patel_text and "Turnover" not in patel_text


def test_chair_and_analysts_see_current_holdings(stub):
    """Without today's holdings, nobody can keep turnover under the cap (the C04 failure)."""
    seen = stub(Proposal(weights={"JPM": 1.0}, thesis="t", reasons={}))
    chair.chair_propose(ALVAREZ, [])
    assert "NVDA 25.0%" in seen["user"] and "Turnover =" in seen["user"]
    chair.chair_revise_with(ALVAREZ, Proposal(weights={"JPM": 1.0}, thesis="t", reasons={}), "fix it")
    assert "NVDA 25.0%" in seen["user"]

    seen = stub(Memo(agent="risk", favor=[], avoid=[], sector_views={}, reasons={}, confidence=0.5))
    req = AnalysisRequest(client_id="C04", client_story=ALVAREZ.story,
                          rules_text=[r.source for r in ALVAREZ.rules], as_of="2026-10-16")
    analysts.analyze("risk", req)
    assert "NVDA 25.0%" in seen["user"]

    seen = stub(Stance(agent="risk", stance="concede", change="c", why="w"))
    analysts.review("risk", ReviewRequest(client_id="C04", round=1, failures=["Turnover too high."],
                                          proposal=Proposal(weights={"JPM": 1.0}, thesis="t", reasons={}),
                                          conflict_explain=""))
    assert "NVDA 25.0%" in seen["user"] and "Turnover =" in seen["user"]
