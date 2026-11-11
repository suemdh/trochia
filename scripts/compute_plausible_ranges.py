"""
Regenerates commodity_maps.PLAUSIBLE_RANGE from each commodity's own full
historical data (0.5x observed min to 2x observed max). Prints a dict
literal to paste back into commodity_maps.py -- not auto-applied, since a
genuine shift in a commodity's real price range (e.g. after a multi-year
rally) is worth a human glance before widening the range that's supposed to
catch bad data.

Usage:
    python scripts/compute_plausible_ranges.py
"""
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from commodity_maps import FRED_COMMODITY_MAP, USDA_COMMODITY_MAP


def run():
    fred_df = pd.read_csv(os.path.join(ROOT, "data", "raw", "fred_data.csv"))
    ranges = {}

    for name, (col, _unit) in FRED_COMMODITY_MAP.items():
        s = fred_df[col].dropna()
        if len(s):
            ranges[name] = (round(float(s.min()) * 0.5, 4), round(float(s.max()) * 2.0, 4))

    for name, (key, _unit) in USDA_COMMODITY_MAP.items():
        path = os.path.join(ROOT, "data", "raw", f"usda_{key}.csv")
        if os.path.exists(path):
            s = pd.read_csv(path)["value"].dropna()
            if len(s):
                ranges[name] = (round(float(s.min()) * 0.5, 4), round(float(s.max()) * 2.0, 4))

    print("PLAUSIBLE_RANGE = {")
    for name, (lo, hi) in ranges.items():
        print(f'    "{name}": ({lo}, {hi}),')
    print("}")
    print(f"\n# {len(ranges)} commodities")


if __name__ == "__main__":
    run()
