"""
Append-only audit log so any price or alert shown to a business can be
explained later: what was fetched, from where, when, and what inputs drove
each RED/YELLOW alert. Two JSONL files in outputs/ (one row per event, never
rewritten) -- plain text, grep-able, no new dependency.

Deduped per (day, commodity) so 43 commodities refreshed on every page load
don't produce unbounded rows -- one entry per commodity per day is enough to
answer "why did this alert fire," and the day boundary is naturally when the
answer could change (a new live price, a new retrain).
"""
import json
import os
from datetime import date, datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT_DIR = os.path.join(ROOT, "outputs")
PRICE_LOG = os.path.join(OUT_DIR, "audit_price_log.jsonl")
ALERT_LOG = os.path.join(OUT_DIR, "audit_alert_log.jsonl")

_seen_today = set()  # (log_path, key) -> dedup within this process's lifetime;
                      # cross-process dedup also checked against today's file below


def _already_logged_today(path: str, key: tuple) -> bool:
    cache_key = (path, key)
    if cache_key in _seen_today:
        return True
    today = date.today().isoformat()
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                f.seek(max(0, os.path.getsize(path) - 200_000))  # tail-scan, not full-file
                for line in f.read().decode("utf-8", errors="ignore").splitlines():
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if row.get("date") == today and tuple(row.get("key", [])) == key:
                        _seen_today.add(cache_key)
                        return True
        except Exception:
            pass
    return False


def _append(path: str, key: tuple, payload: dict):
    if _already_logged_today(path, key):
        return
    row = {"date": date.today().isoformat(), "timestamp": datetime.now(timezone.utc).isoformat(),
           "key": list(key), **payload}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    _seen_today.add((path, key))


def log_price_fetch(commodity: str, source: str, price: float, ticker: str | None,
                     as_of: str, range_check_passed: bool):
    """One row per commodity per day the live feed was actually hit (not a cache read)."""
    _append(PRICE_LOG, (commodity,), {
        "commodity": commodity, "source": source, "price": price,
        "ticker": ticker, "as_of": as_of, "range_check_passed": range_check_passed,
    })


def log_alert(commodity: str, signal: str, pct_change: float, current_price: float,
             forecast_price: float, confidence: float, rmse_pct: float | None,
             beats_naive: bool, message: str, is_live: bool):
    """One row per commodity per day it showed a non-GREEN signal -- GREEN
    ("no action needed") isn't an alert a business would need explained."""
    if signal == "GREEN":
        return
    _append(ALERT_LOG, (commodity, signal), {
        "commodity": commodity, "signal": signal, "pct_change": pct_change,
        "current_price": current_price, "forecast_price": forecast_price,
        "confidence": confidence, "rmse_pct": rmse_pct, "beats_naive": beats_naive,
        "message": message, "is_live_price": is_live,
    })
