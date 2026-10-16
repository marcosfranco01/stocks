"""Download / extend all cached data. Safe to interrupt and re-run.

Usage:
  python scripts/update_data.py prices
  python scripts/update_data.py vol
  python scripts/update_data.py skew [--every 5]
  python scripts/update_data.py all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quant.data import dolt_options, prices  # noqa: E402
from quant.universe import all_symbols  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["prices", "vol", "skew", "all"])
    ap.add_argument("--every", type=int, default=5, help="skew: sample every Nth trading day")
    ap.add_argument("--start", default="2019-01-01")
    args = ap.parse_args()
    syms = all_symbols()

    if args.what in ("prices", "all"):
        df = prices.update_prices(syms)
        print(f"prices: {df['symbol'].nunique()} symbols, {df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}")
    if args.what in ("vol", "all"):
        df = dolt_options.update_vol_history(syms, start=args.start)
        print(f"vol_history: {len(df)} rows through {df['date'].max():%Y-%m-%d}")
    if args.what in ("skew", "all"):
        df = dolt_options.update_skew(syms, start=args.start, every_n_days=args.every)
        print(f"skew: {len(df)} rows through {df['date'].max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
