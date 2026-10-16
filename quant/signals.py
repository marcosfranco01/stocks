"""Price-vs-options divergence signal.

Idea: price shows what already happened; options pricing shows what traders are paying to bet on next.
When they agree there is no edge. When they disagree, flag it.

Per symbol and date:
  price_trend  = 20-day return divided by its expected size (20-day realized vol scaled to 20 days).
                 A t-stat-like number: +2 = unusually strong rally, -2 = unusually strong selloff.
  iv_change    = log change in at-the-money implied volatility over ~5 trading days.
                 Rising IV = traders paying up for options (usually fear).
  skew_change  = change in 25-delta put IV minus call IV over ~5 trading days.
                 Rising = traders paying more for downside protection than upside.
  options_bull = -(z(iv_change) + z(skew_change)), cross-sectionally standardized each day.
                 Positive = options market getting calmer / less hedged = bullish positioning.
  divergence   = z(options_bull) - z(price_trend).
                 Large positive: price weak but options turning bullish  -> possible accumulation.
                 Large negative: price strong but options turning bearish -> possible distribution.

All inputs on date T use only data known at T's close. Trade on T+1 at the earliest.
"""

import numpy as np
import pandas as pd

TREND_DAYS = 20
CHANGE_DAYS = 5


def _cs_z(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score per date (row), clipped to +/-3 to limit outliers."""
    z = df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1), axis=0)
    return z.clip(-3, 3)


def price_trend(closes: pd.DataFrame, days: int = TREND_DAYS) -> pd.DataFrame:
    logret = np.log(closes).diff()
    ret_n = np.log(closes / closes.shift(days))
    expected = logret.rolling(60, min_periods=40).std() * np.sqrt(days)
    return ret_n / expected


def _to_trading_day(dates: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Map each date to the last trading day on or before it (e.g. Saturday snapshots -> Friday close)."""
    pos = index.searchsorted(pd.to_datetime(dates), side="right") - 1
    return pd.Series(index[pos.clip(0)], index=dates.index).where(pos >= 0)


def _wide(long: pd.DataFrame, col: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    df = long.assign(date=_to_trading_day(long["date"], index)).dropna(subset=["date"])
    w = df.pivot_table(index="date", columns="symbol", values=col, aggfunc="last")
    return w.reindex(index)


def _sampled_change(w: pd.DataFrame, max_gap: int, hold: int) -> pd.DataFrame:
    """Change between consecutive observations of a sparsely sampled series, per symbol.

    Only counts pairs no more than `max_gap` trading days apart; the change is known on the later
    observation date and carried forward `hold` days (it is stale after that).
    """
    out = pd.DataFrame(index=w.index, columns=w.columns, dtype=float)
    pos = pd.Series(range(len(w.index)), index=w.index)
    for sym in w.columns:
        s = w[sym].dropna()
        if len(s) < 2:
            continue
        gap = pos[s.index].diff()
        chg = s.diff().where(gap <= max_gap)
        out[sym] = chg.reindex(w.index)
    return out.ffill(limit=hold)


def build_features(closes: pd.DataFrame, vol: pd.DataFrame, skew: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Return wide (date x symbol) frames for each feature, aligned to trading dates in `closes`."""
    idx = closes.index
    trend = price_trend(closes)

    # IV is daily from 2025 but sparser before (weekly in 2019): use change between observations
    # at least CHANGE_DAYS apart where possible, via log-IV differences on the observation grid.
    iv_raw = _wide(vol, "iv_current", idx)
    iv = iv_raw.ffill(limit=CHANGE_DAYS)
    iv_chg = np.log(iv / iv.shift(CHANGE_DAYS))
    # Where daily-ish data is missing, fall back to change between consecutive observations.
    iv_chg = iv_chg.fillna(_sampled_change(np.log(iv_raw), max_gap=10, hold=CHANGE_DAYS))

    feats = {"price_trend": trend, "iv": iv, "iv_change": iv_chg}

    if skew is not None and not skew.empty:
        sk_raw = _wide(skew, "skew_25d", idx)
        feats["skew"] = sk_raw.ffill(limit=CHANGE_DAYS)
        # Skew is sampled every ~5 trading days: change between consecutive samples up to ~3 weeks apart.
        feats["skew_change"] = _sampled_change(sk_raw, max_gap=15, hold=CHANGE_DAYS)

    z_iv = _cs_z(iv_chg)
    if "skew_change" in feats:
        z_sk = _cs_z(feats["skew_change"])
        # Where skew is missing, fall back to IV alone.
        options_bear = (z_iv + z_sk.fillna(z_iv)) / 2
    else:
        options_bear = z_iv
    feats["options_bull"] = _cs_z(-options_bear)
    feats["divergence"] = feats["options_bull"] - _cs_z(trend)
    return feats


def snapshot(feats: dict[str, pd.DataFrame], date: pd.Timestamp) -> pd.DataFrame:
    """One row per symbol for a given date."""
    cols = {name: f.loc[date] for name, f in feats.items() if date in f.index}
    return pd.DataFrame(cols).dropna(subset=["divergence"])


def label(row: pd.Series, threshold: float = 1.5) -> str:
    d = row["divergence"]
    if d >= threshold:
        return "BULLISH DIVERGENCE: price weak, options calming"
    if d <= -threshold:
        return "BEARISH DIVERGENCE: price strong, options hedging"
    return ""
