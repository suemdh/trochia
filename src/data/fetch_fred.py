"""
Fetch economic indicator data from FRED (Federal Reserve Economic Data).
Used for: inflation, interest rates, broader macro signals that affect commodity prices.

Docs: https://fred.stlouisfed.org/docs/api/fred/
"""
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Useful FRED series for commodity risk forecasting
SERIES_IDS = {
    # ── Macro context ───────────────────────────────────────────────
    "cpi_food":          "CPIUFDSL",      # CPI for food
    "ppi_food":          "WPUFD4111",     # PPI: Final demand, finished consumer foods
    "fed_funds_rate":    "FEDFUNDS",      # Interest rate (affects financing/storage costs)

    # ── Proteins ────────────────────────────────────────────────────
    "ground_beef_price": "APU0000703112", # Ground beef, $/lb
    "chicken_price":     "APU0000706111", # Chicken (whole), $/lb
    "bacon_price":       "APU0000704111", # Bacon, $/lb
    "pork_chops":        "APU0000FD3101", # All pork chops, $/lb
    "ham":               "APU0000704312", # Ham, boneless (excl. canned), $/lb
    "tuna_canned":       "APU0000707111", # Canned tuna, light chunk, $/lb -- discontinued by BLS Sep 2017, no current replacement

    # ── Dairy & eggs ────────────────────────────────────────────────
    "eggs_price":        "APU0000708111", # Eggs, $/dozen
    "butter_price":      "APU0000FS1101", # Butter, stick, $/lb
    "milk_price":        "APU0000709112", # Whole milk, $/gal
    "cheese_price":      "APU0000710212", # Natural cheese, $/lb

    # ── Bakery & dry goods ──────────────────────────────────────────
    "bread_price":       "APU0000702111", # White bread, $/lb
    "flour_price":       "APU0000701111", # All-purpose white flour, $/lb
    "peanut_butter":     "APU0000716141", # Peanut butter, creamy, $/lb -- discontinued by BLS Dec 2017, no current replacement
    "sugar_retail":      "APU0000715211", # White granulated sugar, $/lb
    "coffee_retail":     "APU0000717311", # Ground coffee (100%), $/lb

    # ── Produce ─────────────────────────────────────────────────────
    "bananas":           "APU0000711211", # Bananas, $/lb
    "potatoes":          "APU0000712112", # White potatoes, $/lb
    "tomatoes":          "APU0000712311", # Tomatoes, $/lb
    "oranges":           "APU0000711311", # Navel oranges, $/lb
    "apples":            "APU0000711111", # Red Delicious apples, $/lb -- discontinued by BLS Oct 2017, no current replacement

    # ── Energy (retail) ─────────────────────────────────────────────
    "diesel_price":      "GASDESW",       # On-highway diesel, $/gal
    "gasoline_retail":   "GASREGCOVW",    # Regular unleaded gasoline, $/gal
}


def fetch_series(series_id: str, start_date: str = "2014-01-01") -> pd.DataFrame:
    """Fetch a single FRED series as a DataFrame with columns [date, value]."""
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY not set. Check your .env file.")

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    obs = data.get("observations", [])
    df = pd.DataFrame(obs)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.rename(columns={"value": series_id})
    return df


def fetch_all() -> pd.DataFrame:
    """Fetch all configured FRED series and merge into one DataFrame on date."""
    merged = None
    for name, series_id in SERIES_IDS.items():
        try:
            df = fetch_series(series_id)
            df = df.rename(columns={series_id: name})
            merged = df if merged is None else merged.merge(df, on="date", how="outer")
        except Exception as e:
            print(f"  WARNING: skipping FRED series {name} ({series_id}): {e}")
    return merged.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    df = fetch_all()
    out_path = "data/raw/fred_data.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    print(df.tail())
