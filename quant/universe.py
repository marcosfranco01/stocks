"""Trading universe: SPDR sector ETFs, broad-market ETFs, and liquid optionable stocks by sector."""

SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

MARKET_ETFS = ["SPY", "QQQ", "IWM"]

STOCKS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "AMD", "ORCL", "CRM", "ADBE", "INTC", "MU",
                   "QCOM", "TXN", "AMAT", "LRCX", "PLTR", "SMCI", "ARM", "NOW", "PANW", "CSCO"],
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "C", "SCHW", "V", "MA", "PYPL", "COIN", "HOOD", "SOFI", "BLK"],
    "Health Care": ["UNH", "LLY", "JNJ", "PFE", "MRK", "ABBV", "TMO", "CVS", "OSCR", "HIMS", "MRNA", "ISRG"],
    "Energy": ["XOM", "CVX", "COP", "OXY", "SLB", "HAL", "DVN", "EOG"],
    "Industrials": ["BA", "CAT", "GE", "HON", "UPS", "DE", "LMT", "RTX", "UBER"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "LULU", "BABA", "PDD", "CMG", "F", "GM"],
    "Consumer Staples": ["WMT", "COST", "PG", "KO", "PEP", "TGT", "PM"],
    "Utilities": ["NEE", "DUK", "SO", "VST", "CEG"],
    "Materials": ["LIN", "FCX", "NEM", "DOW", "NUE"],
    "Real Estate": ["PLD", "AMT", "O", "SPG"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "T", "VZ", "RDDT", "SNAP", "ROKU"],
}

SYMBOL_SECTOR = {s: sector for sector, syms in STOCKS.items() for s in syms}
SYMBOL_SECTOR.update({etf: sector for sector, etf in SECTOR_ETFS.items()})


def all_symbols() -> list[str]:
    stocks = [s for syms in STOCKS.values() for s in syms]
    return sorted(set(MARKET_ETFS + list(SECTOR_ETFS.values()) + stocks))
