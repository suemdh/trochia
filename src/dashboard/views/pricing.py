"""Trochia - Pricing page."""
import os, sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from commodity_maps import TOTAL_COMMODITIES

PLANS = [
    {
        "name": "Starter",
        "price": 19,
        "desc": "For individual operators and small buyers.",
        "featured": False,
        "features": [
            (True,  "5 tracked commodities"),
            (True,  "Weekly price signals"),
            (True,  "Email alerts on RED signals"),
            (True,  "Basic price charts"),
            (False, f"All {TOTAL_COMMODITIES} commodities"),
            (False, "Daily updates"),
            (False, "AI Chat assistant"),
            (False, "API access"),
            (False, "Multi-user seats"),
        ],
    },
    {
        "name": "Pro",
        "price": 49,
        "desc": "For growing businesses tracking multiple inputs.",
        "featured": True,
        "features": [
            (True,  f"All {TOTAL_COMMODITIES} commodities"),
            (True,  "Daily signal updates"),
            (True,  "Email + SMS alerts"),
            (True,  "Full price chart history"),
            (True,  "AI Chat assistant"),
            (True,  "Scenario Calculator"),
            (True,  "Forecast confidence bands"),
            (False, "API access"),
            (False, "Multi-user seats"),
        ],
    },
    {
        "name": "Business",
        "price": 99,
        "desc": "For teams and companies with complex supply chains.",
        "featured": False,
        "features": [
            (True,  "Everything in Pro"),
            (True,  "REST API access"),
            (True,  "Up to 10 user seats"),
            (True,  "Dedicated account support"),
            (True,  "Custom commodity tracking"),
            (True,  "White-label data exports"),
            (True,  "Priority model updates"),
            (True,  "SLA guarantee"),
            (True,  "Monthly cost review call"),
        ],
    },
]


def render():
    st.markdown('<div class="sec-header">Subscription Plans</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8BA0B0;font-size:0.88rem;margin-bottom:1.5rem;">'
                'Simple, transparent pricing. Cancel anytime.</p>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, plan in zip([c1, c2, c3], PLANS):
        card_css = "price-card-featured" if plan["featured"] else "price-card"
        tag = '<span style="background:#007A8E;color:white;font-size:0.7rem;padding:2px 8px;border-radius:10px;margin-left:0.5rem;">POPULAR</span>' if plan["featured"] else ""
        feature_rows = "".join(
            f'<div class="price-feature"><span class="price-{"check" if ok else "x"}">{"+" if ok else "-"}</span>{feat}</div>'
            for ok, feat in plan["features"]
        )
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
            cta = "Start Pro Trial" if plan["featured"] else f"Start {plan['name']}"
            btn_type = "primary" if plan["featured"] else "secondary"
            if st.button(cta, use_container_width=True, type=btn_type, key=f"plan_{plan['name']}"):
                st.session_state.page = "Profile"; st.rerun()

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    st.markdown('<div class="sec-header">FAQ</div>', unsafe_allow_html=True)
    faqs = [
        ("Can I cancel anytime?", "Yes. Cancel before your next billing date and you will not be charged again."),
        ("Is there a free trial?", "Yes - all plans come with a 14-day free trial. No credit card required to start."),
        ("What payment methods do you accept?", "Visa, Mastercard, Amex, and PayPal via Stripe."),
        ("Can I switch plans later?", "Yes, you can upgrade or downgrade at any time. Changes apply at the next billing cycle."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.markdown(f'<span style="font-size:0.85rem;color:#8BA0B0;">{a}</span>', unsafe_allow_html=True)
