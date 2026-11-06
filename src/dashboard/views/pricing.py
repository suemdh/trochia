"""Trochia - Pricing page."""
import os, sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from commodity_maps import TOTAL_COMMODITIES

# Each feature is True (included), False (not in this plan), or SOON (planned,
# not built yet). Only list as True what the product actually does today --
# this used to advertise SMS alerts, an API, team seats and an SLA that didn't exist.
SOON = "soon"

PLANS = [
    {
        "name": "Starter",
        "price": 19,
        "desc": "For individual operators and small buyers.",
        "featured": False,
        "features": [
            (True,  "Up to 5 commodities"),
            (True,  "Weekly forecasts with live market prices"),
            (True,  "Price charts"),
            (True,  "Savings calculator"),
            (SOON,  "Email alerts when an item turns Buy ahead"),
            (False, f"All {TOTAL_COMMODITIES} commodities"),
            (False, "API access"),
            (False, "Team seats"),
        ],
    },
    {
        "name": "Pro",
        "price": 49,
        "desc": "For growing businesses tracking multiple inputs.",
        "featured": True,
        "features": [
            (True,  f"All {TOTAL_COMMODITIES} commodities"),
            (True,  "Weekly forecasts with live market prices"),
            (True,  "Full price history charts"),
            (True,  "Savings calculator"),
            (True,  "Margin of error and likely price range on every forecast"),
            (SOON,  "Email and text alerts"),
            (SOON,  "AI chat assistant"),
            (False, "API access"),
            (False, "Team seats"),
        ],
    },
    {
        "name": "Business",
        "price": 99,
        "desc": "For teams and companies with complex supply chains.",
        "featured": False,
        "features": [
            (True,  "Everything in Pro"),
            (True,  "Priority email support"),
            (SOON,  "API access"),
            (SOON,  "Up to 10 team seats"),
            (SOON,  "Custom commodity tracking"),
            (SOON,  "Data exports"),
        ],
    },
]


def _feature_row(state, feat: str) -> str:
    if state == SOON:
        return (f'<div class="price-feature"><span class="price-x">·</span>{feat} '
                f'<span style="font-size:0.7rem;color:#F0B429;">coming soon</span></div>')
    return f'<div class="price-feature"><span class="price-{"check" if state else "x"}">{"+" if state else "-"}</span>{feat}</div>'


def render():
    st.markdown('<div class="sec-header">Subscription Plans</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8BA0B0;font-size:0.88rem;margin-bottom:1.5rem;">'
                'Simple, transparent pricing. Cancel anytime. <strong style="color:#F0B429;">Paid plans '
                'are coming soon</strong> -- start with a free 14-day trial today.</p>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, plan in zip([c1, c2, c3], PLANS):
        card_css = "price-card-featured" if plan["featured"] else "price-card"
        tag = '<span style="background:#007A8E;color:white;font-size:0.7rem;padding:2px 8px;border-radius:10px;margin-left:0.5rem;">POPULAR</span>' if plan["featured"] else ""
        feature_rows = "".join(_feature_row(state, feat) for state, feat in plan["features"])
        with col:
            st.markdown(f"""
            <div class="{card_css}">
                <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.25rem;">
                    {plan['name']}{tag}
                </div>
                <div style="font-size:0.8rem;color:#8BA0B0;margin-bottom:1rem;">{plan['desc']}</div>
                <div class="price-amount">${plan['price']}</div>
                <div class="price-period">/ month</div>
                <hr style="border-color:#1E3A5F;margin:1rem 0;">
                {feature_rows}
            </div>
            """, unsafe_allow_html=True)
            cta = "Start free trial"
            btn_type = "primary" if plan["featured"] else "secondary"
            if st.button(cta, use_container_width=True, type=btn_type, key=f"plan_{plan['name']}"):
                st.session_state.page = "Profile"; st.rerun()

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    st.markdown('<div class="sec-header">FAQ</div>', unsafe_allow_html=True)
    faqs = [
        ("Can I cancel anytime?", "Yes, from the Billing page. You keep access until the end of the month "
                                  "you've already paid for, and you won't be charged again."),
        ("Is there a free trial?", "Yes -- a 14-day free trial. No credit card needed to start."),
        ("What payment methods do you accept?", "All major credit and debit cards, processed securely by Stripe."),
        ("Can I switch plans later?", "Yes, anytime from Billing > Manage subscription. The change takes effect "
                                      "right away, and you're only charged (or credited) the difference for the "
                                      "rest of the month."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.markdown(f'<span style="font-size:0.85rem;color:#8BA0B0;">{a}</span>', unsafe_allow_html=True)
