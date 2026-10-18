"""
Save committee runs for the web app (data/demo_runs/<client_id>.json).

A live committee run takes minutes (many LLM calls), so the app replays saved runs instead.

    # Real run (needs ASI1_API_KEY in .env; uses committee.loop.run_committee + LocalTransport):
    python data/demo_runs/save_demo_run.py C02 C91

    # Development run (no API key): scripted analysts + Chair (fakes.py story for C02,
    # a hand-written story for C91), but every receipt comes from the REAL Referee:
    python data/demo_runs/save_demo_run.py C02 C91 C03 --fakes

Each file is a CommitteeResult plus an "extras" block the app uses for the step-by-step view:
    extras.proposals = the Chair's weights for each round (round 1 = first draft)
    extras.receipts  = the Referee's receipt for each round
    extras.source    = "live" or "dev-fakes", extras.saved_at = when it was saved
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import committee.loop as loop  # noqa: E402
import fakes  # noqa: E402
from models import Memo, Stance  # noqa: E402
from referee.receipt import referee  # noqa: E402
from referee.schema import Proposal  # noqa: E402


# ---------- Development script for C91 (Ms. Okafor): volatility cap just above the floor ----------

C91_PROPOSALS = [
    ({"MSFT": 0.15, "AAPL": 0.10, "NVDA": 0.10, "JNJ": 0.10, "UNH": 0.10,
      "PG": 0.15, "KO": 0.15, "WMT": 0.15},
     "Quality tech (MSFT, AAPL, NVDA) for growth, JNJ/UNH for the healthcare floor, "
     "and three consumer staples to keep swings small."),
    ({"MSFT": 0.15, "AAPL": 0.10, "GOOGL": 0.05, "JNJ": 0.10, "UNH": 0.05,
      "PG": 0.15, "KO": 0.20, "WMT": 0.20},
     "Dropped NVDA (the most volatile name) for a small GOOGL stake and leaned harder on staples."),
    ({"MSFT": 0.15, "AAPL": 0.05, "GOOGL": 0.05, "JNJ": 0.10, "UNH": 0.05,
      "PG": 0.15, "KO": 0.15, "WMT": 0.15, "XOM": 0.10, "JPM": 0.05},
     "Added XOM and JPM: they move differently from tech and staples, which lowers overall "
     "volatility more than piling into staples did."),
]

C91_MEMOS = {
    "macro": Memo(agent="macro", favor=["MSFT", "GOOGL", "WMT"], avoid=["TLT", "GLD"],
                  sector_views={"Tech": "overweight", "Consumer": "neutral", "Energy": "neutral"},
                  reasons={"MSFT": "Tech led the last 6 months; cloud spending is still rising.",
                           "TLT": "Client wants stocks only."},
                  confidence=0.6),
    "fundamentals": Memo(agent="fundamentals", favor=["MSFT", "UNH", "JNJ", "AAPL"], avoid=["PFE"],
                         sector_views={"Healthcare": "overweight", "Tech": "neutral"},
                         reasons={"UNH": "Below its 5-year average P/E with steady revenue growth.",
                                  "PFE": "Revenue still shrinking after the vaccine boom."},
                         confidence=0.7),
    "risk": Memo(agent="risk", favor=["PG", "KO", "WMT", "JNJ"], avoid=["NVDA", "META"],
                 sector_views={"Consumer": "overweight", "Tech": "underweight"},
                 reasons={"PG": "Among the lowest-volatility names in the universe.",
                          "NVDA": "Volatility above 45%; hard to fit under an 11% portfolio cap."},
                 confidence=0.8),
}

C91_STANCES = {
    1: {
        "risk": Stance(agent="risk", stance="concede", change="Drop NVDA entirely.",
                       why="It's the single biggest contributor to volatility, and the cap is 11%."),
        "fundamentals": Stance(agent="fundamentals", stance="defend", change="Keep MSFT at 15%.",
                               why="Tech must stay at 25% anyway; MSFT is the steadiest way to hold it."),
        "macro": Stance(agent="macro", stance="modify", change="Swap NVDA for 5% GOOGL, rest to staples.",
                        why="Keeps tech exposure while cutting the most volatile name."),
    },
    2: {
        "risk": Stance(agent="risk", stance="modify", change="Add 10% XOM and 5% JPM.",
                       why="More staples barely helped; names that move differently from tech lower risk faster."),
        "fundamentals": Stance(agent="fundamentals", stance="concede", change="Trim AAPL to 5%.",
                               why="Volatility is still over the cap; AAPL is the easiest tech to trim."),
        "macro": Stance(agent="macro", stance="defend", change="Keep tech at exactly 25%.",
                        why="The client asked for at least 25% tech; going lower breaks R2."),
    },
}


def _scripted_brains(client_id: str):
    """Return (analyze, review, chair_propose, chair_revise) that replay a fixed story."""
    if client_id == "C91":
        def analyze(agent, req):
            return C91_MEMOS[agent]

        def review(agent, req):
            return C91_STANCES.get(req.round, C91_STANCES[2])[agent]

        def propose(client, memos):
            w, thesis = C91_PROPOSALS[0]
            return Proposal(weights=w, thesis=thesis, reasons={})

        state = {"i": 0}

        def revise(client, proposal, receipt, stances):
            state["i"] = min(state["i"] + 1, len(C91_PROPOSALS) - 1)
            w, thesis = C91_PROPOSALS[state["i"]]
            return Proposal(weights=w, thesis=thesis, reasons={})

        return analyze, review, propose, revise
    # Everyone else: the Dr. Patel story from fakes.py.
    return fakes.analyze, fakes.review, fakes.chair_propose, fakes.chair_revise


class ScriptedTransport:
    """Same async methods as LocalTransport, but analysts are scripted; the Referee is real."""

    name = "local"

    def __init__(self, analyze, review):
        self._analyze, self._review = analyze, review

    async def analyze(self, agent, req):
        return self._analyze(agent, req)

    async def review(self, agent, req):
        return self._review(agent, req)

    async def verify(self, req):
        return await asyncio.to_thread(referee, req.client, req.proposal)


async def save_run(client_id: str, use_fakes: bool, max_rounds: int) -> str:
    """Run the committee for one client (recording every proposal and receipt) and save it."""
    client = fakes.load_client(client_id)
    proposals, receipts = [], []

    if use_fakes:
        analyze, review, propose, revise = _scripted_brains(client_id)
        transport = ScriptedTransport(analyze, review)
    else:
        from committee import llm
        from committee.transport_local import LocalTransport
        llm.use_live_model()  # the same fast model as the live agents, so the demo cache is reused
        propose, revise = loop.chair_propose, loop.chair_revise
        transport = LocalTransport()

    # Wrap the Chair and the Referee so we can record each round without touching the loop.
    def recording_propose(c, memos):
        p = propose(c, memos)
        proposals.append(p.weights)
        return p

    def recording_revise(c, proposal, receipt, stances):
        p = revise(c, proposal, receipt, stances)
        proposals.append(p.weights)
        return p

    real_verify = transport.verify

    async def recording_verify(req):
        r = await real_verify(req)
        receipts.append(r.model_dump(mode="json"))
        return r

    transport.verify = recording_verify
    original = (loop.chair_propose, loop.chair_revise)
    loop.chair_propose, loop.chair_revise = recording_propose, recording_revise
    try:
        result = await loop.run_committee(client, transport, max_rounds=max_rounds)
    finally:
        loop.chair_propose, loop.chair_revise = original

    data = result.model_dump(mode="json")
    data["extras"] = {
        "source": "dev-fakes" if use_fakes else "live",
        "model": None if use_fakes else __import__("committee.llm", fromlist=["x"]).model_id_for("chair"),
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "proposals": proposals,
        "receipts": receipts,
    }
    path = os.path.join(HERE, f"{client_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client_ids", nargs="+", help="e.g. C02 C91")
    parser.add_argument("--fakes", action="store_true", help="scripted analysts/Chair (no API key needed)")
    parser.add_argument("--max-rounds", type=int, default=None)
    args = parser.parse_args()

    if not args.fakes and not os.getenv("ASI1_API_KEY"):
        sys.exit("ASI1_API_KEY is not set (put it in .env), or pass --fakes for a development run.")

    import config
    max_rounds = args.max_rounds or config.MAX_ROUNDS
    for cid in args.client_ids:
        path = asyncio.run(save_run(cid, args.fakes, max_rounds))
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
