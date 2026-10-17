"""
Turn a client's rules into an exact optimization problem (MASTER 6.2-6.4).

check.py measures one portfolio. This file asks a bigger question: does ANY
portfolio exist that follows all these rules at once? We write the rules as math
over two sets of variables and hand them to the SCIP solver, which either finds
a portfolio or proves that none exists.

  w[i] = fraction of money in stock i (a number from 0 to 1)
  z[i] = 1 if we hold stock i, 0 if we don't (a yes/no variable)

The yes/no variables are what make rules like "at most 8 holdings" and "no
position smaller than 5%" possible to write as math.
"""

from dataclasses import dataclass

import cvxpy as cp
import numpy as np

import config
from referee.market import Market, get_market, load_sectors
from referee.schema import Client, Rule

SOLVED = {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}
INFEASIBLE = {cp.INFEASIBLE, cp.INFEASIBLE_INACCURATE}


@dataclass
class Variables:
    """The solver's unknowns for one client, plus what we need to build rules on them."""

    w: cp.Variable       # weights, one per stock in the universe
    z: cp.Variable       # held (1) or not (0), one per stock
    tickers: list[str]   # universe order: w[i] and z[i] belong to tickers[i]
    market: Market       # mu, Sigma, L for the volatility rule

    def index(self, ticker: str) -> int | None:
        """Position of a ticker in the universe, or None if it isn't in it."""
        return self.tickers.index(ticker) if ticker in self.tickers else None


def make_variables(client: Client) -> Variables:
    """Create w and z for every stock in the client's universe."""
    n = len(client.universe)
    return Variables(
        w=cp.Variable(n, name="w"),
        z=cp.Variable(n, boolean=True, name="z"),
        tickers=list(client.universe),
        market=get_market(client.universe),
    )


def base_constraints(v: Variables) -> list:
    """Rules that are always on, for every client (MASTER 6.2).

    - The weights add up to 100% and none is negative (no short selling).
    - w <= z: you can only put money in a stock you hold (z = 0 forces w = 0).
    - w >= DUST * z: if you hold it, hold at least 0.5% (no dust positions).
    """
    return [
        cp.sum(v.w) == 1,
        v.w >= 0,
        v.w <= v.z,
        v.w >= config.DUST * v.z,
    ]


# ---------- One function per rule type (the "Solver constraint" column of MASTER 6.3) ----------

def _max_weight(rule: Rule, v: Variables, client: Client) -> list:
    cap = rule.params["max"]
    if rule.params["ticker"] == "*":
        return [v.w <= cap]  # every single stock at most `cap`
    i = v.index(rule.params["ticker"])
    return [] if i is None else [v.w[i] <= cap]  # not in the universe = always 0, nothing to cap


def _min_weight(rule: Rule, v: Variables, client: Client) -> list:
    ticker = rule.params["ticker"]
    i = v.index(ticker)
    if i is None:
        raise ValueError(f"Rule {rule.id} needs {ticker}, which isn't in the client's universe")
    return [v.w[i] >= rule.params["min"]]


def _exclude(rule: Rule, v: Variables, client: Client) -> list:
    indices = [v.index(t) for t in rule.params["tickers"]]
    return [v.w[i] == 0 for i in indices if i is not None]


def _sector_indices(sector: str, v: Variables) -> list[int]:
    """Positions of every stock in the universe that belongs to `sector`."""
    sectors = load_sectors()
    return [i for i, t in enumerate(v.tickers) if sectors.get(t) == sector]


def _sector_max(rule: Rule, v: Variables, client: Client) -> list:
    idx = _sector_indices(rule.params["sector"], v)
    return [cp.sum(v.w[idx]) <= rule.params["max"]] if idx else []


def _sector_min(rule: Rule, v: Variables, client: Client) -> list:
    sector = rule.params["sector"]
    idx = _sector_indices(sector, v)
    if not idx:
        raise ValueError(f"Rule {rule.id} needs the {sector} sector, but no stock in the universe is in it")
    return [cp.sum(v.w[idx]) >= rule.params["min"]]


def _max_holdings(rule: Rule, v: Variables, client: Client) -> list:
    # Each z[i] is 0 or 1, so their sum is the number of stocks held.
    return [cp.sum(v.z) <= rule.params["k"]]


def _min_holdings(rule: Rule, v: Variables, client: Client) -> list:
    # Works because of w >= DUST * z in the base constraints: a "held" stock really has money in it.
    return [cp.sum(v.z) >= rule.params["k"]]


def _buy_in(rule: Rule, v: Variables, client: Client) -> list:
    # z = 0: w >= 0 (not held, fine). z = 1: w >= min. So every position is 0 or at least `min`.
    return [v.w >= rule.params["min"] * v.z]


def _max_volatility(rule: Rule, v: Variables, client: Client) -> list:
    # ||L^T w|| equals sqrt(w^T Sigma w), the portfolio's volatility. This is a "cone" constraint.
    return [cp.norm(v.market.L.T @ v.w, 2) <= rule.params["max"]]


def _max_turnover(rule: Rule, v: Variables, client: Client) -> list:
    current = client.current_weights
    c = np.array([current.get(t, 0.0) for t in v.tickers])
    # Stocks the client holds now but that aren't in the universe must be sold completely.
    forced_sales = sum(w for t, w in current.items() if t not in v.tickers)
    return [cp.norm(v.w - c, 1) + forced_sales <= rule.params["max"]]


CONSTRAINTS = {
    "max_weight": _max_weight,
    "min_weight": _min_weight,
    "exclude": _exclude,
    "sector_max": _sector_max,
    "sector_min": _sector_min,
    "max_holdings": _max_holdings,
    "min_holdings": _min_holdings,
    "buy_in": _buy_in,
    "max_volatility": _max_volatility,
    "max_turnover": _max_turnover,
}


def rule_constraints(rule: Rule, v: Variables, client: Client) -> list:
    """The exact solver constraints for one rule."""
    return CONSTRAINTS[rule.type](rule, v, client)


def build_problem(client: Client, active_rule_ids: list[str] | None = None, objective=None):
    """Build the optimization problem: base constraints + the chosen rules.

    active_rule_ids: which rules to include (None = all of the client's rules).
    objective: a function that takes the Variables and returns a cvxpy expression
               to minimize (None = minimize 0, i.e. "just find any portfolio").
    Returns (problem, variables) so callers can read the weights after solving.
    """
    if active_rule_ids is None:
        rules = client.rules
    else:
        unknown = set(active_rule_ids) - {r.id for r in client.rules}
        if unknown:
            raise ValueError(f"Unknown rule ids: {', '.join(sorted(unknown))}")
        rules = [r for r in client.rules if r.id in active_rule_ids]

    v = make_variables(client)
    constraints = base_constraints(v)
    for rule in rules:
        constraints += rule_constraints(rule, v, client)

    goal = cp.Minimize(0) if objective is None else cp.Minimize(objective(v))
    return cp.Problem(goal, constraints), v


def solve(problem: cp.Problem) -> bool:
    """Solve with SCIP. True = solved, False = proven infeasible, anything else = error."""
    problem.solve(solver=cp.SCIP)
    if problem.status in SOLVED:
        return True
    if problem.status in INFEASIBLE:
        return False
    raise RuntimeError(f"Solver returned an unexpected status: {problem.status}")


def is_feasible(client: Client, rule_ids: list[str] | None = None) -> bool:
    """Can ANY portfolio follow all these rules at once? (None = all of the client's rules.)"""
    problem, _ = build_problem(client, rule_ids)
    return solve(problem)
