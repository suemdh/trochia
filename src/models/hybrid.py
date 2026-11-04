"""
Model 4: Hybrid
Combines Baseline + SARIMA + LSTM into a weighted ensemble for best accuracy.
This is what would get published in a research paper per the guide.
"""
import numpy as np
import pandas as pd


class HybridModel:
    """
    Simple weighted-average ensemble. Weights default to equal, but should be tuned
    via backtesting once each component model's accuracy is known
    (e.g. weight inversely by each model's RMSE).
    """

    def __init__(self, weights: dict = None):
        # default equal weighting across the three component models
        self.weights = weights or {"baseline": 1 / 3, "sarima": 1 / 3, "lstm": 1 / 3}

    def combine_weighted(self, forecasts: dict) -> np.ndarray:
        """forecasts: {model_name: np.ndarray}. Weights must match keys."""
        arrays = {k: np.asarray(v) for k, v in forecasts.items()}
        combined = sum(self.weights.get(k, 0) * arr for k, arr in arrays.items())
        return combined

    def combine(self, baseline_forecast: np.ndarray, sarima_forecast: np.ndarray, lstm_forecast: np.ndarray) -> np.ndarray:
        """All three forecast arrays must be the same length (same horizon)."""
        arrays = {
            "baseline": np.asarray(baseline_forecast),
            "sarima": np.asarray(sarima_forecast),
            "lstm": np.asarray(lstm_forecast),
        }
        lengths = {k: len(v) for k, v in arrays.items()}
        if len(set(lengths.values())) > 1:
            raise ValueError(f"Forecast horizons don't match: {lengths}")

        combined = sum(self.weights[k] * arrays[k] for k in arrays)
        return combined

    def tune_weights_from_rmse(self, rmse_by_model: dict):
        """Set weights inversely proportional to each model's historical RMSE (lower RMSE = more weight)."""
        inv = {k: 1.0 / (v + 1e-9) for k, v in rmse_by_model.items()}
        total = sum(inv.values())
        self.weights = {k: v / total for k, v in inv.items()}
        return self.weights


if __name__ == "__main__":
    # Example with dummy forecasts
    baseline_fc = np.array([100, 101, 102, 103])
    sarima_fc = np.array([99, 102, 104, 105])
    lstm_fc = np.array([101, 103, 103, 106])

    hybrid = HybridModel()
    combined = hybrid.combine(baseline_fc, sarima_fc, lstm_fc)
    print("Combined forecast:", combined)
