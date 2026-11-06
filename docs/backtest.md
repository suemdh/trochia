# Backtest summary

Generated 2026-11-06 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**10 of 43 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Cotton | yfinance | 8 weeks | ±5.5% | ±12.7% | +0.57 | Yes |
| Soybean Oil | yfinance | 8 weeks | ±3.8% | ±6.4% | +0.41 | Yes |
| Oranges | FRED | 8 months | ±6.7% | ±9.9% | +0.32 | Yes |
| Crude Oil (WTI) | yfinance | 8 weeks | ±12.2% | ±17.7% | +0.31 | Yes |
| Crude Oil (Brent) | yfinance | 8 weeks | ±13.6% | ±18.4% | +0.26 | Yes |
| Orange Juice | yfinance | 8 weeks | ±8.2% | ±11.0% | +0.25 | Yes |
| Natural Gas | yfinance | 8 weeks | ±10.9% | ±13.7% | +0.20 | Yes |
| Gold | yfinance | 8 weeks | ±8.7% | ±10.5% | +0.17 | Yes |
| Eggs | FRED | 8 months | ±67.7% | ±73.1% | +0.07 | Yes |
| Cheese | FRED | 8 months | ±2.7% | ±2.8% | +0.02 | Yes |
| Diesel / Freight | FRED | 8 weeks | ±8.5% | ±8.4% | -0.02 | No |
| Chicken | FRED | 8 months | ±2.1% | ±2.0% | -0.02 | No |
| Milk | FRED | 8 months | ±2.5% | ±2.4% | -0.03 | No |
| Butter | FRED | 8 months | ±5.3% | ±5.0% | -0.07 | No |
| Gasoline (RBOB) | yfinance | 8 weeks | ±17.4% | ±16.1% | -0.08 | No |
| Soybeans | yfinance | 8 weeks | ±5.2% | ±4.8% | -0.09 | No |
| Pork Chops | FRED | 8 months | ±2.6% | ±2.4% | -0.09 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.2% | ±8.6% | -0.18 | No |
| Coffee (Arabica) | yfinance | 8 weeks | ±10.3% | ±8.7% | -0.19 | No |
| Gasoline | FRED | 8 weeks | ±10.4% | ±8.6% | -0.20 | No |
| Tomatoes | FRED | 8 months | ±9.7% | ±7.9% | -0.22 | No |
| Flour | FRED | 8 months | ±3.3% | ±2.7% | -0.23 | No |
| Oats | yfinance | 8 weeks | ±13.1% | ±10.2% | -0.28 | No |
| Cocoa | yfinance | 8 weeks | ±12.1% | ±9.3% | -0.31 | No |
| Silver | yfinance | 8 weeks | ±34.0% | ±24.6% | -0.38 | No |
| Corn | yfinance | 8 weeks | ±10.0% | ±7.1% | -0.40 | No |
| Ham | FRED | 8 months | ±2.6% | ±1.7% | -0.49 | No |
| Coffee (Retail) | FRED | 8 months | ±8.9% | ±5.9% | -0.50 | No |
| Potatoes | FRED | 8 months | ±5.1% | ±3.2% | -0.58 | No |
| Wheat (USDA Cash) | USDA | 8 days | ±2.0% | ±1.3% | -0.58 | No |
| Lean Hogs | yfinance | 8 weeks | ±13.3% | ±8.2% | -0.62 | No |
| Heating Oil | yfinance | 8 weeks | ±18.6% | ±11.3% | -0.64 | No |
| Pork / Bacon | FRED | 8 months | ±2.6% | ±1.5% | -0.81 | No |
| Rough Rice | yfinance | 8 weeks | ±8.6% | ±4.6% | -0.85 | No |
| Ground Beef | FRED | 8 months | ±3.7% | ±1.9% | -0.93 | No |
| Wheat | yfinance | 8 weeks | ±8.4% | ±4.1% | -1.05 | No |
| White Bread | FRED | 8 months | ±4.6% | ±2.2% | -1.06 | No |
| Bananas | FRED | 8 months | ±2.8% | ±1.3% | -1.19 | No |
| Copper | yfinance | 8 weeks | ±4.0% | ±1.6% | -1.49 | No |
| Sugar (11) | yfinance | 8 weeks | ±11.1% | ±3.6% | -2.12 | No |
| Live Cattle | yfinance | 8 weeks | ±9.0% | ±2.5% | -2.61 | No |
| Feeder Cattle | yfinance | 8 weeks | ±14.1% | ±3.5% | -3.01 | No |
| Sugar (Retail) | FRED | 8 months | ±2.4% | ±0.6% | -3.22 | No |
