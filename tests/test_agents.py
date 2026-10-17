"""
Tests for the Fetch.ai wiring (Plan B step 2), all offline on the fake brains.

The main test runs the real Referee Agent and a stand-in "Chair" in one local Bureau
and checks that AgentTransport.verify() gets a Receipt back over uAgents messages.
"""

import asyncio
import threading

from uagents import Agent, Bureau, Context

import fakes
from agents import referee_agent
from agents.chat import committee_reply, find_client
from agents.transport import AgentTransport
from models import Receipt, VerifyRequest


def _patel_request() -> VerifyRequest:
    """Dr. Patel's client with the fake Chair's first proposal."""
    patel = fakes.load_client("C02")
    return VerifyRequest(client=patel, proposal=fakes.chair_propose(patel, []))


def test_transport_gets_receipt_from_referee_agent():
    """The Chair's AgentTransport sends a VerifyRequestMsg and gets the Referee Agent's receipt."""
    got: dict = {}

    async def run():
        # Agents are built inside the running loop (Python 3.14 has no implicit loop).
        loop = asyncio.get_running_loop()
        referee = referee_agent.build_agent("test referee seed for swarmfolio unit tests only", 8102,
                                            mailbox=False, publish=False)
        probe = Agent(name="probe", seed="test chair probe seed for swarmfolio unit tests only",
                      port=8101, loop=loop, publish_agent_details=False)

        @probe.on_event("startup")
        async def ask(ctx: Context):
            transport = AgentTransport(ctx, referee.address)
            got["receipt"] = await transport.verify(_patel_request())
            got["notes"] = transport.notes
            done.set()

        await Bureau(agents=[referee, probe], port=8100, loop=loop).run_async()

    # Cancelling a Bureau hits a uagents shutdown bug on Python 3.14, so run it in a
    # background (daemon) thread and simply stop waiting once the receipt arrives.
    done = threading.Event()
    threading.Thread(target=lambda: asyncio.run(run()), daemon=True).start()
    assert done.wait(timeout=60), "the Referee Agent never answered"
    assert isinstance(got.get("receipt"), Receipt)
    assert got["receipt"].verdict == "VIOLATIONS_REPAIRED"  # the fake first proposal breaks Healthcare
    assert got["notes"] == []  # came from the agent, not the local fallback


def test_transport_falls_back_to_local_referee_with_note():
    """With no Referee address, verification still happens locally and says so."""
    transport = AgentTransport(ctx=None, referee_address=None)
    receipt = asyncio.run(transport.verify(_patel_request()))
    assert receipt.verdict == "VIOLATIONS_REPAIRED"
    assert any("verified locally" in n for n in receipt.notes)
    assert len(transport.notes) == 1


def test_find_client_by_id_and_name():
    """'C02' and 'Dr. Patel' both mean C02; the longer C03 name doesn't steal it."""
    assert find_client("Build a portfolio for client C02").client_id == "C02"
    assert find_client("Build a portfolio for Dr. Patel").client_id == "C02"
    assert find_client("c03 please").client_id == "C03"
    assert find_client("hello") is None


def test_committee_reply_format():
    """The Chair's reply has the verdict, debate, weights, receipt id and notes."""
    patel = fakes.load_client("C02")
    result = asyncio.run(fakes.run_committee(patel, fakes.FakeLocalTransport()))
    text = committee_reply(result, ["Referee Agent unavailable: test."])
    assert text.startswith("**✅ Compliant after 2 rounds**")
    assert "risk conceded" in text and "fundamentals defended" in text
    assert "• JNJ 30.0%" in text
    assert result.receipt.receipt_id in text
    assert "Referee Agent unavailable: test." in text


def test_referee_agent_uses_real_referee_on_pasted_chat():
    """A5b: the chat JSON a judge pastes into ASI:One goes through the REAL referee, not the fake."""
    import json
    from referee.receipt import referee as real_referee

    assert referee_agent.referee is real_referee
    text = json.dumps({"client_id": "C02", "proposal": {
        "weights": {"NVDA": 0.41, "JNJ": 0.30, "GOOGL": 0.15, "XOM": 0.14},
        "thesis": "AI and healthcare growth.", "reasons": {}}})
    req = referee_agent.parse_chat_request(text)
    receipt = referee_agent.referee(req.client, req.proposal)
    assert receipt.verdict == "VIOLATIONS_REPAIRED"
    assert {c.rule_id for c in receipt.checks if not c.passed} == {"R1", "R2", "R7"}


def test_chat_request_ignores_asi1_mentions():
    """ASI:One sends '@swarmfolio-referee @swarmfolio-referee {...}'; the mentions must not break parsing."""
    text = ('@swarmfolio-referee @swarmfolio-referee {"client_id":"C02","proposal":{"weights":'
            '{"NVDA":0.41,"JNJ":0.30,"GOOGL":0.15,"XOM":0.14},"thesis":"test","reasons":{}}}')
    req = referee_agent.parse_chat_request(text)
    assert req is not None and req.client.client_id == "C02"
    assert referee_agent.parse_chat_request("@swarmfolio-referee hello") is None
