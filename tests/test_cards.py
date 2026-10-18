"""
Tests for the ASI:One Interactive Cards (agents/cards.py), checked against the documented format:
https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards
"""

import asyncio
import json

import fakes
from agents.cards import (MAX_DEPTH, MAX_PAYLOAD_BYTES, build_selection, card_metadata, client_picker_card,
                          price_tags_card, receipt_card, selection_text, try_card)
from agents.chat import find_client, load_clients, say
from referee.prices import rule_prices

REQUIRED_KEYS = {"card_protocol_version", "requires_card_interaction", "card_kind", "card_payload"}
CARD_KINDS = {"carousel", "detail", "form", "review", "custom"}
# Custom element-tree primitives from the docs, with their required fields.
ELEMENTS = {
    "section": {"children"}, "group": {"direction", "children"}, "divider": set(),
    "text": {"value"}, "heading": {"value", "level"}, "image": {"src"}, "badge": {"label"},
    "button": {"label", "action"}, "input": {"name", "kind", "label"}, "list": {"items"},
    "choice_grid": {"name", "choices"},
}


def _check_element(node: dict, depth: int = 1) -> None:
    """Every node is a documented primitive with its required fields, at most 8 levels deep."""
    assert depth <= MAX_DEPTH
    assert node["type"] in ELEMENTS, node["type"]
    assert ELEMENTS[node["type"]] <= set(node), node
    if node["type"] == "text":
        assert node.get("style", "body") in {"body", "muted", "emphasis"}
    if node["type"] == "heading":
        assert node["level"] in {1, 2, 3}
    if node["type"] == "badge":
        assert node.get("variant", "info") in {"info", "success", "warning"}
    if node["type"] == "group":
        assert node["direction"] in {"row", "column"}
    if node["type"] == "button":
        assert isinstance(node["action"]["selection"], dict)
    for child in node.get("children", []):
        _check_element(child, depth + 1)
    for item in node.get("items", []):
        if "action" in item:
            assert isinstance(item["action"]["selection"], dict)
        for child in item["children"]:
            _check_element(child, depth + 1)


def _payload(card) -> dict:
    """Check the metadata block like ASI:One does, and return the decoded custom payload."""
    assert card.type == "metadata"
    meta = card.metadata
    assert REQUIRED_KEYS <= set(meta)
    assert all(isinstance(v, str) for v in meta.values())  # the wire type is dict[str, str]
    assert meta["card_protocol_version"] == "1" and meta["requires_card_interaction"] == "true"
    assert meta["card_kind"] in CARD_KINDS
    assert 320 <= int(meta["preferred_drawer_width_px"]) <= 800
    assert len(meta["card_payload"].encode("utf-8")) <= MAX_PAYLOAD_BYTES
    payload = json.loads(meta["card_payload"])
    assert set(payload) == {"root"}  # custom cards: the tree sits at the top level, no extra envelope
    _check_element(payload["root"])
    return payload


def _texts(node) -> list[str]:
    """Every string shown on the card (values, labels, titles), for 'does it say X' checks."""
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"value", "label", "title", "subtitle"} and isinstance(value, str):
                out.append(value)
            elif key != "action":
                out += _texts(value)
    elif isinstance(node, list):
        for value in node:
            out += _texts(value)
    return out


def _patel():
    client = fakes.load_client("C02")
    return client, fakes.chair_propose(client, []), {r.id: r.source for r in client.rules}


def test_repaired_receipt_card():
    """Big verdict, the failed rule in the client's words with actual vs limit, before → after, receipt id."""
    client, proposal, sources = _patel()
    receipt = fakes.referee(client, proposal)
    assert receipt.verdict == "VIOLATIONS_REPAIRED"
    card = receipt_card(receipt, before=proposal.weights, rule_sources=sources, client_name=client.name)
    assert card.metadata["is_terminal"] == "true"  # informational: nothing to click
    payload = _payload(card)
    texts = _texts(payload)
    assert payload["root"]["children"][0]["children"][0] == {"type": "heading", "value": "🛠️ The Referee repaired the portfolio", "level": 1}
    assert f"R4: “{sources['R4']}”" in texts
    assert "Actual 40.0%" in texts and "Limit 35.0%" in texts
    assert "UNH  10.0% → 5.0%" in texts and "KO  0.0% → 5.0%" in texts  # every changed position shows
    assert any(receipt.receipt_id in t for t in texts)
    assert "Conflict" not in texts


def test_infeasible_receipt_card_shows_conflict_and_cheapest_fix():
    client = fakes.load_client("C03")
    sources = {r.id: r.source for r in client.rules}
    proposal = fakes.chair_propose(client, [])
    receipt = fakes.referee(client, proposal)
    assert receipt.verdict == "RULES_INFEASIBLE"
    texts = _texts(_payload(receipt_card(receipt, before=proposal.weights, rule_sources=sources)))
    assert "Conflict" in texts and receipt.conflict_explain in texts
    assert "Cheapest fix" in texts and receipt.cheapest_relaxation[0].explain in texts
    for rid in receipt.conflict_set:
        assert any(t.startswith(f"{rid}: “") for t in texts)
    assert "Proposed holdings" in texts and not any("→" in t for t in texts if t[:1].isupper() and "%" in t)


def test_pass_receipt_card_and_holdings_counts():
    """PASS: no failed-rules section; holdings counts show as stocks, not percentages."""
    client, proposal, sources = _patel()
    receipt = fakes._pass_receipt("C02")
    texts = _texts(_payload(receipt_card(receipt, before=proposal.weights, rule_sources=sources)))
    assert "✅ Compliant" in texts and "PASS" in texts and "Top holdings" in texts
    assert not any(t.startswith("Failed rules") for t in texts)

    failing = receipt.model_copy(deep=True)
    failing.checks[4] = failing.checks[4].model_copy(update={"passed": False, "actual": 9, "limit": 8})
    texts = _texts(_payload(receipt_card(failing, rule_sources=sources)))
    assert "Actual 9 stocks" in texts and "Limit 8 stocks" in texts


def test_client_picker_card():
    """One row per client; 'Build portfolio' sends 'Build a portfolio for <id>' back to the Chair."""
    clients = load_clients()
    card = client_picker_card(clients)
    assert "is_terminal" not in card.metadata  # it needs a click, so the drawer must open
    rows = _payload(card)["root"]["children"][0]["items"]
    assert len(rows) == len(clients)
    for client, row in zip(clients, rows):
        button = row["children"][-1]
        assert button["label"] == "Build portfolio"
        assert button["action"]["selection"] == row["action"]["selection"] == build_selection(client.client_id)
        assert button["action"]["selection"]["message"] == f"Build a portfolio for {client.client_id}"


def test_card_click_comes_back_as_a_build_request():
    """Direct @mention delivers the selection as JSON; the Chair turns it back into a request."""
    clicked = json.dumps(build_selection("C02"))
    assert selection_text(clicked) == "Build a portfolio for C02"
    assert selection_text("@swarmfolio-chair " + clicked) == "Build a portfolio for C02"
    assert find_client(selection_text(clicked)).client_id == "C02"
    # Planner prose, normal chat and pasted client JSON pass through untouched.
    prose = "The user picked Build portfolio for client C02."
    assert selection_text(prose) == prose
    assert selection_text("list clients") == "list clients"
    pasted = json.dumps({"client_id": "C02", "proposal": {}})
    assert selection_text(pasted) == pasted


def test_price_tags_card():
    client = fakes.load_client("C02")
    prices = rule_prices(client)
    card = price_tags_card(client, prices)
    assert card.metadata["is_terminal"] == "true"
    payload = _payload(card)
    texts = _texts(payload)
    assert len(payload["root"]["children"][0]["items"]) == len(client.rules)
    for p in prices:
        assert f"{p.rule_id}: “{p.source}”" in texts
    for p in prices:  # utility_cost_pts is already in points (the same number the text reply shows)
        assert (f"costs {p.utility_cost_pts:.2f} pts/yr" if p.binds else "free") in texts
        if p.binds:
            assert f"costs {p.utility_cost_pts:.2f} points" in p.explain


def test_say_sends_text_then_card_then_end_session():
    """The plain text always goes first (the fallback), then the card, then end-session."""
    sent = []

    class Ctx:
        async def send(self, sender, msg):
            sent.append(msg)

    client, proposal, sources = _patel()
    card = receipt_card(fakes.referee(client, proposal), before=proposal.weights, rule_sources=sources)
    asyncio.run(say(Ctx(), "agent1qsomeone", "plain receipt", end=True, card=card))
    assert [c.type for c in sent[0].content] == ["text", "metadata", "end-session"]
    assert sent[0].content[0].text == "plain receipt"
    asyncio.run(say(Ctx(), "agent1qsomeone", "no card"))
    assert [c.type for c in sent[1].content] == ["text"]


def test_bad_or_huge_cards_fall_back_to_text_only():
    """try_card returns None (text-only reply) if building fails or the payload is over 64 KB."""
    assert try_card(receipt_card, None) is None
    huge = {"root": {"type": "text", "value": "x" * (MAX_PAYLOAD_BYTES + 1)}}
    assert try_card(card_metadata, "custom", huge, True) is None
