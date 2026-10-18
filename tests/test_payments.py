"""
Tests for pay-per-check on the Referee Agent (agents/payments.py), all offline with Stripe mocked.

The agent tests run the real Referee Agent and a stand-in "buyer" (like the Agentverse Inspector)
in one local Bureau: chat -> RequestPayment -> CommitPayment -> CompletePayment + receipt.
"""

import asyncio
import threading
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from uagents import Agent, Bureau, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, TextContent, chat_protocol_spec
from uagents_core.contrib.protocols.payment import (
    CancelPayment,
    CommitPayment,
    CompletePayment,
    Funds,
    RequestPayment,
    payment_protocol_spec,
)

import fakes
from agents import payments, referee_agent
from agents.chat import VERDICT_LINES
from models import VerifyRequest

SECRET, PUBLISHABLE = "sk_test_fake_for_unit_tests", "pk_test_fake_for_unit_tests"


class FakeStripe:
    """Just enough of the stripe module: checkout.Session.create / retrieve."""

    def __init__(self, payment_status: str = "paid"):
        self.created: dict = {}
        self.retrieved: list[str] = []
        fake = self

        class Session:
            @staticmethod
            def create(**kwargs):
                fake.created = kwargs
                return SimpleNamespace(id="cs_test_123", client_secret="cs_test_123_secret_abc")

            @staticmethod
            def retrieve(session_id):
                fake.retrieved.append(session_id)
                return SimpleNamespace(id=session_id, payment_status=payment_status)

        self.checkout = SimpleNamespace(Session=Session)


@pytest.fixture
def test_keys(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", SECRET)
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", PUBLISHABLE)


# ---------- payments.py on its own ----------

@pytest.mark.parametrize("secret, publishable", [
    ("", ""),
    ("sk_live_abc", "pk_live_abc"),
    ("sk_live_abc", PUBLISHABLE),
    (SECRET, "pk_live_abc"),
    ("rk_test_abc", PUBLISHABLE),
])
def test_refuses_missing_or_live_keys(monkeypatch, secret, publishable):
    """Anything that isn't an sk_test_ / pk_test_ pair is refused, before Stripe is called."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", secret)
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", publishable)
    with pytest.raises(payments.PaymentSetupError) as err:
        payments.create_embedded_checkout_session(user_address="agent1x", chat_session_id="s", description="d")
    assert "sk_live" not in str(err.value)  # never echo a key back


def test_checkout_session_matches_fetch_example(monkeypatch, test_keys):
    """An embedded $0.50 USD card checkout; the result is the metadata["stripe"] the UI needs."""
    fake = FakeStripe()
    monkeypatch.setattr(payments, "_get_stripe_sdk", lambda: fake)
    checkout = payments.create_embedded_checkout_session(
        user_address="agent1buyer", chat_session_id="chat-1", description="Referee check for Dr. Patel")

    sent = fake.created
    assert sent["ui_mode"] == "embedded" and sent["mode"] == "payment"
    assert sent["redirect_on_completion"] == "if_required"
    assert sent["payment_method_types"] == ["card"]
    item = sent["line_items"][0]
    assert item["quantity"] == 1
    assert item["price_data"]["unit_amount"] == 50 and item["price_data"]["currency"] == "usd"
    assert item["price_data"]["product_data"]["name"] == "Portfolio verification"
    assert sent["metadata"] == {"user_address": "agent1buyer", "session_id": "chat-1",
                                "service": "portfolio_verification"}
    assert "{CHECKOUT_SESSION_ID}" in sent["return_url"] and "user=agent1buyer" in sent["return_url"]
    assert checkout == {"client_secret": "cs_test_123_secret_abc", "id": "cs_test_123",
                        "checkout_session_id": "cs_test_123", "publishable_key": PUBLISHABLE,
                        "currency": "usd", "amount_cents": "50", "ui_mode": "embedded"}


@pytest.mark.parametrize("status, paid", [("paid", True), ("unpaid", False), ("no_payment_required", False)])
def test_verify_checkout_session_paid(monkeypatch, test_keys, status, paid):
    """Only Stripe's payment_status == 'paid' counts."""
    fake = FakeStripe(payment_status=status)
    monkeypatch.setattr(payments, "_get_stripe_sdk", lambda: fake)
    assert payments.verify_checkout_session_paid("cs_test_123") is paid
    assert fake.retrieved == ["cs_test_123"]


def test_payment_request_shape():
    """RequestPayment: $0.50 USD via stripe, with the checkout in metadata['stripe']."""
    checkout = {"checkout_session_id": "cs_test_123", "client_secret": "x", "ui_mode": "embedded"}
    req = payments.payment_request("agent1referee", checkout, reference="chat-1")
    assert req.accepted_funds == [Funds(currency="USD", amount="0.50", payment_method="stripe")]
    assert req.recipient == "agent1referee" and req.reference == "chat-1"
    assert req.deadline_seconds == 300
    assert req.metadata == {"stripe": checkout, "service": "portfolio_verification"}
    assert "4242 4242 4242 4242" in payments.payment_instructions()


def test_flag_and_chair_exemption(monkeypatch):
    """Off by default; when on, everyone pays except our own Chair."""
    monkeypatch.delenv("REFEREE_PAYMENTS", raising=False)
    monkeypatch.setenv("CHAIR_ADDRESS", "agent1chair")
    assert not payments.needs_payment("agent1outsider")
    monkeypatch.setenv("REFEREE_PAYMENTS", "true")
    assert payments.needs_payment("agent1outsider")
    assert not payments.needs_payment("agent1chair")


def test_commit_problem():
    """A commit must be stripe, for the checkout we sent, and something must be waiting."""
    pending = {"checkout_session_id": "cs_test_123"}

    def commit(method="stripe", tx="cs_test_123"):
        return CommitPayment(funds=Funds(currency="USD", amount="0.50", payment_method=method),
                             recipient="agent1referee", transaction_id=tx)

    assert payments.commit_problem(commit(), pending) == ""
    assert "stripe" in payments.commit_problem(commit(method="fet_direct"), pending)
    assert "no unpaid check" in payments.commit_problem(commit(), None)
    assert "doesn't match" in payments.commit_problem(commit(tx="cs_test_other"), pending)


# ---------- the Referee Agent with a buyer, over uAgents ----------

def _chat(text: str) -> ChatMessage:
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                       content=[TextContent(type="text", text=text)])


def _run_buyer(port: int, finished, chair: bool = False, timeout: int = 60) -> list:
    """Run the Referee Agent and a buyer that sends Dr. Patel's portfolio, pays if asked, and
    records every message it gets. finished(events) says when to stop waiting."""
    patel = fakes.load_client("C02")
    request = VerifyRequest(client=patel, proposal=fakes.chair_propose(patel, []))
    events: list = []
    done = threading.Event()

    def record(event):
        events.append(event)
        if finished(events):
            done.set()

    async def run():
        loop = asyncio.get_running_loop()
        referee = referee_agent.build_agent(f"test paid referee seed {port} for swarmfolio unit tests only",
                                            port + 1, mailbox=False, publish=False)
        buyer = Agent(name="buyer", seed=f"test buyer seed {port} for swarmfolio unit tests only",
                      port=port + 2, loop=loop, publish_agent_details=False)
        if chair:  # make the buyer our own Chair
            import os
            os.environ["CHAIR_ADDRESS"] = buyer.address

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
            # What the Inspector does after the user pays in the embedded checkout and approves.
            await ctx.send(sender, CommitPayment(funds=msg.accepted_funds[0], recipient=msg.recipient,
                                                 transaction_id=msg.metadata["stripe"]["checkout_session_id"],
                                                 reference=msg.reference))

        @pay.on_message(CompletePayment)
        async def on_complete(ctx: Context, sender: str, msg: CompletePayment):
            record(("complete", msg))

        @pay.on_message(CancelPayment)
        async def on_cancel(ctx: Context, sender: str, msg: CancelPayment):
            record(("cancel", msg))

        buyer.include(chat)
        buyer.include(pay)

        @buyer.on_event("startup")
        async def ask(ctx: Context):
            await ctx.send(referee.address, _chat(request.model_dump_json()))

        await Bureau(agents=[referee, buyer], port=port, loop=loop).run_async()

    # Bureau shutdown hangs, so run it on a daemon thread (same trick as tests/test_agents.py).
    threading.Thread(target=lambda: asyncio.run(run()), daemon=True).start()
    assert done.wait(timeout=timeout), f"never finished; got {[e[0] for e in events]}"
    return events


def _is_receipt(event) -> bool:
    return event[0] == "chat" and VERDICT_LINES["VIOLATIONS_REPAIRED"] in event[1]


@pytest.fixture
def paid_mode(monkeypatch):
    """REFEREE_PAYMENTS on, Stripe mocked, and nobody is the Chair."""
    monkeypatch.setenv("REFEREE_PAYMENTS", "true")
    monkeypatch.delenv("CHAIR_ADDRESS", raising=False)
    monkeypatch.delenv("CHAIR_SEED", raising=False)
    checkouts = []

    def fake_checkout(**kwargs):
        checkouts.append(kwargs)
        return {"client_secret": "cs_test_123_secret", "id": "cs_test_123", "checkout_session_id": "cs_test_123",
                "publishable_key": PUBLISHABLE, "currency": "usd", "amount_cents": "50", "ui_mode": "embedded"}

    monkeypatch.setattr(payments, "create_embedded_checkout_session", fake_checkout)
    return checkouts


def test_outside_user_pays_then_gets_receipt(monkeypatch, paid_mode):
    """RequestPayment + how-to-pay text first; after a paid commit: CompletePayment, then the receipt."""
    verified = []
    monkeypatch.setattr(payments, "verify_checkout_session_paid", lambda tx: verified.append(tx) or True)
    events = _run_buyer(8120, lambda ev: any(_is_receipt(e) for e in ev))

    kinds = [e[0] for e in events]
    assert kinds.index("request") < kinds.index("complete") < next(i for i, e in enumerate(events) if _is_receipt(e))
    request = next(e[1] for e in events if e[0] == "request")
    assert request.accepted_funds[0].amount == "0.50" and request.accepted_funds[0].payment_method == "stripe"
    assert request.metadata["stripe"]["checkout_session_id"] == "cs_test_123"
    assert any(e[0] == "chat" and "4242 4242 4242 4242" in e[1] for e in events)  # plain-text fallback
    assert next(e[1] for e in events if e[0] == "complete").transaction_id == "cs_test_123"
    assert verified == ["cs_test_123"]
    assert len(paid_mode) == 1 and paid_mode[0]["description"] == "Referee check for Dr. Patel (synthetic)"


def test_unpaid_commit_is_cancelled_without_receipt(monkeypatch, paid_mode):
    """Stripe says not paid -> CancelPayment, and no receipt."""
    monkeypatch.setattr(payments, "verify_checkout_session_paid", lambda tx: False)
    events = _run_buyer(8124, lambda ev: any(e[0] == "cancel" for e in ev))
    cancel = next(e[1] for e in events if e[0] == "cancel")
    assert cancel.transaction_id == "cs_test_123" and "isn't paid" in cancel.reason
    assert not any(e[0] == "complete" or _is_receipt(e) for e in events)


def test_chair_never_pays(monkeypatch, paid_mode):
    """Our own Chair gets the receipt straight away, with no payment request."""
    monkeypatch.setenv("CHAIR_ADDRESS", "set-below-to-the-buyer-address")
    events = _run_buyer(8128, lambda ev: any(_is_receipt(e) for e in ev), chair=True)
    assert not any(e[0] == "request" for e in events)
    assert paid_mode == []  # no Stripe checkout was even created


def test_payments_off_by_default(monkeypatch, paid_mode):
    """Without REFEREE_PAYMENTS, outside users get the receipt straight away (today's behaviour)."""
    monkeypatch.delenv("REFEREE_PAYMENTS")
    events = _run_buyer(8132, lambda ev: any(_is_receipt(e) for e in ev))
    assert not any(e[0] == "request" for e in events)
    assert paid_mode == []
