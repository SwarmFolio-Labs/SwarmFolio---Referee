"""
Plain-English rules -> Rule objects (the 10 types in referee/schema.py).

An LLM reads the paragraph and proposes rules; this module then checks every proposal in code
and keeps only what maps exactly onto a rule type. Anything it can't map (unknown ticker or
sector, a percentage outside 0-100%, a quote that isn't in the text, a rule type the Referee
doesn't have) comes back in `unmapped` with the reason, so nothing is guessed.

The LLM layer (committee/llm.py) is imported only inside extract_rules(), so importing this
module stays pure math (the public API image has no LLM code).
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from referee.market import load_sectors
from referee.schema import Client, Rule, RuleType

# What each rule type's params must look like: (key, kind). "frac" = a fraction 0-1.
PARAMS: dict[str, tuple[tuple[str, str], ...]] = {
    "max_weight": (("ticker", "ticker_or_all"), ("max", "frac")),
    "min_weight": (("ticker", "ticker"), ("min", "frac")),
    "exclude": (("tickers", "tickers"),),
    "sector_max": (("sector", "sector"), ("max", "frac")),
    "sector_min": (("sector", "sector"), ("min", "frac")),
    "max_holdings": (("k", "count"),),
    "min_holdings": (("k", "count"),),
    "buy_in": (("min", "frac"),),
    "max_volatility": (("max", "frac"),),
    "max_turnover": (("max", "frac"),),
}
DEFAULT_PRIORITY = 5


# ---------- What the LLM fills in ----------

class DraftRule(BaseModel):
    type: RuleType
    params: dict
    source: str = Field(description="The exact words from the text this rule comes from, copied verbatim")
    hard: bool = Field(False, description="True only if the text says it can never be broken (e.g. 'never', 'no')")


class DraftPhrase(BaseModel):
    text: str = Field(description="The exact words from the text")
    reason: str = Field(description="Why it doesn't fit any of the 10 rule types")


class Draft(BaseModel):
    rules: list[DraftRule] = []
    unmapped: list[DraftPhrase] = []


# ---------- What extract_rules returns ----------

class Unmapped(BaseModel):
    text: str
    reason: str


class Extraction(BaseModel):
    rules: list[Rule]
    unmapped: list[Unmapped]


def _system_prompt(sectors: dict[str, str]) -> str:
    by_sector: dict[str, list[str]] = {}
    for ticker, sector in sectors.items():
        by_sector.setdefault(sector, []).append(ticker)
    universe = "; ".join(f"{s}: {', '.join(ts)}" for s, ts in by_sector.items())
    return (
        "You turn an investor's plain-English portfolio rules into structured rules. Use ONLY these 10 types "
        "(fractions are 0-1, so 30% = 0.30):\n"
        '- max_weight {"ticker": TICKER or "*" for every stock, "max": fraction}\n'
        '- min_weight {"ticker": TICKER, "min": fraction}\n'
        '- exclude {"tickers": [TICKER, ...]}  (for a banned sector, list that sector\'s tickers)\n'
        '- sector_max {"sector": SECTOR, "max": fraction}\n'
        '- sector_min {"sector": SECTOR, "min": fraction}\n'
        '- max_holdings {"k": integer}   - min_holdings {"k": integer}\n'
        '- buy_in {"min": fraction}  (smallest allowed position size)\n'
        '- max_volatility {"max": fraction}  (annual volatility)\n'
        '- max_turnover {"max": fraction}  (share of capital traded vs. current holdings)\n'
        f"Stocks by sector: {universe}.\n"
        "For each rule, `source` must be the exact words from the text, copied character for character. "
        "If a phrase is a rule that doesn't fit these types or stocks (another asset, a return target, ESG "
        "scores, dates...), put it in `unmapped` with the reason. Never invent a number the text doesn't give. "
        "Map EVERY rule, even if two rules contradict each other: never drop or unmap a rule because of a "
        "conflict, since the Referee proves conflicts itself."
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _check_params(rule_type: str, params: dict, sectors: dict[str, str]) -> tuple[dict | None, str]:
    """Return (clean params, "") or (None, reason)."""
    spec = PARAMS[rule_type]
    keys = {k for k, _ in spec}
    # Small LLMs often nest the params under the type name: {"max_weight": {"ticker": "*", "max": 0.4}}.
    # Unwrapping that one exact shape is safe: the inner values still go through every check below.
    if len(params) == 1 and rule_type in params and isinstance(params[rule_type], dict):
        params = params[rule_type]
    if set(params) != keys:
        return None, f"{rule_type} needs exactly {sorted(keys)}, got {sorted(params)}"
    clean = {}
    for key, kind in spec:
        value = params[key]
        if kind == "frac":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                return None, f"{key} must be a fraction between 0 and 1, got {value!r}"
            clean[key] = float(value)
        elif kind == "count":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                return None, f"{key} must be a whole number of holdings, got {value!r}"
            clean[key] = value
        elif kind in ("ticker", "ticker_or_all"):
            t = str(value).upper()
            if not (t in sectors or (kind == "ticker_or_all" and t == "*")):
                return None, f"unknown ticker {value!r}"
            clean[key] = t
        elif kind == "tickers":
            tickers = [str(t).upper() for t in value] if isinstance(value, list) else []
            unknown = [t for t in tickers if t not in sectors]
            if not tickers or unknown:
                return None, f"unknown tickers {unknown or value!r}"
            clean[key] = sorted(set(tickers))
        elif kind == "sector":
            match = next((s for s in set(sectors.values()) if s.lower() == str(value).lower()), None)
            if match is None:
                return None, f"unknown sector {value!r} (known: {', '.join(sorted(set(sectors.values())))})"
            clean[key] = match
    return clean, ""


def validate_draft(text: str, draft: Draft, sectors: dict[str, str] | None = None) -> Extraction:
    """Keep the draft rules that map exactly onto the Referee's rule types; flag the rest."""
    sectors = sectors or load_sectors()
    haystack = _normalize(text)
    rules: list[Rule] = []
    unmapped = [Unmapped(text=p.text, reason=p.reason) for p in draft.unmapped]
    for d in draft.rules:
        source = d.source.strip()
        if not source or _normalize(source) not in haystack:
            unmapped.append(Unmapped(text=source, reason="this quote isn't in the text, so it may be made up"))
            continue
        params, problem = _check_params(d.type, d.params, sectors)
        if params is None:
            unmapped.append(Unmapped(text=source, reason=problem))
            continue
        try:
            rules.append(Rule(id=f"R{len(rules) + 1}", type=d.type, params=params,
                              priority=DEFAULT_PRIORITY, hard=d.hard, source=source))
        except ValidationError as e:
            unmapped.append(Unmapped(text=source, reason=str(e)))
    return Extraction(rules=rules, unmapped=unmapped)


def extract_rules(text: str) -> Extraction:
    """Ask the LLM for rules (committee/llm.py complete_json), then validate them in code."""
    from committee.llm import complete_json  # lazy: keeps referee/ importable without LLM code

    sectors = load_sectors()
    draft = complete_json("chair", _system_prompt(sectors), f"Rules:\n{text.strip()}", Draft)
    return validate_draft(text, draft, sectors)


# ---------- Chat helpers: "check NVDA 50, JNJ 30, KO 20 against: ..." ----------

_PAIR = re.compile(r"\b([A-Za-z]{1,5})\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%?")


def split_weights(text: str, tickers: set[str] | None = None) -> tuple[dict[str, float] | None, str]:
    """Split a chat message into (weights or None, rules text).

    Weights come before "against" (or the first ":"), as TICKER NUMBER pairs. Numbers that add up
    to about 100 are percentages; numbers that add up to about 1 are fractions.
    """
    tickers = tickers or set(load_sectors())
    m = re.search(r"\bagainst\b\s*:?", text, re.IGNORECASE) or re.search(r":", text)
    if not m:
        return None, text.strip()
    head, rules_text = text[:m.start()], text[m.end():].strip()
    pairs = [(t.upper(), float(n)) for t, n in _PAIR.findall(head) if t.upper() in tickers]
    if not pairs:
        return None, text.strip()
    weights: dict[str, float] = {}
    for t, n in pairs:
        weights[t] = weights.get(t, 0.0) + n
    total = sum(weights.values())
    if total > 1.5:  # percentages
        weights = {t: w / 100 for t, w in weights.items()}
    return weights, rules_text


def chat_client(rules: list[Rule], tickers: list[str] | None = None) -> Client:
    """A one-off client for rules pasted in chat; it may hold any stock in the data."""
    return Client(client_id="CHAT", name="Rules from chat", story="Rules pasted in plain English.",
                  universe=sorted(tickers or load_sectors()), rules=rules)


def describe(extraction: Extraction, client: Client | None = None) -> str:
    """Plain text: the rules as read, anything not mapped, and (given a client) whether they can all be met."""
    lines = ["I read these rules:"] if extraction.rules else ["I couldn't find any rule I can check."]
    lines += [f"• {r.id} ({r.type}): \"{r.source}\"" for r in extraction.rules]
    if extraction.unmapped:
        lines.append("Not used (I won't guess):")
        lines += [f"• \"{u.text}\": {u.reason}" for u in extraction.unmapped]
    if client is not None and extraction.rules:
        from referee.conflicts import explain_conflict, find_conflicts
        from referee.solver import is_feasible
        if is_feasible(client):
            lines.append("✅ Some portfolio can meet all of them.")
        else:
            lines.append(f"⛔ No portfolio can meet all of them: {explain_conflict(client, find_conflicts(client))}")
    return "\n".join(lines)
