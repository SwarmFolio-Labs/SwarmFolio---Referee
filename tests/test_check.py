"""Tests for referee/check.py: one passing and one failing case per rule type, plus dust cleaning."""

import pytest

from referee.check import check, check_rule, clean_dust
from referee.market import get_market, portfolio_volatility
from referee.schema import Client, Rule

UNIVERSE = ["AAPL", "MSFT", "NVDA", "JNJ", "UNH", "KO", "PG", "XOM", "TLT"]


def make_client(current=None) -> Client:
    return Client(
        client_id="T01",
        name="Test client",
        story="Only for tests.",
        universe=UNIVERSE,
        current_weights=current or {},
        rules=[],
    )


def rule(type_, params, id_="R1") -> Rule:
    return Rule(id=id_, type=type_, params=params, priority=5, hard=False, source="Test rule.")


def run(type_, params, weights, current=None):
    return check_rule(rule(type_, params), weights, make_client(current))


# ---------- the 10 rule types: pass and fail ----------

def test_max_weight_single_ticker():
    assert run("max_weight", {"ticker": "NVDA", "max": 0.35}, {"NVDA": 0.30, "KO": 0.70}).passed
    r = run("max_weight", {"ticker": "NVDA", "max": 0.35}, {"NVDA": 0.41, "KO": 0.59})
    assert not r.passed
    assert r.violation == pytest.approx(0.06)
    assert "NVDA is 41.0%" in r.explain and "Test rule." in r.explain


def test_max_weight_star_checks_the_largest_position():
    assert run("max_weight", {"ticker": "*", "max": 0.35}, {"NVDA": 0.35, "KO": 0.35, "PG": 0.30}).passed
    r = run("max_weight", {"ticker": "*", "max": 0.35}, {"NVDA": 0.20, "KO": 0.50, "PG": 0.30})
    assert not r.passed
    assert r.actual == pytest.approx(0.50)
    assert "KO" in r.explain


def test_min_weight():
    assert run("min_weight", {"ticker": "JNJ", "min": 0.30}, {"JNJ": 0.30, "KO": 0.70}).passed
    r = run("min_weight", {"ticker": "JNJ", "min": 0.30}, {"KO": 1.0})  # JNJ missing = 0%
    assert not r.passed
    assert r.violation == pytest.approx(0.30)


def test_exclude():
    assert run("exclude", {"tickers": ["XOM"]}, {"KO": 1.0}).passed
    r = run("exclude", {"tickers": ["XOM"]}, {"XOM": 0.14, "KO": 0.86})
    assert not r.passed
    assert r.violation == pytest.approx(0.14)


def test_sector_max():
    # JNJ + UNH are both Healthcare.
    assert run("sector_max", {"sector": "Healthcare", "max": 0.35}, {"JNJ": 0.30, "UNH": 0.05, "KO": 0.65}).passed
    r = run("sector_max", {"sector": "Healthcare", "max": 0.35}, {"JNJ": 0.30, "UNH": 0.10, "KO": 0.60})
    assert not r.passed
    assert r.actual == pytest.approx(0.40)
    assert r.violation == pytest.approx(0.05)


def test_sector_min():
    assert run("sector_min", {"sector": "Tech", "min": 0.20}, {"AAPL": 0.10, "MSFT": 0.10, "KO": 0.80}).passed
    r = run("sector_min", {"sector": "Tech", "min": 0.20}, {"AAPL": 0.05, "KO": 0.95})
    assert not r.passed
    assert r.violation == pytest.approx(0.15)


def test_max_holdings():
    assert run("max_holdings", {"k": 2}, {"KO": 0.5, "PG": 0.5}).passed
    r = run("max_holdings", {"k": 2}, {"KO": 0.4, "PG": 0.3, "TLT": 0.3})
    assert not r.passed
    assert r.actual == 3 and r.violation == 1


def test_min_holdings():
    assert run("min_holdings", {"k": 3}, {"KO": 0.4, "PG": 0.3, "TLT": 0.3}).passed
    r = run("min_holdings", {"k": 3}, {"KO": 1.0})
    assert not r.passed
    assert r.violation == 2


def test_buy_in():
    assert run("buy_in", {"min": 0.05}, {"KO": 0.95, "PG": 0.05}).passed
    r = run("buy_in", {"min": 0.05}, {"KO": 0.90, "PG": 0.02, "TLT": 0.03, "AAPL": 0.05})
    assert not r.passed
    assert r.actual == pytest.approx(0.02)
    # Both too-small positions count: (5 - 2) + (5 - 3) = 5 percentage points.
    assert r.violation == pytest.approx(0.05)


def test_max_volatility():
    weights = {"KO": 0.5, "TLT": 0.5}
    vol = portfolio_volatility(get_market(UNIVERSE), weights)
    assert run("max_volatility", {"max": vol + 0.01}, weights).passed
    r = run("max_volatility", {"max": vol - 0.01}, weights)
    assert not r.passed
    assert r.actual == pytest.approx(vol)
    assert r.violation == pytest.approx(0.01)


def test_max_turnover():
    current = {"JNJ": 0.40, "TLT": 0.30, "KO": 0.30}
    # Move 10% from TLT to KO: |0| + |-0.1| + |+0.1| = 0.20 turnover.
    assert run("max_turnover", {"max": 0.20}, {"JNJ": 0.40, "TLT": 0.20, "KO": 0.40}, current).passed
    r = run("max_turnover", {"max": 0.20}, {"AAPL": 1.0}, current)
    assert not r.passed
    assert r.actual == pytest.approx(2.0)  # sell everything (1.0) + buy AAPL (1.0)


def test_check_runs_every_rule():
    client = make_client()
    client.rules = [
        rule("max_weight", {"ticker": "*", "max": 0.35}, "R1"),
        rule("exclude", {"tickers": ["XOM"]}, "R2"),
    ]
    results = check({"NVDA": 0.41, "XOM": 0.14, "KO": 0.45}, client)
    assert [r.rule_id for r in results] == ["R1", "R2"]
    assert not any(r.passed for r in results)


# ---------- dust cleaning ----------

def test_clean_dust_drops_tiny_positions_and_renormalizes():
    cleaned, dropped = clean_dust({"KO": 0.597, "PG": 0.4, "TLT": 0.003}, UNIVERSE)
    assert dropped == ["TLT"]
    assert set(cleaned) == {"KO", "PG"}
    assert sum(cleaned.values()) == pytest.approx(1.0)
    assert cleaned["KO"] == pytest.approx(0.597 / 0.997)


def test_clean_dust_fixes_weights_that_dont_sum_to_one():
    cleaned, dropped = clean_dust({"KO": 0.5, "PG": 0.48}, UNIVERSE)
    assert dropped == []
    assert sum(cleaned.values()) == pytest.approx(1.0)


def test_clean_dust_rejects_outside_universe():
    with pytest.raises(ValueError, match="GLD"):
        clean_dust({"KO": 0.5, "GLD": 0.5}, UNIVERSE)


def test_clean_dust_rejects_negative_and_empty():
    with pytest.raises(ValueError, match="Negative"):
        clean_dust({"KO": 1.2, "PG": -0.2}, UNIVERSE)
    with pytest.raises(ValueError, match="no positions"):
        clean_dust({"KO": 0.001}, UNIVERSE)
