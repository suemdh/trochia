# Backtest summary

Generated 2026-11-11 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**10 of 33 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Eggs | FRED | 8 months | ±44.9% | ±73.8% | +0.39 | Yes |
| Oranges | FRED | 8 months | ±6.8% | ±10.1% | +0.32 | Yes |
| Oats | USDA | 8 weeks | ±6.9% | ±9.9% | +0.31 | Yes |
| Gasoline | FRED | 8 weeks | ±9.0% | ±11.8% | +0.24 | Yes |
| Pork Chops | FRED | 8 months | ±2.2% | ±2.7% | +0.17 | Yes |
| Soybean Oil | USDA | 8 weeks | ±4.6% | ±5.3% | +0.13 | Yes |
| Crude Oil (WTI) | FRED | 8 weeks | ±15.5% | ±17.0% | +0.09 | Yes |
| Gasoline (Wholesale) | FRED | 8 weeks | ±15.8% | ±17.0% | +0.07 | Yes |
| Coffee (Retail) | FRED | 8 months | ±6.4% | ±6.9% | +0.06 | Yes |
| Chicken | FRED | 8 months | ±2.9% | ±2.9% | +0.02 | Yes |
| Heating Oil | FRED | 8 weeks | ±12.0% | ±11.1% | -0.08 | No |
| Ham | FRED | 8 months | ±3.6% | ±3.2% | -0.13 | No |
| Milk | FRED | 8 months | ±2.3% | ±2.0% | -0.15 | No |
| Crude Oil (Brent) | FRED | 8 weeks | ±22.4% | ±19.1% | -0.17 | No |
| Diesel / Freight | FRED | 8 weeks | ±12.4% | ±10.5% | -0.17 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.2% | ±8.7% | -0.18 | No |
| Flour | FRED | 8 months | ±3.2% | ±2.7% | -0.20 | No |
| Natural Gas | FRED | 8 weeks | ±19.5% | ±15.3% | -0.27 | No |
| Cheese | FRED | 8 months | ±2.8% | ±2.2% | -0.29 | No |
| Corn | USDA | 8 weeks | ±8.0% | ±6.0% | -0.34 | No |
| White Bread | FRED | 8 months | ±3.9% | ±2.9% | -0.34 | No |
| Ground Beef | FRED | 8 months | ±3.1% | ±2.2% | -0.42 | No |
| Wheat (USDA Cash) | USDA | 8 weeks | ±10.8% | ±5.7% | -0.89 | No |
| Potatoes | FRED | 8 months | ±5.4% | ±2.8% | -0.96 | No |
| Tomatoes | FRED | 8 months | ±9.3% | ±4.2% | -1.21 | No |
| Soybeans | USDA | 8 weeks | ±6.4% | ±2.7% | -1.38 | No |
| Pork / Bacon | FRED | 8 months | ±3.1% | ±1.3% | -1.39 | No |
| Bananas | FRED | 8 months | ±2.6% | ±1.1% | -1.51 | No |
| Lean Hogs | USDA | 8 weeks | ±8.1% | ±2.9% | -1.82 | No |
| Sugar (Retail) | FRED | 8 months | ±2.3% | ±0.7% | -2.36 | No |
| Butter | FRED | 8 months | ±7.9% | ±2.4% | -2.38 | No |
| Live Cattle | USDA | 8 weeks | ±5.4% | ±1.2% | -3.39 | No |
| Rice (Milled) | USDA | 8 weeks | ±4.5% | ±0.2% | -25.10 | No |
