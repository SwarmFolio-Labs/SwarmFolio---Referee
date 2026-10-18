"""
The Chair Agent (MASTER 9): the one people chat with on ASI:One.

It reads the user's message, loads the client, runs the committee loop with AgentTransport
(so the Referee Agent does the checking), and replies in the MASTER 9 format.
Run it with:  python -m agents.chair_agent
"""

import asyncio
import os

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec
from uagents_core.identity import Identity

import config
from agents import brains, event_loop
from agents.chat import (CHAIR_HELP, acknowledge, committee_reply, find_client, list_clients_text,
                         price_tags_text, say, text_of)
from agents.transport import AgentTransport
from referee.prices import rule_prices


def referee_address() -> str | None:
    """REFEREE_ADDRESS from .env, or worked out from REFEREE_SEED (an address is fixed by its seed)."""
    address = os.getenv("REFEREE_ADDRESS")
    if address:
        return address
    seed = os.getenv("REFEREE_SEED")
    if seed:
        return Identity.from_seed(seed, 0).address
    return None


def build_agent(seed: str, port: int, mailbox: bool = True, publish: bool = True) -> Agent:
    """Make the Chair Agent. Tests pass mailbox=False/publish=False to stay offline."""
    agent = Agent(name="swarmfolio-chair", seed=seed, port=port, loop=event_loop(),
                  mailbox=mailbox, publish_agent_details=publish)
    chat = Protocol(spec=chat_protocol_spec)

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        await acknowledge(ctx, sender, msg)
        text = text_of(msg)

        if "list" in text.lower() and "client" in text.lower():
            await say(ctx, sender, list_clients_text(), end=True)
            return
        client = find_client(text)
        if client is None:
            await say(ctx, sender, CHAIR_HELP, end=True)
            return

        # "price tags for C02": just the rule costs (pure math, under a second).
        if "price" in text.lower():
            try:
                prices = await asyncio.to_thread(rule_prices, client)
                await say(ctx, sender, price_tags_text(client.client_id, prices), end=True)
            except Exception as e:
                await say(ctx, sender, f"⚠️ Sorry, I couldn't price those rules: {e}", end=True)
            return

        # The committee takes a while with real LLMs, so say something first.
        await say(ctx, sender, f"Convening the committee for {client.client_id}…")
        transport = AgentTransport(ctx, referee_address())
        try:
            result = await brains.run_committee(client, transport, max_rounds=config.MAX_ROUNDS)
            reply = committee_reply(result, transport.notes)
            try:  # the top 3 rule price tags go under the verdict; never let them block the answer
                prices = await asyncio.to_thread(rule_prices, client)
                reply += "\n\n" + price_tags_text(client.client_id, prices, top=3)
            except Exception as e:
                ctx.logger.warning(f"price tags failed: {e}")
            await say(ctx, sender, reply, end=True)
        except Exception as e:
            ctx.logger.error(f"committee failed: {e}")
            await say(ctx, sender, f"⚠️ Sorry, the committee hit an error: {e}", end=True)

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass  # nothing to do when someone acknowledges our reply

    agent.include(chat, publish_manifest=publish)
    return agent


if __name__ == "__main__":
    seed = os.getenv("CHAIR_SEED")
    if not seed:
        raise SystemExit("CHAIR_SEED is missing from .env (any long random sentence; keep it stable).")
    build_agent(seed, config.AGENT_PORTS["chair"]).run()
