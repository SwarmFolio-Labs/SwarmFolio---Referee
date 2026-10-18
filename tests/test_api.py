"""The web API (api.py): client data the design needs and live runs with progress events (fakes, no keys)."""
import time

import pytest
from fastapi.testclient import TestClient

import api
import config


@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def _wait_done(c, job_id, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        body = c.get(f"/api/run/{job_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.05)
    raise AssertionError("live run did not finish")


def test_clients_have_starting_holdings(client):
    rows = {r["client_id"]: r for r in client.get("/api/clients").json()}
    c04 = rows["C04"]["current_weights"]
    assert sum(c04[t] for t in ("NVDA", "MSFT", "AAPL")) == pytest.approx(0.60)
    assert all("source" in rule for rule in rows["C04"]["rules"])


def test_referee_checks_carry_actual_and_limit(client):
    weights = api.load_client("C04").current_weights
    receipt = client.post("/api/referee", json={"client_id": "C04",
                                                "proposal": {"weights": weights, "thesis": "x", "reasons": {}}}).json()
    assert receipt["checks"] and all({"actual", "limit", "passed", "type"} <= set(ch) for ch in receipt["checks"])
    exclude = next(ch for ch in receipt["checks"] if ch["type"] == "exclude")
    assert exclude["actual"] == 0 and exclude["passed"]


def test_live_run_with_fakes_reports_progress(client, monkeypatch):
    monkeypatch.setattr(config, "USE_FAKES", True)
    started = client.post("/api/run/C02")
    assert started.status_code == 200
    body = _wait_done(client, started.json()["job_id"])
    assert body["status"] == "done", body["error"]
    events = body["events"]
    types = [e["type"] for e in events]
    assert types[0] == "started" and types[-1] == "done"
    memos = [e for e in events if e["type"] == "memo"]
    assert {e["agent"] for e in memos} == {"macro", "fundamentals", "risk"}
    assert any(e["type"] == "chair_draft" and e["round"] == 1 for e in events)
    referee_rounds = [e for e in events if e["type"] == "referee"]
    assert referee_rounds[0]["round"] == 1 and referee_rounds[0]["total"] > 0
    assert [e["round"] for e in referee_rounds] == sorted(e["round"] for e in referee_rounds)
    if body["result"]["rounds"] > 1:
        assert any(e["type"] == "stance" and e["stance"] for e in events)
    assert body["result"]["receipt"]["verdict"] == events[-1]["verdict"]
    assert any(e["type"] == "working" and e["agent"] == "chair" for e in events)
    # Incremental polling: only the new events after `after`.
    tail = client.get(f"/api/run/{body['job_id']}?after={len(events) - 1}").json()["events"]
    assert [e["type"] for e in tail] == ["done"]
    # The Chair patch is undone after the run.
    from committee import chair
    assert api.committee_loop.chair_propose is chair.chair_propose


def test_live_run_needs_key_or_fakes(client, monkeypatch):
    monkeypatch.setattr(config, "USE_FAKES", False)
    monkeypatch.delenv("ASI1_API_KEY", raising=False)
    assert client.post("/api/run/C02").status_code == 400
    assert client.post("/api/run/NOPE?fakes=true").status_code == 404
    assert client.get("/api/run/doesnotexist").status_code == 404


def test_live_run_failure_is_reported(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("chair exploded")
    monkeypatch.setattr(api.committee_loop, "run_committee", boom)
    job_id = client.post("/api/run/C02?fakes=true").json()["job_id"]
    body = _wait_done(client, job_id)
    assert body["status"] == "error" and "chair exploded" in body["error"]
    assert body["events"][-1]["type"] == "error"


def test_step_delay_keeps_working_state_visible(client):
    """With step_delay, each agent's "working" event comes well before its result (for the UI tiles)."""
    job_id = client.post("/api/run/C02?fakes=true&step_delay=0.2").json()["job_id"]
    events = _wait_done(client, job_id)["events"]
    for i, e in enumerate(events):
        if e["type"] != "working":
            continue
        result = next(x for x in events[i + 1:] if x.get("agent") == e["agent"] and x["type"] != "working")
        assert result["t"] - e["t"] >= 0.15, (e, result)
