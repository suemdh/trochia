"""
Fetch live commodity futures prices from Yahoo Finance via yfinance.
No API key required. Prices are exchange-delayed ~15 min (standard for futures).
Uses fast_info.last_price for the most current tick available.
Cache to data/raw/yfinance_live.json with 2-min TTL.
"""
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
CACHE_FILE = os.path.join(RAW_DIR, "yfinance_live.json")
CACHE_TTL_SECONDS = 120  # 2 minutes — get the freshest available price

CONTRACT_CACHE_FILE = os.path.join(RAW_DIR, "yfinance_contracts.json")
CONTRACT_CACHE_TTL_SECONDS = 86400  # 1 day -- the active contract only rolls a
                                     # few times a year, and t.info is ~15x
                                     # slower per ticker than fast_info

# ticker -> (display_name, unit, scale_factor)
# scale_factor converts raw price to displayed unit
# (e.g. grain futures quote in cents/bushel; divide by 100 for $/bushel)
TICKERS = {
    "BZ=F":  ("Crude Oil (Brent)",  "$/barrel",        1.0),
    "CL=F":  ("Crude Oil (WTI)",    "$/barrel",        1.0),
    "NG=F":  ("Natural Gas",        "$/MMBtu",         1.0),
    "RB=F":  ("Gasoline (RBOB)",    "$/gal",           1.0),
    "HO=F":  ("Heating Oil",        "$/gal",           1.0),
    "ZW=F":  ("Wheat",              "$/bushel",        0.01),  # quoted ¢/bushel
    "ZC=F":  ("Corn",               "$/bushel",        0.01),
    "ZS=F":  ("Soybeans",           "$/bushel",        0.01),
    "ZL=F":  ("Soybean Oil",        "$/lb",            0.01),
    "ZO=F":  ("Oats",               "$/bushel",        0.01),
    "ZR=F":  ("Rough Rice",         "$/cwt",           1.0),
    "KC=F":  ("Coffee (Arabica)",   "$/lb",            0.01),
    "CC=F":  ("Cocoa",              "$/metric ton",    1.0),
    "SB=F":  ("Sugar (11)",         "$/lb",            0.01),
    "CT=F":  ("Cotton",             "$/lb",            0.01),
    "OJ=F":  ("Orange Juice",       "$/lb",            0.01),
    "LE=F":  ("Live Cattle",        "$/lb",            0.01),
    "HE=F":  ("Lean Hogs",          "$/lb",            0.01),
    "GF=F":  ("Feeder Cattle",      "$/lb",            0.01),
    "HG=F":  ("Copper",             "$/lb",            1.0),
    "GC=F":  ("Gold",               "$/troy oz",       1.0),
    "SI=F":  ("Silver",             "$/troy oz",       1.0),
}

# Reverse map: name -> ticker (for lookup)
NAME_TO_TICKER = {v[0]: k for k, v in TICKERS.items()}


def _cache_is_fresh() -> bool:
    if not os.path.exists(CACHE_FILE):
        return False
    age = time.time() - os.path.getmtime(CACHE_FILE)
    return age < CACHE_TTL_SECONDS


def _fetch_ticker_price(ticker: str, scale: float) -> tuple[float | None, float | None, str]:
    """
    Get the most current price for a single ticker using fast_info.
    fast_info.last_price is the last traded price (exchange-delayed ~15 min).
    Falls back to recent 1-min bar if fast_info fails.
    Returns (price, prev_close, as_of_str).
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        raw_price = fi.last_price
        raw_prev  = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if raw_price and raw_price > 0:
            return round(raw_price * scale, 4), round(raw_prev * scale, 4) if raw_prev else None, as_of
    except Exception:
        pass

    # Fallback: 1-min bar from today
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d", interval="1m", auto_adjust=True)
        if not hist.empty:
            raw_price = float(hist["Close"].dropna().iloc[-1])
            as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            return round(raw_price * scale, 4), None, as_of
    except Exception:
        pass

    return None, None, ""


def _contract_cache_is_fresh() -> bool:
    if not os.path.exists(CONTRACT_CACHE_FILE):
        return False
    return time.time() - os.path.getmtime(CONTRACT_CACHE_FILE) < CONTRACT_CACHE_TTL_SECONDS


def fetch_contract_symbols(force_refresh: bool = False) -> dict:
    """
    Returns {ticker: "HEZ26.CME"} -- the exact active contract Yahoo is
    quoting under a continuous symbol like "HE=F", from Ticker.info's
    underlyingSymbol field (confirmed present for CME/CBOT/COMEX futures by
    direct inspection, not assumed). "HE=F" always means "whichever contract
    is currently active," which rolls several times a year -- this is the
    one place that gets resolved to the specific month/year code for display,
    so a card can say "HEZ26" instead of a continuous ticker that silently
    refers to a different contract next quarter.
    """
    if not force_refresh and _contract_cache_is_fresh():
        try:
            with open(CONTRACT_CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    results = {}
    for ticker in TICKERS:
        try:
            info = yf.Ticker(ticker).info
            contract = info.get("underlyingSymbol") or info.get("underlyingExchangeSymbol")
            if contract:
                results[ticker] = contract
        except Exception:
            pass

    if results:  # don't clobber a good cache with an all-failed fetch
        os.makedirs(RAW_DIR, exist_ok=True)
        try:
            with open(CONTRACT_CACHE_FILE, "w") as f:
                json.dump(results, f, indent=2)
        except Exception:
            pass
    return results


def fetch_live_prices(force_refresh: bool = False) -> dict:
    """
    Returns dict: {commodity_name: {"price": float, "prev_close": float,
                                     "unit": str, "source": "yfinance",
                                     "as_of": str, "ticker": str}}
    Uses fast_info.last_price for the most current available tick (~15-min exchange delay).
    Cache TTL is 2 minutes.
    """
    if not force_refresh and _cache_is_fresh():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    os.makedirs(RAW_DIR, exist_ok=True)
    results = {}

    for ticker, (name, unit, scale) in TICKERS.items():
        price, prev_close, as_of = _fetch_ticker_price(ticker, scale)
        if price is None:
            continue
        results[name] = {
            "price":        price,
            "prev_close":   prev_close,
            "unit":         unit,
            "source":       "yfinance",
            "as_of":        as_of,
            "ticker":       ticker,
            "is_live":      True,
            "is_estimated": False,
        }

    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(results, f, indent=2)
    except Exception:
        pass

    return results


def fetch_history(ticker: str, period: str = "10y", interval: str = "1wk") -> pd.DataFrame:
    """Download weekly historical data for a single ticker. Returns df with [date, value]."""
    try:
        raw = yf.download(ticker, period=period, interval=interval,
                          auto_adjust=True, progress=False)
        if raw.empty:
            return pd.DataFrame()
        df = raw[["Close"]].copy()
        df.index = pd.to_datetime(df.index)
        df = df.rename(columns={"Close": "value"})
        df.index.name = "date"
        _, _, scale = TICKERS.get(ticker, (None, None, 1.0))
        df["value"] = df["value"] * scale
        df = df.dropna().reset_index()
        return df
    except Exception as e:
        print(f"  Warning: history fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def save_all_history():
    """Download and save 2-year weekly history for all tickers to data/raw/."""
    os.makedirs(RAW_DIR, exist_ok=True)
    for ticker, (name, unit, scale) in TICKERS.items():
        safe_name = name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        out_path = os.path.join(RAW_DIR, f"yfinance_{safe_name}.csv")
        print(f"  Fetching history: {name} ({ticker})")
        df = fetch_history(ticker)
        if not df.empty:
            df.to_csv(out_path, index=False)
            print(f"    Saved {len(df)} rows to {out_path}")
        else:
            print(f"    No data for {ticker}")
        time.sleep(0.5)


if __name__ == "__main__":
    print("Fetching live prices...")
    prices = fetch_live_prices(force_refresh=True)
    for name, info in prices.items():
        print(f"  {name:30s}  {info['unit']:18s}  ${info['price']:.4f}  (as of {info['as_of']})")
    print(f"\nTotal: {len(prices)} commodities")

    print("\nSaving 2-year weekly history...")
    save_all_history()
