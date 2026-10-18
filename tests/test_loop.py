"""Offline tests for the committee loop and feedback modes (A8). Real Referee, scripted Chair, no LLM."""

import asyncio

import pytest

from committee import analysts, chair, feedback, llm, loop
from models import Memo, Stance
from referee.receipt import referee
from referee.schema import Proposal

PATEL = analysts.load_client("C02")
BAD = Proposal(weights={"NVDA": 0.41, "JNJ": 0.30, "GOOGL": 0.15, "XOM": 0.14}, thesis="Bad draft.", reasons={})
GOOD = Proposal(weights={"JNJ": 0.30, "MSFT": 0.15, "GOOGL": 0.10, "KO": 0.10, "PG": 0.10,
                         "TLT": 0.10, "WMT": 0.10, "NVDA": 0.05}, thesis="Good draft.", reasons={})


class StubTransport:
    """Analysts answer from a script; the Referee is the real one."""
    name = "local"

    def __init__(self, missing=()):
        self.missing = set(missing)

    async def analyze(self, agent, req):
        if agent in self.missing:
            return None
        return Memo(agent=agent, favor=["JNJ"], avoid=["XOM"], sector_views={}, reasons={}, confidence=0.5)

    async def review(self, agent, req):
        return Stance(agent=agent, stance="concede", change="Sell XOM.", why="Rule broke.")

    async def verify(self, req):
        return referee(req.client, req.proposal)


def _run(monkeypatch, drafts, client=PATEL, transport=None, max_rounds=3):
    """Run the loop with the Chair answering `drafts` in order (first = chair_propose)."""
    queue = list(drafts)
    monkeypatch.setattr(loop, "chair_propose", lambda c, memos: queue.pop(0))
    monkeypatch.setattr(loop, "chair_revise", lambda c, p, r, s: queue.pop(0))
    return asyncio.run(loop.run_committee(client, transport or StubTransport(), max_rounds))


def test_first_draft_passes(monkeypatch):
    result = _run(monkeypatch, [GOOD])
    assert result.receipt.verdict == "PASS" and result.rounds == 1
    assert not result.self_corrected  # nothing needed correcting
    assert result.final_proposal.weights == GOOD.weights


def test_committee_fixes_itself_after_one_round(monkeypatch):
    result = _run(monkeypatch, [BAD, GOOD])
    assert result.first_receipt.verdict == "VIOLATIONS_REPAIRED"
    assert result.receipt.verdict == "PASS" and result.rounds == 2 and result.self_corrected
    assert [e.agent for e in result.debate_log if e.kind == "stance"] == ["macro", "fundamentals", "risk"]


def test_out_of_rounds_uses_referee_repair(monkeypatch):
    result = _run(monkeypatch, [BAD, BAD, BAD], max_rounds=2)
    assert result.rounds == 3  # first draft + 2 debate rounds
    assert not result.self_corrected
    assert result.final_proposal.weights == result.receipt.repaired_weights
    assert any("could not self-correct" in n for n in result.notes)


def test_infeasible_rules_go_to_the_advisor(monkeypatch):
    c03 = analysts.load_client("C03")
    draft = Proposal(weights={t: 1 / len(c03.universe) for t in c03.universe}, thesis="Even split.", reasons={})
    result = _run(monkeypatch, [draft], client=c03)
    assert result.receipt.verdict == "RULES_INFEASIBLE" and result.rounds == 1
    assert "NEEDS ADVISOR APPROVAL" in result.final_proposal.thesis
    assert any(e.kind == "note" for e in result.debate_log)


def test_missing_analyst_is_noted_not_fatal(monkeypatch):
    result = _run(monkeypatch, [GOOD], transport=StubTransport(missing={"risk"}))
    assert result.receipt.verdict == "PASS"
    assert any("risk analyst did not answer" in n for n in result.notes)


# ---------- Feedback modes (MASTER 10.3) ----------

@pytest.fixture(scope="module")
def bad_receipt():
    return referee(PATEL, BAD)


def test_feedback_modes_reveal_more_and_more(bad_receipt):
    self_text = feedback.format_feedback(bad_receipt, PATEL, "self")
    bare = feedback.format_feedback(bad_receipt, PATEL, "bare")
    explained = feedback.format_feedback(bad_receipt, PATEL, "explained")
    assert "R1" not in self_text and "41.0%" not in self_text
    assert "R1" in bare and "No fossil fuel companies." in bare and "41.0%" not in bare
    assert "41.0%" in explained and "XOM" in explained


def test_no_mode_leaks_the_repaired_weights(bad_receipt):
    # If the feedback never reads repaired_weights, changing them can't change the text.
    other = bad_receipt.model_copy(update={"repaired_weights": {"KO": 1.0}})
    for mode in feedback.MODES:
        assert feedback.format_feedback(bad_receipt, PATEL, mode) == feedback.format_feedback(other, PATEL, mode)


def test_unknown_mode_is_an_error(bad_receipt):
    with pytest.raises(ValueError):
        feedback.format_feedback(bad_receipt, PATEL, "vibes")


def test_chair_revise_uses_explained_feedback(monkeypatch, bad_receipt):
    seen = {}

    def fake(role, system, user, schema):
        seen["user"] = user
        return GOOD
    monkeypatch.setattr(llm, "complete_json", fake)
    chair.chair_revise(PATEL, BAD, bad_receipt, [])
    assert seen["user"].count("41.0%") >= 1
