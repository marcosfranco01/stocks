"""Test whether the divergence signal (and its components) predict forward returns.

Usage: python scripts/evaluate_signal.py [--split 2023-01-01] [--cost-bps 10]
Writes reports/signal_eval_<date>.md
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant import evaluate, signals  # noqa: E402
from quant.data import dolt_options, prices  # noqa: E402
from quant.universe import MARKET_ETFS, SECTOR_ETFS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="2023-01-01", help="out-of-sample starts here")
    ap.add_argument("--cost-bps", type=float, default=10.0, help="cost per side per leg, basis points")
    args = ap.parse_args()

    px = prices.load_prices()
    closes = prices.close_matrix(px)
    opens = px.pivot(index="date", columns="symbol", values="open").sort_index()
    vol = dolt_options.load_vol_history()
    skew = dolt_options.load_skew()

    start = vol["date"].min()
    closes, opens = closes[closes.index >= start - pd.Timedelta(days=120)], opens[opens.index >= start - pd.Timedelta(days=120)]
    feats = signals.build_features(closes, vol, skew if not skew.empty else None)

    stocks = [c for c in closes.columns if c not in set(SECTOR_ETFS.values()) | set(MARKET_ETFS)]
    tests = {
        "divergence (options_bull - price_trend)": feats["divergence"],
        "options_bull only": feats["options_bull"],
        "-price_trend only (short-term reversal)": -feats["price_trend"],
        "-iv_change only": -feats["iv_change"],
    }
    if "skew_change" in feats:
        tests["-skew_change only"] = -feats["skew_change"]

    sections = []
    for name, sig in tests.items():
        sig = sig[[c for c in stocks if c in sig.columns]]
        # Same dates for every test: only where options data exists.
        sig = sig[(sig.index >= start) & (sig.index <= vol["date"].max())]
        res = evaluate.summarize(sig, opens[sig.columns], split=args.split, cost_bps=args.cost_bps)
        print(f"\n== {name}\n{res.round(4).to_string(index=False)}")
        sections.append(f"## {name}\n\n{res.to_markdown(index=False, floatfmt='.4f')}\n")

    tag = pd.Timestamp.today().strftime("%Y-%m-%d")
    skew_note = (f"skew sampled on {skew['date'].nunique()} dates" if not skew.empty else "no skew data (IV only)")
    md = [
        f"# Divergence signal evaluation ({tag})",
        "",
        f"- Data: {vol['date'].min():%Y-%m-%d} to {vol['date'].max():%Y-%m-%d}; {skew_note}",
        f"- Universe: {len(stocks)} stocks (ETFs excluded). Out-of-sample from {args.split}.",
        f"- Entry next day's open; cost {args.cost_bps:g} bps per side per leg.",
        "- IC = daily rank correlation of signal vs forward return. t-stats use non-overlapping periods.",
        "- Survivorship bias: universe is today's large caps, so absolute returns are optimistic; "
        "the long-short spread is less affected.",
        "",
        *sections,
        "> Hypothetical research results. Not investment advice.",
    ]
    out = ROOT / "reports" / f"signal_eval_{tag}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(md) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
