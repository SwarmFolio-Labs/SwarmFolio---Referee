"""
The three analysts (MASTER 7.1, 7.2): Macro, Fundamentals and Risk.

Python computes the numbers; the LLM only reads them and writes an opinion. Each analyst
sees its own data block plus the client's story and rules (in the client's own words).
"""

import json
import os
import re

from committee import llm
from models import AnalysisRequest, Memo, ReviewRequest, Stance
from referee import market
from referee.schema import Client

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ANALYSTS = ("macro", "fundamentals", "risk")


def load_client(client_id: str) -> Client:
    """Read data/clients/<client_id>.json (the request only carries the id, not the universe)."""
    with open(os.path.join(DATA_DIR, "clients", f"{client_id}.json")) as f:
        return Client.model_validate(json.load(f))


def _pct(x: float | None) -> str:
    """0.123 -> '12.3%', None -> 'n/a'."""
    return "n/a" if x is None else f"{x * 100:.1f}%"


# ---------- Data blocks (numbers computed in Python) ----------

def macro_data(universe: list[str]) -> str:
    """Sector and SPY returns over 1/3/6 months, plus the best and worst 5 stocks over 3 months."""
    lines = [f"As of {market.as_of()}.", "Returns by sector (1m / 3m / 6m):"]
    for sector, r in market.sector_returns(universe).items():
        lines.append(f"- {sector}: {_pct(r['ret_1m'])} / {_pct(r['ret_3m'])} / {_pct(r['ret_6m'])}")

    stats = market.stock_stats(universe)
    by_3m = sorted(universe, key=lambda t: stats[t]["ret_3m"], reverse=True)
    lines.append("Best 5 over 3 months: " + ", ".join(f"{t} {_pct(stats[t]['ret_3m'])}" for t in by_3m[:5]))
    lines.append("Worst 5 over 3 months: " + ", ".join(f"{t} {_pct(stats[t]['ret_3m'])}" for t in by_3m[-5:]))
    return "\n".join(lines)


def fundamentals_data(universe: list[str]) -> str:
    """Per ticker: trailing P/E, revenue growth, profit margin (missing -> 'n/a')."""
    with open(os.path.join(DATA_DIR, "fundamentals.json")) as f:
        fund = json.load(f)
    lines = [f"As of {fund['as_of']}. Ticker: P/E, revenue growth, profit margin"]
    for t in universe:
        row = fund["tickers"].get(t, {})
        pe = row.get("pe")
        pe_text = "n/a" if pe is None else f"{pe:.1f}"
        lines.append(f"- {t}: P/E {pe_text}, growth {_pct(row.get('revenue_growth'))}, "
                     f"margin {_pct(row.get('profit_margin'))}")
    return "\n".join(lines)


def risk_data(universe: list[str]) -> str:
    """Per ticker: annual volatility, 3-year max drawdown, correlation to SPY; plus the 3 most correlated pairs."""
    stats = market.stock_stats(universe)
    lines = ["Ticker: annual volatility, max drawdown (3y), correlation to SPY"]
    for t in universe:
        s = stats[t]
        lines.append(f"- {t}: vol {_pct(s['vol'])}, drawdown {_pct(s['max_drawdown'])}, corr {s['corr_spy']:.2f}")

    # Every pair once (i < j), sorted by how closely the two stocks move together.
    corr = market.daily_returns()[universe].corr()
    pairs = []
    for i, a in enumerate(universe):
        for b in universe[i + 1:]:
            pairs.append((float(corr.loc[a, b]), a, b))
    pairs.sort(reverse=True)
    lines.append("Most correlated pairs: " + ", ".join(f"{a}-{b} {c:.2f}" for c, a, b in pairs[:3]))
    return "\n".join(lines)


DATA_BLOCKS = {"macro": macro_data, "fundamentals": fundamentals_data, "risk": risk_data}


def holdings_text(client: Client) -> str:
    """
    What the client owns today, plus how the Referee counts turnover (if a rule limits it).
    Without this, nobody on the committee can know how far a new portfolio moves from today.
    """
    if client.current_weights:
        held = sorted(client.current_weights.items(), key=lambda x: -x[1])
        text = "Current holdings: " + ", ".join(f"{t} {_pct(w)}" for t, w in held) + "."
    else:
        text = "Current holdings: none (starting from cash)."
    if any(r.type == "max_turnover" for r in client.rules):
        text += ("\nTurnover = the sum over every ticker of |new weight - current weight|. Buys AND sells both "
                 "count, so moving 10% from NVDA into JPM is 20% turnover. A ticker not held today counts as 0%.")
    return text


# ---------- Prompts (MASTER 7.2) ----------

def _system(agent: str, schema) -> str:
    return (f"You are the {agent.capitalize()} analyst on an investment committee for a financial advisor. "
            "Use ONLY the data provided. Be specific and brief. "
            "In favor and avoid, list bare ticker symbols only (like [\"JNJ\", \"MSFT\"]); "
            "put every explanation in reasons, keyed by ticker. "
            f"Reply with JSON matching this schema: {json.dumps(schema.model_json_schema())}.")


def _client_text(story: str, rules_text: list[str]) -> str:
    return "Client story: " + story + "\nClient rules:\n" + "\n".join(f"- {r}" for r in rules_text)


# ---------- The two brain functions (contract.py) ----------

def analyze(agent: str, req: AnalysisRequest) -> Memo:
    """One analyst ("macro", "fundamentals" or "risk") writes a memo for this client."""
    if agent not in ANALYSTS:
        raise ValueError(f"Unknown analyst {agent!r} (use one of {ANALYSTS})")
    client = load_client(req.client_id)
    user = (f"{_client_text(req.client_story, req.rules_text)}\n{holdings_text(client)}\n\n"
            f"Tickers you may talk about: {', '.join(client.universe)}\n\n"
            f"Your data:\n{DATA_BLOCKS[agent](client.universe)}\n\n"
            f"Set \"agent\" to \"{agent}\".")
    memo = llm.complete_json("analyst", _system(agent, Memo), user, Memo)

    # Keep the memo honest: our name on it, and only tickers this client can actually buy.
    # LLMs often write "GOOGL: cheap at 17 P/E" instead of "GOOGL", so pull the tickers out.
    reasons = dict(memo.reasons)
    return memo.model_copy(update={
        "agent": agent,
        "favor": _ticker_list(memo.favor, client.universe, reasons),
        "avoid": _ticker_list(memo.avoid, client.universe, reasons),
        "reasons": reasons,
    })


def _tickers_in(item: str, universe: list[str]) -> list[str]:
    """
    The universe tickers an item is about. "XOM/CVX: prohibited" -> ["XOM", "CVX"].
    We look before the first ":", "(" or "—" (where the ticker usually is), and only if
    nothing is there do we search the whole item.
    """
    cut = len(item)
    for sep in (":", "(", "—"):
        pos = item.find(sep)
        if pos != -1:
            cut = min(cut, pos)
    allowed = set(universe)
    found = [w for w in re.findall(r"\b[A-Z]+\b", item[:cut]) if w in allowed]
    if not found:
        found = [w for w in re.findall(r"\b[A-Z]+\b", item) if w in allowed]
    return found


def _ticker_list(items: list[str], universe: list[str], reasons: dict[str, str]) -> list[str]:
    """
    Turn the LLM's favor/avoid items into clean ticker symbols (no duplicates, universe only).
    If an item carried an explanation and that ticker has no reason yet, keep the text as its reason.
    """
    tickers: list[str] = []
    for item in items:
        for t in _tickers_in(item, universe):
            if t not in tickers:
                tickers.append(t)
            if item.strip() != t and t not in reasons:
                reasons[t] = item.strip()
    return tickers


def review(agent: str, req: ReviewRequest) -> Stance:
    """One analyst responds to the Referee's failed checks: concede, defend or modify."""
    if agent not in ANALYSTS:
        raise ValueError(f"Unknown analyst {agent!r} (use one of {ANALYSTS})")
    failures = "\n".join(f"- {f}" for f in req.failures) or "- none"
    client = load_client(req.client_id)
    user = (f"{holdings_text(client)}\n"
            f"Round {req.round}. The committee's portfolio: {json.dumps(req.proposal.weights)}\n"
            f"The independent Referee checked the committee's portfolio. These rules failed:\n{failures}\n"
            f"{req.conflict_explain}\n"
            "Decide: concede (accept a change), defend (keep your view, explain why it doesn't break the rules), "
            f"or modify (propose a different change). Set \"agent\" to \"{agent}\".")
    stance = llm.complete_json("analyst", _system(agent, Stance), user, Stance)
    return stance.model_copy(update={"agent": agent})
