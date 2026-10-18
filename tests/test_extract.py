"""
Plain-English rules -> Referee (referee/extract.py, POST /extract, the Referee Agent's chat).
The LLM is faked (complete_json is patched), so no API keys are needed.
"""

import asyncio
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from uagents import Agent, Bureau, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, TextContent, chat_protocol_spec
from uagents_core.contrib.protocols.payment import (
    CancelPayment,
    CompletePayment,
    RequestPayment,
    payment_protocol_spec,
)

import api
from agents import payments, referee_agent
from agents.chat import VERDICT_LINES
from committee import llm
from referee import extract
from referee.extract import Draft, DraftPhrase, DraftRule

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = "no oil companies, at most 30% in any stock, keep 20% in JNJ, volatility under 15%, beat the S&P"

GOOD = Draft(
    rules=[
        DraftRule(type="exclude", params={"tickers": ["XOM", "CVX"]}, source="no oil companies", hard=True),
        DraftRule(type="max_weight", params={"ticker": "*", "max": 0.3}, source="at most 30% in any stock"),
        DraftRule(type="min_weight", params={"ticker": "JNJ", "min": 0.2}, source="keep 20% in JNJ"),
        DraftRule(type="max_volatility", params={"max": 0.15}, source="volatility under 15%"),
    ],
    unmapped=[DraftPhrase(text="beat the S&P", reason="a return target is not one of the rule types")],
)


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch complete_json: answer with `draft` and record the call."""
    calls = []

    def install(draft: Draft = GOOD):
        def fake(role, system, user, schema):
            calls.append((role, system, user, schema))
            return draft
        monkeypatch.setattr(llm, "complete_json", fake)
        return calls

    return install


# ---------- referee/extract.py ----------

def test_extracts_the_example_paragraph(fake_llm):
    calls = fake_llm()
    out = extract.extract_rules(TEXT)
    assert [(r.id, r.type, r.params) for r in out.rules] == [
        ("R1", "exclude", {"tickers": ["CVX", "XOM"]}),
        ("R2", "max_weight", {"ticker": "*", "max": 0.3}),
        ("R3", "min_weight", {"ticker": "JNJ", "min": 0.2}),
        ("R4", "max_volatility", {"max": 0.15}),
    ]
    assert all(r.source in TEXT for r in out.rules)
    assert out.rules[0].hard and not out.rules[1].hard
    assert [u.text for u in out.unmapped] == ["beat the S&P"]
    role, system, user, schema = calls[0]
    assert role == "chair" and schema is Draft and TEXT in user and "XOM" in system


@pytest.mark.parametrize("bad, reason", [
    (DraftRule(type="max_weight", params={"ticker": "TSLA", "max": 0.3}, source="at most 30% in any stock"),
     "unknown ticker"),
    (DraftRule(type="max_weight", params={"ticker": "*", "max": 30}, source="at most 30% in any stock"),
     "fraction between 0 and 1"),
    (DraftRule(type="sector_max", params={"sector": "Crypto", "max": 0.1}, source="no oil companies"),
     "unknown sector"),
    (DraftRule(type="max_holdings", params={"k": 2.5}, source="no oil companies"), "whole number"),
    (DraftRule(type="buy_in", params={"min": 0.05, "extra": 1}, source="no oil companies"), "needs exactly"),
    (DraftRule(type="exclude", params={"tickers": ["XOM"]}, source="never buy Exxon"), "isn't in the text"),
])
def test_unmappable_rules_are_flagged_not_guessed(bad, reason):
    out = extract.validate_draft(TEXT, Draft(rules=[bad]))
    assert out.rules == []
    assert len(out.unmapped) == 1 and reason in out.unmapped[0].reason


def test_quotes_match_ignoring_case_and_spacing():
    draft = Draft(rules=[DraftRule(type="max_volatility", params={"max": 0.15}, source="Volatility  under 15%")])
    assert len(extract.validate_draft(TEXT, draft).rules) == 1


def test_sector_names_are_normalized():
    draft = Draft(rules=[DraftRule(type="sector_max", params={"sector": "tech", "max": 0.4}, source="no oil companies")])
    assert extract.validate_draft(TEXT, draft).rules[0].params == {"sector": "Tech", "max": 0.4}


@pytest.mark.parametrize("text, weights, rules", [
    ("check NVDA 50, JNJ 30, KO 20 against: no oil", {"NVDA": 0.5, "JNJ": 0.3, "KO": 0.2}, "no oil"),
    ("NVDA 0.6 JNJ 0.4 against at most 30% in any stock", {"NVDA": 0.6, "JNJ": 0.4}, "at most 30% in any stock"),
    ("check nvda: 50%, jnj=50% against: no oil", {"NVDA": 0.5, "JNJ": 0.5}, "no oil"),
    ("Rules: no oil, at most 30% in any stock", None, "Rules: no oil, at most 30% in any stock"),
    ("no oil companies", None, "no oil companies"),
])
def test_split_weights(text, weights, rules):
    got_weights, got_rules = extract.split_weights(text)
    assert got_weights == (pytest.approx(weights) if weights else None)
    assert got_rules == rules


def test_describe_says_whether_rules_can_be_met():
    ok = extract.validate_draft(TEXT, GOOD)
    assert "✅" in extract.describe(ok, extract.chat_client(ok.rules))
    clash = Draft(rules=[
        DraftRule(type="min_weight", params={"ticker": "JNJ", "min": 0.2}, source="keep 20% in JNJ"),
        DraftRule(type="max_weight", params={"ticker": "*", "max": 0.15}, source="volatility under 15%"),
    ])
    bad = extract.validate_draft(TEXT, clash)
    assert "⛔" in extract.describe(bad, extract.chat_client(bad.rules))


def test_importing_extract_loads_no_llm_code():
    """referee/ stays pure math: the LLM layer is only imported when extract_rules() runs."""
    code = "import sys, referee.extract; print(any(m.split('.')[0] in ('committee', 'langchain_core') for m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


# ---------- POST /extract ----------

@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def test_extract_endpoint(client, fake_llm):
    fake_llm()
    body = client.post("/api/extract", json={"text": TEXT}).json()
    assert [r["type"] for r in body["rules"]] == ["exclude", "max_weight", "min_weight", "max_volatility"]
    assert body["unmapped"] == [{"text": "beat the S&P", "reason": "a return target is not one of the rule types"}]


def test_extract_endpoint_off_in_public_demo(client, monkeypatch, fake_llm):
    calls = fake_llm()
    monkeypatch.setattr(api, "ENABLE_LIVE_RUNS", False)
    assert client.post("/api/extract", json={"text": TEXT}).status_code == 503
    assert calls == []


def test_extract_endpoint_reports_llm_failure(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no key")
    monkeypatch.setattr(llm, "complete_json", boom)
    r = client.post("/api/extract", json={"text": TEXT})
    assert r.status_code == 502 and "no key" in r.json()["detail"]
    assert client.post("/api/extract", json={"text": "  "}).status_code == 422


# ---------- Referee Agent chat ----------

def _chat(text: str) -> ChatMessage:
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                       content=[TextContent(type="text", text=text)])


def _talk(port: int, text: str, finished, timeout: int = 60) -> list:
    """Run the Referee Agent and a user who sends `text`; record what comes back."""
    events: list = []
    done = threading.Event()

    def record(event):
        events.append(event)
        if finished(events):
            done.set()

    async def run():
        loop = asyncio.get_running_loop()
        referee = referee_agent.build_agent(f"test extract referee seed {port} for swarmfolio unit tests",
                                            port + 1, mailbox=False, publish=False)
        user = Agent(name="user", seed=f"test extract user seed {port} for swarmfolio unit tests",
                     port=port + 2, loop=loop, publish_agent_details=False)
        chat = Protocol(spec=chat_protocol_spec)

        @chat.on_message(ChatMessage)
        async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
            record(("chat", " ".join(c.text for c in msg.content if isinstance(c, TextContent))))

        @chat.on_message(ChatAcknowledgement)
        async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
            pass

        pay = Protocol(spec=payment_protocol_spec, role="buyer")

        @pay.on_message(RequestPayment)
        async def on_request(ctx: Context, sender: str, msg: RequestPayment):
            record(("request", msg))

        @pay.on_message(CompletePayment)  # the buyer role must handle these too
        async def on_complete(ctx: Context, sender: str, msg: CompletePayment):
            record(("complete", msg))

        @pay.on_message(CancelPayment)
        async def on_cancel(ctx: Context, sender: str, msg: CancelPayment):
            record(("cancel", msg))

        user.include(chat)
        user.include(pay)

        @user.on_event("startup")
        async def ask(ctx: Context):
            await ctx.send(referee.address, _chat(text))

        await Bureau(agents=[referee, user], port=port, loop=loop).run_async()

    threading.Thread(target=lambda: asyncio.run(run()), daemon=True).start()
    assert done.wait(timeout=timeout), f"never finished; got {events}"
    return events


def _is_receipt(event) -> bool:
    return event[0] == "chat" and any(line in event[1] for line in VERDICT_LINES.values())


def test_chat_plain_english_with_weights_gets_receipt(monkeypatch, fake_llm):
    monkeypatch.delenv("REFEREE_PAYMENTS", raising=False)
    calls = fake_llm()
    events = _talk(8140, f"@swarmfolio-referee check NVDA 50, JNJ 30, KO 20 against: {TEXT}",
                   lambda ev: any(_is_receipt(e) for e in ev))
    assert calls[0][2].endswith(TEXT)  # only the rules go to the LLM, not the weights
    read = next(e[1] for e in events if e[0] == "chat")
    assert "I read these rules" in read and "beat the S&P" in read
    receipt = next(e[1] for e in events if _is_receipt(e))
    assert VERDICT_LINES["VIOLATIONS_REPAIRED"] in receipt  # NVDA 50% breaks "at most 30% in any stock"


def test_chat_plain_english_respects_payments(monkeypatch, fake_llm):
    fake_llm()
    monkeypatch.setenv("REFEREE_PAYMENTS", "true")
    monkeypatch.delenv("CHAIR_ADDRESS", raising=False)
    monkeypatch.delenv("CHAIR_SEED", raising=False)
    monkeypatch.setattr(payments, "create_embedded_checkout_session", lambda **kw: {
        "client_secret": "cs_test_1_secret", "id": "cs_test_1", "checkout_session_id": "cs_test_1",
        "publishable_key": "pk_test_x", "currency": "usd", "amount_cents": "50", "ui_mode": "embedded"})
    events = _talk(8144, f"check NVDA 50, JNJ 30, KO 20 against: {TEXT}",
                   lambda ev: any(e[0] == "request" for e in ev))
    assert not any(_is_receipt(e) for e in events)  # no receipt before paying


def test_chat_rules_without_weights_lists_rules_and_feasibility(monkeypatch, fake_llm):
    monkeypatch.delenv("REFEREE_PAYMENTS", raising=False)
    fake_llm()
    events = _talk(8148, TEXT, lambda ev: any("To check a portfolio" in e[1] for e in ev if e[0] == "chat"))
    reply = next(e[1] for e in events if e[0] == "chat")
    assert "I read these rules" in reply and "✅" in reply
    assert not any(_is_receipt(e) or e[0] == "request" for e in events)


def test_chat_nothing_mappable_gets_help(monkeypatch, fake_llm):
    monkeypatch.delenv("REFEREE_PAYMENTS", raising=False)
    fake_llm(Draft(unmapped=[DraftPhrase(text="make me rich", reason="not a rule")]))
    events = _talk(8152, "make me rich", lambda ev: any(e[0] == "chat" for e in ev))
    assert "couldn't find any rule" in events[0][1] and "plain English" in events[0][1]


def test_params_nested_under_the_type_name_are_unwrapped():
    """asi1-mini answered {"max_weight": {"ticker": "*", "max": 0.4}} in a live ASI:One chat; that must still work."""
    from referee.extract import Draft, DraftRule, validate_draft
    text = "no single stock above 40%, at least 35% in healthcare, healthcare at most 25%"
    draft = Draft(rules=[
        DraftRule(type="max_weight", params={"max_weight": {"ticker": "*", "max": 0.4}}, source="no single stock above 40%"),
        DraftRule(type="sector_min", params={"sector_min": {"min": 0.35, "sector": "Healthcare"}}, source="at least 35% in healthcare"),
        DraftRule(type="sector_max", params={"sector_max": {"max": 0.25, "sector": "Healthcare"}}, source="healthcare at most 25%"),
    ])
    out = validate_draft(text, draft)
    assert [r.type for r in out.rules] == ["max_weight", "sector_min", "sector_max"] and out.unmapped == []
    assert out.rules[0].params == {"ticker": "*", "max": 0.4}


def test_nested_params_still_go_through_every_check():
    """Unwrapping is not guessing: a bad value inside is still refused."""
    from referee.extract import Draft, DraftRule, validate_draft
    draft = Draft(rules=[DraftRule(type="max_weight", params={"max_weight": {"ticker": "*", "max": 40}},
                                   source="no single stock above 40%")])
    out = validate_draft("no single stock above 40%", draft)
    assert out.rules == [] and "fraction" in out.unmapped[0].reason
    # Only the rule's OWN type name is unwrapped.
    draft = Draft(rules=[DraftRule(type="max_weight", params={"sector_max": {"ticker": "*", "max": 0.4}},
                                   source="no single stock above 40%")])
    assert validate_draft("no single stock above 40%", draft).rules == []


def test_prompt_says_conflicts_are_the_referees_job():
    """asi1-mini used to drop 'healthcare at most 25%' as 'contradicting' the 35% floor; the Referee must see both."""
    from referee.extract import _system_prompt
    from referee.market import load_sectors
    assert "Map EVERY rule, even if two rules contradict each other" in _system_prompt(load_sectors())
