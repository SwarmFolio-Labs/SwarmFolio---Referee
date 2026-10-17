"""
Market estimates from daily prices (MASTER 6.1).

The Referee needs two numbers per stock universe: how much each stock is expected
to return (mu) and how the stocks move together (Sigma). From those we get any
portfolio's volatility and Sharpe ratio. The analysts also get some simple stats
(recent returns, volatility, drawdown, correlation to SPY) computed here, so the
LLMs read real numbers instead of making them up.
"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

import config

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRICES_PATH = os.path.join(DATA_DIR, "prices.csv")
SECTORS_PATH = os.path.join(DATA_DIR, "sectors.json")

TRADING_DAYS = 252  # trading days in a year, used to annualize daily numbers


@lru_cache(maxsize=1)
def load_prices() -> pd.DataFrame:
    """Read data/prices.csv into a table: one row per day, one column per ticker."""
    prices = pd.read_csv(PRICES_PATH, index_col="Date", parse_dates=True)
    return prices.sort_index()


@lru_cache(maxsize=1)
def load_sectors() -> dict[str, str]:
    """Read data/sectors.json: ticker -> sector name (e.g. "JNJ" -> "Healthcare")."""
    with open(SECTORS_PATH) as f:
        return json.load(f)


def daily_returns(lookback: int = config.LOOKBACK_DAYS) -> pd.DataFrame:
    """Daily returns r_t = P_t / P_(t-1) - 1 over the last `lookback` trading days."""
    prices = load_prices().iloc[-(lookback + 1):]  # one extra day so we get `lookback` returns
    return prices.pct_change().dropna(how="all")


@dataclass
class Market:
    """Annual return and risk estimates for one ordered list of tickers.

    The order of `tickers` is the order of every vector and matrix here, so
    mu[i] and Sigma[i, j] always line up with tickers[i] and tickers[j].
    """

    tickers: list[str]
    mu: np.ndarray     # annual expected return per stock, shape (n,)
    Sigma: np.ndarray  # annual covariance matrix, shape (n, n)
    L: np.ndarray      # Cholesky factor: Sigma = L @ L.T, so ||L.T @ w|| = volatility

    def vector(self, weights: dict[str, float]) -> np.ndarray:
        """Turn {ticker: weight} into a vector in this market's ticker order (missing = 0)."""
        return np.array([weights.get(t, 0.0) for t in self.tickers])


@lru_cache(maxsize=32)
def _market_for(tickers: tuple[str, ...], lookback: int) -> Market:
    """Build (and remember) the Market for one tuple of tickers."""
    missing = [t for t in tickers if t not in load_prices().columns]
    if missing:
        raise ValueError(f"No price data for: {', '.join(missing)}")

    returns = daily_returns(lookback)[list(tickers)].dropna()
    mu = returns.mean().to_numpy() * TRADING_DAYS
    Sigma = returns.cov().to_numpy() * TRADING_DAYS
    # Rounding can make Sigma very slightly lopsided; average it with its transpose.
    Sigma = (Sigma + Sigma.T) / 2
    # A tiny bump on the diagonal guarantees Cholesky works even if two stocks are near-identical.
    L = np.linalg.cholesky(Sigma + 1e-10 * np.eye(len(tickers)))
    return Market(tickers=list(tickers), mu=mu, Sigma=Sigma, L=L)


def get_market(tickers: list[str], lookback: int = config.LOOKBACK_DAYS) -> Market:
    """Market estimates (mu, Sigma, L) for these tickers, in this order."""
    return _market_for(tuple(tickers), lookback)


def portfolio_return(market: Market, weights: dict[str, float]) -> float:
    """Expected annual return of a portfolio: mu^T w."""
    return float(market.mu @ market.vector(weights))


def portfolio_volatility(market: Market, weights: dict[str, float]) -> float:
    """Annual volatility of a portfolio: sqrt(w^T Sigma w)."""
    w = market.vector(weights)
    # max(0, ...) guards against a tiny negative from floating-point rounding.
    return float(np.sqrt(max(0.0, w @ market.Sigma @ w)))


def sharpe(market: Market, weights: dict[str, float]) -> float:
    """Sharpe ratio: (expected return - risk-free rate) / volatility. 0 if volatility is 0."""
    vol = portfolio_volatility(market, weights)
    if vol < 1e-12:
        return 0.0
    return (portfolio_return(market, weights) - config.RISK_FREE) / vol


# ---------- Stats for the analysts (MASTER 7.1) ----------

def _period_return(prices: pd.Series, days: int) -> float:
    """Return over the last `days` trading days, e.g. 0.05 = +5%."""
    return float(prices.iloc[-1] / prices.iloc[-(days + 1)] - 1)


def _max_drawdown(prices: pd.Series) -> float:
    """Worst peak-to-trough drop, as a positive fraction (0.30 = fell 30% from a high)."""
    running_peak = prices.cummax()
    drawdowns = prices / running_peak - 1
    return float(-drawdowns.min())


def stock_stats(tickers: list[str], lookback: int = config.LOOKBACK_DAYS) -> dict[str, dict]:
    """Per-stock numbers for the analysts: 1/3/6-month return, volatility, drawdown, SPY correlation."""
    prices = load_prices()
    window = prices.iloc[-(lookback + 1):]
    returns = window.pct_change().dropna(how="all")

    stats = {}
    for t in tickers:
        p = prices[t].dropna()
        stats[t] = {
            "ret_1m": _period_return(p, 21),
            "ret_3m": _period_return(p, 63),
            "ret_6m": _period_return(p, 126),
            "vol": float(returns[t].std() * np.sqrt(TRADING_DAYS)),
            "max_drawdown": _max_drawdown(window[t].dropna()),
            "corr_spy": float(returns[t].corr(returns["SPY"])),
        }
    return stats


def sector_returns(tickers: list[str]) -> dict[str, dict]:
    """1/3/6-month return per sector (equal-weight average of its stocks), plus SPY."""
    sectors = load_sectors()
    stats = stock_stats(tickers)
    by_sector: dict[str, list[dict]] = {}
    for t in tickers:
        by_sector.setdefault(sectors.get(t, "Other"), []).append(stats[t])

    result = {}
    for sector, rows in by_sector.items():
        result[sector] = {k: float(np.mean([r[k] for r in rows])) for k in ("ret_1m", "ret_3m", "ret_6m")}
    spy = load_prices()["SPY"].dropna()
    result["SPY"] = {k: _period_return(spy, d) for k, d in (("ret_1m", 21), ("ret_3m", 63), ("ret_6m", 126))}
    return result


def as_of() -> str:
    """The date of the last price row, e.g. "2026-10-16"."""
    return load_prices().index[-1].strftime("%Y-%m-%d")
