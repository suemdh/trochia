"""Trochia - Profile page."""
import sys, os
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from auth import login_form, signup_form, logout, get_current_user, save_commodity_prefs

PLAN_COLOR = {"Starter":"#007A8E","Pro":"#21C55D","Business":"#F0B429","Trial":"#A8DBB9"}
PLAN_FEATURES = {
    "Trial":    ["All commodities (trial)", "Daily updates", "AI Chat", "Full charts", "Scenario Calculator"],
    "Starter":  ["5 commodities", "Weekly signals", "Email alerts", "Basic charts"],
    "Pro":      ["All commodities", "Daily updates", "AI Chat", "Full charts", "Scenario Calculator"],
    "Business": ["Everything in Pro", "API access", "10 user seats", "Dedicated support"],
}

ALL_COMMODITIES = [
    "Ground Beef","Chicken","Pork / Bacon","Pork Chops","Ham","Tuna (Canned)",
    "Eggs","Butter","Milk","Cheese","White Bread","Flour","Peanut Butter",
    "Sugar (Retail)","Coffee (Retail)","Bananas","Potatoes","Tomatoes","Oranges","Apples",
    "Diesel / Freight","Gasoline",
    "Crude Oil (Brent)","Crude Oil (WTI)","Natural Gas","Gasoline (RBOB)","Heating Oil",
    "Wheat","Corn","Soybeans","Soybean Oil","Oats","Rough Rice",
    "Coffee (Arabica)","Cocoa","Sugar (11)","Cotton","Orange Juice",
    "Live Cattle","Lean Hogs","Feeder Cattle","Lumber","Copper","Gold","Silver",
]


def render():
    st.markdown('<div class="sec-header">Profile</div>', unsafe_allow_html=True)
    user = get_current_user()
    if user:
        _render_dashboard(user)
    else:
        _render_auth()


def _render_dashboard(user: dict):
    plan  = user.get("plan", "Trial")
    color = PLAN_COLOR.get(plan, "#007A8E")

    if plan == "Trial":
        days = user.get("trial_days_left", 14)
        border_color = "#F0B429" if days < 5 else "#A8DBB9"
        st.markdown(f"""
        <div class="sig-card" style="border-left:4px solid {border_color};margin-bottom:1.25rem;">
            <div style="font-size:0.88rem;font-weight:600;color:#FFFFFF;">
                Free Trial - {days} day{"s" if days != 1 else ""} remaining
            </div>
            <div style="font-size:0.8rem;color:#8BA0B0;margin-top:0.25rem;">
                After your trial ends, access is paused until you subscribe. Go to Billing to choose a plan.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sig-card" style="border-left:4px solid {color};margin-bottom:1.5rem;">
        <div style="font-size:1.05rem;font-weight:700;color:#FFFFFF;">{user['name']}</div>
        <div style="font-size:0.82rem;color:#8BA0B0;margin-top:0.1rem;">{user['email']}</div>
        <div style="margin-top:0.6rem;">
            <span style="background:{color};color:{'#000' if plan=='Trial' else '#fff'};padding:2px 10px;
            border-radius:10px;font-size:0.72rem;font-weight:700;">{plan}</span>
            <span style="font-size:0.75rem;color:#8BA0B0;margin-left:0.75rem;">
                Joined {user.get('joined', '-')}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-header">Plan Features</div>', unsafe_allow_html=True)
    for feat in PLAN_FEATURES.get(plan, []):
        st.markdown(
            f'<div style="font-size:0.84rem;color:#FFFFFF;padding:0.3rem 0;border-bottom:1px solid #1E3A5F;">'
            f'<span style="color:#007A8E;font-weight:700;">+ </span>{feat}</div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-header">My Commodities</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8BA0B0;font-size:0.82rem;margin-bottom:0.5rem;">'
                'Choose which commodities appear on your Market and Home pages. '
                'Leave empty to see all.</p>', unsafe_allow_html=True)

    current_prefs = user.get("commodity_prefs", [])
    selected = st.multiselect(
        "Track these commodities",
        options=ALL_COMMODITIES,
        default=current_prefs if current_prefs else [],
        label_visibility="collapsed",
    )
    col_save, col_clear = st.columns([2, 1])
    with col_save:
        if st.button("Save Preferences", use_container_width=True, type="primary"):
            save_commodity_prefs(user["email"], selected)
            st.success(f"Tracking {len(selected)} commodit{'y' if len(selected)==1 else 'ies'}" if selected else "Showing all commodities")
    with col_clear:
        if st.button("Show All", use_container_width=True):
            save_commodity_prefs(user["email"], [])
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        logout()


def _render_auth():
    t1, t2 = st.tabs(["Sign In", "Create Free Account"])
    with t1:
        login_form()
    with t2:
        signup_form()
        st.markdown("""
        <div style="font-size:0.78rem;color:#4A6A80;margin-top:0.75rem;text-align:center;">
            14-day free trial. No credit card required. Cancel anytime.
        </div>
        """, unsafe_allow_html=True)
