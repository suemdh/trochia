"""Trochiá — Commodities detail page: chart + scenario calculator."""
import os, sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "src"))

from commodity_maps import (
    FRED_COMMODITY_MAP, USDA_COMMODITY_MAP, strip_unit,
)
from decision.engine import SIGNAL_LABEL

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw")

# Built from the same source-of-truth maps train_pipeline.py forecasts from, so
# a commodity's chart can never point at a different (or no) data source than
# the one that actually produced its current/forecast price. This used to be a
# hand-maintained dict that fell out of sync as commodities were added -- by
# the time it was audited, ~34 of 44 commodities had no entry at all and were
# silently charting fabricated random-walk data next to real price metrics.
RAW_FILE_MAP = {}
for _name, (_col, _unit) in FRED_COMMODITY_MAP.items():
    RAW_FILE_MAP[_name] = ("fred_data.csv", _col, 1.0)
for _name, (_key, _unit) in USDA_COMMODITY_MAP.items():
    RAW_FILE_MAP[_name] = (f"usda_{_key}.csv", "value", 1.0)

SIG_COLOR = {"RED":"rgba(255,75,75,1)","YELLOW":"rgba(240,180,41,1)","GREEN":"rgba(33,197,93,1)"}
SIG_BAND  = {"RED":"rgba(255,75,75,0.12)","YELLOW":"rgba(240,180,41,0.12)","GREEN":"rgba(33,197,93,0.12)"}


@st.cache_data(ttl=300)
def load_raw(filename: str, col: str, scale: float = 1.0):
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if col not in df.columns:
        return None
    df = df[["date", col]].dropna()
    df[col] = pd.to_numeric(df[col], errors="coerce") * scale
    return df.dropna().sort_values("date").tail(104)


def render(commodities: dict):
    st.markdown('<div class="sec-header">Commodity Detail</div>', unsafe_allow_html=True)

    names   = list(commodities.keys())
    default = st.session_state.get("selected_commodity", names[0])
    idx     = names.index(default) if default in names else 0
    selected = st.selectbox("Select commodity", names, index=idx)
    st.session_state.selected_commodity = selected

    v   = commodities[selected]
    sig = v["signal"]
    pct = v["pct"] * 100
    unit = v.get("unit", "")
    horizon      = v.get("horizon", 8)
    horizon_unit = v.get("horizon_unit", "weeks")
    span = f"{horizon} {horizon_unit[:-1] if horizon == 1 else horizon_unit}"

    # ── Metrics row ────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price today",  f"${v['current']:.3g}", help=unit)
    m2.metric(f"Expected in {span}", f"${v['forecast']:.3g}")
    m3.metric("Expected change", f"{'+' if pct>=0 else ''}{pct:.1f}%")
    err = v.get("rmse_pct")
    m4.metric("Margin of error", f"±{err*100:.0f}%" if err is not None else "n/a",
              help="On average, past forecasts for this item were off by about this much.")
    with m5:
        st.markdown(f'<div style="padding:1.4rem 0;">'
                    f'<span class="badge-{sig.lower()}">{SIGNAL_LABEL[sig]}</span></div>',
                    unsafe_allow_html=True)

    skill = ("Track record: in testing, this forecast was more accurate than assuming prices stay flat."
             if str(v.get("beat_naive")) == "True" else
             "No proven track record yet: in testing, this forecast wasn't more accurate than assuming "
             "prices stay flat -- treat it as a heads-up, not a reason to buy.")
    st.caption(
        f"{skill} Forecasts are based on past price patterns and can't see breaking news. "
        "Prices shown are market or national-average prices; your supplier's price will include "
        "their own costs like delivery and markup. For information only -- not financial advice."
    )

    # Recommendation
    css = f"sig-card-{sig.lower()}"
    st.markdown(f'<div class="sig-card {css}" style="margin:0.75rem 0;">'
                f'<span style="font-size:0.88rem;">{v.get("message","")}</span></div>',
                unsafe_allow_html=True)

    if v.get("volatility_flag"):
        move = v.get("recent_move_pct")
        move_str = f"{move*100:+.1f}%" if move is not None else "an unusual amount"
        if v.get("sector_flag"):
            reason = (f"Energy prices are all moving the same way right now ({selected}: {move_str} "
                      f"recently). That usually means something big is going on, like a supply disruption.")
        else:
            reason = f"{selected} moved {move_str} over the last {span}, which is more than usual for it."
        st.markdown(f"""
        <div class="sig-card sig-card-yellow" style="margin:0.75rem 0;border-left:4px solid #F0B429;">
            <span style="font-size:0.88rem;font-weight:600;">⚠ Prices are jumping around</span><br>
            <span style="font-size:0.82rem;color:#8BA0B0;">
                {reason} Our forecast is based on past patterns and can't see the news, so
                double-check with your supplier before acting on it.
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Chart ──────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-header">Price History & Forecast</div>', unsafe_allow_html=True)

    fi = RAW_FILE_MAP.get(selected)
    hist_df = load_raw(*fi) if fi else None

    if hist_df is not None and len(hist_df) >= 4:
        hx = hist_df["date"].dt.strftime("%Y-%m-%d").tolist()
        hy = hist_df.iloc[:, 1].tolist()
    else:
        # This used to draw a made-up random-walk "history" here. Say so instead.
        hx = [datetime.today().strftime("%Y-%m-%d")]
        hy = [v["current"]]
        st.info("Price history for this item isn't available right now -- the chart shows "
                "today's price and the forecast only.")

    horizon   = v.get("horizon", 8)
    step_days = int(v.get("step_days", 7))   # a step is the source's own interval: a month, week or day
    last      = pd.to_datetime(hx[-1])
    fx        = [(last + timedelta(days=step_days * (i+1))).strftime("%Y-%m-%d") for i in range(horizon)]
    fy      = list(np.linspace(hy[-1], v["forecast"], horizon))

    # Use model-derived confidence band when available, else fall back to estimate
    lb = v.get("lower_bound")
    ub = v.get("upper_bound")
    if lb is not None and ub is not None:
        lo_band = list(np.linspace(hy[-1], lb, horizon))
        hi_band = list(np.linspace(hy[-1], ub, horizon))
    else:
        band = v["forecast"] * (1 - v["confidence"]) * 0.4
        lo_band = [p - band for p in fy]
        hi_band = [p + band for p in fy]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hx, y=hy, name="Past prices",
                             line=dict(color="#007A8E", width=2)))
    fig.add_trace(go.Scatter(x=fx, y=fy, name="Forecast",
                             line=dict(color=SIG_COLOR[sig], width=2, dash="dash")))
    fig.add_trace(go.Scatter(
        x=fx+fx[::-1], y=hi_band+lo_band[::-1],
        fill="toself", fillcolor=SIG_BAND[sig],
        line=dict(color="rgba(0,0,0,0)"), name="Likely range",
    ))
    fig.update_layout(
        paper_bgcolor="#0B1929", plot_bgcolor="#112233",
        margin=dict(l=0,r=0,t=20,b=0), height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="white")),
        yaxis=dict(title=unit, gridcolor="#1E3A5F", color="white"),
        xaxis=dict(gridcolor="#1E3A5F", color="white"),
        font=dict(color="white"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Scenario calculator ────────────────────────────────────────────────────
    st.markdown('<div class="sec-header">Scenario Calculator</div>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#8BA0B0;font-size:0.85rem;">How much could you save by buying ahead? '
                f'Enter how much you use and how many weeks of stock you\'d buy now. We compare today\'s '
                f'price with the forecast price in {span} (${v["forecast"]:.3g}).</p>',
                unsafe_allow_html=True)

    unit_word = strip_unit(unit)
    ca, cb = st.columns(2)
    with ca:
        usage = st.number_input(f"How much you use per week ({unit_word})", min_value=1, value=100, step=10)
    with cb:
        weeks = st.number_input("Weeks of stock to buy now", min_value=1, max_value=26, value=4)

    now_cost   = v["current"]  * usage * weeks
    later_cost = v["forecast"] * usage * weeks
    savings    = max(0, later_cost - now_cost)

    r1, r2, r3 = st.columns(3)
    r1.metric("Cost if you buy now",       f"${now_cost:,.0f}")
    r2.metric("Cost if you wait",          f"${later_cost:,.0f}")
    r3.metric("You could save",            f"${savings:,.0f}")

    if savings > 0 and sig in ("RED","YELLOW"):
        st.markdown(f"""
        <div class="sig-card sig-card-green" style="font-size:0.86rem;margin-top:0.5rem;">
            Buying {weeks} weeks of {selected} now could save you
            <strong style="color:#21C55D;">${savings:,.0f}</strong>
            -- if prices rise as forecast.
        </div>
        """, unsafe_allow_html=True)
