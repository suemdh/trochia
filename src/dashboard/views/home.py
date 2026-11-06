"""Trochiá — Home page."""
import os
import streamlit as st
from decision.engine import SIGNAL_LABEL
from commodity_maps import TOTAL_COMMODITIES

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

SIG_COLOR = {"RED":"#FF4B4B","YELLOW":"#F0B429","GREEN":"#21C55D"}
SIG_CLASS  = {"RED":"sig-card-red","YELLOW":"sig-card-yellow","GREEN":"sig-card-green"}


def render(commodities: dict):
    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#071420 0%,#003B5C 60%,#007A8E 100%);
         border-radius:12px;padding:3rem 2.5rem 2.5rem;margin-bottom:2rem;">
        <h1 style="font-size:2.4rem;margin:0 0 0.4rem;letter-spacing:0.08em;color:#FFFFFF;">TROCHIÁ</h1>
        <p style="font-size:1.05rem;color:#A8DBB9;margin:0 0 1.5rem;max-width:520px;">
            Price forecasts for the ingredients and supplies your business buys -- so you get a
            heads-up before prices rise, and know when it's fine to wait.
        </p>
    </div>
    """, unsafe_allow_html=True)

    btn1, btn2, _ = st.columns([1, 1, 3])
    with btn1:
        if st.button("View Market", use_container_width=True, type="primary"):
            st.session_state.page = "Market"; st.rerun()
    with btn2:
        if st.button("Start Free Trial", use_container_width=True):
            st.session_state.page = "Profile"; st.rerun()

    # ── Live snapshot ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-header">Live Market Snapshot</div>', unsafe_allow_html=True)

    sig_order = {"RED":0,"YELLOW":1,"GREEN":2}
    top3 = sorted(commodities.items(), key=lambda x: (sig_order.get(x[1]["signal"],3), -abs(x[1]["pct"])))[:3]

    cols = st.columns(3)
    for col, (name, v) in zip(cols, top3):
        sig = v["signal"]
        pct = v["pct"] * 100
        arrow = "+" if pct >= 0 else ""
        color = SIG_COLOR[sig]
        css   = SIG_CLASS[sig]
        with col:
            st.markdown(f"""
            <div class="sig-card {css}" style="text-align:center;">
                <div style="font-size:0.78rem;color:#8BA0B0;margin-bottom:0.3rem;">{name}</div>
                <div style="font-size:1.7rem;font-weight:700;color:#FFFFFF;">${v['current']:.3g}</div>
                <div style="font-size:0.75rem;color:#8BA0B0;margin:0.1rem 0;">{v.get('unit','')}</div>
                <div style="margin-top:0.5rem;">
                    <span class="badge-{sig.lower()}">{SIGNAL_LABEL[sig]}</span>
                    <span style="margin-left:0.5rem;font-size:0.8rem;color:{color};">
                        {arrow}{pct:.1f}%
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    _, c, _ = st.columns([1,1,1])
    with c:
        if st.button(f"See All {TOTAL_COMMODITIES} Commodities", use_container_width=True):
            st.session_state.page = "Market"; st.rerun()

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    # ── Feature cards ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-header">What Trochiá Does</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    for col, title, desc, border in [
        (f1, "Clear signals",
         f"Each of {TOTAL_COMMODITIES} items gets one simple call: Buy ahead, Watch, or No action "
         f"needed -- so you know at a glance what to do.",
         "#FF4B4B"),
        (f2, "Price forecasts",
         "Forecasts built from years of price history and updated every week, with an honest margin "
         "of error and a note when an item's forecast isn't proven yet.",
         "#007A8E"),
        (f3, "Savings calculator",
         "Enter how much you use and see what buying ahead could save you if prices rise as forecast.",
         "#21C55D"),
    ]:
        with col:
            st.markdown(f"""
            <div class="sig-card" style="border-left:4px solid {border};text-align:left;">
                <div style="font-size:0.95rem;font-weight:600;color:#FFFFFF;margin-bottom:0.5rem;">{title}</div>
                <div style="font-size:0.83rem;color:#8BA0B0;line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="trochia-footer">
        TROCHIÁ &nbsp;|&nbsp; Commodity Intelligence Platform<br>
        Data: FRED / BLS &nbsp;·&nbsp; USDA AMS &nbsp;·&nbsp; Yahoo Finance
    </div>
    """, unsafe_allow_html=True)
