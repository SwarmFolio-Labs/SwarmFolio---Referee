"""
Repair: the nearest portfolio that follows every rule (MASTER 6.7).

If the committee's proposal breaks rules, we don't throw it away. We ask the
solver for the compliant portfolio that is as close to it as possible, measured
as "capital moved": the fraction of the money that has to change hands.

    minimize  1/2 * sum |w_i - p_i|   subject to the base constraints + all rules

The 1/2 is there because every dollar moved is counted twice (once sold, once
bought). So 0.20 means "20% of the money changes hands".
"""

import cvxpy as cp

import config
from referee.schema import Client
from referee.solver import build_problem, solve


def capital_moved(a: dict[str, float], b: dict[str, float]) -> float:
    """Fraction of the money that changes hands going from portfolio a to b: 1/2 * sum |a_i - b_i|."""
    tickers = set(a) | set(b)
    return 0.5 * sum(abs(a.get(t, 0.0) - b.get(t, 0.0)) for t in tickers)


def repair(proposal: dict[str, float], client: Client) -> dict[str, float]:
    """The compliant portfolio closest to `proposal` (in capital moved).

    `proposal` should already be dust-cleaned. Raises ValueError if the client's
    rules are impossible (relax them first, see relax.py).
    """
    def distance(v):
        p = v.market.vector(proposal)
        return 0.5 * cp.norm(v.w - p, 1)

    problem, v = build_problem(client, objective=distance)
    if not solve(problem):
        raise ValueError("No portfolio follows all of these rules, so there is nothing to repair towards.")

    # Drop solver crumbs (tiny values that are really zero) and rescale to exactly 100%.
    weights = {t: float(x) for t, x in zip(v.tickers, v.w.value) if x > config.TOL}
    total = sum(weights.values())
    return {t: w / total for t, w in weights.items()}
