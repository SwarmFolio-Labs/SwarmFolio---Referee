"""
Rule price tags (MASTER 6.10): what each client rule costs.

Idea: find the best portfolio under ALL the rules, then re-solve once per rule with that
one rule removed. Removing a rule can only help, so the improvement is that rule's "price".
Big price = this rule is really holding the portfolio back. Price ~0 = the rule never binds,
so it's free to keep (or drop).

"Best" here means the highest mean-variance utility:
    U(w) = mu'w - (gamma/2) * ||L'w||^2      (expected return minus a penalty for variance)
"""

import cvxpy as cp
import numpy as np

import config
from models import RulePrice
from referee.market import sharpe
from referee.relax import apply_relaxations, cheapest_relaxation
from referee.schema import Client
from referee.solver import build_problem, is_feasible

# Verified on C02 (MASTER 6.10): these settings give the same prices as the strict ones,
# in ~0.1 s for all solves instead of hitting the time limit on every one.
SCIP_PARAMS = {"limits/time": 15, "limits/gap": 1e-3}
BINDS_THRESHOLD = 0.0001  # 0.01 points: below this, a rule "costs nothing"


def _negative_utility(v):
    """The thing to MINIMIZE: -(expected return - gamma/2 * variance)."""
    mu = v.market.mu
    variance = cp.sum_squares(v.market.L.T @ v.w)  # ||L'w||^2 = w' Sigma w
    return -(mu @ v.w - (config.RISK_AVERSION / 2) * variance)


def best_utility(client: Client, rule_ids: list[str]) -> tuple[float, float]:
    """Solve for the best portfolio under these rules. Returns (utility U*, its Sharpe)."""
    problem, v = build_problem(client, rule_ids, objective=_negative_utility)
    problem.solve(solver=cp.SCIP, scip_params=SCIP_PARAMS)
    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(f"Price-tag solve failed for {client.client_id} (status: {problem.status})")
    weights = {t: float(x) for t, x in zip(v.tickers, np.asarray(v.w.value).ravel())}
    return -float(problem.value), sharpe(v.market, weights)


def rule_prices(client: Client) -> list[RulePrice]:
    """Price every rule of this client, most expensive first."""
    note = ""
    if not is_feasible(client):
        # Can't price rules that can't all hold: price the cheapest relaxed version instead (MASTER 6.6).
        relax = cheapest_relaxation(client)
        if not relax.relaxations:
            raise ValueError(f"{client.client_id}'s hard rules clash ({', '.join(relax.hard_conflict)}); "
                             "there is nothing to price.")
        client = apply_relaxations(client, relax.relaxations)
        note = " (priced on the relaxed rules, because the original rules can't all hold)"

    all_ids = [r.id for r in client.rules]
    u_all, s_all = best_utility(client, all_ids)

    prices = []
    for rule in client.rules:
        others = [i for i in all_ids if i != rule.id]
        u_without, s_without = best_utility(client, others)
        cost = max(0.0, u_without - u_all)  # removing a rule can only help; clip solver noise
        binds = cost > BINDS_THRESHOLD
        if binds:
            explain = (f"'{rule.source}' costs {cost * 100:.2f} points of risk-adjusted return a year "
                       f"(Sharpe {s_all:.2f} → {s_without:.2f} without it){note}.")
        else:
            explain = f"'{rule.source}' costs nothing: it never binds{note}."
        prices.append(RulePrice(rule_id=rule.id, source=rule.source, binds=binds,
                                utility_cost_pts=round(cost * 100, 4), sharpe_with=s_all,
                                sharpe_without=s_without, explain=explain))

    prices.sort(key=lambda p: p.utility_cost_pts, reverse=True)
    return prices
