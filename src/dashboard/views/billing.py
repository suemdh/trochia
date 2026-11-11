"""Trochiá — Billing page: plan management, payment, trial status."""
import sys, os
import streamlit as st
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from commodity_maps import TOTAL_COMMODITIES
import billing_stripe

STATUS_LABEL = {"active": "Active", "cancelling": "Cancels at period end",
                "past_due": "Payment failed", "cancelled": "Cancelled", "trial": "Trial"}

PLANS = {
    "Starter":  {"price": 19,  "color": "#007A8E", "desc": "For individual operators"},
    "Pro":      {"price": 49,  "color": "#21C55D", "desc": "For growing businesses"},
    "Business": {"price": 99,  "color": "#F0B429", "desc": "For teams and supply chains"},
}


def _handle_stripe_return(user: dict | None):
    """Runs on every Billing page load; only acts when Stripe just redirected
    back with a Checkout outcome in the URL. Works whether or not anyone is
    signed in: the redirect is a full page load, i.e. a new signed-out
    Streamlit session, so requiring a session user here meant every real
    payment went unrecorded. The payer is identified from Stripe's verified
    session record instead."""
    from auth import update_plan
    params = st.query_params
    checkout = params.get("checkout")
    if checkout == "success":
        session_id = params.get("session_id")
        result = billing_stripe.retrieve_paid_session(session_id) if session_id else None
        st.query_params.clear()
        if result and result.get("plan") and result.get("email"):
            update_plan(
                result["email"], result["plan"],
                card_last4=result.get("card_last4"),
                stripe_customer_id=result.get("stripe_customer_id"),
                stripe_subscription_id=result.get("stripe_subscription_id"),
            )
            signed_in_as_payer = bool(user) and user.get("email") == result["email"]
            st.session_state["_billing_toast"] = (
                f"Subscribed to {result['plan']}! Payment confirmed by Stripe."
                + ("" if signed_in_as_payer else f" Sign in as {result['email']} to see your plan."))
        else:
            st.session_state["_billing_error"] = "Could not confirm payment with Stripe. If you were charged, contact support."
        st.rerun()
    elif checkout == "cancelled":
        st.query_params.clear()
        st.session_state["_billing_info"] = "Checkout cancelled -- no charge was made."
        st.rerun()
    elif checkout == "portal":
        # Back from Stripe's billing portal. Like any return from Stripe this is
        # a fresh session; the page below re-syncs from Stripe once signed in.
        st.query_params.clear()
        st.session_state["_billing_info"] = ("Your subscription below is up to date with Stripe." if user
                                             else "Back from Stripe. Sign in to see any changes to your subscription.")
        st.rerun()


def render():
    from auth import get_current_user
    st.markdown('<div class="sec-header">Billing & Subscription</div>', unsafe_allow_html=True)

    user = get_current_user()
    _handle_stripe_return(user)
    if user:
        from auth import sync_billing
        sync_billing(user["email"])  # Stripe is the source of truth for the plan
        user = get_current_user()

    for key, kind in [("_billing_toast", "success"), ("_billing_error", "error"), ("_billing_info", "info")]:
        msg = st.session_state.pop(key, None)
        if msg:
            getattr(st, kind)(msg)
            if kind == "success":
                st.balloons()

    if not user:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="text-align:center;padding:2rem;">
            <div style="font-size:1rem;font-weight:600;color:#FFFFFF;margin-bottom:0.5rem;">Sign in to manage your subscription</div>
            <div style="font-size:0.85rem;color:#8BA0B0;">Create a free account to start your 14-day trial.</div>
        </div>
        """, unsafe_allow_html=True)
        _, c, _ = st.columns([1,1,1])
        with c:
            if st.button("Go to Profile", use_container_width=True, type="primary"):
                st.session_state.page = "Profile"; st.rerun()
        return

    _render_status_bar(user)
    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    plan = user.get("plan", "Trial")
    if plan == "Trial":
        _render_trial_upsell(user)
    else:
        _render_active_billing(user)

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
    _render_plan_compare(user)


def _render_status_bar(user: dict):
    plan   = user.get("plan", "Trial")
    status = user.get("billing_status", "trial")
    color  = PLANS.get(plan, {}).get("color", "#A8DBB9") if plan != "Trial" else "#A8DBB9"

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Current Plan", plan)
    b2.metric("Status", STATUS_LABEL.get(status, status.title()))

    if plan == "Trial":
        days = user.get("trial_days_left", 14)
        b3.metric("Trial Days Left", f"{days} days")
        trial_end = (datetime.now() + timedelta(days=days)).strftime("%b %d, %Y") if days else "-"
        b4.metric("Trial Ends", trial_end)
    else:
        b3.metric("Monthly Cost", f"${PLANS[plan]['price']}/mo")
        b4.metric("Access Until" if status == "cancelling" else "Next Billing", user.get("next_bill") or "-")


def _render_trial_upsell(user: dict):
    days = user.get("trial_days_left", 14)

    # Progress bar
    pct = max(0, min(100, int((14 - days) / 14 * 100)))
    bar_color = "#F0B429" if days < 5 else "#21C55D"

    st.markdown(f"""
    <div class="sig-card sig-card-yellow" style="margin-bottom:1.5rem;">
        <div style="font-size:0.95rem;font-weight:700;color:#FFFFFF;margin-bottom:0.4rem;">
            {f"Free Trial — {days} days remaining" if days else "Your free trial has ended"}
        </div>
        <div style="font-size:0.82rem;color:#8BA0B0;margin-bottom:0.75rem;">
            {"Your trial gives you full access to every commodity and feature." if days else
             "Choose a plan below to see every commodity again. Your account and saved picks are kept."}
        </div>
        <div style="background:#1E3A5F;border-radius:4px;height:8px;width:100%;">
            <div style="background:{bar_color};border-radius:4px;height:8px;width:{pct}%;"></div>
        </div>
        <div style="font-size:0.72rem;color:#8BA0B0;margin-top:0.35rem;">{pct}% of trial used</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-header">Plans</div>', unsafe_allow_html=True)
    _payment_form(user)


def _render_active_billing(user: dict):
    from auth import cancel_subscription
    plan   = user["plan"]
    info   = PLANS.get(plan, {})
    status = user.get("billing_status", "active")
    until  = user.get("next_bill") or "the end of your billing period"
    detail = {
        "cancelling": f"Cancelled -- you keep {plan} until <strong style='color:#FFFFFF;'>{until}</strong>. "
                      f"You won't be charged again.",
        "past_due":   "<strong style='color:#F0B429;'>Your last payment didn't go through.</strong> Stripe is "
                      "retrying -- update your card under Manage subscription to keep access.",
    }.get(status, f"Renews <strong style='color:#FFFFFF;'>{until}</strong>"
                  f" &nbsp;·&nbsp; Card ending in <strong style='color:#FFFFFF;'>{user.get('card_last4') or '-'}</strong>")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"""
        <div class="sig-card" style="border-left:4px solid {info.get('color','#007A8E')};">
            <div style="font-size:0.9rem;font-weight:700;color:#FFFFFF;margin-bottom:0.25rem;">{plan} Plan — ${info.get('price','?')}/mo</div>
            <div style="font-size:0.82rem;color:#8BA0B0;">{info.get('desc','')}</div>
            <div style="margin-top:0.6rem;font-size:0.8rem;color:#8BA0B0;">{detail}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        # Plan changes, card updates and invoices all go through Stripe's portal.
        # This used to start a second checkout, which created a second
        # subscription on top of the first -- billing the customer twice.
        if user.get("stripe_customer_id") and billing_stripe.is_stripe_enabled():
            if st.button("Manage subscription", use_container_width=True, type="primary"):
                try:
                    url = billing_stripe.create_portal_session(user["stripe_customer_id"])
                    st.link_button("Open Stripe billing portal →", url, use_container_width=True)
                    st.caption("Change plan, update your card, or see invoices.")
                except Exception as e:
                    st.error(f"Could not open the billing portal: {e}")
        if status in ("active", "past_due") and st.button("Cancel Subscription", use_container_width=True):
            st.session_state.confirm_cancel = True

    # Cancel confirmation
    if st.session_state.get("confirm_cancel"):
        st.markdown("""
        <div class="sig-card sig-card-red" style="margin-top:1rem;">
            <div style="font-size:0.88rem;font-weight:600;color:#FFFFFF;">Cancel subscription?</div>
            <div style="font-size:0.82rem;color:#8BA0B0;margin-top:0.3rem;">
                You will retain access until the end of your current billing period.
            </div>
        </div>
        """, unsafe_allow_html=True)
        ca, cb, _ = st.columns([1,1,2])
        with ca:
            if st.button("Yes, Cancel", type="primary", key="confirm_cancel_yes"):
                err = (billing_stripe.cancel_stripe_subscription(user.get("stripe_subscription_id"))
                       if billing_stripe.is_stripe_enabled() else None)
                st.session_state.confirm_cancel = False
                if err:
                    # Don't mark it cancelled here if Stripe will keep billing.
                    st.session_state["_billing_error"] = f"{err} Your plan was not changed -- please contact support."
                else:
                    cancel_subscription(user["email"], at_period_end=billing_stripe.is_stripe_enabled())
                    # Set before rerun: messages shown directly are wiped by the rerun.
                    st.session_state["_billing_info"] = "Subscription cancelled. Access continues until the billing period ends."
                st.rerun()
        with cb:
            if st.button("Keep Plan", key="confirm_cancel_no"):
                st.session_state.confirm_cancel = False
                st.rerun()


def _payment_form(user: dict):
    """Real Stripe Checkout -- card entry happens on Stripe's own hosted
    page, never on this one, so no card data ever passes through this app."""
    if not billing_stripe.is_live_mode():
        # Test-mode Stripe can't take real payments, so the public sees this
        # instead of a checkout. Swapping in a live key opens checkout.
        st.markdown("""
        <div class="sig-card sig-card-yellow" style="padding:1rem;">
            <div style="font-size:0.88rem;font-weight:600;color:#FFFFFF;">Paid plans are coming soon</div>
            <div style="font-size:0.82rem;color:#8BA0B0;margin-top:0.3rem;">
                We're putting the finishing touches on paid plans. Your free trial has full access in
                the meantime, and we'll let you know before anything about your access changes.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    plan_choice = st.selectbox(
        "Select plan",
        ["Starter — $19/mo", "Pro — $49/mo", "Business — $99/mo"],
        index=1,
        key="plan_choice_new",
    )
    plan_name = plan_choice.split(" —")[0]
    price     = PLANS[plan_name]["price"]

    if st.button(f"Continue to Stripe Checkout — ${price}/mo", use_container_width=True,
                 type="primary", key="checkout_new"):
        try:
            url = billing_stripe.create_checkout_session(user["email"], plan_name,
                                                         customer_id=user.get("stripe_customer_id"))
            st.link_button("Click to pay on Stripe →", url, use_container_width=True, type="primary")
            st.caption("Opens Stripe's secure hosted checkout in a new tab. Come back here after paying.")
        except Exception as e:
            st.error(f"Could not start checkout: {e}")

    # Security note
    st.markdown("""
    <div style="font-size:0.72rem;color:#4A6A80;margin-top:0.5rem;text-align:center;">
        Payments processed securely via Stripe. Card details are entered on Stripe's own
        page and never touch this app. Cancel anytime from this page.
    </div>
    """, unsafe_allow_html=True)


def _render_plan_compare(user: dict):
    st.markdown('<div class="sec-header">Plan Comparison</div>', unsafe_allow_html=True)

    # Keep in step with views/pricing.py -- only what exists today is "Yes".
    rows = [
        ("Commodities tracked",       "Up to 5", f"All {TOTAL_COMMODITIES}", f"All {TOTAL_COMMODITIES}"),
        ("Forecast updates",          "Weekly",  "Weekly",  "Weekly"),
        ("Government price data, weekly", "Yes",  "Yes",     "Yes"),
        ("Price history charts",      "Yes",     "Full",    "Full"),
        ("Savings calculator",        "Yes",     "Yes",     "Yes"),
        ("Email alerts",              "Coming soon", "Coming soon", "Coming soon"),
        ("Text alerts",               "-",       "Coming soon", "Coming soon"),
        ("AI chat assistant",         "-",       "Coming soon", "Coming soon"),
        ("API access",                "-",       "-",       "Coming soon"),
        ("Team seats",                "1",       "1",       "Coming soon (up to 10)"),
        ("Support",                   "Email",   "Email",   "Priority email"),
    ]

    header = "| Feature | Starter $19 | Pro $49 | Business $99 |\n|---|---|---|---|\n"
    body   = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows)
    st.markdown(header + body)

    st.markdown("""
    <div style="font-size:0.75rem;color:#4A6A80;margin-top:0.75rem;text-align:center;">
        All plans include a 14-day free trial. No credit card required to start.
    </div>
    """, unsafe_allow_html=True)
