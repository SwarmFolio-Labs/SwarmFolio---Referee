"""
Download fresh data with yfinance (MASTER 4.1, PLAN 4).

1) Daily prices for the 19 stocks + SPY from 2015-01-01 to today -> data/prices.csv
   We save to a temp file first and only replace prices.csv if the download is
   complete, so a flaky download never wipes out the good fallback file.
2) A fundamentals snapshot (P/E, revenue growth, profit margin) -> data/fundamentals.json

Run it from the project folder:  .venv/bin/python data/refresh_data.py
"""

import json
import os
from datetime import date, datetime

import pandas as pd
import yfinance as yf

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_PATH = os.path.join(DATA_DIR, "prices.csv")
TEMP_PATH = os.path.join(DATA_DIR, "prices.tmp.csv")
FUNDAMENTALS_PATH = os.path.join(DATA_DIR, "fundamentals.json")

STOCKS = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "JPM", "GS", "BAC", "JNJ",
          "UNH", "PFE", "PG", "KO", "WMT", "XOM", "CVX", "GLD", "TLT"]
TICKERS = STOCKS + ["SPY"]
START = "2015-01-01"


def download_prices() -> pd.DataFrame:
    """Download daily closing prices (adjusted for splits and dividends), one column per ticker."""
    raw = yf.download(TICKERS, start=START, end=None, auto_adjust=True, progress=False)
    prices = raw["Close"]
    # Same layout as SwarmFolio's prices.csv: a Date column, then tickers in alphabetical order.
    prices = prices[sorted(prices.columns)]
    prices.index = pd.to_datetime(prices.index).strftime("%Y-%m-%d")
    prices.index.name = "Date"
    return prices


def is_complete(new: pd.DataFrame, old: pd.DataFrame) -> tuple[bool, str]:
    """Decide if a download is good enough to replace the fallback file. Returns (ok, reason)."""
    missing = [t for t in TICKERS if t not in new.columns]
    if missing:
        return False, f"missing tickers {missing}"
    empty = [t for t in TICKERS if new[t].isna().all()]
    if empty:
        return False, f"no data for {empty}"
    if len(new) < len(old):
        return False, f"fewer rows ({len(new)}) than the fallback ({len(old)})"
    # The last row must have a price for every ticker (otherwise today is half-downloaded).
    if new.iloc[-1].isna().any():
        return False, "last row has missing prices"
    return True, "ok"


def refresh_prices() -> None:
    """Download prices and replace prices.csv only if the download is complete."""
    old = pd.read_csv(PRICES_PATH, index_col="Date")
    try:
        new = download_prices()
    except Exception as e:  # network errors, yfinance changes, rate limits...
        print(f"Price download failed ({e}). Keeping the fallback prices.csv.")
        return
    ok, reason = is_complete(new, old)
    if not ok:
        print(f"Price download incomplete: {reason}. Keeping the fallback prices.csv.")
        return
    new.to_csv(TEMP_PATH)
    os.replace(TEMP_PATH, PRICES_PATH)
    print("Replaced prices.csv with the fresh download.")


def refresh_fundamentals() -> None:
    """Save a snapshot of P/E, revenue growth and profit margin for each stock."""
    snapshot = {"as_of": date.today().isoformat(), "tickers": {}}
    for ticker in STOCKS:
        try:
            info = yf.Ticker(ticker).info
        except Exception as e:
            print(f"  fundamentals for {ticker} failed ({e})")
            info = {}
        snapshot["tickers"][ticker] = {
            "pe": info.get("trailingPE"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
        }
    with open(FUNDAMENTALS_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
    filled = sum(1 for v in snapshot["tickers"].values() if v["pe"] is not None)
    print(f"Saved fundamentals.json ({filled}/{len(STOCKS)} tickers have a P/E).")


def main() -> None:
    refresh_prices()
    refresh_fundamentals()
    prices = pd.read_csv(PRICES_PATH, index_col="Date")
    print(f"prices.csv: {prices.shape[0]} rows x {prices.shape[1]} tickers, "
          f"{prices.index[0]} -> {prices.index[-1]} (checked {datetime.now():%Y-%m-%d %H:%M})")


if __name__ == "__main__":
    main()
