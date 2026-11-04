"""
Lag compensator: estimate today's price for data sources with publication lag.

FRED retail food prices are published 4-6 weeks after collection.
This module uses the most recent available data point + recent trend
to project a best-estimate for today's price.

Method: compound growth extrapolation
  weeks_elapsed = (today - last_data_date).days / 7
  avg_weekly_pct = mean of last N weekly pct_changes
  estimated = last_known * (1 + avg_weekly_pct) ** weeks_elapsed
  confidence_penalty = min(0.15, weeks_elapsed * 0.02)  # 2% per week, max 15%

This is meant for ordinary publication lag (single-digit weeks). If a series
stops being published altogether -- BLS discontinues a handful of FRED items
every so often -- "weeks_elapsed" stops meaning "waiting for this week's
number" and starts meaning "this number is from a different era." Compound
extrapolation over a multi-year gap doesn't estimate anything; it just
relabels an ancient data point as current with barely any confidence penalty
(the formula below caps out at a 10% penalty and an 8% price adjustment
regardless of how long the gap is). MAX_REASONABLE_LAG_WEEKS draws the line:
past it, this returns "too_stale" instead of a false-confidence number.
"""
from datetime import date, datetime
import numpy as np
import pandas as pd

# FRED retail series lag 4-6 weeks in normal operation (we've observed up to
# ~9 weeks in practice). 26 weeks (half a year) is a generous multiple of
# that -- long enough to never falsely flag a series that's just running
# late, but short enough to catch a series that has actually gone dark.
MAX_REASONABLE_LAG_WEEKS = 26


def estimate_today(
    series: pd.Series,
    dates: pd.Series | None = None,
    lookback_weeks: int = 8,
) -> dict:
    """
    Estimate today's price from a lagged price series.

    Args:
        series: Price values (float), most recent last.
        dates:  Corresponding dates. If None, assumes weekly frequency ending today.
        lookback_weeks: How many recent data points to use for trend calculation.

    Returns:
        {
            "estimated_price": float,
            "last_known_price": float,
            "last_known_date": str (YYYY-MM-DD),
            "lag_weeks": float,
            "avg_weekly_pct_change": float,
            "confidence_penalty": float,   # subtract from model confidence
            "is_estimated": True,
        }
    """
    series = pd.to_numeric(series, errors="coerce").dropna()
    if len(series) == 0:
        return _empty_result()

    last_known_price = float(series.iloc[-1])

    if dates is not None:
        dates = pd.to_datetime(dates)
        last_date = dates.iloc[-1].date() if hasattr(dates.iloc[-1], "date") else date.today()
    else:
        last_date = date.today()

    lag_days = (date.today() - last_date).days
    lag_weeks = lag_days / 7.0

    if lag_weeks > MAX_REASONABLE_LAG_WEEKS:
        # The series has gone dark, not just late -- e.g. BLS discontinued it.
        # Extrapolating a multi-year-old price forward and calling it "today"
        # would be a confident-looking number with no real basis. Say so
        # instead of guessing.
        return {
            "estimated_price":      None,
            "last_known_price":     round(last_known_price, 4),
            "last_known_date":      str(last_date),
            "lag_weeks":            round(lag_weeks, 1),
            "avg_weekly_pct_change": 0.0,
            "confidence_penalty":   1.0,
            "is_estimated":         True,
            "is_live":              False,
            "too_stale":            True,
        }

    # Detect data frequency: if median gap between dates > 20 days, treat as monthly
    if dates is not None and len(dates) >= 3:
        gaps = pd.to_datetime(dates).diff().dropna().dt.days
        median_gap_days = float(gaps.median())
    else:
        median_gap_days = 7.0  # assume weekly

    is_monthly = median_gap_days > 20

    # Calculate average period % change over recent history
    recent = series.iloc[-lookback_weeks:]
    pct_changes = recent.pct_change().dropna()

    if len(pct_changes) == 0:
        avg_period_pct = 0.0
    else:
        avg_period_pct = float(pct_changes.median())

    if is_monthly:
        # Monthly data: convert to weekly rate and clamp tighter
        avg_weekly_pct = (1 + avg_period_pct) ** (1 / 4.33) - 1  # monthly → weekly
        avg_weekly_pct = max(-0.005, min(0.005, avg_weekly_pct))   # ±0.5%/week max
    else:
        avg_weekly_pct = max(-0.03, min(0.03, avg_period_pct))

    # Compound extrapolation — cap total adjustment at ±8% of last known price
    if lag_weeks > 0:
        raw_estimate = last_known_price * ((1 + avg_weekly_pct) ** lag_weeks)
        max_adj = last_known_price * 0.08
        estimated_price = float(np.clip(raw_estimate,
                                        last_known_price - max_adj,
                                        last_known_price + max_adj))
    else:
        estimated_price = last_known_price

    # Confidence penalty: more lag = less confident (max 10%)
    confidence_penalty = min(0.10, lag_weeks * 0.015)

    return {
        "estimated_price":      round(estimated_price, 4),
        "last_known_price":     round(last_known_price, 4),
        "last_known_date":      str(last_date),
        "lag_weeks":            round(lag_weeks, 1),
        "avg_weekly_pct_change": round(avg_weekly_pct, 6),
        "confidence_penalty":   round(confidence_penalty, 3),
        "is_estimated":         True,
        "is_live":              False,
        "too_stale":            False,
    }


def estimate_from_csv(csv_path: str, value_col: str, date_col: str = "date",
                      lookback_weeks: int = 8) -> dict:
    """Convenience wrapper: load a raw CSV and return the lag-compensated estimate."""
    try:
        df = pd.read_csv(csv_path, parse_dates=[date_col])
        df = df.sort_values(date_col).dropna(subset=[value_col])
        return estimate_today(df[value_col], df[date_col], lookback_weeks)
    except Exception as e:
        print(f"  lag_compensator: could not read {csv_path}: {e}")
        return _empty_result()


def _empty_result() -> dict:
    return {
        "estimated_price":       None,
        "last_known_price":      None,
        "last_known_date":       None,
        "lag_weeks":             0.0,
        "avg_weekly_pct_change": 0.0,
        "confidence_penalty":    0.0,
        "is_estimated":          False,
        "is_live":               False,
        "too_stale":             False,
    }


if __name__ == "__main__":
    # Quick test with synthetic data
    import os
    fred_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "fred_data.csv")
    if os.path.exists(fred_path):
        df = pd.read_csv(fred_path, parse_dates=["date"])
        df = df.sort_values("date").dropna(subset=["ground_beef_price"])
        result = estimate_today(df["ground_beef_price"], df["date"])
        print("Ground Beef lag compensation:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    else:
        print("No fred_data.csv found — run main.py first")
