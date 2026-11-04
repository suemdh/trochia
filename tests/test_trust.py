"""
Trust checks run across every commodity in commodity_maps -- the things that
must hold for a business to act on a card. No test framework needed:

    python tests/test_trust.py        (pytest also picks these up if installed)
"""
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [os.path.join(ROOT, "src"), ROOT]

from commodity_maps import (FRED_COMMODITY_MAP, USDA_COMMODITY_MAP, YFINANCE_COMMODITY_MAP,
                            PLAUSIBLE_RANGE, strip_unit)
from decision.engine import ForecastInput, evaluate, estimate_dollar_impact, horizon_in_weeks
from data.lag_compensator import estimate_today

ALL = {**FRED_COMMODITY_MAP, **USDA_COMMODITY_MAP, **YFINANCE_COMMODITY_MAP}
FORECASTS = pd.read_csv(os.path.join(ROOT, "outputs", "forecasts.csv"))


def _rec(r, current=None, beats=None):
    bn = r["beat_naive"]
    return evaluate(ForecastInput(
        commodity=r["commodity"], current_price=current or r["current_price"],
        forecast_price=r["forecast_price"], horizon_weeks=int(r["horizon_steps"]),
        confidence=r["confidence"], weekly_usage_units=10, unit_label=r["unit"],
        horizon_unit=r["horizon_unit"], days_per_step=int(r["step_days"]),
        rmse_pct=r["rmse_pct"] if pd.notna(r["rmse_pct"]) else float("inf"),
        beats_naive=(str(bn) == "True") if beats is None else beats,
    ))


def test_config_complete():
    for name in ALL:
        lo, hi = PLAUSIBLE_RANGE[name]
        assert 0 < lo < hi, name


def test_unit_labels_clean():
    for name, (_, unit) in ALL.items():
        u = strip_unit(unit)
        assert u and "$" not in u and not u.startswith("/"), (name, u)


def test_current_prices_in_range():
    for _, r in FORECASTS.iterrows():
        lo, hi = PLAUSIBLE_RANGE[r["commodity"]]
        assert lo <= r["current_price"] <= hi, (r["commodity"], r["current_price"])


def test_range_catches_100x_scale_errors():
    # The cents-vs-dollars class of bug (e.g. hogs quoted 60.0 c/lb shown as $60/lb).
    for _, r in FORECASTS.iterrows():
        lo, hi = PLAUSIBLE_RANGE[r["commodity"]]
        p = r["current_price"]
        assert not (lo <= p * 100 <= hi), f"{r['commodity']}: 100x error would pass range check"
        assert not (lo <= p / 100 <= hi), f"{r['commodity']}: /100 error would pass range check"


def test_header_matches_alert_text():
    # Header % and the % quoted inside the alert must be the same number --
    # including after a live price replaces the training-time one.
    for _, r in FORECASTS.iterrows():
        for current in (None, r["current_price"] * 0.9):
            rec = _rec(r, current)
            assert f"{rec.pct_change * 100:+.1f}%" in rec.message, r["commodity"]


def test_alert_has_no_broken_units():
    for _, r in FORECASTS.iterrows():
        assert "$/" not in _rec(r).message, r["commodity"]


def test_no_skill_model_never_fires_red():
    for _, r in FORECASTS.iterrows():
        # Force a huge forecast move: a no-skill model still must not say RED.
        r = r.copy(); r["forecast_price"] = r["current_price"] * 1.5
        assert _rec(r, beats=False).signal != "RED", r["commodity"]


def test_savings_math():
    for _, r in FORECASTS.iterrows():
        fi = ForecastInput(commodity=r["commodity"], current_price=r["current_price"],
                           forecast_price=r["forecast_price"], horizon_weeks=int(r["horizon_steps"]),
                           confidence=r["confidence"], weekly_usage_units=40,
                           days_per_step=int(r["step_days"]))
        expected = (r["forecast_price"] - r["current_price"]) * 40 * horizon_in_weeks(fi)
        assert abs(estimate_dollar_impact(fi, 0) - expected) < 1e-6, r["commodity"]


def test_stale_data_is_refused():
    dates = pd.Series(pd.date_range("2023-01-01", periods=24, freq="MS"))
    info = estimate_today(pd.Series(range(1, 25), dtype=float), dates)
    assert info["too_stale"] and info["estimated_price"] is None


def test_password_hashing():
    sys.path.insert(0, os.path.join(ROOT, "src", "dashboard"))
    import hashlib
    from auth import _hash, _verify
    h1, h2 = _hash("correct horse"), _hash("correct horse")
    assert h1 != h2, "same password produced the same hash -- no salt"
    assert _verify("correct horse", h1) and not _verify("wrong", h1)
    legacy = hashlib.sha256(b"old pw").hexdigest()  # accounts created before the upgrade
    assert _verify("old pw", legacy) and not _verify("nope", legacy)


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]
    failed = 0
    for n, f in tests:
        try:
            f(); print(f"PASS  {n}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {n}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed across {len(ALL)} commodities")
    sys.exit(1 if failed else 0)
