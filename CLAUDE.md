# stocks: quant research and paper trading

Personal quant project: research US stock/ETF strategies, backtest them honestly, then paper trade on Alpaca.

## Layout
- `quant/universe.py` - symbols: 11 SPDR sector ETFs, SPY/QQQ/IWM, ~100 liquid optionable stocks by sector
- `quant/data/prices.py` - Yahoo Finance daily bars -> `data/prices.parquet`
- `quant/data/dolt_options.py` - DoltHub `post-no-preference/options` IV, HV and 25-delta skew -> `data/*.parquet`
- `quant/signals.py` - price-vs-options divergence signal
- `scripts/update_data.py` - refresh/backfill data (resumable)
- `scripts/scan.py` - daily sector + stock divergence scan -> `reports/scan_<date>.md`
- `.claude/skills/` - vendored skills: backtesting, risk metrics, position sizing, Alpaca backtest + paper trading

## Setup
```
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python scripts/update_data.py all   # first run: ~30 min vol history, ~3 h sampled skew
python scripts/scan.py
```

## Rules
- **No look-ahead.** Signals on date T use data known at T's close; fills happen at T+1 open or later.
- **Include costs.** Every backtest models commission + slippage; report results at 1x and 2x cost.
- **Out-of-sample.** Tune on an early period, evaluate on a later untouched one. Report both.
- **Paper only.** Alpaca clients are constructed with `paper=True` as a literal. Never place live orders.
- **Secrets** come from environment variables (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`). Never print, log or commit them.
- `data/` and `logs/` are regenerated, not committed. `reports/` is committed.
- Research output is not investment advice; say so in reports.

## Data caveats
- DoltHub options data has IV, Greeks, bid/ask but **no volume or open interest**.
- DoltHub's SQL API caps results at 1000 rows and times out on option_chain date-range scans: query one date at a time.
- Some symbols (QQQ, IWM, BABA, ARM, OSCR, PDD, SNAP, SOFI) are missing from the DoltHub mirror.
- Universe is today's large caps -> survivorship bias in long backtests. Treat results as optimistic.
