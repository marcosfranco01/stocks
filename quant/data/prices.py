"""Daily OHLCV prices from Yahoo Finance, cached as parquet in data/prices.parquet."""

from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PRICES_PATH = DATA_DIR / "prices.parquet"


def download_prices(symbols: list[str], start: str = "2010-01-01") -> pd.DataFrame:
    """Download split/dividend-adjusted daily bars. Returns long format: date, symbol, open..volume."""
    raw = yf.download(symbols, start=start, auto_adjust=True, progress=False, group_by="ticker", threads=True)
    frames = []
    for sym in symbols:
        if sym not in raw.columns.get_level_values(0):
            print(f"warning: no price data for {sym}")
            continue
        df = raw[sym].dropna(how="all").rename(columns=str.lower)
        df["symbol"] = sym
        frames.append(df.reset_index().rename(columns={"Date": "date"}))
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    return out[["date", "symbol", "open", "high", "low", "close", "volume"]]


def update_prices(symbols: list[str], start: str = "2010-01-01") -> pd.DataFrame:
    # Adjusted history changes after every dividend/split, so re-download in full rather than append.
    df = download_prices(symbols, start)
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(PRICES_PATH, index=False)
    return df


def load_prices() -> pd.DataFrame:
    return pd.read_parquet(PRICES_PATH)


def close_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Wide matrix of closes: index=date, columns=symbol."""
    return prices.pivot(index="date", columns="symbol", values="close").sort_index()
