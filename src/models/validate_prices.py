"""
Prints a per-commodity validation table: displayed price, source, timestamp,
unit, and whether the price is plausible for that commodity (commodity_maps.PLAUSIBLE_RANGE).

Three checks, none of which trust a single number blindly:
  1. Range check: is the price plausible for this commodity at all (catches
     unit errors, wrong contract, wrong series, a garbage tick)?
  2. Continuity check: how far did the price move from its own previous
     close (catches a corrupted/mis-scaled single tick, as distinct from
     genuine market volatility, which the volatility/sector flags already
     handle elsewhere).
  3. Independent source (see second_source.py): Alpha Vantage, for the 8
     commodities it covers -- strict where it's the same benchmark, a
     gross-error check where it's only a related market. The other 35
     report "n/a" rather than a faked pass.

Usage:
    python src/models/validate_prices.py
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from commodity_maps import PLAUSIBLE_RANGE, YFINANCE_COMMODITY_MAP
from data.fetch_yfinance import fetch_live_prices
from models.second_source import check as second_source_check

OUTPUTS_PATH = os.path.join(ROOT, "outputs", "forecasts.csv")
CONTINUITY_FLAG_PCT = 0.20  # a single-tick jump bigger than this from its own
                             # previous close is worth a human look


def run() -> pd.DataFrame:
    if not os.path.exists(OUTPUTS_PATH):
        print("No outputs/forecasts.csv yet -- run train_pipeline.py first.")
        return pd.DataFrame()

    forecasts = pd.read_csv(OUTPUTS_PATH)
    live = fetch_live_prices()

    rows = []
    for _, r in forecasts.iterrows():
        name = r["commodity"]
        price = float(r["current_price"])
        source = r.get("source", "")
        ticker = YFINANCE_COMMODITY_MAP.get(name, (None, None))[0]
        as_of = r.get("price_as_of", "")
        prev_close = None

        if name in live:
            price = live[name]["price"]
            ticker = live[name]["ticker"]
            as_of = live[name]["as_of"]
            prev_close = live[name].get("prev_close")

        lo, hi = PLAUSIBLE_RANGE.get(name, (None, None))
        range_ok = (lo is not None) and (lo <= price <= hi)

        continuity_ok = True
        continuity_pct = None
        if prev_close:
            continuity_pct = abs(price - prev_close) / (prev_close + 1e-9)
            continuity_ok = continuity_pct <= CONTINUITY_FLAG_PCT

        sc = second_source_check(name, price)
        second_src_check = sc["status"]
        if sc["status"] == "MISMATCH":
            second_src_check += (f" ({sc['diff_pct']:.0%} vs AV ${sc['av_price']})"
                                 if sc["diff_pct"] is not None else f" ({sc['note']})")

        rows.append({
            "commodity":      name,
            "price":          round(price, 4),
            "unit":           r.get("unit", ""),
            "source":         source,
            "ticker":         ticker or "",
            "as_of":          as_of,
            "plausible_range": f"{lo}-{hi}" if lo is not None else "n/a",
            "range_check":    "PASS" if range_ok else "FAIL",
            "continuity_pct": round(continuity_pct, 4) if continuity_pct is not None else None,
            "continuity_check": "PASS" if continuity_ok else ("FAIL" if prev_close else "n/a (no prev_close)"),
            "second_source":    second_src_check,
        })

    result = pd.DataFrame(rows)
    out_path = os.path.join(ROOT, "outputs", "validation_report.csv")
    result.to_csv(out_path, index=False)

    mismatch_mask = result["second_source"].astype(str).str.startswith("MISMATCH")
    failures = result[(result["range_check"] == "FAIL") | (result["continuity_check"] == "FAIL") | mismatch_mask]
    print(result.to_string(index=False))
    print(f"\nSaved {len(result)} rows to {out_path}")
    print(f"Range-check failures: {(result['range_check']=='FAIL').sum()} / {len(result)}")
    print(f"Continuity-check failures: {(result['continuity_check']=='FAIL').sum()} / {len(result)}")
    print(f"Second-source mismatches: {mismatch_mask.sum()} / {(result['second_source']!='n/a').sum()} checked")
    if not failures.empty:
        print("\nFAILURES:")
        print(failures.to_string(index=False))
    return result


if __name__ == "__main__":
    result = run()
    bad = (result.empty or (result["range_check"] == "FAIL").any()
           or (result["continuity_check"] == "FAIL").any()
           or result["second_source"].astype(str).str.startswith("MISMATCH").any())
    sys.exit(1 if bad else 0)
