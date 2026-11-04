"""
Model 1: Baseline (Linear Regression)
Simple trend-line benchmark that every other model must beat.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error


class BaselineLinearModel:
    """Predicts future price as a linear function of lag/momentum features."""

    def __init__(self):
        self.model = LinearRegression()
        self.feature_cols = None

    def fit(self, df: pd.DataFrame, target_col: str, feature_cols: list):
        self.feature_cols = feature_cols
        data = df.dropna(subset=feature_cols + [target_col])
        X = data[feature_cols].values
        y = data[target_col].values
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_cols].values
        return self.model.predict(X)

    def evaluate(self, df: pd.DataFrame, target_col: str) -> dict:
        data = df.dropna(subset=self.feature_cols + [target_col])
        preds = self.predict(data)
        actual = data[target_col].values
        rmse = np.sqrt(mean_squared_error(actual, preds))
        direction_correct = np.mean(
            np.sign(np.diff(preds)) == np.sign(np.diff(actual))
        ) if len(actual) > 1 else np.nan
        return {"rmse": rmse, "directional_accuracy": direction_correct}


if __name__ == "__main__":
    df = pd.read_csv("data/processed/features.csv", parse_dates=["date"])
    # Example usage -- adjust target_col/feature_cols to your actual column names
    print("Available columns:", list(df.columns)[:20], "...")
