# Backtest summary

Generated 2026-11-07 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**12 of 43 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Cotton | yfinance | 8 weeks | ±5.4% | ±12.6% | +0.57 | Yes |
| Oranges | FRED | 8 months | ±6.7% | ±9.9% | +0.32 | Yes |
| Silver | yfinance | 8 weeks | ±16.9% | ±24.7% | +0.32 | Yes |
| Crude Oil (WTI) | yfinance | 8 weeks | ±12.1% | ±17.5% | +0.31 | Yes |
| Crude Oil (Brent) | yfinance | 8 weeks | ±13.5% | ±18.2% | +0.26 | Yes |
| Soybean Oil | yfinance | 8 weeks | ±4.9% | ±6.4% | +0.23 | Yes |
| Eggs | FRED | 8 months | ±57.1% | ±73.2% | +0.22 | Yes |
| Orange Juice | yfinance | 8 weeks | ±9.4% | ±11.6% | +0.19 | Yes |
| Gold | yfinance | 8 weeks | ±8.7% | ±10.5% | +0.17 | Yes |
| Natural Gas | yfinance | 8 weeks | ±12.6% | ±13.8% | +0.09 | Yes |
| Gasoline (RBOB) | yfinance | 8 weeks | ±15.5% | ±16.0% | +0.03 | Yes |
| Cheese | FRED | 8 months | ±2.7% | ±2.8% | +0.02 | Yes |
| Pork Chops | FRED | 8 months | ±2.4% | ±2.4% | -0.01 | No |
| Chicken | FRED | 8 months | ±2.1% | ±2.0% | -0.03 | No |
| Milk | FRED | 8 months | ±2.5% | ±2.4% | -0.03 | No |
| Butter | FRED | 8 months | ±5.3% | ±5.0% | -0.07 | No |
| Soybeans | yfinance | 8 weeks | ±5.2% | ±4.8% | -0.09 | No |
| Coffee (Arabica) | yfinance | 8 weeks | ±10.0% | ±8.7% | -0.15 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.2% | ±8.6% | -0.18 | No |
| Flour | FRED | 8 months | ±3.2% | ±2.7% | -0.18 | No |
| Gasoline | FRED | 8 weeks | ±10.3% | ±8.6% | -0.19 | No |
| Oats | yfinance | 8 weeks | ±12.2% | ±10.2% | -0.20 | No |
| Tomatoes | FRED | 8 months | ±9.7% | ±7.9% | -0.22 | No |
| Diesel / Freight | FRED | 8 weeks | ±10.3% | ±8.4% | -0.22 | No |
| Heating Oil | yfinance | 8 weeks | ±14.3% | ±11.2% | -0.28 | No |
| Cocoa | yfinance | 8 weeks | ±12.3% | ±9.4% | -0.31 | No |
| Corn | yfinance | 8 weeks | ±9.5% | ±7.1% | -0.34 | No |
| Lean Hogs | yfinance | 8 weeks | ±11.3% | ±8.2% | -0.37 | No |
| Ham | FRED | 8 months | ±2.6% | ±1.7% | -0.49 | No |
| Coffee (Retail) | FRED | 8 months | ±8.9% | ±5.9% | -0.50 | No |
| Potatoes | FRED | 8 months | ±5.1% | ±3.2% | -0.58 | No |
| Wheat (USDA Cash) | USDA | 8 days | ±2.0% | ±1.3% | -0.58 | No |
| Sugar (11) | yfinance | 8 weeks | ±6.0% | ±3.6% | -0.68 | No |
| Rough Rice | yfinance | 8 weeks | ±8.3% | ±4.7% | -0.76 | No |
| Pork / Bacon | FRED | 8 months | ±2.6% | ±1.5% | -0.80 | No |
| Ground Beef | FRED | 8 months | ±3.6% | ±1.9% | -0.93 | No |
| Wheat | yfinance | 8 weeks | ±8.5% | ±4.1% | -1.06 | No |
| White Bread | FRED | 8 months | ±4.6% | ±2.2% | -1.06 | No |
| Live Cattle | yfinance | 8 weeks | ±5.3% | ±2.5% | -1.10 | No |
| Feeder Cattle | yfinance | 8 weeks | ±7.4% | ±3.5% | -1.14 | No |
| Bananas | FRED | 8 months | ±2.8% | ±1.3% | -1.19 | No |
| Copper | yfinance | 8 weeks | ±4.1% | ±1.6% | -1.49 | No |
| Sugar (Retail) | FRED | 8 months | ±2.4% | ±0.6% | -3.21 | No |
