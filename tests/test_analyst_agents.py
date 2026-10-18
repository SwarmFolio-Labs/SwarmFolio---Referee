"""
Tests for the three analyst agents (Plan B step 8), all offline on the fake brains.

The main test runs a real macro agent, a broken risk agent and a stand-in "Chair" in one
local Bureau, and checks that AgentTransport gets a Memo and a Stance back over uAgents
messages, and None (not a crash) from an analyst that errors or isn't running.
"""

import asyncio
import threading
from uuid import uuid4

from uagents import Agent, Bureau, Context
from uagents_core.identity import Identity
from uagents_core.types import DeliveryStatus, MsgStatus

import config
import fakes
from agents import brains, fundamentals_agent, macro_agent, risk_agent, run_all
from agents.messages import ErrorMsg, MemoMsg, ReceiptMsg, StanceMsg, pack
from agents.transport import NO_REPLY_DETAIL, AgentTransport, use_analyst_agents
from models import AnalysisRequest, Memo, ReviewRequest, Stance, VerifyRequest


def _requests() -> tuple[AnalysisRequest, ReviewRequest]:
    """Dr. Patel's analysis request and a review of the fake Chair's first proposal."""
    patel = fakes.load_client("C02")
    analysis = AnalysisRequest(client_id="C02", client_story=patel.story,
                               rules_text=[r.source for r in patel.rules], as_of="2026-10-17")
    review = ReviewRequest(client_id="C02", round=1, failures=["Healthcare is 40%, limit 35%."],
                           proposal=fakes.chair_propose(patel, []), conflict_explain="")
    return analysis, review


def _broken(*args):
    raise RuntimeError("LLM is down")


def test_transport_talks_to_analyst_agents(monkeypatch):
    """Memo + Stance from a working analyst; None + a note from a broken one and a missing one."""
    monkeypatch.setattr(brains, "analyze", lambda agent, req: _broken() if agent == "risk" else fakes.analyze(agent, req))
    monkeypatch.setattr(brains, "review", fakes.review)
    monkeypatch.setenv("ANALYST_TIMEOUT_S", "3")  # the "down" analyst would otherwise take 240 s
    analysis, review = _requests()
    nobody = Identity.from_seed("no agent runs with this seed, swarmfolio tests", 0).address
    got: dict = {}

    async def run():
        loop = asyncio.get_running_loop()
        macro = macro_agent.build_agent("test macro seed for swarmfolio unit tests only", 8111,
                                        mailbox=False, publish=False)
        risk = risk_agent.build_agent("test risk seed for swarmfolio unit tests only", 8112,
                                      mailbox=False, publish=False)
        probe = Agent(name="probe", seed="test analyst probe seed for swarmfolio unit tests only",
                      port=8113, loop=loop, publish_agent_details=False)

        @probe.on_event("startup")
        async def ask(ctx: Context):
            try:
                transport = AgentTransport(ctx, None, analyst_agents=True, analyst_addresses={
                    "macro": macro.address, "risk": risk.address, "fundamentals": nobody})
                # Same order as run_committee: every memo first, then the reviews.
                got["memo"] = await transport.analyze("macro", analysis)
                got["risk_memo"] = await transport.analyze("risk", analysis)
                got["down_memo"] = await transport.analyze("fundamentals", analysis)
                got["stance"] = await transport.review("macro", review)
                got["risk_stance"] = await transport.review("risk", review)
                got["notes"] = transport.notes
            finally:
                done.set()

        await Bureau(agents=[macro, risk, probe], port=8110, loop=loop).run_async()

    # Same pattern as test_agents.py: run the Bureau in a daemon thread and stop waiting when done.
    done = threading.Event()
    threading.Thread(target=lambda: asyncio.run(run()), daemon=True).start()
    assert done.wait(timeout=90), "the analyst agents never answered"

    assert isinstance(got["memo"], Memo) and got["memo"] == fakes.analyze("macro", analysis)
    assert isinstance(got["stance"], Stance) and got["stance"] == fakes.review("macro", review)
    assert got["risk_stance"] == fakes.review("risk", review)  # review still works on the risk agent
    assert got["risk_memo"] is None and got["down_memo"] is None
    notes = " ".join(got["notes"])
    assert "risk analyst agent is unavailable for its memo" in notes and "LLM is down" in notes
    assert "fundamentals analyst agent is unavailable for its memo" in notes
    assert "macro" not in notes


def test_flag_off_keeps_local_brains(monkeypatch):
    """USE_ANALYST_AGENTS off (the default): analyze/review call the local brains, no agents needed."""
    monkeypatch.delenv("USE_ANALYST_AGENTS", raising=False)
    monkeypatch.setattr(brains, "analyze", fakes.analyze)
    monkeypatch.setattr(brains, "review", fakes.review)
    analysis, review = _requests()
    transport = AgentTransport(ctx=None, referee_address=None)
    assert transport.analyst_agents is False
    assert asyncio.run(transport.analyze("risk", analysis)) == fakes.analyze("risk", analysis)
    assert asyncio.run(transport.review("macro", review)) == fakes.review("macro", review)
    assert transport.notes == []


def test_flag_and_addresses_from_env(monkeypatch):
    """USE_ANALYST_AGENTS=true turns agents on; addresses come from *_ADDRESS or are derived from *_SEED."""
    monkeypatch.setenv("USE_ANALYST_AGENTS", "true")
    monkeypatch.setenv("MACRO_ADDRESS", "agent1qmacro")
    monkeypatch.delenv("RISK_ADDRESS", raising=False)
    monkeypatch.setenv("RISK_SEED", "risk seed from env")
    monkeypatch.delenv("FUNDAMENTALS_ADDRESS", raising=False)
    monkeypatch.delenv("FUNDAMENTALS_SEED", raising=False)
    assert use_analyst_agents()
    transport = AgentTransport(ctx=None, referee_address=None)
    assert transport.analyst_agents is True
    assert transport.analyst_addresses == {
        "macro": "agent1qmacro",
        "risk": Identity.from_seed("risk seed from env", 0).address,
        "fundamentals": None,
    }
    # No address for fundamentals: skipped with a note, never a crash.
    analysis, _ = _requests()
    assert asyncio.run(transport.analyze("fundamentals", analysis)) is None
    assert "FUNDAMENTALS_SEED" in transport.notes[0]


def test_analyst_agent_addresses_match_their_seeds():
    """Each analyst module builds an agent whose address is the one run_all prints for its seed."""
    async def build():
        return [m.build_agent(f"{m.ROLE} address test seed", 8120 + i, mailbox=False, publish=False)
                for i, m in enumerate([macro_agent, fundamentals_agent, risk_agent])]
    agents = asyncio.run(build())
    for agent, m in zip(agents, [macro_agent, fundamentals_agent, risk_agent]):
        assert agent.address == Identity.from_seed(f"{m.ROLE} address test seed", 0).address
        assert agent.name == f"swarmfolio-{m.ROLE}"


def test_run_all_starts_all_five_agents():
    """run_all knows all 5 agents, on 5 different ports (8001-8005), with the Chair last."""
    names = [name for name, _, _ in run_all.AGENTS]
    assert sorted(names) == sorted(config.AGENT_PORTS) and names[-1] == "chair"
    assert sorted(config.AGENT_PORTS[n] for n in names) == [8001, 8002, 8003, 8004, 8005]


# --- Timeouts, retries and asking the analysts at once, with a scripted stand-in for ctx ---

ADDRESSES = {"macro": "agent1qmacro", "fundamentals": "agent1qfundamentals", "risk": "agent1qrisk"}


def _status(detail: str, delivered: bool = False) -> MsgStatus:
    return MsgStatus(status=DeliveryStatus.DELIVERED if delivered else DeliveryStatus.FAILED,
                     detail=detail, destination="", endpoint="", session=uuid4())


class ScriptedCtx:
    """Plays the part of uAgents' ctx.send_and_receive. script[address] lists what each attempt
    gets back: a reply Model, "timeout", "unreachable", or an Exception to raise.
    An address with no script answers every attempt with the fake brain's memo/stance."""

    def __init__(self, script: dict | None = None, delay: float = 0.0):
        self.script = script or {}
        self.delay = delay
        self.calls: list[tuple[str, str, float]] = []  # (address, message type, timeout)
        self.in_flight = 0
        self.max_in_flight = 0

    async def send_and_receive(self, destination, message, response_type, timeout):
        self.calls.append((destination, type(message).__name__, timeout))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            outcome = self.script[destination].pop(0) if destination in self.script else None
        finally:
            self.in_flight -= 1
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "timeout":
            return None, _status(NO_REPLY_DETAIL)
        if outcome == "unreachable":
            return None, _status("Unable to resolve destination endpoint")
        if outcome is None:
            agent = next(a for a, addr in ADDRESSES.items() if addr == destination)
            analysis, review = _requests()
            outcome = (MemoMsg(payload=pack(fakes.analyze(agent, analysis))) if MemoMsg in response_type
                       else StanceMsg(payload=pack(fakes.review(agent, review))))
        return outcome, _status("delivered", delivered=True)


def _transport(ctx, referee_address=None) -> AgentTransport:
    return AgentTransport(ctx, referee_address, analyst_addresses=dict(ADDRESSES), analyst_agents=True)


def _calls_to(ctx: ScriptedCtx, address: str) -> int:
    return sum(1 for addr, _, _ in ctx.calls if addr == address)


def test_analyst_timeout_defaults_to_240s_and_referee_keeps_agent_timeout(monkeypatch):
    """Analyst calls wait ANALYST_TIMEOUT_S (default 240 s); the Referee still waits AGENT_TIMEOUT_S."""
    monkeypatch.delenv("ANALYST_TIMEOUT_S", raising=False)
    analysis, review = _requests()
    patel = fakes.load_client("C02")
    receipt = fakes.referee(patel, fakes.chair_propose(patel, []))
    ctx = ScriptedCtx({"agent1qreferee": [ReceiptMsg(payload=pack(receipt))]})
    transport = _transport(ctx, referee_address="agent1qreferee")

    async def run():
        await transport.analyze("macro", analysis)
        await transport.review("risk", review)
        await transport.verify(VerifyRequest(client=patel, proposal=fakes.chair_propose(patel, [])))
    asyncio.run(run())

    analyst_timeouts = {t for _, kind, t in ctx.calls if kind != "VerifyRequestMsg"}
    referee_timeouts = {t for _, kind, t in ctx.calls if kind == "VerifyRequestMsg"}
    assert analyst_timeouts == {240}
    assert referee_timeouts == {config.AGENT_TIMEOUT_S}


def test_analyst_timeout_from_env(monkeypatch):
    """ANALYST_TIMEOUT_S in .env changes the analyst wait (and only that)."""
    monkeypatch.setenv("ANALYST_TIMEOUT_S", "90")
    ctx = ScriptedCtx()
    analysis, _ = _requests()
    asyncio.run(_transport(ctx).analyze("fundamentals", analysis))
    assert {t for _, _, t in ctx.calls} == {90}


def test_analyst_timeout_is_not_retried():
    """A silent analyst is still thinking: ask once, then give up with a note (no second LLM call)."""
    ctx = ScriptedCtx({ADDRESSES["macro"]: ["timeout", "timeout"]})
    transport = _transport(ctx)
    analysis, review = _requests()
    assert asyncio.run(transport.analyze("macro", analysis)) is None
    assert _calls_to(ctx, ADDRESSES["macro"]) == 1
    assert any("macro analyst agent is unavailable for its memo: it did not answer within" in n
               for n in transport.notes)

    ctx = ScriptedCtx({ADDRESSES["risk"]: ["timeout", "timeout"]})
    assert asyncio.run(_transport(ctx).review("risk", review)) is None
    assert _calls_to(ctx, ADDRESSES["risk"]) == 1


def test_analyst_error_or_failed_send_is_retried_once():
    """An ErrorMsg or a failed send gets one retry; the retry's answer is used."""
    analysis, review = _requests()
    for first_try in [ErrorMsg(error="LLM hiccup"), "unreachable", ConnectionError("network blip")]:
        ctx = ScriptedCtx({ADDRESSES["macro"]: [first_try, MemoMsg(payload=pack(fakes.analyze("macro", analysis)))]})
        transport = _transport(ctx)
        assert asyncio.run(transport.analyze("macro", analysis)) == fakes.analyze("macro", analysis)
        assert _calls_to(ctx, ADDRESSES["macro"]) == 2
        assert transport.notes == []

    # Still failing after the retry: None plus a note, never a crash.
    ctx = ScriptedCtx({ADDRESSES["risk"]: [ErrorMsg(error="bad JSON"), "unreachable"]})
    transport = _transport(ctx)
    assert asyncio.run(transport.review("risk", review)) is None
    assert _calls_to(ctx, ADDRESSES["risk"]) == 2
    assert "sending failed" in transport.notes[0]


def test_referee_timeout_is_still_retried(monkeypatch):
    """The Referee answers in ~1 s, so a Referee timeout is retried, then verified locally."""
    monkeypatch.setattr(brains, "referee", fakes.referee)
    patel = fakes.load_client("C02")
    ctx = ScriptedCtx({"agent1qreferee": ["timeout", "timeout"]})
    transport = _transport(ctx, referee_address="agent1qreferee")
    receipt = asyncio.run(transport.verify(VerifyRequest(client=patel, proposal=fakes.chair_propose(patel, []))))
    assert _calls_to(ctx, "agent1qreferee") == 1 + config.AGENT_RETRIES
    assert "verified locally" in transport.notes[0] and receipt.client_id == "C02"


def test_analysts_are_asked_at_the_same_time():
    """run_committee asks the analysts one by one; the transport still has all three working at once."""
    ctx = ScriptedCtx(delay=0.2)
    transport = _transport(ctx)
    analysis, review = _requests()

    async def like_run_committee(method, req):
        return [await method(agent, req) for agent in ("macro", "fundamentals", "risk")]

    memos = asyncio.run(like_run_committee(transport.analyze, analysis))
    assert memos == [fakes.analyze(a, analysis) for a in ("macro", "fundamentals", "risk")]
    assert ctx.max_in_flight == 3 and len(ctx.calls) == 3  # all at once, each asked exactly once

    ctx.max_in_flight, ctx.calls = 0, []
    stances = asyncio.run(like_run_committee(transport.review, review))
    assert stances == [fakes.review(a, review) for a in ("macro", "fundamentals", "risk")]
    assert ctx.max_in_flight == 3 and len(ctx.calls) == 3
    assert transport._running == {}  # nothing left over
