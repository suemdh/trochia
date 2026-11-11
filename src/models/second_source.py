"""
Independent second price source: Alpha Vantage's Commodities API, cross-checked
against the prices this app trains on and displays.

What AV actually returns (inspected directly, 2026-11-02 -- not assumed):
  - WTI, Brent, Natural Gas: DAILY EIA spot prices -- the same series we
    download from FRED, so this checks our download and scaling, not EIA.
  - Corn, Wheat: MONTHLY Gulf export price in $/metric ton -- a different
    market from the USDA cash bids we use (Iowa corn, Kansas City wheat),
    with a structural basis/transport gap.

So the tolerance depends on how comparable the series is:
  - "same":    15% -- a real mismatch means something is wrong with our data.
  - "related": 50% -- only catches gross errors (wrong unit, 2x/100x scaling,
               wrong contract), which is what this check exists for; a basis
               gap between two genuinely different markets is not an error.
Tuning a tolerance until mismatches disappear would be fudging; these are
set by what each series is, and the reason is stated per row.

AV's own "unit" field is checked on every call -- if AV ever changes a
series' unit, the row reports that instead of silently mis-scaling.

The other commodities have no second source here (stooq.com, tried first,
is now behind a JS challenge wall). They report "n/a", never a fake pass.

Needs ALPHA_VANTAGE_API_KEY in .env. Free tier: 25 requests/day and 1/second,
so responses are disk-cached for a day.

Usage:
    python src/models/second_source.py
"""
import json
import os
import sys
import time

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

load_dotenv(os.path.join(ROOT, ".env"))
AV_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
AV_URL = "https://www.alphavantage.co/query"

LB_PER_METRIC_TON = 2204.62
# Trochiá name -> (AV function, AV's unit as it reports it, scale to our unit, comparability)
AV_COMMODITIES = {
    "Crude Oil (WTI)":   ("WTI",         "dollars per barrel",      1.0,                     "same"),
    "Crude Oil (Brent)": ("BRENT",       "dollars per barrel",      1.0,                     "same"),
    "Natural Gas":       ("NATURAL_GAS", "dollars per million BTU", 1.0,                     "same"),
    "Wheat (USDA Cash)": ("WHEAT",       "dollar per metric ton",   60 / LB_PER_METRIC_TON,  "related"),  # 60 lb/bu
    "Corn":              ("CORN",        "dollar per metric ton",   56 / LB_PER_METRIC_TON,  "related"),  # 56 lb/bu
}
TOLERANCE = {"same": 0.15, "related": 0.50}
WHY = {"same": "same EIA benchmark",
       "related": "different market (export price vs US cash bid) -- gross-error check only"}

CACHE_DIR = os.path.join(ROOT, "data", "raw")
CACHE_TTL_SECONDS = 86400
_last_call = [0.0]


def fetch_av_raw(function: str) -> dict:
    """Raw AV JSON, disk-cached for a day, spaced >=1.2s apart. Failures aren't cached."""
    path = os.path.join(CACHE_DIR, f"av_{function.lower()}.json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_TTL_SECONDS:
        with open(path) as f:
            return json.load(f)
    wait = 1.2 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    resp = requests.get(AV_URL, params={"function": function, "interval": "daily",
                                        "apikey": AV_API_KEY}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "data" in data:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    return data


def our_value_on(name: str, date_str: str, interval: str) -> float | None:
    """Our own price for the SAME date as AV's data point -- the first value
    on/after that date, or that month's average for a monthly AV series.
    Comparing AV's Oct-27 value against today's price would test market
    movement, not whether the two sources agree."""
    from models.backfill_volatility import load_series
    df = load_series(name)
    d = pd.Timestamp(date_str)
    if interval == "monthly":
        vals = df[(df["date"] >= d) & (df["date"] < d + pd.offsets.MonthBegin(1))]["value"]
        return round(float(vals.mean()), 4) if len(vals) else None
    vals = df[(df["date"] >= d) & (df["date"] <= d + pd.Timedelta(days=6))]["value"]
    return round(float(vals.iloc[0]), 4) if len(vals) else None


def check(name: str, our_price: float) -> dict:
    """Cross-check one commodity, like-for-like by date. our_price is today's
    displayed price, reported for context only. Status: PASS / MISMATCH / n/a."""
    row = {"commodity": name, "our_price": our_price, "our_same_date": None, "av_price": None,
           "av_as_of": None, "diff_pct": None, "status": "n/a",
           "note": "no second source for this commodity"}
    if name not in AV_COMMODITIES:
        return row
    func, unit, scale, kind = AV_COMMODITIES[name]
    if not AV_API_KEY:
        return {**row, "note": "ALPHA_VANTAGE_API_KEY not set"}
    try:
        data = fetch_av_raw(func)
    except Exception as e:
        return {**row, "note": f"request failed: {e}"}
    if "data" not in data:
        return {**row, "note": f"AV error: {str(data.get('Information') or data.get('Note') or data)[:100]}"}
    if data.get("unit") != unit:
        return {**row, "status": "MISMATCH",
                "note": f"AV unit changed: expected {unit!r}, got {data.get('unit')!r} -- fix scale before trusting"}
    point = next((p for p in data["data"] if p.get("value") not in (None, ".", "")), None)
    if point is None:
        return {**row, "note": "AV returned no usable data points"}

    av_price = round(float(point["value"]) * scale, 4)
    interval = data.get("interval", "daily")
    try:
        ours = our_value_on(name, point["date"], interval)
    except Exception as e:
        return {**row, "av_price": av_price, "av_as_of": point.get("date"),
                "note": f"couldn't fetch our own price for {point.get('date')}: {e}"}
    if ours is None:
        return {**row, "av_price": av_price, "av_as_of": point.get("date"),
                "note": f"no price in our source for {point.get('date')}"}
    diff = abs(ours - av_price) / (av_price + 1e-9)
    return {**row, "our_same_date": ours, "av_price": av_price, "av_as_of": point.get("date"),
            "diff_pct": round(diff, 4), "status": "PASS" if diff <= TOLERANCE[kind] else "MISMATCH",
            "note": f"{WHY[kind]}; {interval}; tolerance {TOLERANCE[kind]:.0%}"}


def run() -> pd.DataFrame:
    path = os.path.join(ROOT, "outputs", "forecasts.csv")
    forecasts = pd.read_csv(path)
    prices = dict(zip(forecasts["commodity"], forecasts["current_price"]))
    result = pd.DataFrame([check(n, float(prices[n])) for n in AV_COMMODITIES if n in prices])
    result.to_csv(os.path.join(ROOT, "outputs", "second_source_report.csv"), index=False)
    with pd.option_context("display.max_colwidth", 70, "display.width", 250):
        print(result.to_string(index=False))
    return result


if __name__ == "__main__":
    result = run()
    sys.exit(1 if (result["status"] == "MISMATCH").any() else 0)
