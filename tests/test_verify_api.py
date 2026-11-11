"""
The live verification endpoints: every answer is solved for this request and comes with a
certificate of what the solver did (status, time, model size, input/output hashes).
"""

from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_verify_returns_receipt_and_certificate():
    """POST /verify solves live and records every SCIP call it made."""
    r = client.post("/api/verify", json={"client_id": "C04", "weights": {"NVDA": 0.5, "MSFT": 0.5}})
    assert r.status_code == 200
    body = r.json()
    assert body["receipt"]["verdict"] == "VIOLATIONS_REPAIRED"
    cert = body["certificate"]
    assert cert["solves"], "a repair needs at least one SCIP call"
    assert all(s["status"] == "optimal" for s in cert["solves"])
    assert cert["largest_model"]["binaries"] > 0  # yes/no variables: it really is a mixed-integer problem
    assert len(cert["input_sha256"]) == 64 and len(cert["output_sha256"]) == 64
    assert cert["versions"]["scip"]


def test_same_inputs_give_same_hashes():
    """The hashes depend only on the inputs and the answer, so anyone can reproduce them."""
    req = {"client_id": "C01", "weights": {"AAPL": 0.3, "MSFT": 0.3, "JNJ": 0.4}}
    a = client.post("/api/verify", json=req).json()["certificate"]
    b = client.post("/api/verify", json=req).json()["certificate"]
    assert a["input_sha256"] == b["input_sha256"]
    assert a["output_sha256"] == b["output_sha256"]


def test_saved_draft_is_reverified_live():
    """C04's recorded round-1 AI draft broke 2 rules; re-checking it now must find the same."""
    body = client.get("/api/verify/C04/round/1").json()
    assert body["rounds"] == 3
    broken = [c for c in body["receipt"]["checks"] if not c["passed"]]
    assert len(broken) == 2
    assert body["certificate"]["solves"]


def test_infeasible_rules_are_proven_live():
    """C03's rules can't all hold; the live check proves it again from scratch."""
    body = client.get("/api/verify/C03/round/1").json()
    assert body["receipt"]["verdict"] == "RULES_INFEASIBLE"
    assert any(s["status"] == "infeasible" for s in body["certificate"]["solves"])


def test_unknown_round_and_client_404():
    assert client.get("/api/verify/C04/round/9").status_code == 404
    assert client.post("/api/verify", json={"client_id": "NOPE", "weights": {}}).status_code == 404
