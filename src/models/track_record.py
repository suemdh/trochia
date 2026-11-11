"""
Scores past forecasts against what actually happened -- the real evidence
for "can businesses trust these forecasts," not just backtest confidence.

outputs/forecast_history.csv accumulates one row per commodity per retrain
(see log_snapshot() in train_pipeline.py). Once a snapshot's horizon has
actually elapsed (e.g. its 8-week forecast is now 8+ weeks in the past), this
looks up what the price actually did (from the same raw data files
train_pipeline.py trains on) and scores the forecast against reality:
direction correct? how far off was the number?

Snapshots whose horizon hasn't elapsed yet are skipped -- nothing to score
until enough calendar time has actually passed. Early on this will report
"nothing scoreable yet"; that's expected, not a bug.

Usage:
    python src/models/track_record.py
"""
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from models.train_pipeline import HISTORY_PATH
from models.backfill_volatility import load_series

RESULTS_PATH = os.path.join(ROOT, "outputs", "track_record.csv")


def actual_price_near(name: str, target_date: pd.Timestamp):
    """Nearest available actual price to target_date, from the same raw
    data train_pipeline.py reads."""
    try:
        df = load_series(name)
    except Exception:  # commodity since removed, or its data file missing
        return None
    if df.empty:
        return None
    idx = (df["date"] - target_date).abs().idxmin()
    row = df.loc[idx]
    # Don't accept a "nearest" match that's wildly far from the target --
    # that would silently score against the wrong point in time.
    if abs((row["date"] - target_date).days) > 14:
        return None
    return float(row["value"])


def score_track_record() -> pd.DataFrame:
    if not os.path.exists(HISTORY_PATH):
        print("No forecast_history.csv yet -- nothing logged.")
        return pd.DataFrame()

    hist = pd.read_csv(HISTORY_PATH, parse_dates=["snapshot_date"])
    hist["due_date"] = hist["snapshot_date"] + pd.to_timedelta(
        hist["horizon_steps"] * hist["step_days"], unit="D")

    due = hist[hist["due_date"] <= pd.Timestamp.now()].copy()
    if due.empty:
        print(f"Nothing scoreable yet -- earliest forecast comes due "
              f"{hist['due_date'].min().date()}.")
        return pd.DataFrame()

    rows = []
    for _, r in due.iterrows():
        actual = actual_price_near(r["commodity"], r["due_date"])
        if actual is None:
            continue
        forecast_direction_up = r["pct_change"] > 0
        actual_direction_up = actual > r["current_price"]
        rows.append({
            "commodity":        r["commodity"],
            "snapshot_date":    r["snapshot_date"].date(),
            "due_date":         r["due_date"].date(),
            "current_price":    r["current_price"],
            "forecast_price":   r["forecast_price"],
            "actual_price":     round(actual, 4),
            "forecast_pct":     r["pct_change"],
            "actual_pct":       round((actual - r["current_price"]) / (r["current_price"] + 1e-9), 4),
            "direction_correct": forecast_direction_up == actual_direction_up,
            "abs_pct_error":    round(abs(actual - r["forecast_price"]) / (r["current_price"] + 1e-9), 4),
        })

    result = pd.DataFrame(rows)
    if result.empty:
        print("Forecasts are due, but no matching actual price data found yet.")
        return result

    result.to_csv(RESULTS_PATH, index=False)
    print(f"Scored {len(result)} due forecasts -> {RESULTS_PATH}")
    print(f"Direction accuracy: {result['direction_correct'].mean():.1%}")
    print(f"Median abs % error: {result['abs_pct_error'].median():.1%}")
    return result


if __name__ == "__main__":
    score_track_record()
