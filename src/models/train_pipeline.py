"""
Training pipeline: trains Baseline + SARIMA + LSTM for each commodity,
tunes RMSE-weighted hybrid blending, applies lag compensation for current prices,
and writes outputs/forecasts.csv.

Usage:
    python src/models/train_pipeline.py
    python src/models/train_pipeline.py --force-retrain   # ignore cached models
    python src/models/train_pipeline.py --commodity "Ground Beef"  # single commodity
"""
import argparse
import concurrent.futures
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from models.baseline_linear import BaselineLinearModel
from models.statistical_sarima import SarimaModel
from models.ai_lstm import train_lstm, forecast as lstm_forecast
from models.hybrid import HybridModel
from models.naive_baseline import evaluate_on_holdout as naive_holdout, rolling_backtest as naive_backtest
from decision.engine import ForecastInput, evaluate
from data.lag_compensator import estimate_today
from commodity_maps import (
    FRED_COMMODITY_MAP, USDA_COMMODITY_MAP,
)

FEATURES_PATH  = os.path.join(ROOT, "data", "processed", "features.csv")
FRED_PATH      = os.path.join(ROOT, "data", "raw",       "fred_data.csv")
USDA_DIR       = os.path.join(ROOT, "data", "raw")
OUTPUTS_PATH   = os.path.join(ROOT, "outputs",           "forecasts.csv")
HISTORY_PATH   = os.path.join(ROOT, "outputs",           "forecast_history.csv")
MODELS_DIR     = os.path.join(ROOT, "data",              "models")
HORIZON        = 8      # steps ahead -- one step = the source's own sampling
                        # interval (monthly, weekly or daily depending on the series),
                        # so call infer_step_unit() to label it correctly.
HOLDOUT_WEEKS  = 26     # steps held back for RMSE evaluation
SARIMA_FIT_TIMEOUT_SEC = 90  # see fit_with_timeout()


def fit_with_timeout(fn, *args, timeout: float = SARIMA_FIT_TIMEOUT_SEC, **kwargs):
    """
    Run fn(*args, **kwargs) with a hard wall-clock timeout, raising
    TimeoutError instead of blocking forever.

    Added after Gasoline (RBOB) hung this pipeline for 130+ real minutes
    with zero CPU usage during SARIMA fitting -- a genuine hang, not just a
    slow fit, and not something the existing try/except around each model
    could catch (except blocks only catch raised exceptions; they can't
    interrupt a call that never returns or raises).

    This can't force-kill a hung native call (Python can't safely terminate
    an arbitrary thread), so a timed-out call leaves its thread running in
    the background rather than actually stopping it -- but that's still
    enough to unblock the pipeline: the goal is "one bad fit can't block the
    rest of this commodity's training," not "reclaim the CPU it wastes."

    Deliberately spins up a fresh single-use executor per call rather than
    sharing one persistent pool: a shared pool's worker would stay wedged on
    the hung call forever, silently queuing (and hanging) every later fit
    behind it too -- turning one hang into an unbounded one. A fresh
    throwaway executor per call means a hang leaks exactly one thread for
    this commodity's process lifetime, and every other fit call is unaffected.

    Note: deliberately NOT a `with ThreadPoolExecutor(...) as executor:`
    block -- its __exit__ calls shutdown(wait=True), which would itself
    block forever waiting for the hung worker, defeating the whole point.
    shutdown(wait=False) here lets this function return on timeout while the
    orphaned thread is abandoned to finish (or not) on its own.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(fn, *args, **kwargs)
        return future.result(timeout=timeout)
    finally:
        executor.shutdown(wait=False)


def infer_step_unit(dates) -> tuple[str, int]:
    """
    Work out what one step actually means on the calendar.
    Returns (label, days_per_step) e.g. ("months", 30).
    """
    gaps = pd.Series(pd.to_datetime(pd.Series(dates))).diff().dt.days.dropna()
    if gaps.empty:
        return ("steps", 7)
    med = float(gaps.median())
    if med <= 2:
        return ("days", 1)
    if med <= 10:
        return ("weeks", 7)
    if med <= 45:
        return ("months", 30)
    return ("quarters", 91)


def to_weekly(df: pd.DataFrame, col: str = "value") -> pd.DataFrame:
    """Daily series -> the last real observation of each week (its real date
    kept, so "as of" never shows a future Friday). Daily EIA/USDA prices would
    otherwise make an 8-step forecast mean 8 *days* -- too short to act on."""
    df = df.dropna(subset=[col]).sort_values("date")
    if infer_step_unit(df["date"])[0] != "days":
        return df.reset_index(drop=True)
    return df.groupby(df["date"].dt.to_period("W-FRI")).last().reset_index(drop=True)


N_BACKTEST_WINDOWS = 3


def backtest_windows(n: int, holdout_n: int, horizon: int, k: int = N_BACKTEST_WINDOWS) -> list[tuple[int, int]]:
    """
    Up to k (train_end, test_end) index pairs for walk-forward backtesting
    within the reserved holdout region [n-holdout_n, n) -- oldest window
    first, each stepping `horizon` steps forward, so later windows use more
    training data and test on more recent (more relevant) data.

    Each model is meant to be fit on data[:train_end] and scored against
    data[train_end:test_end]. Every model previously scored on a single
    window (test_end = n-holdout_n+horizon only) -- one unlucky or lucky
    window could dominate a model's apparent accuracy and, through
    RMSE-weighted blending, how much the hybrid forecast trusts it. That's
    exactly what happened to Silver's SARIMA component after the seasonal-
    period fix: a single-window RMSE of 40,836 that the ensemble had to be
    saved from by weighting, rather than caught by the scoring itself.
    Averaging RMSE across several walk-forward windows is the standard fix.

    Falls back to a single window (the original behavior) if the holdout
    region isn't long enough to fit more than one.
    """
    windows = []
    for i in range(k):
        train_end = n - holdout_n + i * horizon
        test_end  = train_end + horizon
        if test_end > n or train_end < horizon:
            break
        windows.append((train_end, test_end))
    return windows or [(n - holdout_n, n - holdout_n + horizon)]


def seasonal_period(horizon_unit: str) -> int:
    """
    SARIMA's seasonal period (m) must match the data's actual sampling
    frequency to find a real annual cycle -- e.g. m=12 for monthly data
    (12 months/year), m=52 for weekly. This used to be hardcoded to a single
    value (52 in the auto_arima search, 12 in the eval/fallback model)
    regardless of what frequency the series actually was, so half of every
    commodity's SARIMA fit was searching for a seasonal pattern at the wrong
    period -- e.g. FRED's monthly series searched for a ~4.3-year cycle
    instead of an annual one, which is almost certainly why most of them came
    back with no seasonal component at all.
    """
    return {"days": 5, "weeks": 52, "months": 12, "quarters": 4}.get(horizon_unit, 12)


VOLATILITY_Z_THRESHOLD = 2.0  # see compute_volatility_flag()


def compute_volatility_flag(prices: np.ndarray, window: int,
                             z_threshold: float = VOLATILITY_Z_THRESHOLD) -> dict:
    """
    Flags when the most recent `window`-step price move is a statistical
    outlier against this commodity's own history of window-step moves.

    All three models (Baseline, SARIMA, LSTM) are pure extrapolations of
    historical price/macro patterns -- none of them have any real-time news
    or event input. That's invisible on an ordinary day, but it produced a
    confidently wrong forecast for Gasoline (RBOB) during the Sept 2026
    Strait of Hormuz supply shock: the model saw a normal post-summer
    seasonal decline in ~10 years of history and extrapolated that, right
    through an active, still-unfolding war-driven price spike it had no way
    to have learned from. This can't be fixed by retraining -- the signal
    isn't in any historical series by definition -- so instead it's
    surfaced: when the recent move is a big outlier vs. this series' own
    history, say so, rather than presenting a seasonal-reversion forecast
    with the same unqualified confidence as a normal, unremarkable day.

    Uses `window = HORIZON` by both call sites so "recent" means "the same
    span the forecast itself covers" -- an apples-to-apples comparison.
    """
    n = len(prices)
    if n < window * 3 + 1:
        return {"volatility_flag": False, "volatility_zscore": None, "recent_move_pct": None}

    # One window-step % move ending at each possible point in history.
    hist_moves = (prices[window:] - prices[:-window]) / (prices[:-window] + 1e-9)
    # Score the most recent move against everything BEFORE it, not against
    # itself -- otherwise a big move partly inflates its own baseline stats.
    baseline    = hist_moves[:-1]
    recent_move = float(hist_moves[-1])

    mean = float(np.mean(baseline))
    std  = float(np.std(baseline)) + 1e-9
    z    = (recent_move - mean) / std

    return {
        "volatility_flag":   bool(abs(z) > z_threshold),
        "volatility_zscore": round(float(z), 2),
        "recent_move_pct":   round(recent_move, 4),
    }


# Commodities sharing crude oil as a common driver. A single member's own
# z-score (compute_volatility_flag) can stay under threshold even during a
# real shock if that series is already volatile historically -- exactly what
# happened to WTI/Brent during the Sept 2026 Hormuz crisis, while Diesel
# (thinner historical swings) cleared it easily on the same event. Checking
# the group's *shared* direction catches that: several ordinarily-volatile
# series all leaning the same way, at the same time, is a much rarer and
# more informative signal than any one of them moving alone.
ENERGY_GROUP = [
    "Crude Oil (Brent)", "Crude Oil (WTI)", "Natural Gas",
    "Gasoline", "Gasoline (Wholesale)", "Heating Oil", "Diesel / Freight",
]
SECTOR_Z_THRESHOLD = 0.5  # median signed z-score across the group to trigger


def apply_sector_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Second pass over the assembled forecasts table: flags every member of
    ENERGY_GROUP if the group's *median signed* volatility z-score clears
    SECTOR_Z_THRESHOLD, even for members whose own individual z-score didn't.
    Signed (not absolute) so a genuine coordinated move survives the median
    while mixed, uncorrelated noise across the group cancels toward zero.
    Safe to call multiple times / on a partial table -- no-ops if fewer than
    two group members with a real z-score are present.
    """
    if "sector_flag" not in df.columns:
        df["sector_flag"] = False
    mask = df["commodity"].isin(ENERGY_GROUP) & df["volatility_zscore"].notna()
    if mask.sum() < 2:
        return df
    sector_z = float(df.loc[mask, "volatility_zscore"].median())
    if abs(sector_z) >= SECTOR_Z_THRESHOLD:
        df.loc[mask, "volatility_flag"] = True
        df.loc[mask, "sector_flag"] = True
    return df


def build_lstm_features(prices: np.ndarray, step_days: int, dates=None,
                         macro_df: pd.DataFrame | None = None) -> np.ndarray:
    """
    Build a multi-feature array for the LSTM: [price, lag_1mo, lag_3mo,
    lag_6mo, lag_12mo, momentum_1mo, momentum_3mo, volatility_3mo] plus,
    when available, macro columns from `macro_df` (e.g. cpi_food, ppi_food,
    fed_funds_rate) merged in by date.

    The LSTM's architecture already supports multi-feature input (n_features
    in LSTMForecaster/SequenceDataset), but train_pipeline.py previously only
    ever fed it a single price column -- reasonable lag/momentum/volatility
    features existed in build_features.py, but for a different, unused
    pipeline (data/processed/features.csv), and with lookbacks hardcoded in
    weeks (e.g. lag_1yr = shift(52)) that would silently mean something else
    entirely on monthly FRED data -- the same frequency-mismatch bug already
    found and fixed in the SARIMA seasonal period. Here every lookback is
    defined in calendar time (1/3/6/12 months) and converted to a step count
    via step_days, so it means the same real-world span regardless of
    whether the series is daily, weekly, or monthly.

    Macro indicators are only ever used as *lagged, already-known* values --
    merged as of each row's own date -- never as future values the model
    would need to already know, so there's no chicken-and-egg forecasting
    problem the way there would be feeding them to SARIMAX's exog parameter
    (which requires future exog values for the whole forecast horizon).

    Returns a 2-D array (T', n_features), column 0 = price. Leading rows that
    don't have a full 12-month lookback are dropped (can't compute a
    year-ago lag for the series' first year) -- the last row always still
    aligns with the most recent price, only the head shrinks.
    """
    def steps_for(days: int) -> int:
        return max(1, round(days / step_days))

    s = pd.Series(np.asarray(prices, dtype=float))
    feats = pd.concat([
        s,
        s.shift(steps_for(30)),
        s.shift(steps_for(91)),
        s.shift(steps_for(182)),
        s.shift(steps_for(365)),
        s.pct_change(steps_for(30)),
        s.pct_change(steps_for(91)),
        s.pct_change().rolling(steps_for(91)).std(),
    ], axis=1)
    feats.columns = ["price", "lag_1mo", "lag_3mo", "lag_6mo", "lag_12mo",
                      "momentum_1mo", "momentum_3mo", "volatility_3mo"]

    if dates is not None and macro_df is not None and not macro_df.empty:
        feats["date"] = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
        macro_sorted = macro_df.sort_values("date")
        feats = feats.sort_values("date")
        feats = pd.merge_asof(feats, macro_sorted, on="date", direction="backward")
        feats = feats.drop(columns=["date"])

    return feats.dropna().values

# FRED_COMMODITY_MAP and USDA_COMMODITY_MAP live in
# commodity_maps.py, shared with the dashboard so chart data can't drift out of
# sync with what's actually being forecast (see that module's docstring).


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = ~np.isnan(actual) & ~np.isnan(predicted)
    if mask.sum() == 0:
        return float("inf")
    return float(np.sqrt(np.mean((actual[mask] - predicted[mask]) ** 2)))


def _naive_rmse(naive: dict, best_rmse: float) -> tuple[float, bool | None]:
    """
    Re-score the naive baseline with RMSE so it's comparable to the models.
    Returns (naive_rmse, beat_naive); beat_naive is None when there's no data.
    """
    lv = naive.get("last_value", {})
    fc     = np.asarray(lv.get("forecast", []), dtype=float)
    actual = np.asarray(naive.get("actual", []), dtype=float)
    if fc.size == 0 or actual.size == 0:
        return (float("nan"), None)
    n = min(fc.size, actual.size)
    n_rmse = rmse(actual[:n], fc[:n])
    return (n_rmse, bool(best_rmse < n_rmse))


def train_fred_commodity(
    name: str,
    col: str,
    unit: str,
    fred_df: pd.DataFrame,
    force_retrain: bool = False,
    use_auto_arima: bool = True,
    source: str = "FRED",
    macro_df: pd.DataFrame | None = None,
) -> dict | None:
    """Train all models for one commodity from a date/value series (FRED or USDA). Returns a forecast row dict."""
    if col not in fred_df.columns:
        print(f"  [{name}] Column '{col}' not in {source} data — skipping")
        return None

    series = to_weekly(fred_df[["date", col]].copy(), col)

    if len(series) < HOLDOUT_WEEKS + 20:
        print(f"  [{name}] Not enough data ({len(series)} rows) — skipping")
        return None

    prices = series[col].values
    dates  = series["date"]

    # What does one step actually mean here? FRED is monthly, so HORIZON=8
    # is 8 months -- not 8 weeks, whatever the constant is named.
    horizon_unit, step_days = infer_step_unit(dates)

    # Lag compensation for "today" price
    lag_info = estimate_today(series[col], series["date"])
    if lag_info.get("too_stale"):
        print(f"  [{name}] Last data point is from {lag_info['last_known_date']} "
              f"({lag_info['lag_weeks']:.0f} weeks ago) — too stale to estimate a "
              f"current price or issue a signal. Skipping.")
        return None
    # The latest OFFICIAL price, never a trend-projected guess: a projection
    # made our "today" price disagree with USDA/EIA/BLS's own published number
    # (Brent: $103.37 shown vs EIA's $107.03), and businesses check those.
    current_price = float(prices[-1])

    # Train/test split (for the real forward-forecasting fits, below)
    train_series = series[col].iloc[:-HOLDOUT_WEEKS]

    # Walk-forward windows, shared by all three models so their RMSEs are
    # scored on the same stretches of history and stay comparable.
    windows = backtest_windows(len(prices), HOLDOUT_WEEKS, HORIZON)

    # ── Baseline ──────────────────────────────────────────────────
    try:
        from sklearn.linear_model import LinearRegression
        bl_rmses = []
        for train_end, test_end in windows:
            train_idx = np.arange(train_end).reshape(-1, 1)
            bl_w = LinearRegression().fit(train_idx, prices[:train_end])
            test_idx = np.arange(train_end, test_end).reshape(-1, 1)
            bl_rmses.append(rmse(prices[train_end:test_end], bl_w.predict(test_idx)))
        bl_rmse = float(np.mean(bl_rmses))

        full_idx  = np.arange(len(prices)).reshape(-1, 1)
        bl_full   = LinearRegression().fit(full_idx, prices)
        fc_idx    = np.arange(len(prices), len(prices) + HORIZON).reshape(-1, 1)
        baseline_fc = bl_full.predict(fc_idx)
        print(f"  [{name}] Baseline RMSE={bl_rmse:.4f} (avg of {len(windows)} windows)")
    except Exception as e:
        print(f"  [{name}] Baseline failed: {e}")
        baseline_fc = np.full(HORIZON, current_price)
        bl_rmse     = float("inf")

    # ── SARIMA ────────────────────────────────────────────────────
    m = seasonal_period(horizon_unit)
    try:
        # Fit 1 — walk-forward: train-only fits across several windows, for
        # an honest, non-single-lucky-window holdout score.
        s_rmses = []
        for train_end, test_end in windows:
            sarima_w = SarimaModel(order=(1,1,1), seasonal_order=(1,1,1,m))
            fit_with_timeout(sarima_w.fit, series[col].iloc[:train_end])
            s_holdout = sarima_w.forecast_mean(steps=HORIZON)[:test_end - train_end]
            s_rmses.append(rmse(prices[train_end:test_end], s_holdout))
        s_rmse = float(np.mean(s_rmses))

        # Fit 2 — full series, for the actual forward forecast
        sarima = SarimaModel(order=(1,1,1), seasonal_order=(1,1,1,m))
        if use_auto_arima:
            fit_with_timeout(sarima.auto_fit, series[col], commodity=name, force_search=force_retrain, m=m)
        else:
            fit_with_timeout(sarima.fit, series[col])
        sarima_fc = sarima.forecast_mean(steps=HORIZON)

        print(f"  [{name}] SARIMA RMSE={s_rmse:.4f} (avg of {len(windows)} windows)")
    except Exception as e:
        print(f"  [{name}] SARIMA failed: {e}")
        sarima_fc = np.full(HORIZON, current_price)
        s_rmse    = float("inf")

    # ── LSTM ──────────────────────────────────────────────────────
    try:
        window = 12
        # Fit 1 — walk-forward across the same windows as Baseline/SARIMA.
        # Each window's features + scaling are built from that window's own
        # train-only data, so nothing about its test period leaks in.
        l_rmses = []
        for train_end, test_end in windows:
            tr_feats = build_lstm_features(prices[:train_end], step_days,
                                            dates=series["date"].iloc[:train_end],
                                            macro_df=macro_df)
            if len(tr_feats) <= window:
                continue
            tr_mean = tr_feats.mean(axis=0)
            tr_std  = tr_feats.std(axis=0) + 1e-9
            tr_normed = (tr_feats - tr_mean) / tr_std
            eval_model = train_lstm(
                tr_normed,
                commodity=f"{name}__eval",
                force_retrain=True,
                epochs=40,
            )
            l_holdout = lstm_forecast(eval_model, tr_normed[-window:]) * tr_std[0] + tr_mean[0]
            steps = test_end - train_end
            l_rmses.append(rmse(prices[train_end:test_end], l_holdout[:steps]))
        l_rmse = float(np.mean(l_rmses)) if l_rmses else float("inf")

        # Fit 2 — full series, for the actual forward forecast
        feats      = build_lstm_features(prices, step_days, dates=series["date"], macro_df=macro_df)
        price_mean = feats.mean(axis=0)
        price_std  = feats.std(axis=0) + 1e-9
        normed     = (feats - price_mean) / price_std

        lstm_model = train_lstm(
            normed,
            commodity=name,
            force_retrain=force_retrain,
            epochs=40,
        )
        if len(normed) > window:
            lstm_fc = lstm_forecast(lstm_model, normed[-window:]) * price_std[0] + price_mean[0]
        else:
            lstm_fc = np.full(HORIZON, current_price)

        print(f"  [{name}] LSTM RMSE={l_rmse:.4f} (avg of {len(l_rmses)} windows)")
    except Exception as e:
        print(f"  [{name}] LStTM failed: {e}")
        lstm_fc = np.full(HORIZON, current_price)
        l_rmse  = float("inf")

    # ── Hybrid blend ──────────────────────────────────────────────
    hybrid = HybridModel()
    hybrid.tune_weights_from_rmse({"baseline": bl_rmse, "sarima": s_rmse, "lstm": l_rmse})
    forecast_price = float(hybrid.combine(baseline_fc, sarima_fc, lstm_fc)[HORIZON - 1])

    # Clip forecast to ±40% of current price (sanity check)
    forecast_price = float(np.clip(forecast_price,
                                   current_price * 0.6,
                                   current_price * 1.4))

    pct_change  = (forecast_price - current_price) / (current_price + 1e-9)
    best_rmse   = min(bl_rmse, s_rmse, l_rmse)
    rmse_pct    = best_rmse / (current_price + 1e-9)
    confidence  = float(np.clip(0.95 - rmse_pct * 0.5 - lag_info["confidence_penalty"], 0.50, 0.95))

    # Confidence band: ±1.645 sigma (90% interval) using best model RMSE as sigma
    # proxy. No usable estimate means wide, not narrow.
    band = (best_rmse * 1.645) if np.isfinite(best_rmse) else (forecast_price * 0.25)
    lower_bound = round(max(forecast_price - band, forecast_price * 0.5), 4)
    upper_bound = round(forecast_price + band, 4)

    # Naive baseline comparison (honest backtest).
    # Score naive with RMSE too -- comparing our RMSE against its MAE would be
    # comparing two different metrics, and RMSE is always the harsher one.
    naive = naive_holdout(prices, horizon=HORIZON, holdout_n=HOLDOUT_WEEKS)
    naive_rmse, beat_naive = _naive_rmse(naive, best_rmse)
    naive_dir  = naive.get("last_value", {}).get("directional_accuracy", float("nan"))
    print(f"  [{name}] naive_RMSE={naive_rmse:.4f}  model_best_RMSE={best_rmse:.4f}  beat_naive={beat_naive}")

    fi = ForecastInput(
        commodity=name, current_price=current_price,
        forecast_price=forecast_price, horizon_weeks=HORIZON,
        confidence=confidence, weekly_usage_units=10, unit_label=unit,
        horizon_unit=horizon_unit, days_per_step=step_days,
        rmse_pct=rmse_pct,
        beats_naive=bool(beat_naive),
    )
    rec = evaluate(fi)
    vol = compute_volatility_flag(prices, HORIZON)

    return {
        "commodity":      name,
        "unit":           unit,
        "current_price":  round(current_price, 4),
        "forecast_price": round(forecast_price, 4),
        "lower_bound":    lower_bound,
        "upper_bound":    upper_bound,
        "pct_change":     round(pct_change, 4),
        "horizon_steps":  HORIZON,
        "horizon_unit":   horizon_unit,
        "step_days":      step_days,
        "horizon_weeks":  HORIZON,   # legacy key, kept so older readers don't break
        "confidence":     round(confidence, 4),
        "signal":         rec.signal,
        "message":        rec.message,
        "baseline_rmse":  round(bl_rmse, 4),
        "sarima_rmse":    round(s_rmse,  4),
        "lstm_rmse":      round(l_rmse,  4),
        "naive_rmse":     round(naive_rmse, 4) if not np.isnan(naive_rmse) else None,
        "naive_dir_acc":  round(naive_dir, 4) if not np.isnan(naive_dir) else None,
        "beat_naive":     beat_naive,
        "is_estimated":   False,  # official published price; "as of" shows its date
        "price_as_of":    lag_info.get("last_known_date", ""),
        "lag_weeks":      lag_info.get("lag_weeks", 0),
        "source":         source,
        "rmse_pct":       round(rmse_pct, 6) if np.isfinite(rmse_pct) else None,
        "volatility_flag":   vol["volatility_flag"],
        "volatility_zscore": vol["volatility_zscore"],
        "recent_move_pct":   vol["recent_move_pct"],
    }


PARTIAL_PATH = os.path.join(ROOT, "outputs", "forecasts_partial.csv")


def _flush(rows: list, path: str = OUTPUTS_PATH):
    """Write partial results after each commodity, so a crashed run can resume.
    Fresh (weekly) runs flush to PARTIAL_PATH instead, so the dashboard keeps
    showing the last complete forecast set until the new one is fully built."""
    if not rows:
        return
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def log_snapshot(df_out: pd.DataFrame):
    """
    Appends this run's forecasts to a permanent, timestamped history log --
    the only way to eventually show businesses a real track record ("8 weeks
    ago we said X, here's what actually happened") instead of just asserting
    the model is accurate. Confidence/backtest scores prove the model fit
    its own past data well; they don't prove anything about a forecast that
    hasn't come true yet. This starts accumulating that proof on every
    retrain from now on -- see score_track_record() for reading it back once
    enough time has passed for forecasts to have actually come due.
    """
    snap = df_out[["commodity", "current_price", "forecast_price", "pct_change",
                   "signal", "confidence", "horizon_steps", "horizon_unit", "step_days"]].copy()
    snap.insert(0, "snapshot_date", pd.Timestamp.now().strftime("%Y-%m-%d"))
    header = not os.path.exists(HISTORY_PATH)
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    snap.to_csv(HISTORY_PATH, mode="a", header=header, index=False)


def run(force_retrain: bool = False, only_commodity: str | None = None,
        use_auto_arima: bool = True, fresh: bool = False):
    if fresh and only_commodity:
        # A fresh run replaces the whole forecasts file at the end -- with a
        # single-commodity filter that would wipe the other 42.
        raise ValueError("--fresh re-forecasts everything; it can't be combined with --commodity")
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    flush_path = PARTIAL_PATH if fresh else OUTPUTS_PATH

    # Resume from a previous partial run instead of redoing already-saved
    # commodities from scratch -- long runs here have repeatedly been killed
    # mid-way by the environment recycling the session, not by anything wrong
    # with the training itself, and losing 20+ minutes of finished work to a
    # cold restart every time is its own reliability problem worth fixing.
    rows = []
    already_done = set()
    if not force_retrain and not fresh and os.path.exists(OUTPUTS_PATH):
        try:
            existing = pd.read_csv(OUTPUTS_PATH)
            rows = existing.to_dict("records")
            already_done = set(existing["commodity"])
            print(f"Resuming: {len(already_done)} commodities already saved, skipping those.")
        except Exception as e:
            print(f"Could not resume from existing {OUTPUTS_PATH}: {e}")

    # ── FRED commodities ─────────────────────────────────────────────
    if os.path.exists(FRED_PATH):
        fred_df = pd.read_csv(FRED_PATH, parse_dates=["date"])
        fred_df = fred_df.sort_values("date").reset_index(drop=True)
        print(f"\nFRED data loaded: {len(fred_df)} rows, columns: {list(fred_df.columns)}")
    else:
        print(f"\nNo FRED data at {FRED_PATH} — run python main.py first")
        fred_df = pd.DataFrame()

    # Macro indicators (food inflation, producer prices, interest rates) --
    # fetched alongside every commodity's own price data but, until now,
    # never actually used by any model. Passed to every FRED/USDA commodity
    # as extra LSTM input features, merged in by date (see build_lstm_features).
    macro_cols = [c for c in ["cpi_food", "ppi_food", "fed_funds_rate"] if c in fred_df.columns]
    macro_df = fred_df[["date"] + macro_cols].dropna(how="all", subset=macro_cols) if macro_cols else None

    for name, (col, unit) in FRED_COMMODITY_MAP.items():
        if only_commodity and only_commodity.lower() not in name.lower():
            continue
        if name in already_done:
            continue
        if fred_df.empty:
            continue
        print(f"\n{'='*50}\nTraining: {name} (FRED:{col})")
        try:
            row = train_fred_commodity(
                name, col, unit, fred_df,
                force_retrain=force_retrain,
                use_auto_arima=use_auto_arima,
                macro_df=macro_df,
            )
            if row:
                rows.append(row)
                _flush(rows, flush_path)
                print(f"  → signal={row['signal']}  current=${row['current_price']:.3f}  "
                      f"forecast=${row['forecast_price']:.3f}  ({row['pct_change']:+.1%})")
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")

    # ── USDA commodities ────────────────────────────────────────────────
    for name, (key, unit) in USDA_COMMODITY_MAP.items():
        if only_commodity and only_commodity.lower() not in name.lower():
            continue
        if name in already_done:
            continue
        usda_path = os.path.join(USDA_DIR, f"usda_{key}.csv")
        if not os.path.exists(usda_path):
            print(f"\n[{name}] No USDA data at {usda_path} — run python main.py first")
            continue
        usda_df = pd.read_csv(usda_path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
        print(f"\n{'='*50}\nTraining: {name} (USDA:{key})")
        try:
            row = train_fred_commodity(
                name, "value", unit, usda_df,
                force_retrain=force_retrain,
                use_auto_arima=use_auto_arima,
                source="USDA",
                macro_df=macro_df,
            )
            if row:
                rows.append(row)
                _flush(rows, flush_path)
                print(f"  → signal={row['signal']}  current=${row['current_price']:.3f}  "
                      f"forecast=${row['forecast_price']:.3f}  ({row['pct_change']:+.1%})")
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")

    if not rows:
        print("\nNo forecasts generated — check data and try again")
        return

    df_out = pd.DataFrame(rows)
    df_out = apply_sector_flags(df_out)
    df_out = df_out.sort_values(
        by=["signal", "pct_change"],
        key=lambda s: s.map({"RED": 0, "YELLOW": 1, "GREEN": 2}).fillna(3) if s.name == "signal" else -s.abs(),
    )
    # Write-then-rename so the dashboard never reads a half-written file.
    tmp_path = OUTPUTS_PATH + ".tmp"
    df_out.to_csv(tmp_path, index=False)
    os.replace(tmp_path, OUTPUTS_PATH)
    if fresh and os.path.exists(PARTIAL_PATH):
        os.remove(PARTIAL_PATH)
    expected = set(FRED_COMMODITY_MAP) | set(USDA_COMMODITY_MAP)
    missing = expected - set(df_out["commodity"])
    if missing and not only_commodity:
        print(f"WARNING: {len(missing)} commodities failed and are absent from this run: {sorted(missing)}")
    log_snapshot(df_out)
    print(f"\n{'='*50}")
    print(f"Saved {len(rows)} forecasts to {OUTPUTS_PATH}")
    print(df_out[["commodity", "signal", "current_price", "forecast_price", "pct_change", "confidence"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-retrain",  action="store_true", help="Ignore cached models")
    parser.add_argument("--commodity",      type=str, default=None, help="Train only this commodity")
    parser.add_argument("--no-auto-arima",  action="store_true", help="Skip auto-ARIMA param search")
    parser.add_argument("--fresh",          action="store_true",
                        help="Re-forecast every commodity (no resume), swapping the new set in only when complete")
    args = parser.parse_args()
    run(
        force_retrain=args.force_retrain,
        only_commodity=args.commodity,
        use_auto_arima=not args.no_auto_arima,
        fresh=args.fresh,
    )
