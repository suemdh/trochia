"""
LSTM forecaster with improved architecture, early stopping, and model persistence.
Architecture: 2-layer LSTM (hidden=128) + Dropout(0.2) + Linear output (horizon=8).
Saves trained weights to data/models/{commodity}_lstm.pt and reloads if < 7 days old.
"""
import os
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")


class SequenceDataset(Dataset):
    def __init__(self, arr: np.ndarray, window: int = 12, horizon: int = 8):
        self.window  = window
        self.horizon = horizon
        self.X, self.y = [], []
        for i in range(len(arr) - window - horizon + 1):
            self.X.append(arr[i: i + window])
            self.y.append(arr[i + window: i + window + horizon, 0])
        self.X = torch.tensor(np.array(self.X), dtype=torch.float32)
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)

    def __len__(self):  return len(self.X)
    def __getitem__(self, i): return self.X[i], self.y[i]


class LSTMForecaster(nn.Module):
    def __init__(self, n_features: int = 1, hidden_size: int = 128,
                 num_layers: int = 2, horizon: int = 8, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden_size, num_layers,
                            batch_first=True, dropout=dropout if num_layers > 1 else 0.0)
        self.dropout = nn.Dropout(dropout)
        self.fc     = nn.Linear(hidden_size, horizon)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :])
        return self.fc(out)


def _model_path(commodity: str) -> str:
    os.makedirs(MODELS_DIR, exist_ok=True)
    safe = commodity.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
    return os.path.join(MODELS_DIR, f"{safe}_lstm.pt")


def _model_is_fresh(path: str, max_age_days: int = 7) -> bool:
    if not os.path.exists(path):
        return False
    age_days = (time.time() - os.path.getmtime(path)) / 86400
    return age_days < max_age_days


def train_lstm(
    feature_array: np.ndarray,
    commodity: str = "unknown",
    window: int = 12,
    horizon: int = 8,
    epochs: int = 100,
    batch_size: int = 16,
    lr: float = 1e-3,
    val_fraction: float = 0.2,
    patience: int = 10,
    force_retrain: bool = False,
) -> LSTMForecaster:
    """
    Train or load an LSTM model for a single commodity.
    feature_array: 2-D numpy array, shape (T, n_features). Column 0 is the target price.
    Returns a trained LSTMForecaster ready for inference.
    """
    n_features = feature_array.shape[1]
    path = _model_path(commodity)

    # Load from disk if fresh enough
    if not force_retrain and _model_is_fresh(path):
        model = LSTMForecaster(n_features=n_features)
        try:
            model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
            model.eval()
            print(f"  [{commodity}] Loaded LSTM from disk")
            return model
        except Exception:
            pass

    dataset = SequenceDataset(feature_array, window=window, horizon=horizon)
    if len(dataset) < 4:
        return LSTMForecaster(n_features=n_features)

    # Chronological train/val split
    val_size   = max(1, int(len(dataset) * val_fraction))
    train_size = len(dataset) - val_size
    train_ds = torch.utils.data.Subset(dataset, list(range(train_size)))
    val_ds   = torch.utils.data.Subset(dataset, list(range(train_size, len(dataset))))

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)

    model     = LSTMForecaster(n_features=n_features)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    best_val_loss  = float("inf")
    best_state     = None
    patience_count = 0

    for epoch in range(1, epochs + 1):
        model.train()
        for X_batch, y_batch in train_dl:
            optimizer.zero_grad()
            loss = criterion(model(X_batch), y_batch)
            loss.backward()
            optimizer.step()

        model.eval()
        val_losses = []
        with torch.no_grad():
            for X_val, y_val in val_dl:
                val_losses.append(criterion(model(X_val), y_val).item())
        val_loss = float(np.mean(val_losses))

        if epoch % 20 == 0:
            print(f"  [{commodity}] Epoch {epoch}/{epochs}  val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss  = val_loss
            best_state     = {k: v.clone() for k, v in model.state_dict().items()}
            patience_count = 0
        else:
            patience_count += 1
            if patience_count >= patience:
                print(f"  [{commodity}] Early stop at epoch {epoch} (best val={best_val_loss:.4f})")
                break

    if best_state:
        model.load_state_dict(best_state)

    try:
        torch.save(model.state_dict(), path)
        print(f"  [{commodity}] Saved LSTM to {path}")
    except Exception as e:
        print(f"  [{commodity}] Could not save LSTM: {e}")

    model.eval()
    return model


def forecast(model: LSTMForecaster, last_window: np.ndarray) -> np.ndarray:
    """
    Generate an 8-step forecast.
    last_window: shape (window, n_features)
    Returns: shape (horizon,)
    """
    model.eval()
    x = torch.tensor(last_window[np.newaxis], dtype=torch.float32)
    with torch.no_grad():
        return model(x).squeeze(0).numpy()
