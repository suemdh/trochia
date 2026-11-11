# Backtest summary

Generated 2026-11-11 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**8 of 33 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Eggs | FRED | 8 months | ±43.1% | ±73.8% | +0.42 | Yes |
| Oranges | FRED | 8 months | ±6.7% | ±9.9% | +0.32 | Yes |
| Oats | USDA | 8 weeks | ±7.4% | ±10.0% | +0.26 | Yes |
| Gasoline | FRED | 8 weeks | ±8.9% | ±11.8% | +0.25 | Yes |
| Soybean Oil | USDA | 8 weeks | ±4.5% | ±5.4% | +0.15 | Yes |
| Pork Chops | FRED | 8 months | ±2.3% | ±2.7% | +0.14 | Yes |
| Crude Oil (WTI) | FRED | 8 weeks | ±15.3% | ±16.8% | +0.09 | Yes |
| Coffee (Retail) | FRED | 8 months | ±6.5% | ±6.9% | +0.06 | Yes |
| Chicken | FRED | 8 months | ±3.0% | ±2.9% | -0.02 | No |
| Diesel / Freight | FRED | 8 weeks | ±11.0% | ±10.6% | -0.04 | No |
| Cheese | FRED | 8 months | ±2.4% | ±2.2% | -0.10 | No |
| Gasoline (Wholesale) | FRED | 8 weeks | ±19.3% | ±17.6% | -0.10 | No |
| Ham | FRED | 8 months | ±3.6% | ±3.2% | -0.13 | No |
| Crude Oil (Brent) | FRED | 8 weeks | ±23.2% | ±19.8% | -0.17 | No |
| Milk | FRED | 8 months | ±2.4% | ±2.0% | -0.18 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.2% | ±8.6% | -0.18 | No |
| Flour | FRED | 8 months | ±3.2% | ±2.7% | -0.21 | No |
| Natural Gas | FRED | 8 weeks | ±18.8% | ±14.8% | -0.27 | No |
| White Bread | FRED | 8 months | ±3.9% | ±2.9% | -0.34 | No |
| Ground Beef | FRED | 8 months | ±3.1% | ±2.2% | -0.42 | No |
| Heating Oil | FRED | 8 weeks | ±17.8% | ±11.5% | -0.54 | No |
| Corn | USDA | 8 weeks | ±9.5% | ±6.0% | -0.59 | No |
| Wheat (USDA Cash) | USDA | 8 weeks | ±10.8% | ±5.7% | -0.89 | No |
| Potatoes | FRED | 8 months | ±5.3% | ±2.7% | -0.97 | No |
| Tomatoes | FRED | 8 months | ±9.5% | ±4.3% | -1.21 | No |
| Soybeans | USDA | 8 weeks | ±6.5% | ±2.7% | -1.38 | No |
| Pork / Bacon | FRED | 8 months | ±3.1% | ±1.3% | -1.39 | No |
| Bananas | FRED | 8 months | ±2.8% | ±1.1% | -1.66 | No |
| Sugar (Retail) | FRED | 8 months | ±2.3% | ±0.7% | -2.37 | No |
| Butter | FRED | 8 months | ±8.0% | ±2.4% | -2.38 | No |
| Lean Hogs | USDA | 8 weeks | ±10.8% | ±2.9% | -2.77 | No |
| Live Cattle | USDA | 8 weeks | ±16.9% | ±1.2% | -12.85 | No |
| Rice (Milled) | USDA | 8 weeks | ±4.5% | ±0.2% | -25.10 | No |
