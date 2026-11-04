"""
Naive baseline models — the minimum bar every other model must beat.

Two variants:
  1. LastValue  — forecast = last observed price (random walk)
  2. SeasonalNaive — forecast = price from same week one year ago

Both are evaluated with MAE, MAPE, and directional accuracy on a held-out
test set AND a rolling walk-forward backtest.
"""
import numpy as np
import pandas as pd


class LastValueBaseline:
    """Forecast: next value = last observed value (random walk hypothesis)."""

    def forecast(self, series: np.ndarray, horizon: int) -> np.ndarray:
        return np.full(horizon, series[-1])


class SeasonalNaiveBaseline:
    """Forecast: next h values = values from 52 weeks ago (seasonal repeat)."""

    def __init__(self, season_len: int = 52):
        self.season_len = season_len

    def forecast(self, series: np.ndarray, horizon: int) -> np.ndarray:
        if len(series) < self.season_len + horizon:
            return np.full(horizon, series[-1])  # fall back to last value
        return series[-(self.season_len + horizon): -self.season_len + horizon or None][:horizon]


def _mae(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred)))


def _mape(actual: np.ndarray, pred: np.ndarray) -> float:
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100)


def _directional_accuracy(actual: np.ndarray, pred: np.ndarray) -> float:
    """% of steps where predicted direction matches actual direction."""
    if len(actual) < 2:
        return float("nan")
    actual_dir = np.sign(np.diff(actual))
    pred_dir = np.sign(np.diff(pred))
    valid = actual_dir != 0
    if not valid.any():
        return float("nan")
    return float(np.mean(actual_dir[valid] == pred_dir[valid]))


def evaluate_on_holdout(
    series: np.ndarray,
    horizon: int = 8,
    holdout_n: int = 26,
) -> dict:
    """
    Single train/test split. Train on everything before holdout_n,
    forecast `horizon` steps, compare to first `horizon` steps of holdout.
    Returns metrics for last-value and seasonal-naive.
    """
    if len(series) < holdout_n + horizon + 52:
        return {"error": "insufficient data"}

    train = series[: -holdout_n]
    test = series[-holdout_n: -holdout_n + horizon]

    lv = LastValueBaseline()
    sn = SeasonalNaiveBaseline()

    lv_fc = lv.forecast(train, horizon)
    sn_fc = sn.forecast(train, horizon)

    return {
        "last_value": {
            "mae":  _mae(test, lv_fc),
            "mape": _mape(test, lv_fc),
            "directional_accuracy": _directional_accuracy(test, lv_fc),
            "forecast": lv_fc.tolist(),
        },
        "seasonal_naive": {
            "mae":  _mae(test, sn_fc),
            "mape": _mape(test, sn_fc),
            "directional_accuracy": _directional_accuracy(test, sn_fc),
            "forecast": sn_fc.tolist(),
        },
        "actual": test.tolist(),
    }


def rolling_backtest(
    series: np.ndarray,
    horizon: int = 8,
    n_windows: int = 12,
    step: int = 4,
) -> dict:
    """
    Walk-forward rolling backtest over n_windows windows, each stepping
    `step` weeks forward. Reports mean MAE/MAPE/directional accuracy
    across all windows for both naive models.
    """
    min_train = 52 * 2  # 2 years minimum training history
    results = {"last_value": [], "seasonal_naive": []}

    for i in range(n_windows):
        end_train = len(series) - horizon - (n_windows - 1 - i) * step
        if end_train < min_train:
            continue
        train = series[:end_train]
        test = series[end_train: end_train + horizon]
        if len(test) < horizon:
            continue

        lv_fc = LastValueBaseline().forecast(train, horizon)
        sn_fc = SeasonalNaiveBaseline().forecast(train, horizon)

        for name, fc in [("last_value", lv_fc), ("seasonal_naive", sn_fc)]:
            results[name].append({
                "mae":  _mae(test, fc),
                "mape": _mape(test, fc),
                "dir":  _directional_accuracy(test, fc),
            })

    summary = {}
    for name, windows in results.items():
        if not windows:
            summary[name] = {}
            continue
        summary[name] = {
            "mean_mae":  float(np.mean([w["mae"]  for w in windows])),
            "mean_mape": float(np.mean([w["mape"] for w in windows])),
            "mean_dir":  float(np.mean([w["dir"]  for w in windows if not np.isnan(w["dir"])])),
            "n_windows": len(windows),
        }
    return summary
