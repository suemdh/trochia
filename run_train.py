import sys
sys.path.insert(0, "src")
from models.train_pipeline import run
run(use_auto_arima=False)
