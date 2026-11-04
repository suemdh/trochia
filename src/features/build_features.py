"""
Build model-ready features from the cleaned master dataset.

Creates:
- Lag features (4wk, 8wk, 6mo, 1yr ago)
- Momentum (% change over trailing windows)
- Rolling volatility
- Seasonal indicators (month, quarter)
- Cross-commodity signals (e.g. corn/feed proxy -> beef)
"""
import os
import pandas as pd
import numpy as np

PROCESSED_DIR = "data/processed"
INPUT_PATH = os.path.join(PROCESSED_DIR, "master_dataset.csv")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "features.csv")

LAG_WEEKS = {
    "lag_4w": 4,
    "lag_8w": 8,
    "lag_6mo": 26,
    "lag_1yr": 52,
}

MOMENTUM_WEEKS = [4, 8, 12]
VOLATILITY_WINDOW = 12


def add_lags(df: pd.DataFrame, target_cols: list) -> pd.DataFrame:
    df = df.copy()
    for col in target_cols:
        for label, weeks in LAG_WEEKS.items():
            df[f"{col}_{label}"] = df[col].shift(weeks)
    return df


def add_momentum(df: pd.DataFrame, target_cols: list) -> pd.DataFrame:
    df = df.copy()
    for col in target_cols:
        for weeks in MOMENTUM_WEEKS:
            df[f"{col}_momentum_{weeks}w"] = df[col].pct_change(weeks)
    return df


def add_volatility(df: pd.DataFrame, target_cols: list) -> pd.DataFrame:
    df = df.copy()
    for col in target_cols:
        df[f"{col}_volatility_{VOLATILITY_WINDOW}w"] = (
            df[col].pct_change().rolling(VOLATILITY_WINDOW).std()
        )
    return df


def add_seasonality(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    df = df.copy()
    dates = pd.to_datetime(df[date_col])
    df["month"] = dates.dt.month
    df["quarter"] = dates.dt.quarter
    df["week_of_year"] = dates.dt.isocalendar().week.astype(int)
    return df


def build_features(df: pd.DataFrame, target_cols: list = None) -> pd.DataFrame:
    """
    target_cols: list of price columns to build lag/momentum/volatility features for.
    If None, auto-detects all numeric, non-flag, non-date columns.
    """
    if target_cols is None:
        target_cols = [
            c for c in df.columns
            if c != "date" and not c.endswith("_outlier") and pd.api.types.is_numeric_dtype(df[c])
        ]

    df = add_seasonality(df)
    df = add_lags(df, target_cols)
    df = add_momentum(df, target_cols)
    df = add_volatility(df, target_cols)
    return df


def run():
    if not os.path.exists(INPUT_PATH):
        print(f"{INPUT_PATH} not found. Run src/data/clean.py first.")
        return

    df = pd.read_csv(INPUT_PATH, parse_dates=["date"])
    featured = build_features(df)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    featured.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved feature dataset with {len(featured)} rows and {len(featured.columns)} columns to {OUTPUT_PATH}")


if __name__ == "__main__":
    run()
