"""
The cheapest fix for impossible rules (MASTER 6.6).

When the rules clash, someone has to give a little. Each soft rule gets a
"slack" s >= 0: how far we let it bend. The solver then picks the slacks that
make the rules possible at the lowest total cost, where

    cost = priority x size of the bend
    size = percentage points for weight / sector / volatility / turnover rules
         = number of names for holdings rules

So a high-priority rule is expensive to bend and the solver avoids it. Hard
rules never get slack. If even that is impossible, the hard rules themselves
clash, and we report which ones.

Note: `exclude` rules are never bent here, even when marked soft. "No fossil
fuels" relaxed to "a little fossil fuel" isn't a fix any client would accept.
"""

import math
from dataclasses import dataclass, field

import cvxpy as cp
import numpy as np

import config
from models import Relaxation
from referee.conflicts import find_conflicts
from referee.schema import Client, Rule
from referee.solver import _sector_indices, base_constraints, make_variables, rule_constraints, solve

# Floors ("at least") are relaxed by lowering the limit; every other rule is a cap ("at most").
FLOOR_TYPES = {"min_weight", "sector_min", "min_holdings", "buy_in"}
COUNT_TYPES = {"max_holdings", "min_holdings"}
NEVER_RELAXED = {"exclude"}


@dataclass
class RelaxResult:
    """What the cheapest-fix step found.

    relaxations: the rules to loosen, and by how much (empty if nothing can help).
    hard_conflict: rule ids of clashing HARD rules (only when no relaxation can fix it).
    """

    relaxations: list[Relaxation] = field(default_factory=list)
    hard_conflict: list[str] = field(default_factory=list)


def _limit_key(rule: Rule) -> str:
    """Which param holds the rule's number: "max", "min" or "k"."""
    if rule.type in COUNT_TYPES:
        return "k"
    return "min" if rule.type in FLOOR_TYPES else "max"


def _elastic_constraints(rule: Rule, v, client: Client, s) -> list:
    """The "Elastic form" column of MASTER 6.3: the rule with slack s added."""
    p = rule.params
    if rule.type == "max_weight":
        if p["ticker"] == "*":
            return [v.w <= p["max"] + s]
        i = v.index(p["ticker"])
        return [] if i is None else [v.w[i] <= p["max"] + s]
    if rule.type == "min_weight":
        i = v.index(p["ticker"])
        if i is None:
            raise ValueError(f"Rule {rule.id} needs {p['ticker']}, which isn't in the client's universe")
        return [v.w[i] >= p["min"] - s]
    if rule.type == "sector_max":
        idx = _sector_indices(p["sector"], v)
        return [cp.sum(v.w[idx]) <= p["max"] + s] if idx else []
    if rule.type == "sector_min":
        idx = _sector_indices(p["sector"], v)
        if not idx:
            raise ValueError(f"Rule {rule.id} needs the {p['sector']} sector, but no stock in the universe is in it")
        return [cp.sum(v.w[idx]) >= p["min"] - s]
    if rule.type == "max_holdings":
        return [cp.sum(v.z) <= p["k"] + s]
    if rule.type == "min_holdings":
        return [cp.sum(v.z) >= p["k"] - s]
    if rule.type == "buy_in":
        return [v.w >= p["min"] * v.z - s]
    if rule.type == "max_volatility":
        return [cp.norm(v.market.L.T @ v.w, 2) <= p["max"] + s]
    if rule.type == "max_turnover":
        c = np.array([client.current_weights.get(t, 0.0) for t in v.tickers])
        forced_sales = sum(w for t, w in client.current_weights.items() if t not in v.tickers)
        return [cp.norm(v.w - c, 1) + forced_sales <= p["max"] + s]
    raise ValueError(f"No elastic form for rule type {rule.type}")


def _describe(rule: Rule, old: float, new: float, cost: float) -> str:
    """One sentence, e.g. "Raise 'Healthcare at most 35%' from 35% to 40% (cost 4 x 5 = 20)."."""
    quote = f"'{rule.source.rstrip('.')}'"
    if rule.type in COUNT_TYPES:
        size, unit = abs(new - old), "names"
        old_txt, new_txt = str(int(old)), str(int(new))
    else:
        size, unit = abs(new - old) * 100, "points"
        old_txt, new_txt = f"{old * 100:.1f}%", f"{new * 100:.1f}%"
    verb = "Lower" if rule.type in FLOOR_TYPES else "Raise"
    return (f"{verb} {quote} from {old_txt} to {new_txt} "
            f"(cost {rule.priority} x {size:g} {unit} = {cost:g}).")


def cheapest_relaxation(client: Client) -> RelaxResult:
    """Find the lowest-cost way to loosen soft rules so that all rules become possible."""
    v = make_variables(client)
    constraints = base_constraints(v)
    slacks: dict[str, cp.Variable] = {}
    cost_terms = []

    for rule in client.rules:
        if rule.hard or rule.type in NEVER_RELAXED:
            constraints += rule_constraints(rule, v, client)  # exact, no bending
            continue
        is_count = rule.type in COUNT_TYPES
        # Holdings rules bend by whole names, so their slack is a whole number.
        s = cp.Variable(nonneg=True, integer=is_count, name=f"s_{rule.id}")
        slacks[rule.id] = s
        constraints += _elastic_constraints(rule, v, client, s)
        size = s if is_count else 100 * s  # names, or percentage points
        cost_terms.append(rule.priority * size)

    objective = cp.Minimize(cp.sum(cp.hstack(cost_terms))) if cost_terms else cp.Minimize(0)
    problem = cp.Problem(objective, constraints)

    if not solve(problem):
        # Even bending every soft rule can't help: the hard rules clash on their own.
        hard_ids = [r.id for r in client.rules if r.hard or r.type in NEVER_RELAXED]
        return RelaxResult(hard_conflict=find_conflicts(client, hard_ids))

    relaxations = []
    for rule in client.rules:
        if rule.id not in slacks:
            continue
        amount = float(slacks[rule.id].value)
        if amount <= config.TOL:
            continue  # this rule didn't need to bend
        if rule.type in COUNT_TYPES:
            amount = float(round(amount))
        else:
            # Round off solver noise like 0.0500000001 so limits read cleanly. Round UP
            # (to 6 decimals), so the relaxed rules are never a hair too tight to solve.
            amount = math.ceil(amount * 1e6 - 1e-3) / 1e6
        old = float(rule.params[_limit_key(rule)])
        new = old - amount if rule.type in FLOOR_TYPES else old + amount
        size = amount if rule.type in COUNT_TYPES else amount * 100
        cost = round(rule.priority * size, 6)
        relaxations.append(Relaxation(
            rule_id=rule.id,
            old_limit=old,
            new_limit=new,
            cost=cost,
            explain=_describe(rule, old, new, cost),
        ))
    return RelaxResult(relaxations=relaxations)


def apply_relaxations(client: Client, relaxations: list[Relaxation]) -> Client:
    """A copy of the client with each relaxed rule's limit replaced by its new limit."""
    by_id = {r.rule_id: r for r in relaxations}
    new_rules = []
    for rule in client.rules:
        if rule.id in by_id:
            key = _limit_key(rule)
            new_limit = by_id[rule.id].new_limit
            params = {**rule.params, key: int(round(new_limit)) if key == "k" else new_limit}
            rule = rule.model_copy(update={"params": params})
        new_rules.append(rule)
    return client.model_copy(update={"rules": new_rules})
