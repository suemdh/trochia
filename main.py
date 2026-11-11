"""
Main orchestrator -- fetches raw data ahead of training:
1. Fetch data from FRED and USDA -- the only sources: both are public
   government data, safe to show to paying users
2. (Models are trained separately/interactively -- see src/models/)

src/data/clean.py and src/features/build_features.py exist but aren't called
here -- they write to data/processed/ (master_dataset.csv, features.csv),
and nothing downstream reads either file. train_pipeline.py reads straight
from data/raw/ and builds its own features in build_lstm_features(), so
running that extra clean/merge/feature-build step here would just burn time
producing output nothing uses.

Usage:
    python main.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.data import fetch_fred, fetch_usda


def ensure_dirs():
    for d in ["data/raw", "data/processed", "outputs"]:
        os.makedirs(d, exist_ok=True)


def run_pipeline():
    ensure_dirs()

    print("=" * 60)
    print("STEP 1: Fetching data (FRED, USDA)")
    print("=" * 60)

    print("\n-- FRED --")
    try:
        fred_df = fetch_fred.fetch_all()
        fred_df.to_csv("data/raw/fred_data.csv", index=False)
        print(f"Saved {len(fred_df)} rows")
    except Exception as e:
        print(f"FRED fetch failed: {e}")

    print("\n-- USDA AMS --")
    try:
        usda_results = fetch_usda.fetch_all()
        for name, df in usda_results.items():
            df.to_csv(f"data/raw/usda_{name}.csv", index=False)
            print(f"Saved {name}: {len(df)} rows")
    except Exception as e:
        print(f"USDA fetch failed: {e}")

    print("\n" + "=" * 60)
    print("DONE. Next steps:")
    print("- Train models: see src/models/ (baseline_linear.py, statistical_sarima.py, ai_lstm.py, hybrid.py)")
    print("- Launch dashboard: streamlit run src/dashboard/app.py")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
