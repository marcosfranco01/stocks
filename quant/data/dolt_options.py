"""Options-implied data from the free DoltHub mirror `post-no-preference/options`.

Tables used:
  volatility_history: daily per-symbol implied (iv_current) and historical (hv_current) volatility, 2019-present.
  option_chain:       per-contract bid/ask/IV/Greeks. No volume or open interest.

The SQL API returns at most 1000 rows per query and times out on date-range scans of option_chain,
so we query one date at a time and cache to parquet, resuming from the last cached date.
"""

import time
from pathlib import Path

import pandas as pd
import requests

API = "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
VOL_PATH = DATA_DIR / "vol_history.parquet"
SKEW_PATH = DATA_DIR / "skew.parquet"

VOL_COLS = ["iv_current", "hv_current", "iv_week_ago", "hv_week_ago", "iv_year_high", "iv_year_low"]


def query(sql: str, retries: int = 4) -> list[dict]:
    for attempt in range(retries):
        try:
            r = requests.get(API, params={"q": sql}, timeout=120)
            j = r.json()
            if j.get("query_execution_status") == "Error":
                raise RuntimeError(j.get("query_execution_message"))
            return j.get("rows", [])
        except (requests.RequestException, RuntimeError, ValueError) as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  dolthub query failed ({e}); retrying in {wait}s")
            time.sleep(wait)
    return []


def _in_list(symbols: list[str]) -> str:
    return ",".join(f"'{s}'" for s in symbols)


def available_dates(start: str, end: str | None = None) -> list[str]:
    # SPY has a row on every date the table was updated; use it as the calendar.
    end_clause = f" and date <= '{end}'" if end else ""
    dates: list[str] = []
    while True:  # page past the 1000-row API cap
        lower = f"date > '{dates[-1]}'" if dates else f"date >= '{start}'"
        rows = query(f"select date from volatility_history where act_symbol='SPY' and {lower}{end_clause} order by date limit 1000")
        dates += [r["date"] for r in rows]
        if len(rows) < 1000:
            return dates


def fetch_vol_day(date: str, symbols: list[str]) -> pd.DataFrame:
    cols = ", ".join(["date", "act_symbol"] + VOL_COLS)
    rows = query(f"select {cols} from volatility_history where date='{date}' and act_symbol in ({_in_list(symbols)})")
    if len(rows) >= 1000:
        raise RuntimeError(f"{date}: hit the 1000-row API cap; split the symbol list")
    return pd.DataFrame(rows)


def update_vol_history(symbols: list[str], start: str = "2019-01-01") -> pd.DataFrame:
    """Backfill / extend data/vol_history.parquet. Safe to interrupt and re-run."""
    DATA_DIR.mkdir(exist_ok=True)
    cached = pd.read_parquet(VOL_PATH) if VOL_PATH.exists() else pd.DataFrame()
    if not cached.empty:
        start = (cached["date"].max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    dates = available_dates(start)
    print(f"vol_history: {len(dates)} new dates from {start}")
    batch = []
    for i, d in enumerate(dates, 1):
        batch.append(fetch_vol_day(d, symbols))
        if i % 50 == 0 or i == len(dates):
            cached = _append(cached, batch, VOL_PATH)
            batch = []
            print(f"  {i}/{len(dates)} through {d}")
    return cached


def _append(cached: pd.DataFrame, batch: list[pd.DataFrame], path: Path) -> pd.DataFrame:
    new = pd.concat([b for b in batch if not b.empty], ignore_index=True) if batch else pd.DataFrame()
    if new.empty:
        return cached
    new = new.rename(columns={"act_symbol": "symbol"})
    new["date"] = pd.to_datetime(new["date"])
    for c in new.columns.difference(["date", "symbol"]):
        new[c] = pd.to_numeric(new[c], errors="coerce")
    out = pd.concat([cached, new], ignore_index=True).drop_duplicates(["date", "symbol"], keep="last")
    out = out.sort_values(["date", "symbol"]).reset_index(drop=True)
    out.to_parquet(path, index=False)
    return out


def fetch_skew_day(date: str, symbols: list[str], min_dte: int = 20, max_dte: int = 60) -> pd.DataFrame:
    """25-delta risk reversal per symbol: put IV minus call IV near 25 delta, 20-60 days to expiry.

    Positive and rising = traders paying up for downside protection (bearish positioning).
    """
    frames = []
    for i in range(0, len(symbols), 20):  # chunk to stay under the 1000-row cap
        chunk = symbols[i:i + 20]
        rows = query(
            "select act_symbol, expiration, call_put, bid, ask, vol, delta from option_chain "
            f"where date='{date}' and act_symbol in ({_in_list(chunk)}) and bid > 0 "
            f"and expiration between date_add('{date}', interval {min_dte} day) and date_add('{date}', interval {max_dte} day) "
            "and ((delta between 0.10 and 0.40) or (delta between -0.40 and -0.10))"
        )
        if len(rows) >= 1000:
            print(f"  warning: {date} skew chunk hit the 1000-row cap")
        frames.append(pd.DataFrame(rows))
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return df
    for c in ["bid", "ask", "vol", "delta"]:
        df[c] = pd.to_numeric(df[c])
    # Drop unquoted / very wide markets: their IV and delta are unreliable.
    mid = (df["bid"] + df["ask"]) / 2
    df = df[(df["ask"] - df["bid"]) / mid <= 0.5].copy()
    # Per expiration and side, keep the contract closest to 25 delta.
    df["dist"] = (df["delta"].abs() - 0.25).abs()
    best = df.loc[df.groupby(["act_symbol", "expiration", "call_put"])["dist"].idxmin()]
    iv = best.pivot_table(index=["act_symbol", "expiration"], columns="call_put", values="vol")
    if not {"Call", "Put"} <= set(iv.columns):
        return pd.DataFrame()
    per_exp = (iv["Put"] - iv["Call"]).dropna().rename("skew_25d").reset_index()
    # Use the expiration closest to 30 days out.
    per_exp["dte_gap"] = (pd.to_datetime(per_exp["expiration"]) - pd.Timestamp(date)).dt.days.sub(30).abs()
    out = per_exp.loc[per_exp.groupby("act_symbol")["dte_gap"].idxmin(), ["act_symbol", "skew_25d"]]
    out["date"] = date
    return out.reset_index(drop=True)


def update_skew(symbols: list[str], start: str = "2019-01-01", every_n_days: int = 5) -> pd.DataFrame:
    """Backfill skew on a sample of dates (every Nth trading day) - full daily history is ~10h of queries."""
    cached = pd.read_parquet(SKEW_PATH) if SKEW_PATH.exists() else pd.DataFrame()
    # Use the local vol-history calendar when available (the remote calendar query can time out).
    if VOL_PATH.exists():
        cal = sorted(pd.read_parquet(VOL_PATH, columns=["date"])["date"].dt.strftime("%Y-%m-%d").unique())
        cal = [d for d in cal if d >= start]
    else:
        cal = available_dates(start)
    have = set(cached["date"].dt.strftime("%Y-%m-%d")) if not cached.empty else set()
    dates = [d for d in cal[::every_n_days] if d not in have]
    print(f"skew: {len(dates)} sampled dates still to fetch from {start}")
    batch = []
    for i, d in enumerate(dates, 1):
        batch.append(fetch_skew_day(d, symbols))
        if i % 10 == 0 or i == len(dates):
            cached = _append(cached, batch, SKEW_PATH)
            batch = []
            print(f"  {i}/{len(dates)} through {d}")
    return cached


def load_vol_history() -> pd.DataFrame:
    return pd.read_parquet(VOL_PATH)


def load_skew() -> pd.DataFrame:
    return pd.read_parquet(SKEW_PATH) if SKEW_PATH.exists() else pd.DataFrame(columns=["date", "symbol", "skew_25d"])
