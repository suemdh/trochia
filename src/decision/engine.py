"""
Decision Engine
Converts a raw forecast ("beef up 14% in 8 weeks") into a GREEN/YELLOW/RED signal
and a plain-English, dollar-quantified recommendation for a restaurant owner.
"""
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from commodity_maps import strip_unit


@dataclass
class ForecastInput:
    commodity: str
    current_price: float
    forecast_price: float
    horizon_weeks: int  # horizon in STEPS -- see horizon_unit for what a step is
    confidence: float  # 0-1, e.g. derived from model RMSE / prediction interval width
    weekly_usage_units: float  # kept for backward compatibility; no longer used in
                                # message text -- see build_message()'s docstring
    unit_label: str = "lb"
    horizon_unit: str = "weeks"  # "weeks" / "months" -- what one step means
    days_per_step: int = 7       # calendar days per step, for usage maths
    rmse_pct: float = 0.0        # model's own backtested error, as a fraction of price --
                                  # lets classify_signal() require a move to be bigger than
                                  # the model's typical mistake before calling it high-confidence
    beats_naive: bool = True     # did the model beat a "price stays the same" forecast in
                                  # backtesting? If not, it has no demonstrated skill, so its
                                  # signal is capped at a YELLOW "watch" -- never a RED buy alert


@dataclass
class Recommendation:
    commodity: str
    signal: str  # GREEN / YELLOW / RED
    pct_change: float
    horizon_weeks: int
    dollar_impact: float
    message: str


# Thresholds -- tune these to your actual risk tolerance
YELLOW_THRESHOLD_PCT = 0.05   # 5% forecasted move triggers YELLOW
RED_THRESHOLD_PCT = 0.10      # 10% forecasted move triggers RED
MIN_CONFIDENCE_FOR_RED = 0.6  # below this confidence, cap signal at YELLOW even if move is big
RED_RMSE_MULTIPLIER = 1.5     # a move must also clear this many multiples of the model's
                               # own backtested error to be called "high-confidence" -- a 10%
                               # move means nothing if this model is typically off by 15%


def classify_signal(pct_change: float, confidence: float, rmse_pct: float = 0.0,
                    beats_naive: bool = True) -> str:
    direction_up = pct_change > 0
    magnitude = abs(pct_change)

    if magnitude < YELLOW_THRESHOLD_PCT:
        return "GREEN"
    red_bar = max(RED_THRESHOLD_PCT, RED_RMSE_MULTIPLIER * rmse_pct)
    if magnitude < red_bar or confidence < MIN_CONFIDENCE_FOR_RED or not beats_naive:
        return "YELLOW" if direction_up else "GREEN"
    return "RED" if direction_up else "GREEN"


def horizon_in_weeks(forecast: ForecastInput) -> float:
    """Horizon expressed in weeks, whatever unit the steps are in."""
    return forecast.horizon_weeks * forecast.days_per_step / 7.0


def estimate_dollar_impact(forecast: ForecastInput, pct_change: float) -> float:
    """
    Rough savings/cost estimate: if you pre-buy the whole horizon's usage at today's
    price instead of paying the forecasted price, the savings/cost is the price delta
    times volume. Usage is quoted weekly, so convert the horizon to weeks first --
    8 monthly steps is ~34 weeks of usage, not 8.
    """
    price_delta = forecast.forecast_price - forecast.current_price
    total_units = forecast.weekly_usage_units * horizon_in_weeks(forecast)
    return price_delta * total_units


def build_message(forecast: ForecastInput, signal: str, pct_change: float, dollar_impact: float) -> str:
    """
    Used to quote a specific "pre-purchase ~N units" recommendation built on
    a hardcoded, fake weekly_usage_units=10 assumption baked in at training
    time -- training runs once per commodity, shared across every business,
    so it can never know any real business's actual usage. That produced
    nonsense like "pre-purchase ~40 $/lb" (the raw unit string leaking into
    the sentence) based on a volume nobody actually buys. Per-unit price
    delta needs no such assumption -- it's just forecast minus current -- so
    it's always honest. The real, usage-specific savings number comes from
    the Scenario Calculator on the Commodity Detail page, which asks the
    business for their own usage instead of guessing one.
    """
    pct_str   = f"{pct_change * 100:+.1f}%"
    direction = "up" if pct_change > 0 else "down"
    span      = f"{forecast.horizon_weeks} {forecast.horizon_unit}"
    unit      = strip_unit(forecast.unit_label)
    delta     = forecast.forecast_price - forecast.current_price
    delta_str = f"${abs(delta):.2f}/{unit} {'more' if delta > 0 else 'less'}"

    if signal == "GREEN":
        return (
            f"{forecast.commodity}: prices stable or favorable ({pct_str} over {span}). "
            f"No action needed."
        )
    elif signal == "YELLOW":
        caveat = ("" if forecast.beats_naive else
                  " This model hasn't beaten a simple \"price stays the same\" forecast in "
                  "backtesting, so treat this as a watch item, not a buy signal.")
        return (
            f"{forecast.commodity}: moderate risk detected, {direction} {pct_str} over "
            f"{span} ({delta_str} than today). Monitor closely, and use the Scenario "
            f"Calculator below to estimate the impact on your own usage.{caveat}"
        )
    else:  # RED
        return (
            f"{forecast.commodity}: forecast move ({pct_str} over {span}, {delta_str} "
            f"than today) is large enough, relative to this model's own track record, to "
            f"call it a likely price spike. Consider locking in current pricing -- use the "
            f"Scenario Calculator below for savings based on your own usage."
        )


def evaluate(forecast: ForecastInput) -> Recommendation:
    pct_change = (forecast.forecast_price - forecast.current_price) / forecast.current_price
    signal = classify_signal(pct_change, forecast.confidence, forecast.rmse_pct, forecast.beats_naive)
    dollar_impact = estimate_dollar_impact(forecast, pct_change)
    message = build_message(forecast, signal, pct_change, dollar_impact)

    return Recommendation(
        commodity=forecast.commodity,
        signal=signal,
        pct_change=pct_change,
        horizon_weeks=forecast.horizon_weeks,
        dollar_impact=dollar_impact,
        message=message,
    )


if __name__ == "__main__":
    # Reproduces the "Real Example" from the guide
    example = ForecastInput(
        commodity="Ground Beef",
        current_price=4.20,
        forecast_price=4.79,  # ~14% up
        horizon_weeks=8,
        confidence=0.75,
        weekly_usage_units=120,  # lbs/week
        unit_label="lbs",
        rmse_pct=0.03,
    )
    rec = evaluate(example)
    print(f"Signal: {rec.signal}")
    print(f"Message: {rec.message}")

    # ── Self-check: catches the two bugs this module was just fixed for ──
    assert "$/" not in rec.message, "raw unit string leaked into message"
    assert rec.signal == "RED", "14% move with low error and high confidence should be RED"

    # A model with high historical error shouldn't get to call the same move "RED".
    noisy = ForecastInput(**{**example.__dict__, "rmse_pct": 0.20})
    noisy_rec = evaluate(noisy)
    assert noisy_rec.signal != "RED", "a move smaller than the model's own error was called high-confidence"

    # pct_change in the message must match the Recommendation's own pct_change --
    # the exact class of bug found in app.py (header recomputed pct, alert text didn't).
    pct_str_in_message = f"{rec.pct_change * 100:+.1f}%"
    assert pct_str_in_message in rec.message, "message text disagrees with rec.pct_change"

    # A model that can't beat "no change" must never fire a RED buy alert.
    no_skill = evaluate(ForecastInput(**{**example.__dict__, "beats_naive": False}))
    assert no_skill.signal == "YELLOW", "no-skill model fired a high-confidence alert"
    assert "watch item" in no_skill.message

    print("All self-checks passed.")
