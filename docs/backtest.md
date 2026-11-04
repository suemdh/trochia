# Backtest summary

Generated 2026-11-02 from `outputs/forecasts.csv` by `scripts/write_backtest_doc.py`.

**11 of 43 commodities** have a model that beat a simple "price stays the same" forecast in backtesting. Commodities that don't are capped at a YELLOW watch signal on the dashboard and can never trigger a RED buy alert.

## Method

- Each model (Baseline linear, SARIMA, LSTM) is fit walk-forward on 3 historical windows and scored on data it never saw (no lookahead). The best model's average RMSE is the **typical error** shown on each card.
- The **no-change baseline** forecasts that today's price holds; its RMSE is scored on the final holdout window. Caveat: that is one window vs. the model's three, so the comparison is close but not perfectly like-for-like.
- **Skill** = 1 - model RMSE / no-change RMSE. Positive = better than no-change.
- **Not yet available:** MAE, directional accuracy, and calibration of stated ranges on *real* out-of-sample outcomes. Those come from `src/models/track_record.py`, which scores every logged forecast once it comes due (first ones due 2026-11-06).

## Per commodity

| Commodity | Source | Horizon | Typical error | No-change error | Skill | Beats no-change |
|---|---|---|---|---|---|---|
| Copper | yfinance | 8 weeks | ±5.2% | ±9.6% | +0.46 | Yes |
| Cotton | yfinance | 8 weeks | ±6.6% | ±12.1% | +0.45 | Yes |
| Oranges | FRED | 8 months | ±6.7% | ±9.9% | +0.32 | Yes |
| Soybean Oil | yfinance | 8 weeks | ±6.0% | ±8.6% | +0.30 | Yes |
| Eggs | FRED | 8 months | ±54.3% | ±72.8% | +0.25 | Yes |
| Natural Gas | yfinance | 8 weeks | ±10.9% | ±12.5% | +0.13 | Yes |
| Gasoline | FRED | 8 weeks | ±6.2% | ±7.0% | +0.11 | Yes |
| Orange Juice | yfinance | 8 weeks | ±12.8% | ±14.3% | +0.11 | Yes |
| Wheat (USDA Cash) | USDA | 8 days | ±4.0% | ±4.4% | +0.10 | Yes |
| Sugar (11) | yfinance | 8 weeks | ±7.0% | ±7.7% | +0.09 | Yes |
| Cheese | FRED | 8 months | ±2.7% | ±2.8% | +0.02 | Yes |
| Chicken | FRED | 8 months | ±2.1% | ±2.0% | -0.02 | No |
| Milk | FRED | 8 months | ±2.5% | ±2.4% | -0.03 | No |
| Cream (USDA) | USDA | 8 weeks | ±10.1% | ±9.8% | -0.04 | No |
| Heating Oil | yfinance | 8 weeks | ±15.0% | ±14.2% | -0.06 | No |
| Pork Chops | FRED | 8 months | ±2.5% | ±2.4% | -0.06 | No |
| Butter | FRED | 8 months | ±5.3% | ±4.9% | -0.07 | No |
| Crude Oil (Brent) | yfinance | 8 weeks | ±11.4% | ±10.6% | -0.08 | No |
| Live Cattle | yfinance | 8 weeks | ±5.9% | ±5.4% | -0.09 | No |
| Silver | yfinance | 8 weeks | ±18.2% | ±15.9% | -0.14 | No |
| Cocoa | yfinance | 8 weeks | ±11.4% | ±9.6% | -0.19 | No |
| Tomatoes | FRED | 8 months | ±9.7% | ±7.9% | -0.22 | No |
| Flour | FRED | 8 months | ±3.3% | ±2.7% | -0.23 | No |
| Gold | yfinance | 8 weeks | ±7.2% | ±5.9% | -0.23 | No |
| Rough Rice | yfinance | 8 weeks | ±6.8% | ±5.0% | -0.34 | No |
| Feeder Cattle | yfinance | 8 weeks | ±4.0% | ±2.9% | -0.38 | No |
| Ham | FRED | 8 months | ±2.6% | ±1.7% | -0.49 | No |
| Coffee (Retail) | FRED | 8 months | ±8.9% | ±5.9% | -0.50 | No |
| Lean Hogs | yfinance | 8 weeks | ±9.6% | ±6.4% | -0.52 | No |
| Crude Oil (WTI) | yfinance | 8 weeks | ±12.0% | ±7.8% | -0.54 | No |
| Potatoes | FRED | 8 months | ±5.1% | ±3.3% | -0.58 | No |
| Oats | yfinance | 8 weeks | ±7.3% | ±4.3% | -0.69 | No |
| Diesel / Freight | FRED | 8 weeks | ±7.5% | ±4.4% | -0.70 | No |
| Wheat | yfinance | 8 weeks | ±7.0% | ±3.9% | -0.78 | No |
| Pork / Bacon | FRED | 8 months | ±2.6% | ±1.5% | -0.81 | No |
| Coffee (Arabica) | yfinance | 8 weeks | ±9.1% | ±4.9% | -0.88 | No |
| Ground Beef | FRED | 8 months | ±3.7% | ±1.9% | -0.93 | No |
| White Bread | FRED | 8 months | ±4.6% | ±2.2% | -1.06 | No |
| Soybeans | yfinance | 8 weeks | ±3.8% | ±1.8% | -1.09 | No |
| Bananas | FRED | 8 months | ±2.8% | ±1.3% | -1.17 | No |
| Gasoline (RBOB) | yfinance | 8 weeks | ±20.5% | ±8.9% | -1.31 | No |
| Corn | yfinance | 8 weeks | ±6.3% | ±2.3% | -1.72 | No |
| Sugar (Retail) | FRED | 8 months | ±2.4% | ±0.6% | -3.22 | No |
