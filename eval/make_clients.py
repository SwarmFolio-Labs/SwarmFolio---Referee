"""
Generate the hard synthetic clients C10-C27 (MASTER 10.1, task B2).

    python -m eval.make_clients          # writes data/clients/C10.json ... C27.json

15 feasible clients (C10-C24) and 3 with a planted conflict (C25-C27). They are
built to be HARD for an LLM: the limits sit just above what the math allows, so
you have to calculate, not just read.

  (a) Volatility caps 0.5-1.0 point above the lowest volatility the solver can
      reach under the client's other rules (we compute that floor with SCIP).
  (b) Interlocking sector floors/caps and single-name caps (e.g. "Financials at
      least 25%" but "JPM and GS at most 8% each", so BAC has to carry the rest).
  (c) max_holdings + buy_in together (few names, each one big).
  (d) Legacy current_weights + a turnover cap a few points above the least
      selling the other rules force.

Every client is checked before it's written: feasible clients must pass
referee.solver.is_feasible; planted clients must fail it AND
referee.conflicts.find_conflicts must return exactly planted_conflict. If a random
draw doesn't meet that, we draw again (same seed -> same clients every run).
C01-C04 and C91-C94 are hand-made and never touched here.
"""

import json
import math
import os
from collections.abc import Callable

import cvxpy as cp
import numpy as np

from referee.conflicts import find_conflicts
from referee.schema import Client, Rule
from referee.solver import build_problem, is_feasible

SEED = 20261018
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENTS_DIR = os.path.join(ROOT, "data", "clients")
UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "JPM", "GS", "BAC", "JNJ",
    "UNH", "PFE", "PG", "KO", "WMT", "XOM", "CVX", "GLD", "TLT",
]
SCIP_PARAMS = {"limits/time": 15, "limits/gap": 1e-3}
VOL_MARGIN = (0.006, 0.009)        # cap = floor + 0.6..0.9 points, then rounded to 0.1 point
TURNOVER_MARGIN = (0.03, 0.07)     # cap = least forced turnover + 3..7 points
MAX_ATTEMPTS = 25

# Realistic synthetic surnames; none overlaps with C01-C04 / C91-C94 (the chat agent matches by name).
SURNAMES = [
    "Adebayo", "Kowalski", "Ramanathan", "Castellanos", "Brennan", "Takahashi",
    "Oyelaran", "Fitzgerald", "Petrova", "Delgado", "Abernathy", "Sorensen",
    "Mbeki", "Vasquez", "Holloway", "Iyer", "Kaczmarek", "Beaumont",
]
# How each archetype is addressed, so names match the pronouns in its story.
TITLES = {"f": ["Ms."], "m": ["Mr."], "dr": ["Dr."], "any": ["Ms.", "Mr."]}


def pct(x: float) -> str:
    """0.25 -> '25%', 0.134 -> '13.4%'."""
    return f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"


def u(rng, lo: float, hi: float, step: float = 0.01) -> float:
    """A random number in [lo, hi] rounded to `step` (so limits look like real ones: 25%, not 24.731%)."""
    return round(round(float(rng.uniform(lo, hi)) / step) * step, 4)


# ---------- Rule builders (id is filled in later, in order) ----------

def rule(type_: str, params: dict, source: str, priority: int = 4, hard: bool = False) -> dict:
    return {"type": type_, "params": params, "priority": priority, "hard": hard, "source": source}


def vol_rule(source: str) -> dict:
    """A volatility cap whose number is computed later. `source` has a {cap} placeholder."""
    return rule("max_volatility", {"max": None}, source, priority=6)


def turnover_rule(source: str) -> dict:
    """A turnover cap whose number is computed later. `source` has a {cap} placeholder."""
    return rule("max_turnover", {"max": None}, source, priority=7)


# ---------- Solver helpers ----------

def _solve_min(client: Client, rule_ids: list[str], objective) -> float:
    problem, _ = build_problem(client, rule_ids, objective=objective)
    problem.solve(solver=cp.SCIP, scip_params=SCIP_PARAMS)
    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        raise ValueError(f"{client.client_id}: minimization status {problem.status}")
    return float(problem.value)


def min_volatility(client: Client) -> float:
    """Lowest volatility any portfolio can have under the client's rules, ignoring their max_volatility rule."""
    ids = [r.id for r in client.rules if r.type != "max_volatility"]
    return _solve_min(client, ids, lambda v: cp.norm(v.market.L.T @ v.w, 2))


def min_turnover(client: Client) -> float:
    """Least turnover (sum of |w - current|) the client's other rules force, ignoring vol and turnover caps."""
    ids = [r.id for r in client.rules if r.type not in ("max_volatility", "max_turnover")]
    c = np.array([client.current_weights.get(t, 0.0) for t in client.universe])
    return _solve_min(client, ids, lambda v: cp.norm(v.w - c, 1))


# ---------- The archetypes ----------
# Each returns (story, current_weights, rule drafts). Random numbers come from rng, so a
# retry gives a fresh draw. Order of rule drafts = R1, R2, ...

def c10_nurse(rng):
    hc_min = u(rng, 0.22, 0.28)
    jnj_cap = u(rng, 0.08, 0.10)
    cap = u(rng, 0.14, 0.16)
    return (
        "ICU nurse in her 40s who trusts the healthcare industry she works in, but wants a calm ride and no fossil fuels.",
        {},
        [
            rule("sector_min", {"sector": "Healthcare", "min": hc_min},
                 f"I want at least {pct(hc_min)} in healthcare; it's the industry I know best.", 5),
            rule("max_weight", {"ticker": "JNJ", "max": jnj_cap},
                 f"Don't let Johnson & Johnson go over {pct(jnj_cap)}, my hospital already buys a lot from them."),
            rule("max_weight", {"ticker": "*", "max": cap}, f"Nothing bigger than {pct(cap)} in any one name.", 5),
            rule("exclude", {"tickers": ["XOM", "CVX"]}, "No oil companies, period.", 9, True),
            vol_rule("I don't want the portfolio to swing more than {cap} in a year."),
        ],
    )


def c11_engineer(rng):
    tech_min = u(rng, 0.38, 0.45)
    tech_max = round(tech_min + u(rng, 0.08, 0.12), 2)
    nvda_cap = u(rng, 0.06, 0.09)
    cap = u(rng, 0.16, 0.20)
    return (
        "29-year-old chip designer who wants a real tech tilt but already has plenty of NVDA exposure through his stock grants.",
        {},
        [
            rule("sector_min", {"sector": "Tech", "min": tech_min}, f"At least {pct(tech_min)} in tech, I believe in it.", 5),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"But no more than {pct(tech_max)} tech overall.", 4),
            rule("max_weight", {"ticker": "NVDA", "max": nvda_cap},
                 f"Keep NVDA under {pct(nvda_cap)}, my RSUs are already NVDA.", 6),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single holding above {pct(cap)}.", 5),
            rule("exclude", {"tickers": ["GLD"]}, "No gold, it doesn't produce anything.", 8, True),
            vol_rule("Still, keep annual volatility at {cap} or less."),
        ],
    )


def c12_retired_couple(rng):
    k = int(rng.integers(5, 7))
    buy = u(rng, 0.11, 0.14)
    fin_min = u(rng, 0.18, 0.25)
    con_min = u(rng, 0.20, 0.28)
    tech_max = u(rng, 0.15, 0.22)
    return (
        "Retired couple who want a short list of names they can follow in the newspaper, leaning on banks and household brands.",
        {},
        [
            rule("max_holdings", {"k": k}, f"We can only keep track of {k} companies at most.", 4),
            rule("buy_in", {"min": buy}, f"If we own something, it should be at least {pct(buy)} of the money.", 3),
            rule("sector_min", {"sector": "Financials", "min": fin_min}, f"Banks at least {pct(fin_min)}.", 4),
            rule("sector_min", {"sector": "Consumer", "min": con_min},
                 f"At least {pct(con_min)} in everyday brands like Procter & Gamble or Walmart.", 4),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech no more than {pct(tech_max)}.", 4),
            rule("exclude", {"tickers": ["GLD", "TLT"]}, "Stocks only, no gold or bond funds.", 8, True),
        ],
    )


def c13_dentist(rng):
    k = int(rng.integers(5, 7))
    buy = u(rng, 0.12, 0.15)
    cap = u(rng, 0.24, 0.28)
    tech_max = u(rng, 0.25, 0.32)
    return (
        "Dentist with a busy practice who wants a concentrated portfolio of a few big positions, but with guardrails on risk.",
        {},
        [
            rule("max_holdings", {"k": k}, f"I want {k} names or fewer.", 3),
            rule("buy_in", {"min": buy}, f"Every position at least {pct(buy)}, otherwise why bother.", 3),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single stock above {pct(cap)}.", 5),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech capped at {pct(tech_max)}.", 4),
            vol_rule("And annual volatility no higher than {cap}."),
        ],
    )


def c14_esg_ten_rules(rng):
    hc_min = u(rng, 0.15, 0.20)
    tech_min = u(rng, 0.20, 0.25)
    tech_max = round(tech_min + u(rng, 0.08, 0.12), 2)
    cap = u(rng, 0.14, 0.17)
    aapl_cap = u(rng, 0.06, 0.08)
    k_min = int(rng.integers(8, 10))
    buy = u(rng, 0.04, 0.06)
    return (
        "Climate-policy researcher with a long list of values-based rules who still wants a sensible, low-swing portfolio.",
        {},
        [
            rule("exclude", {"tickers": ["XOM", "CVX"]}, "No fossil fuel producers.", 10, True),
            rule("exclude", {"tickers": ["GLD"]}, "No gold, mining is too destructive.", 8, True),
            rule("sector_min", {"sector": "Healthcare", "min": hc_min}, f"At least {pct(hc_min)} in healthcare.", 4),
            rule("sector_min", {"sector": "Tech", "min": tech_min}, f"Tech at least {pct(tech_min)}, clean energy needs chips.", 4),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"But tech at most {pct(tech_max)}.", 4),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single company above {pct(cap)}.", 5),
            rule("max_weight", {"ticker": "AAPL", "max": aapl_cap},
                 f"Apple at most {pct(aapl_cap)}, I worry about its supply chain.", 4),
            rule("min_holdings", {"k": k_min}, f"Spread it across at least {k_min} holdings.", 3),
            rule("buy_in", {"min": buy}, f"Nothing smaller than {pct(buy)}.", 3),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


def c15_founder_legacy(rng):
    tech_max = u(rng, 0.30, 0.38)
    msft_min = u(rng, 0.10, 0.14)
    cap = u(rng, 0.18, 0.22)
    return (
        "Early Microsoft employee whose money is almost all in big tech; wants to diversify but every sale triggers capital-gains tax.",
        {"MSFT": 0.40, "AAPL": 0.20, "GOOGL": 0.15, "NVDA": 0.10, "JPM": 0.10, "KO": 0.05},
        [
            turnover_rule("Don't trade more than {cap} of the portfolio, the tax bill would be brutal."),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Get tech down to {pct(tech_max)} or less.", 5),
            rule("min_weight", {"ticker": "MSFT", "min": msft_min},
                 f"Keep at least {pct(msft_min)} in Microsoft, it's where I made my career.", 6),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single stock above {pct(cap)}.", 5),
            rule("exclude", {"tickers": ["TLT"]}, "No bond funds.", 8, True),
        ],
    )


def c16_banker(rng):
    fin_min = u(rng, 0.24, 0.28)
    name_cap = u(rng, 0.07, 0.09)
    cap = round(fin_min - 2 * name_cap + u(rng, 0.03, 0.05), 2)  # BAC has to carry the rest of the floor
    con_min = u(rng, 0.18, 0.24)
    return (
        "Former regional-bank executive who wants a big financials stake but is wary of Wall Street investment banks.",
        {},
        [
            rule("sector_min", {"sector": "Financials", "min": fin_min}, f"At least {pct(fin_min)} in financials.", 5),
            rule("max_weight", {"ticker": "JPM", "max": name_cap}, f"JPMorgan no more than {pct(name_cap)}.", 4),
            rule("max_weight", {"ticker": "GS", "max": name_cap}, f"Goldman Sachs no more than {pct(name_cap)}, too much trading risk.", 4),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No position above {pct(cap)}.", 5),
            rule("sector_min", {"sector": "Consumer", "min": con_min}, f"Consumer brands at least {pct(con_min)}.", 4),
            rule("exclude", {"tickers": ["AMZN"]}, "No Amazon, it put my brother's store out of business.", 8, True),
        ],
    )


def c17_four_pillars(rng):
    k_max = int(rng.integers(7, 9))
    buy = u(rng, 0.07, 0.09)
    floors = {s: u(rng, 0.15, 0.20) for s in ("Tech", "Healthcare", "Financials", "Consumer")}
    return (
        "Teacher who read a 'four pillars' book and wants tech, healthcare, banks and consumer brands all represented, in a compact portfolio.",
        {},
        [
            rule("sector_min", {"sector": s, "min": m}, f"{s} at least {pct(m)}.", 4) for s, m in floors.items()
        ] + [
            rule("max_holdings", {"k": k_max}, f"No more than {k_max} holdings.", 3),
            rule("buy_in", {"min": buy}, f"Each position at least {pct(buy)}.", 3),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


def c18_oil_heir(rng):
    energy_max = u(rng, 0.15, 0.22)
    cap = u(rng, 0.20, 0.25)
    return (
        "Inherited a Texas family portfolio heavy in oil; wants less energy and lower risk without selling everything at once.",
        {"XOM": 0.30, "CVX": 0.25, "JPM": 0.15, "WMT": 0.10, "KO": 0.10, "GLD": 0.10},
        [
            turnover_rule("Turnover no more than {cap}; my father's accountant gets nervous otherwise."),
            rule("sector_max", {"sector": "Energy", "max": energy_max}, f"Energy down to {pct(energy_max)} or less.", 5),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single stock over {pct(cap)}.", 5),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


def c19_income_retiree(rng):
    con_min = u(rng, 0.20, 0.25)
    bond_min = u(rng, 0.15, 0.20)
    tlt_cap = round(bond_min + u(rng, 0.05, 0.08), 2)
    gold_max = u(rng, 0.03, 0.06)
    tech_max = u(rng, 0.20, 0.25)
    return (
        "Widowed retiree living off her savings who wants steady consumer staples, some bonds, and almost no gold.",
        {},
        [
            rule("sector_min", {"sector": "Consumer", "min": con_min}, f"At least {pct(con_min)} in household names.", 4),
            rule("sector_min", {"sector": "Bonds", "min": bond_min}, f"Bonds at least {pct(bond_min)}.", 5),
            rule("max_weight", {"ticker": "TLT", "max": tlt_cap}, f"But the bond fund no more than {pct(tlt_cap)}.", 4),
            rule("sector_max", {"sector": "Gold", "max": gold_max}, f"Gold at most {pct(gold_max)}.", 4),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech at most {pct(tech_max)}.", 4),
            vol_rule("I can't handle more than {cap} annual volatility."),
        ],
    )


def c20_concentrated(rng):
    k = 4
    buy = u(rng, 0.18, 0.22)
    cap = u(rng, 0.29, 0.32)
    tech_max = u(rng, 0.28, 0.32)
    return (
        "Hedge-fund analyst who wants exactly the conviction-portfolio style she uses at work: a handful of big, similar-sized bets.",
        {},
        [
            rule("max_holdings", {"k": k}, f"{k} stocks at most.", 4),
            rule("buy_in", {"min": buy}, f"Each one at least {pct(buy)}.", 3),
            rule("max_weight", {"ticker": "*", "max": cap}, f"None above {pct(cap)}.", 5),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech at most {pct(tech_max)}.", 4),
            rule("exclude", {"tickers": ["GLD", "TLT"]}, "Only operating companies, no funds.", 8, True),
        ],
    )


def c21_cleanup(rng):
    k = int(rng.integers(5, 7))
    buy = u(rng, 0.10, 0.13)
    return (
        "Small-business owner whose old advisor left him with ten tiny positions; wants a short, clean list without a big tax bill.",
        {"AAPL": 0.12, "MSFT": 0.12, "JPM": 0.11, "JNJ": 0.10, "PG": 0.10,
         "KO": 0.10, "XOM": 0.09, "GS": 0.09, "PFE": 0.09, "WMT": 0.08},
        [
            turnover_rule("Trade no more than {cap} of the portfolio."),
            rule("max_holdings", {"k": k}, f"Cut it down to {k} holdings or fewer.", 4),
            rule("buy_in", {"min": buy}, f"Every holding at least {pct(buy)}.", 3),
            rule("exclude", {"tickers": ["XOM"]}, "Sell the Exxon, I don't want it anymore.", 8, True),
        ],
    )


def c22_physician_nine_rules(rng):
    hc_max = u(rng, 0.08, 0.12)
    tech_max = u(rng, 0.25, 0.32)
    cap = u(rng, 0.12, 0.15)
    k_min = int(rng.integers(8, 10))
    buy = u(rng, 0.05, 0.07)
    fin_min = u(rng, 0.15, 0.20)
    con_min = u(rng, 0.20, 0.25)
    return (
        "Hospital physician who avoids healthcare stocks for conflict-of-interest reasons and wants a broad, stable portfolio.",
        {},
        [
            rule("sector_max", {"sector": "Healthcare", "max": hc_max},
                 f"Healthcare at most {pct(hc_max)}, I don't want conflicts of interest.", 7),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech at most {pct(tech_max)}.", 4),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single holding above {pct(cap)}.", 5),
            rule("min_holdings", {"k": k_min}, f"At least {k_min} holdings.", 3),
            rule("buy_in", {"min": buy}, f"No position smaller than {pct(buy)}.", 3),
            rule("sector_min", {"sector": "Financials", "min": fin_min}, f"Financials at least {pct(fin_min)}.", 4),
            rule("sector_min", {"sector": "Consumer", "min": con_min}, f"Consumer at least {pct(con_min)}.", 4),
            rule("exclude", {"tickers": ["XOM", "CVX"]}, "No oil.", 8, True),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


def c23_pension_rebalance(rng):
    fin_min = u(rng, 0.15, 0.20)
    hc_min = u(rng, 0.15, 0.20)
    tech_max = u(rng, 0.25, 0.30)
    cap = u(rng, 0.20, 0.24)
    return (
        "Union pension trustee rebalancing a tech-heavy fund toward banks and healthcare, under a strict trading budget.",
        {"NVDA": 0.20, "META": 0.15, "AAPL": 0.15, "AMZN": 0.15, "JPM": 0.10, "UNH": 0.10, "TLT": 0.15},
        [
            turnover_rule("The board allows at most {cap} turnover this year."),
            rule("sector_min", {"sector": "Financials", "min": fin_min}, f"Financials at least {pct(fin_min)}.", 4),
            rule("sector_min", {"sector": "Healthcare", "min": hc_min}, f"Healthcare at least {pct(hc_min)}.", 4),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech at most {pct(tech_max)}.", 5),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single holding above {pct(cap)}.", 5),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


def c24_gold_bug(rng):
    gold_min = u(rng, 0.10, 0.14)
    gld_cap = round(gold_min + u(rng, 0.02, 0.04), 2)
    k_max = int(rng.integers(7, 9))
    buy = u(rng, 0.06, 0.08)
    return (
        "Semi-retired contractor who distrusts the dollar: insists on gold and no Treasury bonds, but in a tidy, low-risk portfolio.",
        {},
        [
            rule("sector_min", {"sector": "Gold", "min": gold_min}, f"At least {pct(gold_min)} in gold.", 6),
            rule("max_weight", {"ticker": "GLD", "max": gld_cap}, f"But gold no more than {pct(gld_cap)}, my wife insists.", 4),
            rule("exclude", {"tickers": ["TLT"]}, "No government bonds.", 9, True),
            rule("max_holdings", {"k": k_max}, f"At most {k_max} holdings.", 3),
            rule("buy_in", {"min": buy}, f"No position under {pct(buy)}.", 3),
            vol_rule("Annual volatility at most {cap}."),
        ],
    )


# ---------- Planted conflicts ----------

def c25_planted_vol(rng):
    # Planted: R1 (Tech >= ~45%) + R5 (vol cap). The cap is set 0.3-0.5 points BELOW the lowest
    # volatility reachable with the Tech floor, but above the floor without it. So: drop either
    # rule and it's possible; keep both and it isn't. (Cap filled in by build_planted_vol.)
    tech_min = u(rng, 0.42, 0.48)
    cap = u(rng, 0.25, 0.30)
    return (
        "Startup founder who insists on a heavy tech allocation yet promised his spouse the portfolio would be 'boring'.",
        {},
        [
            rule("sector_min", {"sector": "Tech", "min": tech_min}, f"At least {pct(tech_min)} in tech, non-negotiable.", 6),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single stock above {pct(cap)}.", 5),
            rule("exclude", {"tickers": ["XOM", "CVX"]}, "No oil.", 8, True),
            rule("min_holdings", {"k": 5}, "At least 5 holdings.", 3),
            vol_rule("Annual volatility at most {cap}, I promised my wife."),
        ],
    )


def c26_planted_holdings(rng):
    # Planted: R2 (min_holdings k) + R3 (buy_in b) with k * b > 100%:
    # e.g. 8 holdings x 13% each = 104% > 100%. Everything else is loose.
    k = int(rng.integers(8, 10))
    buy = round(math.floor(100 / k + 1 + float(rng.integers(0, 2))) / 100, 2)  # just over 100% / k
    cap = u(rng, 0.20, 0.25)
    tech_max = u(rng, 0.35, 0.40)
    return (
        "Recent MBA graduate who wants a broadly diversified portfolio where every single position still 'matters'.",
        {},
        [
            rule("max_weight", {"ticker": "*", "max": cap}, f"Nothing above {pct(cap)}.", 5),
            rule("min_holdings", {"k": k}, f"At least {k} different stocks for diversification.", 4),
            rule("buy_in", {"min": buy}, f"And every position at least {pct(buy)}, so each one matters.", 4),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech at most {pct(tech_max)}.", 4),
            rule("exclude", {"tickers": ["GLD"]}, "No gold.", 8, True),
        ],
    )


def c27_planted_turnover(rng):
    # Planted: R1 (turnover cap) + R2 (Tech <= cap). Current tech is 75%; getting it down to
    # tech_max means selling at least (75% - tech_max) and buying the same amount elsewhere, so
    # turnover >= 2 * (75% - tech_max). The turnover cap is set a few points below that.
    tech_max = u(rng, 0.35, 0.40)
    needed = round(2 * (0.75 - tech_max), 2)
    turnover_cap = round(needed - u(rng, 0.04, 0.08), 2)
    cap = u(rng, 0.30, 0.35)
    return (
        "Retired Apple engineer sitting on decades of tech gains who wants to cut tech sharply but refuses a large tax bill.",
        {"AAPL": 0.35, "MSFT": 0.20, "GOOGL": 0.20, "JPM": 0.10, "PG": 0.15},
        [
            rule("max_turnover", {"max": turnover_cap},
                 f"Trade at most {pct(turnover_cap)} of the portfolio, I won't pay more tax than that.", 7),
            rule("sector_max", {"sector": "Tech", "max": tech_max}, f"Tech must come down to {pct(tech_max)} or less.", 5),
            rule("max_weight", {"ticker": "*", "max": cap}, f"No single stock above {pct(cap)}.", 5),
            rule("exclude", {"tickers": ["XOM", "CVX"]}, "No oil.", 8, True),
        ],
    )


ARCHETYPES: list[tuple[str, str, Callable, list[str] | None]] = [
    # (client_id, how they're addressed, archetype, planted conflict rule ids or None)
    ("C10", "f", c10_nurse, None),
    ("C11", "m", c11_engineer, None),
    ("C12", "couple", c12_retired_couple, None),
    ("C13", "dr", c13_dentist, None),
    ("C14", "dr", c14_esg_ten_rules, None),
    ("C15", "any", c15_founder_legacy, None),
    ("C16", "any", c16_banker, None),
    ("C17", "any", c17_four_pillars, None),
    ("C18", "any", c18_oil_heir, None),
    ("C19", "f", c19_income_retiree, None),
    ("C20", "f", c20_concentrated, None),
    ("C21", "m", c21_cleanup, None),
    ("C22", "dr", c22_physician_nine_rules, None),
    ("C23", "any", c23_pension_rebalance, None),
    ("C24", "m", c24_gold_bug, None),
    ("C25", "m", c25_planted_vol, ["R1", "R5"]),
    ("C26", "any", c26_planted_holdings, ["R2", "R3"]),
    ("C27", "any", c27_planted_turnover, ["R1", "R2"]),
]


# ---------- Building and validating ----------

def _to_client(client_id: str, name: str, story: str, current: dict, drafts: list[dict]) -> Client:
    rules = [Rule(id=f"R{i}", **d) for i, d in enumerate(drafts, start=1)]
    return Client(client_id=client_id, name=f"{name} (synthetic)", story=story,
                  universe=list(UNIVERSE), current_weights=current, rules=rules)


def _set_limit(client: Client, rule_type: str, value: float) -> None:
    """Fill in the computed limit of the (single) rule of this type, and its {cap} placeholder."""
    for r in client.rules:
        if r.type == rule_type:
            r.params["max"] = value
            r.source = r.source.format(cap=pct(value))


def calibrate(client: Client, rng) -> None:
    """Set turnover caps first (ignoring vol), then vol caps (with every other rule on)."""
    if any(r.type == "max_turnover" for r in client.rules):
        t = min_turnover(client)
        _set_limit(client, "max_turnover", math.ceil((t + u(rng, *TURNOVER_MARGIN)) * 100) / 100)
    if any(r.type == "max_volatility" for r in client.rules):
        floor = min_volatility(client)
        _set_limit(client, "max_volatility", round(floor + float(rng.uniform(*VOL_MARGIN)), 3))


def calibrate_planted_vol(client: Client, rng) -> None:
    """C25: put the vol cap just under the floor WITH the Tech rule, but above the floor without it."""
    floor = min_volatility(client)
    _set_limit(client, "max_volatility", round(floor - float(rng.uniform(0.003, 0.005)), 3))


def make_client(client_id: str, name: str, archetype: Callable, planted: list[str] | None, rng) -> Client:
    """Draw an archetype until it passes its checks (feasible, or infeasible with exactly the planted clash)."""
    for _ in range(MAX_ATTEMPTS):
        story, current, drafts = archetype(rng)
        client = _to_client(client_id, name, story, current, drafts)
        if planted is None:
            calibrate(client, rng)
            if is_feasible(client):
                return client
        else:
            if any(r.type == "max_volatility" for r in client.rules):
                calibrate_planted_vol(client, rng)
            client.planted_conflict = planted
            if not is_feasible(client) and sorted(find_conflicts(client)) == sorted(planted):
                return client
    raise RuntimeError(f"{client_id}: no valid draw after {MAX_ATTEMPTS} attempts")


def make_all(seed: int = SEED) -> list[Client]:
    """Every generated client, C10-C27, deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    surnames = [SURNAMES[i] for i in rng.permutation(len(SURNAMES))]
    clients = []
    for (cid, who, fn, planted), surname in zip(ARCHETYPES, surnames):
        name = f"The {surname} couple" if who == "couple" else f"{rng.choice(TITLES[who])} {surname}"
        clients.append(make_client(cid, name, fn, planted, rng))
    return clients


def main() -> None:
    for client in make_all():
        path = os.path.join(CLIENTS_DIR, f"{client.client_id}.json")
        with open(path, "w") as f:
            json.dump(client.model_dump(), f, indent=1)
            f.write("\n")
        status = f"planted {client.planted_conflict}" if client.planted_conflict else "feasible"
        print(f"{client.client_id}  {len(client.rules):2d} rules  {status}  {client.name}")


if __name__ == "__main__":
    main()
