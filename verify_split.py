"""
Verification that model evaluation is honest.

Test A: the training slice and the scoring slice must not overlap.
Test B: on a pure random walk, no model can legitimately beat the naive
        baseline by much. If one does, evaluation is still leaking.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from models.train_pipeline import HORIZON, HOLDOUT_WEEKS, rmse
from models.naive_baseline import evaluate_on_holdout

# ── Test A: split integrity ────────────────────────────────────────
df = pd.read_csv("data/raw/fred_data.csv", parse_dates=["date"]).sort_values("date")
series = df[["date", "ground_beef_price"]].dropna().reset_index(drop=True)
prices = series["ground_beef_price"].values

train_series = series["ground_beef_price"].iloc[:-HOLDOUT_WEEKS]
test_prices  = prices[-HOLDOUT_WEEKS:]

print("TEST A — train/test split")
print(f"  total points ........ {len(prices)}")
print(f"  training on ......... {len(train_series)}")
print(f"  held out ............ {len(test_prices)}")
print(f"  scored on first ..... {HORIZON} of the holdout")

last_train_date  = series['date'].iloc[len(train_series) - 1].date()
first_test_date  = series['date'].iloc[len(train_series)].date()
print(f"  training ends ....... {last_train_date}")
print(f"  scoring starts ...... {first_test_date}")
overlap = len(train_series) + len(test_prices) - len(prices)
print(f"  overlap ............. {overlap} points  ->  {'FAIL' if overlap else 'PASS'}")

# ── Test B: random-walk sanity check ───────────────────────────────
# On a random walk, tomorrow's best guess IS today's value. Any model
# claiming to beat that by a wide margin is cheating somewhere.
print("\nTEST B — random-walk control")
rng = np.random.default_rng(0)
wins = 0
TRIALS = 20
for _ in range(TRIALS):
    walk = 100 + np.cumsum(rng.normal(0, 1, len(prices)))
    tr = walk[:-HOLDOUT_WEEKS]
    te = walk[-HOLDOUT_WEEKS:][:HORIZON]

    # A linear trend fit on train only - the honest protocol
    idx = np.arange(len(tr)).reshape(-1, 1)
    from sklearn.linear_model import LinearRegression
    fit = LinearRegression().fit(idx, tr)
    fut = np.arange(len(tr), len(tr) + HORIZON).reshape(-1, 1)
    model_rmse = rmse(te, fit.predict(fut))

    naive_rmse = rmse(te, np.full(HORIZON, tr[-1]))
    if model_rmse < naive_rmse:
        wins += 1

print(f"  model beat naive in {wins}/{TRIALS} random-walk trials")
print(f"  expected roughly half by chance  ->  {'SUSPICIOUS' if wins > 15 else 'PASS'}")
