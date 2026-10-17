"""
Fake brains with realistic, hard-coded outputs (MASTER 4.3).

Devin builds the app and agents against these until the real Referee and
committee are ready. Same signatures as contract.py, so switching to the real
thing is just flipping config.USE_FAKES.

The fake story is Dr. Patel (client C02):
  round 1: the Chair proposes JNJ 30% + UNH 10% -> Healthcare 40% breaks R4 (max 35%)
  analysts: Risk concedes, Fundamentals defends UNH, Macro modifies
  round 2: the Chair trims UNH to 5% and adds KO -> PASS
For a client with planted_conflict (C03) the fake Referee says RULES_INFEASIBLE.

Run `python fakes.py` to rewrite data/samples/*.json from these fakes.
"""

import asyncio
import json
import os

from models import (
    AnalysisRequest,
    CheckResult,
    CommitteeResult,
    DebateEntry,
    Memo,
    Receipt,
    Relaxation,
    ReviewRequest,
    Stance,
    VerifyRequest,
)
from referee.schema import Client, Proposal

ANALYSTS = ["macro", "fundamentals", "risk"]
TIMESTAMP = "2026-10-17T14:00:00Z"
AS_OF = "2026-10-16"

# ---------- The two proposals in the fake story ----------

FIRST_WEIGHTS = {"JNJ": 0.30, "UNH": 0.10, "MSFT": 0.15, "AAPL": 0.10,
                 "GOOGL": 0.10, "JPM": 0.10, "PG": 0.15}
REVISED_WEIGHTS = {"JNJ": 0.30, "UNH": 0.05, "MSFT": 0.15, "AAPL": 0.10,
                   "GOOGL": 0.10, "JPM": 0.10, "PG": 0.15, "KO": 0.05}

FIRST_REASONS = {
    "JNJ": "Legacy position the client must keep at 30% for tax reasons.",
    "UNH": "Strong earnings growth and pricing power in managed care.",
    "MSFT": "Steady cloud growth with high margins.",
    "AAPL": "Cash-rich, lower volatility than most tech.",
    "GOOGL": "Cheap relative to earnings growth.",
    "JPM": "Best-run large bank; adds a non-tech sector.",
    "PG": "Defensive staple that keeps volatility down.",
}
REVISED_REASONS = dict(FIRST_REASONS)
REVISED_REASONS["UNH"] = "Kept a smaller 5% stake so Healthcare stays at the 35% cap."
REVISED_REASONS["KO"] = "Defensive staple to absorb the 5% trimmed from UNH."


# ---------- Small helpers to build fake receipts ----------

def _passing_checks() -> list[CheckResult]:
    """Every Dr. Patel rule passing, for the revised portfolio."""
    return [
        CheckResult(rule_id="R1", type="max_weight", passed=True, actual=0.30, limit=0.35, violation=0.0,
                    explain="Largest position is JNJ at 30.0%, under the 35.0% cap."),
        CheckResult(rule_id="R2", type="exclude", passed=True, actual=0.0, limit=0.0, violation=0.0,
                    explain="No money in XOM or CVX."),
        CheckResult(rule_id="R3", type="min_weight", passed=True, actual=0.30, limit=0.30, violation=0.0,
                    explain="JNJ is 30.0%, meeting the 30.0% minimum."),
        CheckResult(rule_id="R4", type="sector_max", passed=True, actual=0.35, limit=0.35, violation=0.0,
                    explain="Healthcare is 35.0%, at the 35.0% cap."),
        CheckResult(rule_id="R5", type="max_holdings", passed=True, actual=8, limit=8, violation=0.0,
                    explain="8 holdings, at the limit of 8."),
        CheckResult(rule_id="R6", type="buy_in", passed=True, actual=0.05, limit=0.05, violation=0.0,
                    explain="Smallest position is 5.0%, meeting the 5.0% minimum."),
        CheckResult(rule_id="R7", type="max_volatility", passed=True, actual=0.162, limit=0.18, violation=0.0,
                    explain="Annual volatility is 16.2%, under the 18.0% limit."),
    ]


def _first_checks() -> list[CheckResult]:
    """Dr. Patel's rules against the first proposal: only R4 (Healthcare) fails."""
    checks = _passing_checks()
    checks[3] = CheckResult(rule_id="R4", type="sector_max", passed=False, actual=0.40, limit=0.35,
                            violation=0.05,
                            explain="Healthcare is 40.0% (JNJ 30% + UNH 10%), above the 35.0% cap by 5.0 points.")
    checks[4] = CheckResult(rule_id="R5", type="max_holdings", passed=True, actual=7, limit=8, violation=0.0,
                            explain="7 holdings, under the limit of 8.")
    checks[5] = CheckResult(rule_id="R6", type="buy_in", passed=True, actual=0.10, limit=0.05, violation=0.0,
                            explain="Smallest position is 10.0%, above the 5.0% minimum.")
    checks[6] = CheckResult(rule_id="R7", type="max_volatility", passed=True, actual=0.165, limit=0.18,
                            violation=0.0, explain="Annual volatility is 16.5%, under the 18.0% limit.")
    return checks


def _violation_receipt(client_id: str) -> Receipt:
    return Receipt(
        receipt_id="RCPT-C02-0001", timestamp=TIMESTAMP, client_id=client_id,
        verdict="VIOLATIONS_REPAIRED", checks=_first_checks(), dust_removed=[],
        rules_feasible=True, conflict_set=[], conflict_explain="",
        cheapest_relaxation=[], repaired_weights=REVISED_WEIGHTS, capital_moved=0.05,
        sharpe_before=0.84, sharpe_after=0.81, vol_after=0.162,
        summary="1 of 7 rules failed: Healthcare is 40%, cap is 35%. "
                "Nearest compliant portfolio moves 5% of capital (UNH 10% -> 5%, KO +5%).",
        notes=["Rules are feasible together.", "Repair kept JNJ at its 30% minimum."],
    )


def _pass_receipt(client_id: str) -> Receipt:
    return Receipt(
        receipt_id="RCPT-C02-0002", timestamp=TIMESTAMP, client_id=client_id,
        verdict="PASS", checks=_passing_checks(), dust_removed=[],
        rules_feasible=True, conflict_set=[], conflict_explain="",
        cheapest_relaxation=[], repaired_weights=REVISED_WEIGHTS, capital_moved=0.0,
        sharpe_before=0.81, sharpe_after=0.81, vol_after=0.162,
        summary="All 7 rules pass. No changes needed.",
        notes=[],
    )


def _infeasible_receipt(client_id: str) -> Receipt:
    return Receipt(
        receipt_id="RCPT-C03-0001", timestamp=TIMESTAMP, client_id=client_id,
        verdict="RULES_INFEASIBLE", checks=_first_checks(), dust_removed=[],
        rules_feasible=False, conflict_set=["R3", "R4", "R8"],
        conflict_explain="JNJ at least 30% (R3) plus UNH at least 10% (R8) is 40% Healthcare, "
                         "but Healthcare is capped at 35% (R4). No portfolio can satisfy all three.",
        cheapest_relaxation=[
            Relaxation(rule_id="R4", old_limit=0.35, new_limit=0.40, cost=0.20,
                       explain="Raise the Healthcare cap from 35% to 40% (priority 4 x 0.05 = 0.20)."),
        ],
        repaired_weights={"JNJ": 0.30, "UNH": 0.10, "MSFT": 0.15, "AAPL": 0.10,
                          "GOOGL": 0.10, "JPM": 0.10, "PG": 0.15},
        capital_moved=0.0, sharpe_before=0.84, sharpe_after=0.84, vol_after=0.165,
        summary="These rules can't all be met: R3, R4 and R8 clash. "
                "Cheapest fix: raise the Healthcare cap to 40%.",
        notes=["Ask the client which rule to loosen."],
    )


# ---------- The fake brain functions (same signatures as contract.py) ----------

def referee(client: Client, proposal: Proposal) -> Receipt:
    """Fake Referee: infeasible for planted-conflict clients, PASS for the revised portfolio,
    otherwise one Healthcare violation."""
    if client.planted_conflict:
        return _infeasible_receipt(client.client_id)
    if proposal.weights == REVISED_WEIGHTS:
        return _pass_receipt(client.client_id)
    return _violation_receipt(client.client_id)


def analyze(agent: str, req: AnalysisRequest) -> Memo:
    """Fake analyst memo for "macro", "fundamentals" or "risk"."""
    memos = {
        "macro": Memo(
            agent="macro", favor=["MSFT", "GOOGL", "JPM"], avoid=["TLT"],
            sector_views={"Tech": "overweight", "Financials": "neutral", "Bonds": "underweight"},
            reasons={"MSFT": "Tech led the last 6 months (+14%).",
                     "TLT": "Long bonds fell as rates stayed high."},
            confidence=0.6),
        "fundamentals": Memo(
            agent="fundamentals", favor=["UNH", "GOOGL", "AAPL"], avoid=["PFE"],
            sector_views={"Healthcare": "overweight", "Tech": "neutral"},
            reasons={"UNH": "P/E below its 5-year average with 8% revenue growth.",
                     "PFE": "Revenue shrinking after the vaccine boom."},
            confidence=0.7),
        "risk": Memo(
            agent="risk", favor=["PG", "KO", "JNJ"], avoid=["NVDA"],
            sector_views={"Consumer": "overweight", "Tech": "underweight"},
            reasons={"PG": "Lowest volatility in the universe (15%).",
                     "NVDA": "Volatility above 45% would break the 18% portfolio cap."},
            confidence=0.8),
    }
    return memos[agent]


def review(agent: str, req: ReviewRequest) -> Stance:
    """Fake analyst stance after the Referee reports a failure."""
    stances = {
        "risk": Stance(agent="risk", stance="concede", change="Cut UNH to 5%.",
                       why="Healthcare is over the 35% cap; JNJ can't move, so UNH has to."),
        "fundamentals": Stance(agent="fundamentals", stance="defend", change="Keep some UNH.",
                               why="UNH is the cheapest quality name in Healthcare; don't drop it entirely."),
        "macro": Stance(agent="macro", stance="modify", change="Move the freed 5% to KO.",
                        why="A staple keeps volatility low while staying out of Healthcare."),
    }
    return stances[agent]


def chair_propose(client: Client, memos: list[Memo]) -> Proposal:
    """Fake Chair first proposal (breaks the Healthcare cap on purpose)."""
    return Proposal(weights=dict(FIRST_WEIGHTS),
                    thesis="Keep the legacy JNJ, add quality growth (MSFT, GOOGL, UNH) and defensive PG.",
                    reasons=dict(FIRST_REASONS))


def chair_revise(client: Client, proposal: Proposal, receipt: Receipt, stances: list[Stance]) -> Proposal:
    """Fake Chair revision: trim UNH to 5% and add KO, which passes every rule."""
    return Proposal(weights=dict(REVISED_WEIGHTS),
                    thesis="Same plan, with UNH trimmed to 5% and KO added so Healthcare sits at the 35% cap.",
                    reasons=dict(REVISED_REASONS))


def _failures(receipt: Receipt) -> list[str]:
    """Plain-English text of every failed check."""
    return [c.explain for c in receipt.checks if not c.passed]


async def run_committee(client: Client, transport, max_rounds: int = 3) -> CommitteeResult:
    """Fake committee loop. It really calls the transport (so Devin can test AgentTransport
    against the fake brains), but every brain answer is hard-coded."""
    log: list[DebateEntry] = []
    notes: list[str] = []

    # Round 0: every analyst writes a memo.
    req = AnalysisRequest(client_id=client.client_id, client_story=client.story,
                          rules_text=[r.source for r in client.rules], as_of=AS_OF)
    memos = []
    for agent in ANALYSTS:
        memo = await transport.analyze(agent, req)
        if memo is None:
            notes.append(f"{agent} analyst did not answer; continued without it.")
            continue
        memos.append(memo)
        log.append(DebateEntry(round=0, agent=agent, kind="memo",
                               text=f"Favor {', '.join(memo.favor)}; avoid {', '.join(memo.avoid)}."))

    proposal = chair_propose(client, memos)
    log.append(DebateEntry(round=1, agent="chair", kind="proposal", text=proposal.thesis))
    receipt = await transport.verify(VerifyRequest(client=client, proposal=proposal))
    first_receipt = receipt
    log.append(DebateEntry(round=1, agent="referee", kind="receipt", text=receipt.summary))

    rounds = 1
    while receipt.verdict == "VIOLATIONS_REPAIRED" and rounds < max_rounds:
        review_req = ReviewRequest(client_id=client.client_id, round=rounds, failures=_failures(receipt),
                                   proposal=proposal, conflict_explain=receipt.conflict_explain)
        stances = []
        for agent in ANALYSTS:
            stance = await transport.review(agent, review_req)
            if stance is None:
                continue
            stances.append(stance)
            log.append(DebateEntry(round=rounds, agent=agent, kind="stance",
                                   text=f"{stance.change} {stance.why}", stance=stance.stance))
        rounds += 1
        proposal = chair_revise(client, proposal, receipt, stances)
        log.append(DebateEntry(round=rounds, agent="chair", kind="proposal", text=proposal.thesis))
        receipt = await transport.verify(VerifyRequest(client=client, proposal=proposal))
        log.append(DebateEntry(round=rounds, agent="referee", kind="receipt", text=receipt.summary))

    if receipt.verdict == "RULES_INFEASIBLE":
        log.append(DebateEntry(round=rounds, agent="chair", kind="note",
                               text="The rules themselves clash; asking the client which to loosen."))

    return CommitteeResult(
        client_id=client.client_id, final_proposal=proposal, receipt=receipt,
        first_receipt=first_receipt, debate_log=log, rounds=rounds,
        self_corrected=(first_receipt.verdict != "PASS" and receipt.verdict == "PASS"),
        notes=notes,
    )


class FakeLocalTransport:
    """Direct calls to the fake brains (stand-in until committee/transport_local.py exists)."""

    name = "local"

    async def analyze(self, agent, req):
        return await asyncio.to_thread(analyze, agent, req)

    async def review(self, agent, req):
        return await asyncio.to_thread(review, agent, req)

    async def verify(self, req):
        return await asyncio.to_thread(referee, req.client, req.proposal)


# ---------- Write data/samples/*.json ----------

def load_client(client_id: str) -> Client:
    """Read data/clients/<client_id>.json."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "clients", f"{client_id}.json")
    with open(path) as f:
        return Client.model_validate(json.load(f))


def build_samples() -> dict:
    """One example of every model, keyed by the sample file name."""
    patel = load_client("C02")
    first = chair_propose(patel, [])
    result = asyncio.run(run_committee(patel, FakeLocalTransport()))
    req = AnalysisRequest(client_id="C02", client_story=patel.story,
                          rules_text=[r.source for r in patel.rules], as_of=AS_OF)
    first_receipt = referee(patel, first)
    return {
        "Rule": patel.rules[3],
        "Client": patel,
        "Proposal": first,
        "CheckResult": first_receipt.checks[3],
        "Relaxation": _infeasible_receipt("C03").cheapest_relaxation[0],
        "Receipt": first_receipt,
        "Receipt_infeasible": _infeasible_receipt("C03"),
        "AnalysisRequest": req,
        "Memo": analyze("fundamentals", req),
        "ReviewRequest": ReviewRequest(client_id="C02", round=1, failures=_failures(first_receipt),
                                       proposal=first, conflict_explain=""),
        "Stance": review("fundamentals", None),
        "VerifyRequest": VerifyRequest(client=patel, proposal=first),
        "DebateEntry": result.debate_log[0],
        "CommitteeResult": result,
    }


def write_samples() -> None:
    """Save each sample to data/samples/<Name>.json."""
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "samples")
    os.makedirs(folder, exist_ok=True)
    for name, model in build_samples().items():
        with open(os.path.join(folder, f"{name}.json"), "w") as f:
            f.write(model.model_dump_json(indent=2) + "\n")
    print(f"Wrote samples to {folder}")


if __name__ == "__main__":
    write_samples()
