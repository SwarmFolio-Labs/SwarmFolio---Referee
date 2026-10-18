"""
Tests for the three analyst agents (Plan B step 8), all offline on the fake brains.

The main test runs a real macro agent, a broken risk agent and a stand-in "Chair" in one
local Bureau, and checks that AgentTransport gets a Memo and a Stance back over uAgents
messages, and None (not a crash) from an analyst that errors or isn't running.
"""

import asyncio
import threading

from uagents import Agent, Bureau, Context
from uagents_core.identity import Identity

import config
import fakes
from agents import brains, fundamentals_agent, macro_agent, risk_agent, run_all
from agents.transport import AgentTransport, use_analyst_agents
from models import AnalysisRequest, Memo, ReviewRequest, Stance


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
    monkeypatch.setattr(config, "AGENT_TIMEOUT_S", 3)  # the "down" analyst would otherwise take 2 x 45 s
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
                got["memo"] = await transport.analyze("macro", analysis)
                got["stance"] = await transport.review("macro", review)
                got["risk_memo"] = await transport.analyze("risk", analysis)
                got["risk_stance"] = await transport.review("risk", review)
                got["down_memo"] = await transport.analyze("fundamentals", analysis)
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
