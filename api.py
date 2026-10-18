"""
The web app's API (FastAPI). Run it with:

    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /clients              every client: id, name, story, universe, current weights, rules (+ source text)
    GET  /demo/{client_id}     a saved committee run (data/demo_runs/<id>.json, see save_demo_run.py)
    POST /referee              {client_id, proposal} -> Receipt from the real Referee (pure math, no API keys)
    GET  /prices/{client_id}   what each rule costs (referee.prices.rule_prices), cached per client
    GET  /experiment           eval/results/experiment.json, if it exists
    GET  /settings             {live_runs}: whether POST /run is on (the UI hides the Live run tab if not)
    GET  /run/capabilities     {live_runs, llm_available, provider, model}: real committee or scripted by default
    POST /run/{client_id}      start a live committee run (503 when ENABLE_LIVE_RUNS=false)
    GET  /run/{job_id}         its progress events
    POST /extract              {text} -> {rules, unmapped}: plain-English rules -> Rule objects (LLM; 503 when ENABLE_LIVE_RUNS=false)

Live committee runs take minutes, so the app replays saved runs by default.
ENABLE_LIVE_RUNS=false (the public deployment) turns /run off; committee/ is then never imported.
Every route is also available under /api (that's what the frontend calls).
If frontend/dist exists (after `npm run build`), it is served at / so one process runs the whole app.
"""

import asyncio
import json
import os
import time
import uuid
from functools import lru_cache

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from models import Receipt, RulePrice
from referee.prices import rule_prices
from referee.receipt import referee
from referee.schema import Client, Proposal

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIENTS_DIR = os.path.join(ROOT, "data", "clients")
DEMO_DIR = os.path.join(ROOT, "data", "demo_runs")
EXPERIMENT_PATH = os.path.join(ROOT, "eval", "results", "experiment.json")
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")

# Live committee runs need committee/ (LLM code). The public image sets ENABLE_LIVE_RUNS=false and
# doesn't ship committee/, so it is only imported inside the live-run code.
ENABLE_LIVE_RUNS = os.getenv("ENABLE_LIVE_RUNS", "true").strip().lower() not in ("0", "false", "no", "off")
LIVE_RUNS_DISABLED = "Live committee runs are disabled in the public demo"

app = FastAPI(title="SwarmFolio Referee")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
api = APIRouter()


# ---------- Helpers ----------

def _client_ids() -> list[str]:
    """Every client file in data/clients, sorted (C01, C02, ...)."""
    return sorted(f[:-5] for f in os.listdir(CLIENTS_DIR) if f.endswith(".json"))


def load_client(client_id: str) -> Client:
    """Read and validate data/clients/<client_id>.json, or 404."""
    path = os.path.join(CLIENTS_DIR, f"{client_id}.json")
    if not os.path.basename(path) == f"{client_id}.json" or not os.path.exists(path):
        raise HTTPException(404, f"Unknown client {client_id}")
    with open(path) as f:
        return Client.model_validate(json.load(f))


def _demo_path(client_id: str) -> str:
    return os.path.join(DEMO_DIR, f"{client_id}.json")


@lru_cache(maxsize=64)
def _prices(client_id: str) -> list[RulePrice]:
    """Rule prices take ~0.3-2 s of solving per client, so compute each client once."""
    return rule_prices(load_client(client_id))


# ---------- Endpoints ----------

@api.get("/clients")
def get_clients() -> list[dict]:
    """All clients with their rules in the client's own words, plus whether a saved run exists."""
    out = []
    for cid in _client_ids():
        c = load_client(cid)
        out.append({
            "client_id": c.client_id,
            "name": c.name,
            "story": c.story,
            "universe": c.universe,
            "current_weights": c.current_weights,
            "rules": [r.model_dump() for r in c.rules],
            "has_demo": os.path.exists(_demo_path(cid)),
        })
    return out


@api.get("/demo/{client_id}")
def get_demo(client_id: str) -> dict:
    """A saved CommitteeResult (plus an optional "extras" block with per-round proposals/receipts)."""
    load_client(client_id)  # 404 for unknown clients
    path = _demo_path(client_id)
    if not os.path.exists(path):
        raise HTTPException(404, f"No saved committee run for {client_id}. "
                                 f"Run: python data/demo_runs/save_demo_run.py {client_id}")
    with open(path) as f:
        return json.load(f)


class RefereeRequest(BaseModel):
    client_id: str
    proposal: Proposal


@api.post("/referee")
def post_referee(req: RefereeRequest) -> Receipt:
    """Check a proposal with the real Referee. Never raises: bad input comes back as an ERROR receipt."""
    return referee(load_client(req.client_id), req.proposal)


@api.get("/prices/{client_id}")
def get_prices(client_id: str) -> list[RulePrice]:
    """What each of this client's rules costs, most expensive first."""
    load_client(client_id)
    try:
        return _prices(client_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(422, str(e))


@api.get("/experiment")
def get_experiment() -> dict:
    """The feedback experiment's results (MASTER 10.3), if eval/experiment.py has been run."""
    if not os.path.exists(EXPERIMENT_PATH):
        raise HTTPException(404, "No experiment results yet. Run: python -m eval.experiment")
    with open(EXPERIMENT_PATH) as f:
        return json.load(f)


# ---------- Live committee runs (background job + progress events) ----------
# committee/ is not edited: progress is captured by wrapping the transport and the Chair calls.

JOBS: dict[str, dict] = {}
_RUN_LOCK = asyncio.Lock()  # the Chair is patched on committee.loop, so one live run at a time


def _event(job: dict, type_: str, **fields) -> None:
    job["events"].append({"seq": len(job["events"]), "t": round(time.time() - job["started"], 2),
                          "type": type_, **fields})


class ProgressTransport:
    """Wraps any transport (LocalTransport or the fakes) and records a progress event per call."""

    def __init__(self, inner, job: dict):
        self.inner, self.job, self.name = inner, job, getattr(inner, "name", "local")
        self.round = 0

    async def _working(self, **fields) -> None:
        # step_delay keeps "who is working" visible when the fakes answer instantly.
        _event(self.job, "working", **fields)
        await asyncio.sleep(self.job["step_delay"])

    async def analyze(self, agent, req):
        await self._working(agent=agent, round=0, task="memo")
        memo = await self.inner.analyze(agent, req)
        _event(self.job, "memo", agent=agent, round=0, ok=memo is not None,
               text=getattr(memo, "thesis", None) if memo is not None else None)
        return memo

    async def review(self, agent, req):
        await self._working(agent=agent, round=req.round, task="stance")
        stance = await self.inner.review(agent, req)
        _event(self.job, "stance", agent=agent, round=req.round, ok=stance is not None,
               stance=getattr(stance, "stance", None), text=getattr(stance, "change", None))
        return stance

    async def verify(self, req):
        await self._working(agent="referee", round=self.round, task="check")
        receipt = await self.inner.verify(req)
        failed = [c.rule_id for c in receipt.checks if not c.passed]
        _event(self.job, "referee", agent="referee", round=self.round, verdict=receipt.verdict,
               failed=failed, passed=len(receipt.checks) - len(failed), total=len(receipt.checks),
               text=receipt.summary)
        return receipt


class _FakeTransport:
    """The scripted fakes from fakes.py for the analysts; the real Referee."""

    name = "local"

    async def analyze(self, agent, req):
        import fakes
        return await asyncio.to_thread(fakes.analyze, agent, req)

    async def review(self, agent, req):
        import fakes
        return await asyncio.to_thread(fakes.review, agent, req)

    async def verify(self, req):
        return await asyncio.to_thread(referee, req.client, req.proposal)


def _committee_loop():
    from committee import loop
    return loop


def _brains(use_fakes: bool):
    """(transport, chair_propose, chair_revise) for a real or a fake run."""
    if use_fakes:
        import fakes
        return _FakeTransport(), fakes.chair_propose, fakes.chair_revise
    from committee.transport_local import LocalTransport
    committee_loop = _committee_loop()
    return LocalTransport(), committee_loop.chair_propose, committee_loop.chair_revise


async def _run_job(job: dict, client: Client, use_fakes: bool, max_rounds: int, fresh: bool = False) -> None:
    committee_loop = _committee_loop()
    inner, propose, revise = _brains(use_fakes)
    transport = ProgressTransport(inner, job)
    delay = job["step_delay"]

    def chair_propose(c, memos):
        _event(job, "working", agent="chair", round=1, task="draft")
        time.sleep(delay)
        p = propose(c, memos)
        transport.round = 1
        _event(job, "chair_draft", agent="chair", round=1, weights=p.weights, text=p.thesis)
        return p

    def chair_revise(c, proposal, receipt, stances):
        r = transport.round + 1
        _event(job, "working", agent="chair", round=r, task="revise")
        time.sleep(delay)
        p = revise(c, proposal, receipt, stances)
        transport.round = r
        _event(job, "chair_draft", agent="chair", round=r, weights=p.weights, text=p.thesis)
        return p

    async with _RUN_LOCK:
        original = (committee_loop.chair_propose, committee_loop.chair_revise)
        committee_loop.chair_propose, committee_loop.chair_revise = chair_propose, chair_revise
        try:
            if fresh and not use_fakes:
                # ?fresh=1: every LLM answers anew (no cache read or write); the request carries the flag.
                from committee import llm
                with llm.fresh_run():
                    result = await committee_loop.run_committee(client, transport, max_rounds=max_rounds)
            else:
                result = await committee_loop.run_committee(client, transport, max_rounds=max_rounds)
            job["result"] = result.model_dump(mode="json")
            job["status"] = "done"
            _event(job, "done", verdict=result.receipt.verdict, rounds=result.rounds,
                   self_corrected=result.self_corrected)
        except Exception as e:  # surface the failure to the UI instead of hanging
            job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"
            _event(job, "error", text=job["error"])
        finally:
            committee_loop.chair_propose, committee_loop.chair_revise = original


@api.get("/settings")
def get_settings() -> dict:
    """What this deployment allows (the public demo has no live committee runs)."""
    return {"live_runs": ENABLE_LIVE_RUNS}


@api.get("/run/capabilities")
def get_run_capabilities() -> dict:
    """What a live run can use here. The UI picks the real committee by default when llm_available,
    and the scripted analysts only when no LLM key is configured. Never imports committee/."""
    llm_available = ENABLE_LIVE_RUNS and not config.USE_FAKES and bool(os.getenv("ASI1_API_KEY"))
    return {"live_runs": ENABLE_LIVE_RUNS, "llm_available": llm_available,
            "provider": config.LLM_PROVIDER, "model": config.CHAIR_MODEL}


@api.post("/run/{client_id}")
async def post_run(client_id: str, fakes: bool = False, step_delay: float = 0.0, fresh: bool = False) -> dict:
    if not ENABLE_LIVE_RUNS:
        raise HTTPException(503, LIVE_RUNS_DISABLED)
    """Start run_committee for a client in the background; poll GET /run/{job_id} for progress."""
    client = load_client(client_id)
    use_fakes = fakes or config.USE_FAKES
    if not use_fakes and not os.getenv("ASI1_API_KEY"):
        raise HTTPException(400, "Live runs need ASI1_API_KEY (or set USE_FAKES / pass ?fakes=true).")
    job_id = uuid.uuid4().hex[:12]
    job = {"job_id": job_id, "client_id": client_id, "status": "running", "fakes": use_fakes,
           "max_rounds": config.MAX_ROUNDS, "started": time.time(), "events": [], "result": None,
           "error": None, "step_delay": max(0.0, min(step_delay, 5.0)),
           # "fresh" = every LLM answers anew; "cached" = saved answers are replayed when available.
           "run_mode": "fresh" if fresh and not use_fakes else "cached"}
    JOBS[job_id] = job
    _event(job, "started", client_id=client_id, fakes=use_fakes, max_rounds=config.MAX_ROUNDS,
           run_mode=job["run_mode"])
    job["task"] = asyncio.create_task(_run_job(job, client, use_fakes, config.MAX_ROUNDS, fresh=fresh))
    return {"job_id": job_id, "client_id": client_id, "fakes": use_fakes, "run_mode": job["run_mode"]}


@api.get("/run/{job_id}")
def get_run(job_id: str, after: int = 0) -> dict:
    """A live run's status and its progress events (from index `after` on); the result once done."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, f"Unknown run {job_id}")
    return {k: job[k] for k in ("job_id", "client_id", "status", "fakes", "max_rounds", "run_mode", "result",
                                "error")} | {
        "events": job["events"][max(after, 0):], "event_count": len(job["events"])}


class ExtractRequest(BaseModel):
    text: str


@api.post("/extract")
def post_extract(req: ExtractRequest) -> dict:
    """Plain-English rules -> {rules, unmapped} (referee/extract.py). Uses the LLM, so it's off in the public demo."""
    if not ENABLE_LIVE_RUNS:
        raise HTTPException(503, "Rule extraction uses an LLM and is disabled in the public demo")
    if not req.text.strip():
        raise HTTPException(422, "text is empty")
    from referee.extract import extract_rules  # lazy: pulls in the LLM layer
    try:
        return extract_rules(req.text).model_dump()
    except Exception as e:  # LLM down, no key, invalid JSON twice
        raise HTTPException(502, f"Rule extraction failed: {type(e).__name__}: {e}")


# Same routes at / and at /api (the frontend always calls /api/..., in dev via Vite's proxy).
app.include_router(api)
app.include_router(api, prefix="/api")

# Serve the built frontend (npm run build) at / when it exists. Mounted last so API routes win.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
