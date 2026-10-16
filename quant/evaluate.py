"""Does the divergence signal predict forward returns?

Signal on date T (known at T's close) is compared with returns from T+1 open to T+1+h open,
so there is no look-ahead: you could only have traded after seeing the signal.

Outputs:
  - Rank information coefficient (IC): daily Spearman correlation between signal and forward return.
    Mean IC around 0.02-0.05 with a t-stat above ~2 is a meaningful equity signal; ~0 is noise.
  - Quintile returns: average forward return of the top-20% vs bottom-20% signal buckets.
  - Long-short spread net of costs, split into in-sample and out-of-sample periods.
"""

import numpy as np
import pandas as pd


def forward_returns(opens: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Return from T+1 open to T+1+horizon open, indexed at T."""
    return opens.shift(-1 - horizon) / opens.shift(-1) - 1


def daily_ic(signal: pd.DataFrame, fwd: pd.DataFrame, min_names: int = 20) -> pd.Series:
    s, f = signal.align(fwd, join="inner")
    ics = {}
    for d in s.index:
        x, y = s.loc[d], f.loc[d]
        ok = x.notna() & y.notna()
        if ok.sum() >= min_names:
            ics[d] = x[ok].rank().corr(y[ok].rank())
    return pd.Series(ics, dtype=float)


def quintile_returns(signal: pd.DataFrame, fwd: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    s, f = signal.align(fwd, join="inner")
    rows = []
    for d in s.index:
        x, y = s.loc[d], f.loc[d]
        ok = x.notna() & y.notna()
        if ok.sum() < n * 4:
            continue
        q = pd.qcut(x[ok].rank(method="first"), n, labels=False) + 1
        rows.append(y[ok].groupby(q).mean().rename(d))
    return pd.DataFrame(rows)


def summarize(signal: pd.DataFrame, opens: pd.DataFrame, horizons=(5, 10, 20),
              split: str = "2023-01-01", cost_bps: float = 10.0) -> pd.DataFrame:
    """IC and top-minus-bottom quintile spread per horizon, in-sample vs out-of-sample.

    cost_bps is charged per side on each leg, once per holding period (round trip = 2 x cost on each leg).
    Overlapping daily observations inflate t-stats, so t-stats are computed on non-overlapping samples.
    """
    out = []
    for h in horizons:
        fwd = forward_returns(opens, h)
        ic = daily_ic(signal, fwd)
        qr = quintile_returns(signal, fwd)
        spread = qr[qr.columns.max()] - qr[qr.columns.min()] - 4 * cost_bps / 1e4
        for name, mask_ic, mask_q in [
            ("in-sample", ic.index < split, spread.index < split),
            ("out-of-sample", ic.index >= split, spread.index >= split),
        ]:
            ic_p, sp_p = ic[mask_ic], spread[mask_q]
            ic_nov, sp_nov = ic_p.iloc[::h], sp_p.iloc[::h]
            out.append({
                "horizon_days": h,
                "period": name,
                "dates": len(ic_p),
                "mean_IC": ic_p.mean(),
                "IC_t": ic_nov.mean() / ic_nov.std() * np.sqrt(len(ic_nov)) if len(ic_nov) > 2 else np.nan,
                "hit_rate_IC>0": (ic_p > 0).mean(),
                "top_minus_bottom_net_%": sp_p.mean() * 100,
                "spread_t": sp_nov.mean() / sp_nov.std() * np.sqrt(len(sp_nov)) if len(sp_nov) > 2 else np.nan,
                "annualized_spread_net_%": sp_p.mean() * 252 / h * 100,
            })
    return pd.DataFrame(out)
