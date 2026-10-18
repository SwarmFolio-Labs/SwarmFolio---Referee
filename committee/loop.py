"""
The committee loop (MASTER 7.3): memos -> Chair's draft -> Referee -> debate rounds -> result.

It only talks to the outside world through a `transport` (LocalTransport = direct calls,
AgentTransport = Fetch.ai messages), so the same loop runs both ways.
The Chair itself runs here (it's the one calling the loop), in a worker thread.
"""

import asyncio

import config
from committee.chair import chair_propose, chair_revise, failures_text
from models import AnalysisRequest, CommitteeResult, DebateEntry, Receipt, ReviewRequest, VerifyRequest
from referee import market
from referee.schema import Client, Proposal

ANALYSTS = ("macro", "fundamentals", "risk")


def _memo_text(memo) -> str:
    """One line per memo for the debate log."""
    favor = ", ".join(memo.favor) or "nothing in particular"
    avoid = ", ".join(memo.avoid) or "nothing in particular"
    return f"Favor {favor}; avoid {avoid}."


def _advisor_note(receipt: Receipt) -> str:
    """When the rules themselves clash: say which ones, and the cheapest way to loosen them."""
    lines = [receipt.conflict_explain]  # already reads "These rules can't all hold: ..."
    if receipt.cheapest_relaxation:
        lines.append("Cheapest fix (needs advisor approval): "
                     + " ".join(r.explain for r in receipt.cheapest_relaxation))
    return " ".join(lines)


async def run_committee(client: Client, transport, max_rounds: int = config.MAX_ROUNDS) -> CommitteeResult:
    """
    Run the whole committee for one client and return everything that happened.

    `rounds` counts the Chair's proposals: 1 = the first draft, 2 = after one debate round, ...
    The committee gets up to `max_rounds` debate rounds to fix its own portfolio.
    """
    log: list[DebateEntry] = []
    notes: list[str] = []

    # --- Round 0: every analyst writes a memo (a missing one is noted, not fatal) ---
    req = AnalysisRequest(client_id=client.client_id, client_story=client.story,
                          rules_text=[r.source for r in client.rules], as_of=market.as_of())
    # All three analysts work at the same time (gather keeps their order: macro, fundamentals, risk).
    answers = await asyncio.gather(*(transport.analyze(agent, req) for agent in ANALYSTS))
    memos = []
    for agent, memo in zip(ANALYSTS, answers):
        if memo is None:
            notes.append(f"The {agent} analyst did not answer; the committee continued without it.")
            continue
        memos.append(memo)
        log.append(DebateEntry(round=0, agent=agent, kind="memo", text=_memo_text(memo)))

    # --- Round 1: the Chair's first draft, checked by the Referee ---
    rounds = 1
    proposal = await asyncio.to_thread(chair_propose, client, memos)
    log.append(DebateEntry(round=rounds, agent="chair", kind="proposal", text=proposal.thesis))
    receipt = await transport.verify(VerifyRequest(client=client, proposal=proposal))
    first_receipt = receipt
    log.append(DebateEntry(round=rounds, agent="referee", kind="receipt", text=receipt.summary))

    # --- The rules themselves clash: no debate can fix that, so ask the advisor ---
    if receipt.verdict == "RULES_INFEASIBLE":
        note = _advisor_note(receipt)
        log.append(DebateEntry(round=rounds, agent="chair", kind="note", text=note))
        notes.append("Needs advisor approval: the client's rules conflict.")
        final = Proposal(weights=receipt.repaired_weights or proposal.weights,
                         thesis=f"{proposal.thesis} NEEDS ADVISOR APPROVAL: {note}",
                         reasons=proposal.reasons)
        return CommitteeResult(client_id=client.client_id, final_proposal=final, receipt=receipt,
                               first_receipt=first_receipt, debate_log=log, rounds=rounds,
                               self_corrected=False, notes=notes)

    # --- Debate rounds: analysts react to the Referee, the Chair revises, the Referee re-checks ---
    while receipt.verdict == "VIOLATIONS_REPAIRED" and rounds <= max_rounds:
        review_req = ReviewRequest(client_id=client.client_id, round=rounds, failures=failures_text(receipt),
                                   proposal=proposal, conflict_explain=receipt.conflict_explain)
        answers = await asyncio.gather(*(transport.review(agent, review_req) for agent in ANALYSTS))
        stances = []
        for agent, stance in zip(ANALYSTS, answers):
            if stance is None:
                notes.append(f"The {agent} analyst did not answer in round {rounds}.")
                continue
            stances.append(stance)
            log.append(DebateEntry(round=rounds, agent=agent, kind="stance",
                                   text=f"{stance.change} {stance.why}", stance=stance.stance))

        proposal = await asyncio.to_thread(chair_revise, client, proposal, receipt, stances)
        rounds += 1
        log.append(DebateEntry(round=rounds, agent="chair", kind="proposal", text=proposal.thesis))
        receipt = await transport.verify(VerifyRequest(client=client, proposal=proposal))
        log.append(DebateEntry(round=rounds, agent="referee", kind="receipt", text=receipt.summary))

    # --- Wrap up ---
    if receipt.verdict == "PASS":
        final = proposal
    elif receipt.verdict == "VIOLATIONS_REPAIRED":
        # Out of rounds: the Referee's nearest compliant portfolio is the safe answer.
        notes.append("The committee could not self-correct; the Referee's repair was applied.")
        final = Proposal(weights=receipt.repaired_weights, thesis=proposal.thesis, reasons=proposal.reasons)
    else:  # ERROR
        notes.append("The Referee could not check the last portfolio; it is NOT verified.")
        final = proposal

    return CommitteeResult(
        client_id=client.client_id, final_proposal=final, receipt=receipt,
        first_receipt=first_receipt, debate_log=log, rounds=rounds,
        # "Self-corrected" = the first draft broke rules, and the committee fixed it on its own.
        self_corrected=(first_receipt.verdict != "PASS" and receipt.verdict == "PASS"),
        notes=notes,
    )
