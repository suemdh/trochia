"""
SARIMA model with optional auto-ARIMA parameter selection.
Uses pmdarima.auto_arima when available to find optimal (p,d,q)(P,D,Q,m) params.
Caches best params per commodity to data/models/{commodity}_sarima_params.json.
"""
import json
import os
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")


class SarimaModel:
    """Seasonal ARIMA wrapper for a single price series."""

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)):
        self.order          = order
        self.seasonal_order = seasonal_order
        self.fitted_model   = None

    def fit(self, series: pd.Series):
        series = series.dropna()
        model = SARIMAX(
            series,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        self.fitted_model = model.fit(disp=False)
        return self

    def auto_fit(self, series: pd.Series, commodity: str = "unknown",
                 force_search: bool = False, m: int = 52) -> "SarimaModel":
        """
        Use pmdarima.auto_arima to find optimal params, then fit.
        Caches result to disk so subsequent runs skip the search.
        Falls back to this instance's current order/seasonal_order if
        pmdarima isn't installed or the search fails.

        `m` is the seasonal period (periods per year) -- it must match the
        series' actual sampling frequency (12 for monthly, 52 for weekly, ...)
        or the search looks for a seasonal cycle at the wrong timescale.
        Callers should pass the real value; the default of 52 here is only a
        fallback for direct/ad-hoc use, not for train_pipeline.py's calls.
        """
        os.makedirs(MODELS_DIR, exist_ok=True)
        safe = commodity.lower().replace(" ", "_").replace("/", "_").replace("(","").replace(")","")
        cache_path = os.path.join(MODELS_DIR, f"{safe}_sarima_params.json")

        # Try loading cached params
        if not force_search and os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    params = json.load(f)
                self.order          = tuple(params["order"])
                self.seasonal_order = tuple(params["seasonal_order"])
                print(f"  [{commodity}] SARIMA loaded params from cache: "
                      f"order={self.order}, seasonal={self.seasonal_order}")
                return self.fit(series)
            except Exception:
                pass

        # Try auto_arima
        try:
            import pmdarima as pm
            print(f"  [{commodity}] Running auto_arima (this may take a minute)...")
            result = pm.auto_arima(
                series.dropna(),
                seasonal=True, m=m,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_p=3, max_q=3, max_P=2, max_Q=2,
                information_criterion="aic",
            )
            self.order          = result.order
            self.seasonal_order = result.seasonal_order
            params = {"order": list(self.order), "seasonal_order": list(self.seasonal_order)}
            with open(cache_path, "w") as f:
                json.dump(params, f)
            print(f"  [{commodity}] auto_arima found: order={self.order}, seasonal={self.seasonal_order}")
        except ImportError:
            print(f"  [{commodity}] pmdarima not installed, using default SARIMA params")
        except Exception as e:
            print(f"  [{commodity}] auto_arima failed ({e}), using default SARIMA params")

        return self.fit(series)

    def forecast(self, steps: int = 8) -> pd.DataFrame:
        """Returns forecast with 80% confidence intervals."""
        if self.fitted_model is None:
            raise RuntimeError("Call .fit() or .auto_fit() before .forecast()")
        result = self.fitted_model.get_forecast(steps=steps)
        return result.summary_frame(alpha=0.20)

    def forecast_mean(self, steps: int = 8) -> np.ndarray:
        """Returns just the point forecast as a numpy array."""
        return self.forecast(steps=steps)["mean"].values
