"""
The three analysts (MASTER 7.1, 7.2): Macro, Fundamentals and Risk.

Python computes the numbers; the LLM only reads them and writes an opinion. Each analyst
sees its own data block plus the client's story and rules (in the client's own words).
"""

import json
import os

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


# ---------- Prompts (MASTER 7.2) ----------

def _system(agent: str, schema) -> str:
    return (f"You are the {agent.capitalize()} analyst on an investment committee for a financial advisor. "
            "Use ONLY the data provided. Be specific and brief. "
            f"Reply with JSON matching this schema: {json.dumps(schema.model_json_schema())}.")


def _client_text(story: str, rules_text: list[str]) -> str:
    return "Client story: " + story + "\nClient rules:\n" + "\n".join(f"- {r}" for r in rules_text)


# ---------- The two brain functions (contract.py) ----------

def analyze(agent: str, req: AnalysisRequest) -> Memo:
    """One analyst ("macro", "fundamentals" or "risk") writes a memo for this client."""
    if agent not in ANALYSTS:
        raise ValueError(f"Unknown analyst {agent!r} (use one of {ANALYSTS})")
    client = load_client(req.client_id)
    user = (f"{_client_text(req.client_story, req.rules_text)}\n\n"
            f"Tickers you may talk about: {', '.join(client.universe)}\n\n"
            f"Your data:\n{DATA_BLOCKS[agent](client.universe)}\n\n"
            f"Set \"agent\" to \"{agent}\".")
    memo = llm.complete_json("analyst", _system(agent, Memo), user, Memo)

    # Keep the memo honest: our name on it, and only tickers this client can actually buy.
    universe = set(client.universe)
    return memo.model_copy(update={
        "agent": agent,
        "favor": [t for t in memo.favor if t in universe],
        "avoid": [t for t in memo.avoid if t in universe],
    })


def review(agent: str, req: ReviewRequest) -> Stance:
    """One analyst responds to the Referee's failed checks: concede, defend or modify."""
    if agent not in ANALYSTS:
        raise ValueError(f"Unknown analyst {agent!r} (use one of {ANALYSTS})")
    failures = "\n".join(f"- {f}" for f in req.failures) or "- none"
    user = (f"Round {req.round}. The committee's portfolio: {json.dumps(req.proposal.weights)}\n"
            f"The independent Referee checked the committee's portfolio. These rules failed:\n{failures}\n"
            f"{req.conflict_explain}\n"
            "Decide: concede (accept a change), defend (keep your view, explain why it doesn't break the rules), "
            f"or modify (propose a different change). Set \"agent\" to \"{agent}\".")
    stance = llm.complete_json("analyst", _system(agent, Stance), user, Stance)
    return stance.model_copy(update={"agent": agent})
