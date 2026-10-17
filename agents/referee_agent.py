"""
The Referee Agent (MASTER 9): a thin Fetch.ai wrapper around referee().

Two ways in:
- VerifyRequestMsg from the Chair -> ReceiptMsg (or ErrorMsg if something breaks).
- Chat Protocol: anyone on ASI:One can paste {"client_id": "C02", "proposal": {...}}
  (or a full {"client": {...}, "proposal": {...}}) and get the receipt back as text.
Run it with:  python -m agents.referee_agent
"""

import asyncio
import json
import os

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

import config
from agents import event_loop
from agents.chat import acknowledge, find_client, receipt_text, say, text_of
from agents.messages import ErrorMsg, ReceiptMsg, VerifyRequestMsg, pack, unpack
from models import VerifyRequest
# A5b: the Referee Agent always uses the REAL referee (the other agents stay on brains.py / fakes).
from referee.receipt import referee
from referee.schema import Proposal

REFEREE_HELP = (
    "I'm the Portfolio Referee. Paste JSON like "
    '{"client_id": "C02", "proposal": {"weights": {"JNJ": 0.3, "MSFT": 0.7}, "thesis": "...", "reasons": {}}} '
    "and I'll check it against that client's rules."
)


def parse_chat_request(text: str) -> VerifyRequest | None:
    """Turn pasted chat JSON into a VerifyRequest, or None if it doesn't look like one."""
    try:
        data = json.loads(text)
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

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        await acknowledge(ctx, sender, msg)
        req = parse_chat_request(text_of(msg))
        if req is None:
            await say(ctx, sender, REFEREE_HELP, end=True)
            return
        try:
            receipt = await asyncio.to_thread(referee, req.client, req.proposal)
            await say(ctx, sender, receipt_text(receipt), end=True)
        except Exception as e:
            await say(ctx, sender, f"⚠️ Sorry, I couldn't check that: {e}", end=True)

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass  # nothing to do when someone acknowledges our reply

    agent.include(committee)
    agent.include(chat, publish_manifest=publish)
    return agent


if __name__ == "__main__":
    seed = os.getenv("REFEREE_SEED")
    if not seed:
        raise SystemExit("REFEREE_SEED is missing from .env (any long random sentence; keep it stable).")
    build_agent(seed, config.AGENT_PORTS["referee"]).run()
