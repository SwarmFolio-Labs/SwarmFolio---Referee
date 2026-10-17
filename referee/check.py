"""
Check a portfolio against a client's rules, with plain arithmetic (MASTER 6.2-6.3).

No solver here: this only measures. For each rule we compute what the portfolio
actually has, what the rule allows, and how far past the limit it is. A rule
passes when its violation is at most TOL. Every result also gets one sentence in
plain English that quotes the client's own words.
"""

import config
from models import CheckResult
from referee.market import get_market, load_sectors, portfolio_volatility
from referee.schema import Client, Rule


def _pct(x: float) -> str:
    """0.412 -> "41.2%"."""
    return f"{x * 100:.1f}%"


# ---------- Dust cleaning (MASTER 6.2) ----------

def clean_dust(weights: dict[str, float], universe: list[str]) -> tuple[dict[str, float], list[str]]:
    """Drop tiny positions (below DUST) and rescale the rest so they sum to 1.

    LLMs like to sprinkle 0.1% positions around. Those aren't real holdings, so we
    set them to 0 and say so. Returns (cleaned weights, tickers that were dropped).
    Raises ValueError for tickers outside the universe, negative weights, or an
    empty portfolio, because those can't be fixed by rounding.
    """
    outside = sorted(t for t in weights if t not in universe)
    if outside:
        raise ValueError(f"Weights for tickers outside the client's universe: {', '.join(outside)}")

    negative = sorted(t for t, w in weights.items() if w < -config.TOL)
    if negative:
        raise ValueError(f"Negative weights (short positions aren't allowed): {', '.join(negative)}")

    # Positive but below DUST: "not really held". (Zeros aren't worth reporting.)
    dust_removed = sorted(t for t, w in weights.items() if 0 < w < config.DUST)
    kept = {t: w for t, w in weights.items() if w >= config.DUST}

    total = sum(kept.values())
    if total <= 0:
        raise ValueError("The portfolio has no positions of at least 0.5%.")

    cleaned = {t: w / total for t, w in kept.items()}
    return cleaned, dust_removed


# ---------- One function per rule type ----------
# Each returns (actual, limit, violation, fact), where `fact` is the measured part
# of the sentence, e.g. "NVDA is 41.0% of the portfolio".

def _held(weights: dict[str, float]) -> dict[str, float]:
    """Only the positions that count as held (at least DUST, minus TOL for solver rounding)."""
    return {t: w for t, w in weights.items() if w >= config.DUST - config.TOL}


def _check_max_weight(rule: Rule, weights: dict[str, float], client: Client):
    limit = rule.params["max"]
    ticker = rule.params["ticker"]
    if ticker == "*":
        # The largest position is the one that matters for "no single position above X".
        if weights:
            ticker = max(weights, key=weights.get)
            actual = weights[ticker]
        else:
            ticker, actual = "no position", 0.0
        fact = f"The largest position is {ticker} at {_pct(actual)}"
    else:
        actual = weights.get(ticker, 0.0)
        fact = f"{ticker} is {_pct(actual)} of the portfolio"
    return actual, limit, max(0.0, actual - limit), fact


def _check_min_weight(rule: Rule, weights: dict[str, float], client: Client):
    limit = rule.params["min"]
    ticker = rule.params["ticker"]
    actual = weights.get(ticker, 0.0)
    return actual, limit, max(0.0, limit - actual), f"{ticker} is {_pct(actual)} of the portfolio"


def _check_exclude(rule: Rule, weights: dict[str, float], client: Client):
    banned = rule.params["tickers"]
    held = [t for t in banned if weights.get(t, 0.0) > 0]
    actual = sum(weights.get(t, 0.0) for t in banned)
    if held:
        fact = f"The portfolio holds {', '.join(held)} ({_pct(actual)} in total)"
    else:
        fact = f"The portfolio holds none of {', '.join(banned)}"
    return actual, 0.0, actual, fact


def _sector_weight(sector: str, weights: dict[str, float]) -> float:
    """Total weight of all stocks in one sector."""
    sectors = load_sectors()
    return sum(w for t, w in weights.items() if sectors.get(t) == sector)


def _check_sector_max(rule: Rule, weights: dict[str, float], client: Client):
    sector, limit = rule.params["sector"], rule.params["max"]
    actual = _sector_weight(sector, weights)
    return actual, limit, max(0.0, actual - limit), f"{sector} is {_pct(actual)} of the portfolio"


def _check_sector_min(rule: Rule, weights: dict[str, float], client: Client):
    sector, limit = rule.params["sector"], rule.params["min"]
    actual = _sector_weight(sector, weights)
    return actual, limit, max(0.0, limit - actual), f"{sector} is {_pct(actual)} of the portfolio"


def _check_max_holdings(rule: Rule, weights: dict[str, float], client: Client):
    k = rule.params["k"]
    actual = len(_held(weights))
    return float(actual), float(k), float(max(0, actual - k)), f"The portfolio has {actual} holdings"


def _check_min_holdings(rule: Rule, weights: dict[str, float], client: Client):
    k = rule.params["k"]
    actual = len(_held(weights))
    return float(actual), float(k), float(max(0, k - actual)), f"The portfolio has {actual} holdings"


def _check_buy_in(rule: Rule, weights: dict[str, float], client: Client):
    limit = rule.params["min"]
    held = _held(weights)
    if not held:
        return 0.0, limit, 0.0, "The portfolio has no holdings"
    smallest = min(held, key=held.get)
    actual = held[smallest]
    # Add up how far every too-small position falls short, not just the smallest one.
    violation = sum(limit - w for w in held.values() if w < limit)
    return actual, limit, violation, f"The smallest position is {smallest} at {_pct(actual)}"


def _check_max_volatility(rule: Rule, weights: dict[str, float], client: Client):
    limit = rule.params["max"]
    market = get_market(client.universe)
    actual = portfolio_volatility(market, weights)
    return actual, limit, max(0.0, actual - limit), f"Annual volatility is {_pct(actual)}"


def _check_max_turnover(rule: Rule, weights: dict[str, float], client: Client):
    limit = rule.params["max"]
    current = client.current_weights
    tickers = set(weights) | set(current)
    # Sum of |new - current| over every ticker either portfolio touches (MASTER 6.3).
    actual = sum(abs(weights.get(t, 0.0) - current.get(t, 0.0)) for t in tickers)
    return actual, limit, max(0.0, actual - limit), f"Turnover from current holdings is {_pct(actual)}"


CHECKS = {
    "max_weight": _check_max_weight,
    "min_weight": _check_min_weight,
    "exclude": _check_exclude,
    "sector_max": _check_sector_max,
    "sector_min": _check_sector_min,
    "max_holdings": _check_max_holdings,
    "min_holdings": _check_min_holdings,
    "buy_in": _check_buy_in,
    "max_volatility": _check_max_volatility,
    "max_turnover": _check_max_turnover,
}

COUNT_RULES = {"max_holdings", "min_holdings"}


def check_rule(rule: Rule, weights: dict[str, float], client: Client) -> CheckResult:
    """Check one rule against (already dust-cleaned) weights."""
    actual, limit, violation, fact = CHECKS[rule.type](rule, weights, client)

    if rule.type in COUNT_RULES:
        passed = violation == 0  # counts are whole numbers: no tolerance needed
        limit_text = str(int(limit))
    else:
        passed = violation <= config.TOL
        limit_text = _pct(limit)

    verdict = "OK" if passed else "BROKEN"
    explain = f"{fact} (limit {limit_text}): {verdict}. The client said: '{rule.source}'"
    return CheckResult(
        rule_id=rule.id,
        type=rule.type,
        passed=passed,
        actual=actual,
        limit=limit,
        violation=violation,
        explain=explain,
    )


def check(weights: dict[str, float], client: Client) -> list[CheckResult]:
    """Check every one of the client's rules. `weights` should already be dust-cleaned."""
    return [check_rule(rule, weights, client) for rule in client.rules]
