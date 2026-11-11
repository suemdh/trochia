"""
One-off backfill: adds volatility_flag / volatility_zscore / recent_move_pct
to every row already in outputs/forecasts.csv, without re-running training.

train_pipeline.py computes these for any commodity trained from now on: this
script exists only because 43 commodities were already trained before the
volatility flag was added, and re-running the full SARIMA/LSTM training for
all of them again just to pick up three cheap numpy columns would waste the
hours that first run cost. Reads the same raw CSVs train_pipeline.py reads,
computes the same compute_volatility_flag(), and merges the result into the
existing forecasts.csv in place.

Usage:
    python src/models/backfill_volatility.py
"""
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from models.train_pipeline import compute_volatility_flag, apply_sector_flags, to_weekly, HORIZON, OUTPUTS_PATH
from commodity_maps import (
    FRED_COMMODITY_MAP, USDA_COMMODITY_MAP,
)

FRED_PATH = os.path.join(ROOT, "data", "raw", "fred_data.csv")
USDA_DIR  = os.path.join(ROOT, "data", "raw")


def load_series(name: str) -> pd.DataFrame:
    """[date, value] price history for one commodity, oldest first, from the
    same raw files train_pipeline.py trains on."""
    if name in FRED_COMMODITY_MAP:
        col, _ = FRED_COMMODITY_MAP[name]
        df = pd.read_csv(FRED_PATH, parse_dates=["date"])[["date", col]].rename(columns={col: "value"})
    elif name in USDA_COMMODITY_MAP:
        key, _ = USDA_COMMODITY_MAP[name]
        df = pd.read_csv(os.path.join(USDA_DIR, f"usda_{key}.csv"), parse_dates=["date"])
    else:
        raise KeyError(f"{name} not found in any commodity map")
    return to_weekly(df)  # same weekly view the forecasts were trained on


def load_prices(name: str):
    return load_series(name)["value"].values


def run():
    df = pd.read_csv(OUTPUTS_PATH)
    flags, zscores, moves = [], [], []
    for name in df["commodity"]:
        try:
            prices = load_prices(name)
            vol = compute_volatility_flag(prices, HORIZON)
        except Exception as e:
            print(f"  [{name}] could not compute volatility flag: {e}")
            vol = {"volatility_flag": False, "volatility_zscore": None, "recent_move_pct": None}
        flags.append(vol["volatility_flag"])
        zscores.append(vol["volatility_zscore"])
        moves.append(vol["recent_move_pct"])
        flag_str = "FLAGGED" if vol["volatility_flag"] else "ok"
        print(f"  [{name}] z={vol['volatility_zscore']}  recent_move={vol['recent_move_pct']}  {flag_str}")

    df["volatility_flag"]   = flags
    df["volatility_zscore"] = zscores
    df["recent_move_pct"]   = moves
    df = apply_sector_flags(df)
    df.to_csv(OUTPUTS_PATH, index=False)
    print(f"\nUpdated {len(df)} rows in {OUTPUTS_PATH}")
    print(f"Flagged as high-volatility: {df['volatility_flag'].sum()} / {len(df)}  "
          f"(sector-only: {int(df['sector_flag'].sum())})")


if __name__ == "__main__":
    run()
