"""
Chat Protocol helpers shared by the Chair and Referee agents (MASTER 9, 9.2).

Turning a user's chat text into a client, and a result into a reply, is presentation,
not math, so it lives here and the agent files stay thin.
"""

import glob
import json
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
)

from models import CommitteeResult, Receipt
from referee.schema import Client

CLIENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clients")

VERDICT_LINES = {
    "PASS": "✅ Compliant",
    "VIOLATIONS_REPAIRED": "🛠️ The Referee repaired the portfolio",
    "RULES_INFEASIBLE": "⛔ These rules are impossible",
    "ERROR": "⚠️ The Referee hit an error",
}


# ---------- Chat Protocol plumbing ----------

def text_of(msg: ChatMessage) -> str:
    """Join all the text parts of a chat message."""
    return " ".join(part.text for part in msg.content if isinstance(part, TextContent)).strip()


async def acknowledge(ctx, sender: str, msg: ChatMessage) -> None:
    """Tell the sender we got their message (the Chat Protocol wants this first)."""
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc),
                                               acknowledged_msg_id=msg.msg_id))


async def say(ctx, sender: str, text: str, end: bool = False) -> None:
    """Send a chat message. end=True also closes the session (used for the final answer)."""
    content = [TextContent(type="text", text=text)]
    if end:
        content.append(EndSessionContent(type="end-session"))
    await ctx.send(sender, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content))


# ---------- Clients ----------

def load_clients() -> list[Client]:
    """Every client in data/clients, sorted by id."""
    clients = []
    for path in sorted(glob.glob(os.path.join(CLIENTS_DIR, "*.json"))):
        with open(path) as f:
            clients.append(Client.model_validate(json.load(f)))
    return clients


def _short_name(client: Client) -> str:
    """'Dr. Patel (synthetic)' -> 'Dr. Patel' (what a user would actually type)."""
    return client.name.replace("(synthetic)", "").strip()


def find_client(text: str) -> Client | None:
    """Pick the client the user means: pasted client JSON, an id like C02, or a name like Dr. Patel."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return Client.model_validate_json(text)
        except ValueError:
            return None
    clients = load_clients()
    match = re.search(r"\bC\d{2,}\b", text, re.IGNORECASE)
    if match:
        wanted = match.group(0).upper()
        for client in clients:
            if client.client_id == wanted:
                return client
    # Longest name that appears in the text wins, so "Dr. Patel" doesn't pick "Dr. Patel, with a UNH gift".
    named = [c for c in clients if _short_name(c).lower() in text.lower()]
    if named:
        return max(named, key=lambda c: len(_short_name(c)))
    return None


def list_clients_text() -> str:
    """Names and one-line stories of every client."""
    lines = ["Clients I can build for:"]
    for client in load_clients():
        lines.append(f"• {client.client_id}: {_short_name(client)}. {client.story}")
    return "\n".join(lines)


CHAIR_HELP = (
    "Hi! I'm the SwarmFolio investment committee. Try:\n"
    "• \"list clients\"\n"
    "• \"Build a portfolio for Dr. Patel\" or \"Build a portfolio for C02\"\n"
    "• or paste a client as JSON"
)


# ---------- Replies ----------

def _weights_lines(weights: dict[str, float], top: int = 10) -> list[str]:
    """Holdings sorted biggest first, as '• JNJ 30.0%'."""
    ordered = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    return [f"• {ticker} {w * 100:.1f}%" for ticker, w in ordered[:top]]


def receipt_text(receipt: Receipt) -> str:
    """Short plain-text receipt: verdict, failed checks, the fix, and the receipt id."""
    lines = [VERDICT_LINES.get(receipt.verdict, receipt.verdict), receipt.summary]
    failed = [c.explain for c in receipt.checks if not c.passed]
    if failed:
        lines.append("Failed checks:")
        lines += [f"• {f}" for f in failed]
    if receipt.conflict_explain:
        lines.append(f"Why: {receipt.conflict_explain}")
    if receipt.cheapest_relaxation:
        lines.append("Cheapest fix:")
        lines += [f"• {r.explain}" for r in receipt.cheapest_relaxation]
    lines.append(f"Receipt: {receipt.receipt_id}")
    return "\n".join(lines)


def committee_reply(result: CommitteeResult, notes: list[str]) -> str:
    """The Chair's final answer in the MASTER 9 format: verdict, debate, weights, receipt, notes."""
    receipt = result.receipt
    rounds = f"{result.rounds} round{'s' if result.rounds != 1 else ''}"
    verdict = VERDICT_LINES.get(receipt.verdict, receipt.verdict)
    if receipt.verdict != "RULES_INFEASIBLE":
        verdict += f" after {rounds}"
    lines = [f"**{verdict}** ({result.client_id})", ""]

    # 2. Debate highlights: every analyst stance.
    stances = [e for e in result.debate_log if e.kind == "stance"]
    if stances:
        lines.append("**Debate highlights**")
        for e in stances:
            past = {"concede": "conceded", "defend": "defended", "modify": "modified"}.get(e.stance, e.stance)
            lines.append(f"• {e.agent} {past} (round {e.round}): {e.text}")
        lines.append("")

    # 3. Final weights (the Referee's repaired weights if it had to step in).
    if receipt.verdict != "RULES_INFEASIBLE":
        weights = result.final_proposal.weights
        if receipt.verdict == "VIOLATIONS_REPAIRED" and receipt.repaired_weights:
            weights = receipt.repaired_weights
        lines.append("**Final weights**")
        lines += _weights_lines(weights)
        lines.append("")

    # 4. Receipt summary.
    lines.append("**Receipt**")
    lines.append(receipt_text(receipt))

    # 5. Notes: timeouts and fallbacks.
    all_notes = list(dict.fromkeys(result.notes + notes))  # keep order, drop duplicates
    if all_notes:
        lines.append("")
        lines.append("**Notes**")
        lines += [f"• {n}" for n in all_notes]
    return "\n".join(lines)
