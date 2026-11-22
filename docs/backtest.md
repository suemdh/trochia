# Backtest summary

Generated 2026-11-22 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**11 of 33 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Gasoline | FRED | 8 weeks | ±7.3% | ±13.4% | +0.46 | Yes |
| Oats | USDA | 8 weeks | ±6.4% | ±11.1% | +0.43 | Yes |
| Eggs | FRED | 8 months | ±43.6% | ±73.8% | +0.41 | Yes |
| Crude Oil (WTI) | FRED | 8 weeks | ±14.2% | ±23.6% | +0.40 | Yes |
| Oranges | FRED | 8 months | ±6.8% | ±10.1% | +0.32 | Yes |
| Diesel / Freight | FRED | 8 weeks | ±7.7% | ±11.3% | +0.32 | Yes |
| Crude Oil (Brent) | FRED | 8 weeks | ±19.5% | ±28.6% | +0.32 | Yes |
| Gasoline (Wholesale) | FRED | 8 weeks | ±14.7% | ±18.8% | +0.22 | Yes |
| Pork Chops | FRED | 8 months | ±2.2% | ±2.7% | +0.17 | Yes |
| Coffee (Retail) | FRED | 8 months | ±6.4% | ±6.9% | +0.06 | Yes |
| Heating Oil | FRED | 8 weeks | ±12.0% | ±12.7% | +0.06 | Yes |
| Chicken | FRED | 8 months | ±3.0% | ±2.9% | -0.02 | No |
| Ham | FRED | 8 months | ±3.6% | ±3.2% | -0.13 | No |
| Soybean Oil | USDA | 8 weeks | ±6.3% | ±5.6% | -0.14 | No |
| Corn | USDA | 8 weeks | ±9.3% | ±8.0% | -0.16 | No |
| Milk | FRED | 8 months | ±2.4% | ±2.0% | -0.18 | No |
| Flour | FRED | 8 months | ±3.2% | ±2.7% | -0.21 | No |
| Cheese | FRED | 8 months | ±2.8% | ±2.2% | -0.29 | No |
| Live Cattle | USDA | 8 weeks | ±4.9% | ±3.6% | -0.34 | No |
| White Bread | FRED | 8 months | ±3.9% | ±2.9% | -0.34 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.2% | ±7.5% | -0.35 | No |
| Ground Beef | FRED | 8 months | ±3.1% | ±2.2% | -0.42 | No |
| Wheat (USDA Cash) | USDA | 8 weeks | ±9.4% | ±5.7% | -0.64 | No |
| Natural Gas | FRED | 8 weeks | ±14.9% | ±8.8% | -0.69 | No |
| Soybeans | USDA | 8 weeks | ±7.0% | ±4.0% | -0.74 | No |
| Potatoes | FRED | 8 months | ±5.4% | ±2.8% | -0.95 | No |
| Lean Hogs | USDA | 8 weeks | ±6.6% | ±3.0% | -1.18 | No |
| Tomatoes | FRED | 8 months | ±9.3% | ±4.2% | -1.21 | No |
| Pork / Bacon | FRED | 8 months | ±3.0% | ±1.3% | -1.31 | No |
| Bananas | FRED | 8 months | ±2.8% | ±1.1% | -1.66 | No |
| Butter | FRED | 8 months | ±7.9% | ±2.4% | -2.38 | No |
| Sugar (Retail) | FRED | 8 months | ±2.7% | ±0.7% | -2.98 | No |
| Rice (Milled) | USDA | 8 weeks | ±4.4% | ±0.2% | -19.81 | No |
