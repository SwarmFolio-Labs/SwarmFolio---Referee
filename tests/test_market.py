"""Tests for referee/market.py: the return and risk estimates (MASTER 6.1)."""

import numpy as np
import pytest

import config
from referee.market import (
    get_market,
    portfolio_return,
    portfolio_volatility,
    sector_returns,
    sharpe,
    stock_stats,
)

TICKERS = ["AAPL", "JNJ", "KO", "TLT", "XOM"]


def test_shapes_and_symmetry():
    m = get_market(TICKERS)
    assert m.mu.shape == (5,)
    assert m.Sigma.shape == (5, 5)
    assert np.allclose(m.Sigma, m.Sigma.T)
    # Variances on the diagonal must be positive.
    assert (np.diag(m.Sigma) > 0).all()


def test_cholesky_gives_the_same_volatility():
    # The solver uses ||L^T w||; it must equal sqrt(w^T Sigma w).
    m = get_market(TICKERS)
    w = {"AAPL": 0.4, "JNJ": 0.3, "TLT": 0.3}
    vec = m.vector(w)
    assert np.linalg.norm(m.L.T @ vec) == pytest.approx(portfolio_volatility(m, w), rel=1e-6)


def test_sharpe_formula():
    m = get_market(TICKERS)
    w = {"KO": 0.5, "TLT": 0.5}
    expected = (portfolio_return(m, w) - config.RISK_FREE) / portfolio_volatility(m, w)
    assert sharpe(m, w) == pytest.approx(expected)


def test_diversifying_lowers_volatility():
    # Half AAPL / half TLT should be less risky than all AAPL (they don't move together much).
    m = get_market(TICKERS)
    assert portfolio_volatility(m, {"AAPL": 0.5, "TLT": 0.5}) < portfolio_volatility(m, {"AAPL": 1.0})


def test_unknown_ticker_is_an_error():
    with pytest.raises(ValueError, match="ZZZZ"):
        get_market(["AAPL", "ZZZZ"])


def test_analyst_stats():
    stats = stock_stats(["AAPL", "TLT"])
    for row in stats.values():
        assert set(row) == {"ret_1m", "ret_3m", "ret_6m", "vol", "max_drawdown", "corr_spy"}
        assert 0 <= row["max_drawdown"] <= 1
        assert -1 <= row["corr_spy"] <= 1
    sectors = sector_returns(TICKERS)
    assert {"Tech", "Healthcare", "Consumer", "Bonds", "Energy", "SPY"} <= set(sectors)
