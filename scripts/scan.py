"""Daily market scan: sectors and stocks ranked by price-vs-options divergence.

Usage: python scripts/scan.py [--date YYYY-MM-DD]
Writes reports/scan_<date>.md and reports/scan_<date>.csv.
This tells you where to look, not what to buy.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant import signals  # noqa: E402
from quant.data import dolt_options, prices  # noqa: E402
from quant.universe import SECTOR_ETFS, SYMBOL_SECTOR, all_symbols  # noqa: E402

REPORTS = ROOT / "reports"


def ensure_recent_skew(skew: pd.DataFrame, dates: list[pd.Timestamp], syms: list[str]) -> pd.DataFrame:
    """Make sure skew exists for the scan date and CHANGE_DAYS before it (the backfill is only sampled)."""
    have = set(pd.to_datetime(skew["date"])) if not skew.empty else set()
    new = []
    for d in dates:
        if d not in have:
            print(f"fetching skew for {d:%Y-%m-%d} ...")
            new.append(dolt_options.fetch_skew_day(d.strftime("%Y-%m-%d"), syms))
    if not new:
        return skew
    return dolt_options._append(skew, new, dolt_options.SKEW_PATH)


def fmt(df: pd.DataFrame) -> str:
    return df.to_markdown(floatfmt="+.2f")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    args = ap.parse_args()

    syms = all_symbols()
    closes = prices.close_matrix(prices.load_prices())
    vol = dolt_options.load_vol_history()

    # Scan date = latest date that has both prices and options data, unless given.
    last_common = min(closes.index.max(), vol["date"].max())
    date = pd.Timestamp(args.date) if args.date else last_common
    trading_days = closes.index[closes.index <= date]
    prior = trading_days[-1 - signals.CHANGE_DAYS]
    skew = ensure_recent_skew(dolt_options.load_skew(), [date, prior], syms)

    feats = signals.build_features(closes, vol, skew)
    snap = signals.snapshot(feats, date)
    snap["sector"] = snap.index.map(SYMBOL_SECTOR)
    snap["signal"] = snap.apply(signals.label, axis=1)

    etfs = set(SECTOR_ETFS.values())
    stocks = snap[~snap.index.isin(etfs | {"SPY", "QQQ", "IWM"})]

    sector = stocks.groupby("sector")[["price_trend", "options_bull", "divergence"]].mean()
    etf_div = snap.loc[snap.index.isin(etfs), ["sector", "divergence"]].set_index("sector")["divergence"]
    sector["etf_divergence"] = etf_div
    sector["n_stocks"] = stocks.groupby("sector").size()
    sector = sector.sort_values("divergence", ascending=False)

    cols = ["sector", "price_trend", "iv", "iv_change", "skew", "skew_change", "options_bull", "divergence", "signal"]
    cols = [c for c in cols if c in stocks.columns]
    ranked = stocks.sort_values("divergence", ascending=False)[cols]

    REPORTS.mkdir(exist_ok=True)
    tag = f"{date:%Y-%m-%d}"
    ranked.to_csv(REPORTS / f"scan_{tag}.csv")

    md = [
        f"# Market scan {tag}",
        "",
        "Divergence = options sentiment minus price trend (both standardized across the universe).",
        "Positive: price weak but options calming (possible accumulation). "
        "Negative: price strong but options hedging (possible distribution).",
        "**Unvalidated research signal, not a recommendation.** See `reports/` backtests before trusting it.",
        "",
        "## Sectors",
        fmt(sector),
        "",
        "## Top 10 bullish divergence",
        fmt(ranked.head(10)),
        "",
        "## Top 10 bearish divergence",
        fmt(ranked.tail(10).iloc[::-1]),
        "",
        f"Universe: {len(stocks)} stocks with options data on {tag}. "
        "Data: Yahoo Finance prices; DoltHub post-no-preference/options IV and skew.",
    ]
    out = REPORTS / f"scan_{tag}.md"
    out.write_text("\n".join(md) + "\n")
    print("\n".join(md[:3]))
    print(fmt(sector))
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
