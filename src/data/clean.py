"""
Clean and merge all raw data sources into one consistent weekly dataset.

Handles:
- Filling missing weeks (forward-fill, capped at 2 weeks to avoid stale data)
- Converting to consistent units
- Flagging suspicious outliers (z-score > 4)
- Merging all sources into data/processed/master_dataset.csv
"""
import os
import glob
import pandas as pd
import numpy as np

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"


def load_all_raw() -> dict:
    """Load every CSV in data/raw/ into a dict of DataFrames keyed by filename."""
    dfs = {}
    for path in glob.glob(os.path.join(RAW_DIR, "*.csv")):
        name = os.path.splitext(os.path.basename(path))[0]
        df = pd.read_csv(path, parse_dates=["date"]) if "date" in pd.read_csv(path, nrows=0).columns else pd.read_csv(path)
        dfs[name] = df
    return dfs


def to_weekly(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Resample a DataFrame to weekly frequency (W-MON), forward-filling short gaps."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    weekly = df.resample("W-MON").mean(numeric_only=True)
    weekly = weekly.ffill(limit=2)  # cap fill at 2 weeks so we don't paper over real gaps
    return weekly.reset_index()


def flag_outliers(df: pd.DataFrame, cols: list, z_thresh: float = 4.0) -> pd.DataFrame:
    """Add a `<col>_outlier` boolean flag for values with |z-score| > threshold."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            z = (df[col] - df[col].mean()) / (df[col].std() + 1e-9)
            df[f"{col}_outlier"] = z.abs() > z_thresh
    return df


def merge_all(dfs: dict) -> pd.DataFrame:
    """Merge all weekly-resampled DataFrames on date into one master dataset."""
    merged = None
    for name, df in dfs.items():
        if "date" not in df.columns:
            continue
        weekly = to_weekly(df)
        # prefix non-date columns with source name to avoid collisions
        weekly = weekly.rename(columns={c: f"{name}__{c}" for c in weekly.columns if c != "date"})
        merged = weekly if merged is None else merged.merge(weekly, on="date", how="outer")

    if merged is None:
        raise RuntimeError("No raw data found. Run the fetch scripts first.")

    merged = merged.sort_values("date").reset_index(drop=True)

    numeric_cols = [c for c in merged.columns if c != "date" and merged[c].dtype != bool]
    merged = flag_outliers(merged, numeric_cols)

    return merged


def run():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    dfs = load_all_raw()
    if not dfs:
        print("No files found in data/raw/. Run the fetch_*.py scripts first.")
        return
    master = merge_all(dfs)
    out_path = os.path.join(PROCESSED_DIR, "master_dataset.csv")
    master.to_csv(out_path, index=False)
    print(f"Saved merged dataset with {len(master)} rows and {len(master.columns)} columns to {out_path}")


if __name__ == "__main__":
    run()
