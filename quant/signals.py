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


def _wide(long: pd.DataFrame, col: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    w = long.pivot_table(index="date", columns="symbol", values=col)
    return w.reindex(index)


def build_features(closes: pd.DataFrame, vol: pd.DataFrame, skew: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Return wide (date x symbol) frames for each feature, aligned to trading dates in `closes`."""
    idx = closes.index
    trend = price_trend(closes)

    iv = _wide(vol, "iv_current", idx).ffill(limit=3)
    iv_chg = np.log(iv / iv.shift(CHANGE_DAYS))

    feats = {"price_trend": trend, "iv": iv, "iv_change": iv_chg}

    if skew is not None and not skew.empty:
        sk = _wide(skew, "skew_25d", idx)
        # Skew may be sampled every few days: carry forward up to one sample gap, then difference samples.
        sk = sk.ffill(limit=CHANGE_DAYS)
        feats["skew"] = sk
        feats["skew_change"] = sk - sk.shift(CHANGE_DAYS)

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
