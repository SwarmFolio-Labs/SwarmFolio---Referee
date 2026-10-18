"""
Pay-per-check for the Referee Agent: Fetch's Agent Payment Protocol + Stripe embedded Checkout.

Follows Fetch's official Stripe example (innovation-lab-examples/stripe-horoscope-agent):
  1. an outside user asks for a check -> we send RequestPayment with an embedded Stripe Checkout
     session in metadata["stripe"]
  2. they pay in the checkout and approve -> their UI sends CommitPayment(transaction_id=<checkout session id>)
  3. we ask Stripe whether that session is paid -> CompletePayment + the receipt, or CancelPayment.

TEST MODE ONLY: we refuse any Stripe key that isn't sk_test_ / pk_test_.
Off unless REFEREE_PAYMENTS=true. Our own Chair (CHAIR_ADDRESS / CHAIR_SEED) never pays.
"""

import os
import time
from typing import Awaitable, Callable

from uagents import Context, Protocol
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    Funds,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

from agents.transport import agent_address

PRICE_CENTS = 50  # $0.50 per check
CURRENCY = "usd"
PRODUCT_NAME = "Portfolio verification"
SERVICE = "portfolio_verification"
DEADLINE_SECONDS = 300  # how long the RequestPayment is valid (same as Fetch's example)
PENDING_SECONDS = 30 * 60  # how long we remember an unpaid request (Stripe sessions live >= 30 min)

PAYMENT_HELP = (
    "\n\n💳 A full check costs $0.50 (Stripe TEST mode, no real money). "
    "I'll send a Stripe payment request first and the receipt as soon as it's paid."
)


class PaymentSetupError(RuntimeError):
    """Stripe keys are missing or aren't test-mode keys."""


def payments_enabled() -> bool:
    """REFEREE_PAYMENTS=true turns pay-per-check on (default off)."""
    return os.getenv("REFEREE_PAYMENTS", "").strip().lower() in ("1", "true", "yes", "on")


def is_exempt(sender: str) -> bool:
    """Our own Chair never pays, so the committee flow never changes."""
    chair = agent_address("chair")
    return chair is not None and sender == chair


def needs_payment(sender: str) -> bool:
    """Should this sender pay before getting a receipt?"""
    return payments_enabled() and not is_exempt(sender)


# ---------- Stripe (like the example's stripe_payments.py) ----------

def stripe_keys() -> tuple[str, str]:
    """(secret, publishable) test keys from env. Refuses live or missing keys, never prints them."""
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    publishable = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    if not (secret and publishable):
        raise PaymentSetupError("STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY are missing from .env")
    if not secret.startswith("sk_test_") or not publishable.startswith("pk_test_"):
        raise PaymentSetupError("only Stripe TEST keys (sk_test_... / pk_test_...) are allowed")
    return secret, publishable


def _get_stripe_sdk():
    """The stripe module with our test secret key set (a function so tests can swap in a fake)."""
    import stripe

    stripe.api_key = stripe_keys()[0]
    return stripe


def _stripe_expires_at() -> int:
    """Stripe wants expires_at between 30 minutes and 24 hours from now."""
    expires_in_s = int(os.getenv("STRIPE_CHECKOUT_EXPIRES_SECONDS", "1800"))
    expires_in_s = max(1800, min(24 * 60 * 60, expires_in_s))
    return int(time.time()) + expires_in_s


def create_embedded_checkout_session(*, user_address: str, chat_session_id: str, description: str) -> dict:
    """Make an embedded Stripe Checkout session; returns what goes in RequestPayment.metadata["stripe"]."""
    stripe = _get_stripe_sdk()
    publishable_key = stripe_keys()[1]
    success_url = os.getenv("STRIPE_SUCCESS_URL", "https://agentverse.ai/payment-success").strip()
    return_url = (
        f"{success_url}"
        f"?session_id={{CHECKOUT_SESSION_ID}}"
        f"&chat_session_id={chat_session_id}"
        f"&user={user_address}"
    )

    session = stripe.checkout.Session.create(
        ui_mode="embedded",
        redirect_on_completion="if_required",
        payment_method_types=["card"],
        mode="payment",
        return_url=return_url,
        expires_at=_stripe_expires_at(),
        line_items=[
            {
                "price_data": {
                    "currency": CURRENCY,
                    "product_data": {"name": PRODUCT_NAME, "description": description},
                    "unit_amount": PRICE_CENTS,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "user_address": user_address,
            "session_id": chat_session_id,
            "service": SERVICE,
        },
    )

    return {
        "client_secret": session.client_secret,
        # Some UIs call the Checkout Session ID `id`, others `checkout_session_id`; send both (like the example).
        "id": session.id,
        "checkout_session_id": session.id,
        "publishable_key": publishable_key,
        "currency": CURRENCY,
        "amount_cents": str(PRICE_CENTS),
        "ui_mode": "embedded",
    }


def verify_checkout_session_paid(checkout_session_id: str) -> bool:
    """Ask Stripe whether this Checkout session has been paid."""
    stripe = _get_stripe_sdk()
    session = stripe.checkout.Session.retrieve(checkout_session_id)
    return getattr(session, "payment_status", None) == "paid"


# ---------- Payment Protocol messages ----------

def payment_request(recipient: str, checkout: dict, reference: str) -> RequestPayment:
    """The RequestPayment the buyer's UI turns into an embedded Stripe Checkout."""
    return RequestPayment(
        accepted_funds=[Funds(currency="USD", amount=f"{PRICE_CENTS / 100:.2f}", payment_method="stripe")],
        recipient=recipient,
        deadline_seconds=DEADLINE_SECONDS,
        reference=reference,
        description=f"Pay ${PRICE_CENTS / 100:.2f} for a {PRODUCT_NAME.lower()} by the SwarmFolio Referee.",
        metadata={"stripe": checkout, "service": SERVICE},
    )


def payment_instructions() -> str:
    """Plain-text fallback for chat clients that can't show the Stripe checkout (e.g. ASI:One chat)."""
    return (
        f"💳 A full Referee check costs ${PRICE_CENTS / 100:.2f} (Stripe TEST mode, no real money).\n"
        "I've sent you a Stripe payment request. If you don't see a checkout here, open this agent in the "
        "Agentverse Inspector chat, pay with the test card 4242 4242 4242 4242 (any future date, any CVC, "
        "any ZIP), then approve the payment. I'll send your receipt as soon as Stripe confirms it."
    )


def commit_problem(msg: CommitPayment, pending: dict | None) -> str:
    """Why we can't accept this CommitPayment ('' if it looks fine and is ready to verify with Stripe)."""
    if msg.funds.payment_method != "stripe" or not msg.transaction_id:
        return "Unsupported payment method (expected stripe)."
    if pending is None:
        return "I have no unpaid check waiting for you. Send your portfolio again to start."
    if msg.transaction_id != pending["checkout_session_id"]:
        return "That transaction doesn't match the checkout I sent you."
    return ""


class PendingPayments:
    """Unpaid checks, one per sender: the Stripe checkout id and the request to run once it's paid.

    Kept in memory (not ctx.storage) so the client secret never lands in a file in the repo."""

    def __init__(self):
        self._items: dict[str, dict] = {}

    def add(self, sender: str, checkout_session_id: str, request) -> None:
        self._items[sender] = {"checkout_session_id": checkout_session_id, "request": request,
                               "expires_at": time.time() + PENDING_SECONDS}

    def get(self, sender: str) -> dict | None:
        item = self._items.get(sender)
        if item is None or time.time() > item["expires_at"]:
            self._items.pop(sender, None)
            return None
        return item

    def pop(self, sender: str) -> dict | None:
        item = self.get(sender)
        self._items.pop(sender, None)
        return item


CommitHandler = Callable[[Context, str, CommitPayment], Awaitable[None]]
RejectHandler = Callable[[Context, str, RejectPayment], Awaitable[None]]


def build_payment_proto(on_commit: CommitHandler, on_reject: RejectHandler) -> Protocol:
    """The Agent Payment Protocol, seller side (we handle CommitPayment and RejectPayment)."""
    proto = Protocol(spec=payment_protocol_spec, role="seller")

    @proto.on_message(CommitPayment)
    async def _on_commit(ctx: Context, sender: str, msg: CommitPayment):
        await on_commit(ctx, sender, msg)

    @proto.on_message(RejectPayment)
    async def _on_reject(ctx: Context, sender: str, msg: RejectPayment):
        await on_reject(ctx, sender, msg)

    return proto
