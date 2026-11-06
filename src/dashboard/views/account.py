"""Trochia - Profile page."""
import sys, os
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from auth import (login_form, signup_form, logout, get_current_user, save_commodity_prefs,
                  request_password_reset, reset_password, PLAN_COMMODITY_LIMIT)
from commodity_maps import FRED_COMMODITY_MAP, USDA_COMMODITY_MAP, YFINANCE_COMMODITY_MAP
import mailer

PLAN_COLOR = {"Starter":"#007A8E","Pro":"#21C55D","Business":"#F0B429","Trial":"#A8DBB9"}
# Only what exists today -- keep in step with views/pricing.py.
PLAN_FEATURES = {
    "Trial":    ["All commodities", "Weekly forecasts with live prices", "Full charts", "Savings calculator"],
    "Starter":  ["Up to 5 commodities", "Weekly forecasts with live prices", "Price charts", "Savings calculator"],
    "Pro":      ["All commodities", "Weekly forecasts with live prices", "Full charts", "Savings calculator"],
    "Business": ["Everything in Pro", "Priority email support"],
}

# The commodities actually forecast -- this used to be a hand-typed copy that
# still offered discontinued items (Tuna, Peanut Butter, Apples, Lumber).
ALL_COMMODITIES = [*FRED_COMMODITY_MAP, *USDA_COMMODITY_MAP, *YFINANCE_COMMODITY_MAP]


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
                Paid plans are coming soon -- we'll let you know before anything about your access changes.
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
    limit = PLAN_COMMODITY_LIMIT.get(plan)
    st.markdown('<div class="sec-header">My Commodities</div>', unsafe_allow_html=True)
    hint = (f"Your {plan} plan includes up to {limit} commodities. Choose the ones you want to follow."
            if limit else "Choose which commodities appear on your Market and Home pages. Leave empty to see all.")
    st.markdown(f'<p style="color:#8BA0B0;font-size:0.82rem;margin-bottom:0.5rem;">{hint}</p>',
                unsafe_allow_html=True)

    current_prefs = user.get("commodity_prefs", [])
    selected = st.multiselect(
        "Track these commodities",
        options=ALL_COMMODITIES,
        # Saved lists may still hold since-removed items (Streamlit errors on a
        # default not among the options), or more than a downgraded plan allows
        # (Streamlit errors on a default longer than max_selections).
        default=[p for p in current_prefs if p in ALL_COMMODITIES][:limit],
        max_selections=limit,
        label_visibility="collapsed",
    )
    col_save, col_clear = st.columns([2, 1])
    with col_save:
        if st.button("Save Preferences", use_container_width=True, type="primary"):
            save_commodity_prefs(user["email"], selected)
            if selected:
                st.success(f"Tracking {len(selected)} commodit{'y' if len(selected)==1 else 'ies'}")
            else:
                st.success(f"Pick up to {limit} commodities to see them." if limit else "Showing all commodities")
    if not limit:
        with col_clear:
            if st.button("Show All", use_container_width=True):
                save_commodity_prefs(user["email"], [])
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        logout()


def _render_auth():
    msg = st.session_state.pop("_auth_info", None)
    if msg:
        st.success(msg)
    params = st.query_params
    if params.get("reset") and params.get("email"):
        _render_reset_form(params["email"], params["reset"])
        return

    t1, t2 = st.tabs(["Sign In", "Create Free Account"])
    with t1:
        login_form()
        _render_forgot_password()
    with t2:
        signup_form()
        st.markdown("""
        <div style="font-size:0.78rem;color:#4A6A80;margin-top:0.75rem;text-align:center;">
            14-day free trial. No credit card required. Cancel anytime.
        </div>
        """, unsafe_allow_html=True)


def _render_forgot_password():
    with st.expander("Forgot your password?"):
        with st.form("forgot_form"):
            email = st.text_input("Your account email")
            sent = st.form_submit_button("Email me a reset link", use_container_width=True)
        if sent:
            if not email.strip():
                st.error("Enter the email you signed up with.")
            elif not mailer.is_configured():
                st.error("Password reset isn't available yet -- please contact support.")
            elif request_password_reset(email):
                # Same message whether or not an account exists, on purpose.
                st.success("If there's an account for that email, a reset link is on its way. "
                           "Check your inbox and spam folder -- the link works for 30 minutes.")
            else:
                st.error("We couldn't send the email right now. Please try again in a few minutes.")


def _render_reset_form(email: str, token: str):
    st.markdown("### Set a new password")
    st.caption(f"For {email}")
    with st.form("reset_form"):
        pw = st.text_input("New password (min 8 characters)", type="password")
        pw2 = st.text_input("Confirm new password", type="password")
        done = st.form_submit_button("Save new password", use_container_width=True, type="primary")
    if done:
        if pw != pw2:
            st.error("Passwords don't match.")
        else:
            err = reset_password(email, token, pw)
            if err:
                st.error(err)
            else:
                st.query_params.clear()
                st.session_state["_auth_info"] = "Password updated. Sign in with your new password."
                st.rerun()
    if st.button("Back to sign in"):
        st.query_params.clear()
        st.rerun()
