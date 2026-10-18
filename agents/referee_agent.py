"""
The Referee Agent (MASTER 9): a thin Fetch.ai wrapper around referee().

Two ways in:
- VerifyRequestMsg from the Chair -> ReceiptMsg (or ErrorMsg if something breaks).
- Chat Protocol: anyone on ASI:One can paste {"client_id": "C02", "proposal": {...}}
  (or a full {"client": {...}, "proposal": {...}}) and get the receipt back as text.
- Plain English: "check NVDA 50, JNJ 30, KO 20 against: no oil companies, at most 30% in any stock"
  -> referee/extract.py turns the rules into Rule objects (LLM), then the same receipt flow.
  Without weights it lists the rules it read and whether they can all be met.
- With REFEREE_PAYMENTS=true, outside chat users pay $0.50 first (Agent Payment Protocol +
  Stripe TEST mode, agents/payments.py). Our own Chair never pays.
Run it with:  python -m agents.referee_agent
"""

import asyncio
import json
import os

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec
from uagents_core.contrib.protocols.payment import CancelPayment, CommitPayment, CompletePayment, RejectPayment

import config
from agents import event_loop, payments
from agents.cards import receipt_card, try_card
from agents.chat import acknowledge, find_client, receipt_text, say, text_of
from agents.messages import ErrorMsg, ReceiptMsg, VerifyRequestMsg, pack, unpack
from models import VerifyRequest
# A5b: the Referee Agent always uses the REAL referee (the other agents stay on brains.py / fakes).
from referee import extract
from referee.receipt import referee
from referee.schema import Proposal

REFEREE_HELP = (
    "I'm the Portfolio Referee. Paste JSON like "
    '{"client_id": "C02", "proposal": {"weights": {"JNJ": 0.3, "MSFT": 0.7}, "thesis": "...", "reasons": {}}} '
    "and I'll check it against that client's rules. Or write it in plain English: "
    '"check NVDA 50, JNJ 30, KO 20 against: no oil companies, at most 30% in any stock, volatility under 15%".'
)


def parse_chat_request(text: str) -> VerifyRequest | None:
    """Turn pasted chat JSON into a VerifyRequest, or None if it doesn't look like one."""
    # ASI:One puts "@swarmfolio-referee" mentions in front of the JSON, so keep only the {...} part.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
        if "client" in data:
            return VerifyRequest.model_validate(data)
        client = find_client(str(data.get("client_id", "")))
        if client is None:
            return None
        return VerifyRequest(client=client, proposal=Proposal.model_validate(data["proposal"]))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def build_agent(seed: str, port: int, mailbox: bool = True, publish: bool = True) -> Agent:
    """Make the Referee Agent. Tests pass mailbox=False/publish=False to stay offline."""
    agent = Agent(name="swarmfolio-referee", seed=seed, port=port, loop=event_loop(),
                  mailbox=mailbox, publish_agent_details=publish)

    # --- Committee protocol: the Chair asks, we answer with a receipt ---
    committee = Protocol(name="swarmfolio-committee", version="0.1.0")

    @committee.on_message(VerifyRequestMsg, replies={ReceiptMsg, ErrorMsg})
    async def on_verify(ctx: Context, sender: str, msg: VerifyRequestMsg):
        try:
            req = unpack(VerifyRequest, msg.payload)
            receipt = await asyncio.to_thread(referee, req.client, req.proposal)
            await ctx.send(sender, ReceiptMsg(payload=pack(receipt)))
        except Exception as e:  # never crash: tell the Chair what went wrong
            ctx.logger.error(f"verify failed: {e}")
            await ctx.send(sender, ErrorMsg(error=str(e)))

    # --- Chat Protocol: humans on ASI:One ---
    chat = Protocol(spec=chat_protocol_spec)
    pending = payments.PendingPayments()  # unpaid checks, by sender

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        await acknowledge(ctx, sender, msg)
        paid_check = payments.needs_payment(sender)
        text = text_of(msg)
        req = parse_chat_request(text)
        if req is None and "{" not in text and text.strip():
            req = await plain_english_request(ctx, sender, text)
            if req is None:
                return  # already answered (rules only, nothing mappable, or an error)
        if req is None:
            await say(ctx, sender, REFEREE_HELP + (payments.PAYMENT_HELP if paid_check else ""), end=True)
            return
        if paid_check:
            await ask_for_payment(ctx, sender, req)
            return
        await send_receipt(ctx, sender, req)

    async def plain_english_request(ctx: Context, sender: str, text: str) -> VerifyRequest | None:
        """Plain-English rules (+ optional weights) -> VerifyRequest, after saying which rules were read."""
        weights, rules_text = extract.split_weights(text)
        try:
            found = await asyncio.to_thread(extract.extract_rules, rules_text)
        except Exception as e:
            ctx.logger.error(f"rule extraction failed: {e}")
            await say(ctx, sender, f"⚠️ Sorry, I couldn't read those rules: {e}", end=True)
            return None
        if not found.rules:
            await say(ctx, sender, extract.describe(found) + "\n\n" + REFEREE_HELP, end=True)
            return None
        client = extract.chat_client(found.rules)
        if weights is None:
            summary = await asyncio.to_thread(extract.describe, found, client)
            await say(ctx, sender, summary + "\nTo check a portfolio, send: check NVDA 50, JNJ 30, KO 20 against: "
                      "<your rules>", end=True)
            return None
        await say(ctx, sender, extract.describe(found))
        return VerifyRequest(client=client, proposal=Proposal(weights=weights, thesis="From chat", reasons={}))

    async def ask_for_payment(ctx: Context, sender: str, req: VerifyRequest):
        """Send a RequestPayment with a Stripe checkout, plus the plain-text how-to-pay."""
        try:
            checkout = await asyncio.to_thread(
                payments.create_embedded_checkout_session, user_address=sender,
                chat_session_id=str(ctx.session), description=f"Referee check for {req.client.name}")
        except Exception as e:  # missing/live keys or Stripe down: say so, never run the check for free
            ctx.logger.error(f"stripe checkout failed: {e}")
            await say(ctx, sender, f"⚠️ Sorry, I couldn't set up the payment: {e}", end=True)
            return
        pending.add(sender, checkout["checkout_session_id"], req)
        await ctx.send(sender, payments.payment_request(ctx.agent.address, checkout, reference=str(ctx.session)))
        await say(ctx, sender, payments.payment_instructions())

    async def send_receipt(ctx: Context, sender: str, req: VerifyRequest):
        """Run the Referee and reply with the receipt (text + card)."""
        try:
            receipt = await asyncio.to_thread(referee, req.client, req.proposal)
            card = try_card(receipt_card, receipt, before=req.proposal.weights,
                            rule_sources={r.id: r.source for r in req.client.rules}, client_name=req.client.name)
            await say(ctx, sender, receipt_text(receipt), end=True, card=card)
        except Exception as e:
            await say(ctx, sender, f"⚠️ Sorry, I couldn't check that: {e}", end=True)

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass  # nothing to do when someone acknowledges our reply

    # --- Payment Protocol (seller): only used when REFEREE_PAYMENTS is on ---
    async def on_commit(ctx: Context, sender: str, msg: CommitPayment):
        item = pending.get(sender)
        problem = payments.commit_problem(msg, item)
        if not problem:
            try:
                if not await asyncio.to_thread(payments.verify_checkout_session_paid, msg.transaction_id):
                    problem = "Stripe says this checkout isn't paid yet. Finish the checkout, then approve again."
            except Exception as e:
                ctx.logger.error(f"stripe verify failed: {e}")
                problem = f"I couldn't confirm the payment with Stripe ({e})."
        if problem:
            await ctx.send(sender, CancelPayment(transaction_id=msg.transaction_id or None, reason=problem))
            return
        pending.pop(sender)  # a paid checkout buys exactly one check
        await ctx.send(sender, CompletePayment(transaction_id=msg.transaction_id))
        await send_receipt(ctx, sender, item["request"])

    async def on_reject(ctx: Context, sender: str, msg: RejectPayment):
        pending.pop(sender)
        await say(ctx, sender, f"Payment declined, so I didn't run the check. {msg.reason or ''}".strip(), end=True)

    agent.include(committee)
    agent.include(chat, publish_manifest=publish)
    agent.include(payments.build_payment_proto(on_commit, on_reject), publish_manifest=publish)
    return agent


if __name__ == "__main__":
    seed = os.getenv("REFEREE_SEED")
    if not seed:
        raise SystemExit("REFEREE_SEED is missing from .env (any long random sentence; keep it stable).")
    build_agent(seed, config.AGENT_PORTS["referee"]).run()
