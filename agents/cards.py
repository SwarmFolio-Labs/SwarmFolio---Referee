"""
ASI:One Interactive Cards for the Chair and Referee chat replies (Fetch bonus criterion).

Format (https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards):
a ChatMessage carries a TextContent (the chat bubble, and the plain-text fallback for clients
without card support) plus ONE MetadataContent whose metadata is a dict of strings:
  card_protocol_version "1", requires_card_interaction "true", card_kind, card_payload (JSON text),
  optional is_terminal "true" (informational card, no input expected) and preferred_drawer_width_px.
All cards here are card_kind "custom": an element tree under {"root": ...}, at most 8 levels deep,
payload at most 64 KB. If ASI:One rejects a card it just shows the text, so the answer is never lost.
"""

import json

from uagents_core.contrib.protocols.chat import MetadataContent

from agents.chat import VERDICT_LINES
from models import Receipt, RulePrice
from referee.schema import Client

CARD_PROTOCOL_VERSION = "1"
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_DEPTH = 8
TOP_HOLDINGS = 6

VERDICT_BADGES = {
    "PASS": ("PASS", "success"),
    "VIOLATIONS_REPAIRED": ("REPAIRED", "warning"),
    "RULES_INFEASIBLE": ("INFEASIBLE", "warning"),
    "ERROR": ("ERROR", "warning"),
}
COUNT_RULES = {"max_holdings", "min_holdings"}  # their actual/limit are numbers of stocks, not weights


# ---------- The wire format ----------

def card_metadata(card_kind: str, payload: dict, terminal: bool, width_px: int = 560) -> MetadataContent:
    """The MetadataContent block that declares one card. Every value must be a string."""
    body = json.dumps(payload, ensure_ascii=False)
    if len(body.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"card payload is {len(body.encode('utf-8'))} bytes; ASI:One allows {MAX_PAYLOAD_BYTES}")
    metadata = {
        "card_protocol_version": CARD_PROTOCOL_VERSION,
        "requires_card_interaction": "true",
        "card_kind": card_kind,
        "card_payload": body,
        "preferred_drawer_width_px": str(width_px),
    }
    if terminal:
        metadata["is_terminal"] = "true"
    return MetadataContent(type="metadata", metadata=metadata)


def try_card(build, *args, **kwargs) -> MetadataContent | None:
    """Build a card, or None if anything goes wrong: a card must never block the plain-text answer."""
    try:
        return build(*args, **kwargs)
    except Exception:
        return None


# ---------- Element-tree primitives (docs section 3) ----------

def _text(value: str, style: str = "body") -> dict:
    return {"type": "text", "value": value, "style": style}


def _heading(value: str, level: int = 2) -> dict:
    return {"type": "heading", "value": value, "level": level}


def _badge(label: str, variant: str = "info") -> dict:
    return {"type": "badge", "label": label, "variant": variant}


def _section(title: str, children: list, subtitle: str | None = None) -> dict:
    node = {"type": "section", "title": title, "children": children}
    if subtitle:
        node["subtitle"] = subtitle
    return node


def _row(children: list) -> dict:
    return {"type": "group", "direction": "row", "gap": 8, "children": children}


def _list(items: list[dict]) -> dict:
    return {"type": "list", "items": items}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _amount(rule_type: str, x: float) -> str:
    """42.0% for weights, sectors, volatility and turnover; '8 stocks' for holdings counts."""
    if rule_type in COUNT_RULES:
        return f"{round(x)} stocks"
    return _pct(x)


# ---------- Receipt card (Chair final answer + Referee chat replies) ----------

def _holdings_rows(before: dict[str, float] | None, after: dict[str, float] | None) -> list[dict]:
    """'JNJ  30.0% → 25.0%' rows for the biggest positions (before only, or before → after).
    Every position the repair changed is shown, even a small one, since that's the point of the card."""
    before = before or {}
    weights = after if after is not None else before
    biggest = sorted(set(before) | set(weights), key=lambda t: max(before.get(t, 0.0), weights.get(t, 0.0)),
                     reverse=True)
    changed = [t for t in biggest if abs(weights.get(t, 0.0) - before.get(t, 0.0)) > 1e-6]
    keep = set(changed) | set(biggest[:max(0, TOP_HOLDINGS - len(changed))])
    tickers = [t for t in biggest if t in keep]
    rows = []
    for t in tickers:
        if after is None:
            rows.append(_text(f"{t}  {_pct(before.get(t, 0.0))}"))
        else:
            b, a = before.get(t, 0.0), after.get(t, 0.0)
            changed = abs(a - b) > 1e-6
            rows.append(_text(f"{t}  {_pct(b)} → {_pct(a)}", "emphasis" if changed else "body"))
    return rows


def receipt_card(receipt: Receipt, before: dict[str, float] | None = None,
                 rule_sources: dict[str, str] | None = None, client_name: str | None = None) -> MetadataContent:
    """The Referee's receipt as a card: big verdict, failed rules (actual vs limit, in the client's
    words), the conflict and its cheapest fix, before/after top holdings, and the receipt id."""
    sources = rule_sources or {}
    label, variant = VERDICT_BADGES.get(receipt.verdict, (receipt.verdict, "info"))
    children: list = [
        _row([_heading(VERDICT_LINES.get(receipt.verdict, receipt.verdict), 1), _badge(label, variant)]),
        _text(receipt.summary),
    ]

    failed = [c for c in receipt.checks if not c.passed]
    if failed:
        items = []
        for c in failed:
            words = sources.get(c.rule_id)
            items.append({"children": [
                _text(f"{c.rule_id}: “{words}”" if words else f"{c.rule_id} ({c.type})", "emphasis"),
                _row([_badge(f"Actual {_amount(c.type, c.actual)}", "warning"),
                      _badge(f"Limit {_amount(c.type, c.limit)}", "info")]),
                _text(c.explain, "muted"),
            ]})
        children.append(_section(f"Failed rules ({len(failed)} of {len(receipt.checks)})", [_list(items)]))

    if receipt.conflict_explain or receipt.cheapest_relaxation:
        conflict: list = []
        if receipt.conflict_explain:
            conflict.append(_text(receipt.conflict_explain))
        clash = [{"children": [_text(f"{rid}: “{sources[rid]}”" if rid in sources else rid, "emphasis")]}
                 for rid in receipt.conflict_set]
        if clash:
            conflict.append(_list(clash))
        if receipt.cheapest_relaxation:
            conflict.append(_heading("Cheapest fix", 3))
            conflict += [_text(r.explain) for r in receipt.cheapest_relaxation]
        children.append(_section("Conflict", conflict))

    if receipt.verdict == "VIOLATIONS_REPAIRED" and receipt.repaired_weights:
        rows = _holdings_rows(before, receipt.repaired_weights)
        rows.append(_text(f"Capital moved {_pct(receipt.capital_moved)} · Sharpe "
                          f"{receipt.sharpe_before:.2f} → {receipt.sharpe_after:.2f}", "muted"))
        children.append(_section("Top holdings", rows, subtitle="before → after the Referee's repair"))
    elif before:
        title = "Top holdings" if receipt.verdict == "PASS" else "Proposed holdings"
        children.append(_section(title, _holdings_rows(before, None)))

    children += [{"type": "divider"}, _text(f"Receipt {receipt.receipt_id} · {receipt.timestamp}", "muted")]
    title = f"Referee receipt · {receipt.client_id}"
    root = _section(title, children, subtitle=client_name)
    return card_metadata("custom", {"root": root}, terminal=True, width_px=600)


# ---------- Client picker card ("list clients") ----------

def build_selection(client_id: str) -> dict:
    """What a 'Build portfolio' click sends back (as JSON on @mention, or as prose via the planner)."""
    return {"action": "build_portfolio", "client_id": client_id,
            "message": f"Build a portfolio for {client_id}"}


def selection_text(text: str) -> str:
    """Turn a card click back into a chat request: a build_portfolio selection JSON becomes
    'Build a portfolio for C02'. Anything else (including planner prose) comes back unchanged."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        return text
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return text
    if isinstance(data, dict) and data.get("action") == "build_portfolio" and isinstance(data.get("message"), str):
        return data["message"]
    return text


def client_picker_card(clients: list[Client]) -> MetadataContent:
    """One row per client (id, name, story) with a 'Build portfolio' button."""
    items = []
    for c in clients:
        selection = build_selection(c.client_id)
        name = c.name.replace("(synthetic)", "").strip()
        items.append({
            "children": [
                _row([_heading(f"{c.client_id} · {name}", 3), _badge(f"{len(c.rules)} rules")]),
                _text(c.story, "muted"),
                {"type": "button", "label": "Build portfolio", "primary": True, "action": {"selection": selection}},
            ],
            "action": {"selection": selection},
        })
    root = _section("Pick a client", [_list(items)], subtitle="The committee builds a portfolio; the Referee checks it.")
    return card_metadata("custom", {"root": root}, terminal=False, width_px=540)


# ---------- Price-tag card ("price tags for C02") ----------

def price_tags_card(client: Client, prices: list[RulePrice]) -> MetadataContent:
    """What each rule costs, in the client's words: points of risk-adjusted return a year."""
    items = []
    for p in prices:
        cost = (_badge(f"costs {p.utility_cost_pts:.2f} pts/yr", "warning") if p.binds
                else _badge("free", "success"))
        items.append({"children": [
            _text(f"{p.rule_id}: “{p.source}”", "emphasis"),
            _row([cost, _text(f"Sharpe {p.sharpe_with:.2f} with it, {p.sharpe_without:.2f} without", "muted")]),
        ]})
    binding = sum(p.binds for p in prices)
    root = _section(f"What each rule costs · {client.client_id}", [_list(items)],
                    subtitle=f"{binding} of {len(prices)} rules hold the portfolio back")
    return card_metadata("custom", {"root": root}, terminal=True, width_px=560)
