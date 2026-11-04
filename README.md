# Trochiá — Commodity Price Intelligence Platform

A commodity price forecasting platform for small food/energy businesses. Fetches real price
data, trains a hybrid ML forecast (Baseline + SARIMA + LSTM) per commodity, and surfaces
GREEN/YELLOW/RED buy signals through a Streamlit dashboard.

## What's included

- **Data fetchers** for three live sources: FRED/BLS (retail grocery prices), USDA AMS (cash
  wheat bids, wholesale cream), and Yahoo Finance (exchange-traded futures — grains, energy,
  metals, softs, livestock). See `src/commodity_maps.py` for the exact list — it's the single
  source of truth both the training pipeline and the dashboard read from, so they can't drift
  out of sync.
- **Cleaning pipeline** that merges FRED/USDA raw data into one consistent weekly dataset
  (`src/data/clean.py` → `data/processed/master_dataset.csv`)
- **Feature engineering** (lags, momentum) in `src/features/build_features.py` — note this
  output isn't currently consumed by the live training pipeline (see Known limitations)
- **3 models per commodity**: Linear baseline, SARIMA (auto-tuned via `pmdarima` when
  installed), LSTM — blended by a RMSE-weighted Hybrid model
- **Lag compensation** (`src/data/lag_compensator.py`) projects a current-price estimate from
  lagged monthly government data, with a staleness ceiling so a discontinued series can't be
  silently mislabeled as a live, high-confidence price
- **Decision engine** (`src/decision/engine.py`) turns a forecast into GREEN/YELLOW/RED with a
  dollar-quantified recommendation, aware of each commodity's own forecast horizon (weeks for
  futures, months for grocery items — see `horizon_unit`)
- **Dashboard** (Streamlit) — Market list, per-commodity charts + scenario calculator, a real
  Claude-API-backed AI Chat page (falls back to a static FAQ if no `ANTHROPIC_API_KEY` is set),
  pricing/billing/profile pages

## How to run it

1. `pip install -r requirements.txt`
2. Copy the API keys you have into a `.env` file at the project root (see below — none are
   hardcoded or bundled, you need your own)
3. `python main.py` — fetches fresh FRED + USDA data into `data/raw/` and `data/processed/`
4. `python src/models/train_pipeline.py` — trains all commodities (fetching yfinance history on
   demand as it goes) and writes `outputs/forecasts.csv` (this is what the dashboard reads)
5. `streamlit run src/dashboard/app.py`

## API keys (`.env`)

| Var | Required for | Free signup |
|---|---|---|
| `FRED_API_KEY` | Retail grocery prices | fred.stlouisfed.org/docs/api/api_key.html |
| `USDA_API_KEY` | Cash wheat / cream prices | mymarketnews.ams.usda.gov/mars-api/getting-started (MARS API specifically — USDA has other, incompatible key systems) |
| `ANTHROPIC_API_KEY` | AI Chat (optional — falls back to static FAQ without it) | console.anthropic.com |

That's the whole list. Yahoo Finance (grains/energy/metals futures) needs no key at all. Earlier
drafts also fetched Alpha Vantage, EIA, and NOAA data, but none of it ever fed the live forecasts
or dashboard, so those fetchers were removed rather than left as unused dead weight.

## Folder structure

```
trochia/
├── .env                       # Your real keys — not committed, create it yourself
├── requirements.txt
├── main.py                    # Fetches FRED + USDA, cleans, builds features
├── src/
│   ├── commodity_maps.py      # Single source of truth: which commodities, which files
│   ├── data/
│   │   ├── fetch_fred.py
│   │   ├── fetch_usda.py
│   │   ├── fetch_yfinance.py  # Called on demand by train_pipeline.py, not by main.py
│   │   ├── lag_compensator.py
│   │   └── clean.py
│   ├── features/
│   │   └── build_features.py
│   ├── models/
│   │   ├── train_pipeline.py  # The real entry point — trains every commodity, writes forecasts.csv
│   │   ├── baseline_linear.py
│   │   ├── statistical_sarima.py
│   │   ├── ai_lstm.py
│   │   └── hybrid.py
│   ├── decision/
│   │   └── engine.py
│   └── dashboard/
│       ├── app.py
│       ├── chatbot.py
│       └── views/
├── data/raw/                  # Raw pulled data lands here
├── data/processed/            # Cleaned + feature data lands here (see Known limitations)
└── outputs/forecasts.csv      # What the dashboard actually reads
```

## Known limitations

- **`data/processed/features.csv` isn't read by the live pipeline.** `train_pipeline.py` trains
  directly off `data/raw/fred_data.csv`, `data/raw/usda_*.csv`, and yfinance history — not the
  engineered features file. The feature-engineering step still runs (via `main.py`) but its
  output is currently unused; wiring it in (or dropping the step) is a reasonable next call.
- Three FRED-tracked items (canned tuna, apples, peanut butter) were dropped from
  `commodity_maps.py` because BLS discontinued their underlying series in 2017 — there's no live
  data left to forecast from. `lag_compensator.py`'s staleness check (`MAX_REASONABLE_LAG_WEEKS`)
  will automatically catch any other FRED series that goes the same way in the future.
- The decision engine uses reasonable default thresholds (e.g. >5% forecast move = YELLOW,
  >10% = RED) — tune these to your actual risk tolerance in `src/decision/engine.py`.
- Deployment (hosting the dashboard somewhere other than locally) isn't wired up yet.
