"""
The web app's API (FastAPI). Run it with:

    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /clients              every client: id, name, story, universe, current weights, rules (+ source text)
    GET  /demo/{client_id}     a saved committee run (data/demo_runs/<id>.json, see save_demo_run.py)
    POST /referee              {client_id, proposal} -> Receipt from the real Referee (pure math, no API keys)
    GET  /prices/{client_id}   what each rule costs (referee.prices.rule_prices), cached per client
    GET  /experiment           eval/results/experiment.json, if it exists

Live committee runs take minutes, so the app replays saved runs instead of calling run_committee here.
Every route is also available under /api (that's what the frontend calls).
If frontend/dist exists (after `npm run build`), it is served at / so one process runs the whole app.
"""

import json
import os
from functools import lru_cache

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from models import Receipt, RulePrice
from referee.prices import rule_prices
from referee.receipt import referee
from referee.schema import Client, Proposal

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIENTS_DIR = os.path.join(ROOT, "data", "clients")
DEMO_DIR = os.path.join(ROOT, "data", "demo_runs")
EXPERIMENT_PATH = os.path.join(ROOT, "eval", "results", "experiment.json")
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")

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


# Same routes at / and at /api (the frontend always calls /api/..., in dev via Vite's proxy).
app.include_router(api)
app.include_router(api, prefix="/api")

# Serve the built frontend (npm run build) at / when it exists. Mounted last so API routes win.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
