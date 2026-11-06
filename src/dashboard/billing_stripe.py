"""
Trochiá — real Stripe integration for subscriptions.

Replaces the old billing.py form, which collected a card number/CVC/expiry
directly on the page and stored nothing more than the last 4 digits locally
-- while telling the user "Payments processed securely via Stripe," which
was false; no Stripe object was ever created. This module actually talks to
Stripe: it creates real Products/Prices once, opens Stripe's own hosted
Checkout page for the card entry (so raw card data never touches this app
or its server -- the PCI-compliant way to do this), and verifies payment by
retrieving the Checkout Session Stripe hands back, rather than trusting
whatever a browser form happened to submit.

Needs STRIPE_SECRET_KEY in .env (a test-mode "sk_test_..." key while
developing). Everything here no-ops safely if that's not set --
is_stripe_enabled() is checked by billing.py before any of this is called.
"""
import json
import os
from datetime import datetime, timezone

import stripe
from dotenv import load_dotenv

load_dotenv()


def _setting(name: str, default: str | None = None) -> str | None:
    """.env locally; Streamlit Cloud's Secrets box when deployed."""
    if os.getenv(name):
        return os.getenv(name)
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


STRIPE_SECRET_KEY = _setting("STRIPE_SECRET_KEY")
BASE_URL = _setting("APP_BASE_URL", "http://localhost:8501")

PRICES_CACHE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "stripe_prices.json")

PLANS = {
    "Starter":  19,
    "Pro":      49,
    "Business": 99,
}

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def is_stripe_enabled() -> bool:
    return bool(STRIPE_SECRET_KEY)


def is_live_mode() -> bool:
    """True only with a live Stripe key. While Stripe is in test mode the public
    Billing page shows "Coming soon" instead of a checkout that can't take real
    payments -- so launching is just swapping in the live key, nothing else."""
    return bool(STRIPE_SECRET_KEY) and STRIPE_SECRET_KEY.startswith(("sk_live_", "rk_live_"))


def _load_price_cache() -> dict:
    if os.path.exists(PRICES_CACHE):
        with open(PRICES_CACHE) as f:
            return json.load(f)
    return {}


def _save_price_cache(cache: dict):
    os.makedirs(os.path.dirname(PRICES_CACHE), exist_ok=True)
    with open(PRICES_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def ensure_price_ids() -> dict:
    """
    Returns {plan_name: stripe_price_id}, creating the Product + recurring
    Price on Stripe the first time each plan is needed and caching the IDs
    locally so repeat runs reuse the same objects instead of littering the
    Stripe dashboard with duplicates.
    """
    cache = _load_price_cache()
    changed = False
    for plan, amount in PLANS.items():
        if plan in cache:
            continue
        product = stripe.Product.create(name=f"Trochiá {plan}")
        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount * 100,
            currency="usd",
            recurring={"interval": "month"},
        )
        cache[plan] = price.id
        changed = True
    if changed:
        _save_price_cache(cache)
    return cache


def create_checkout_session(email: str, plan_name: str, customer_id: str | None = None) -> str:
    """Creates a Stripe Checkout Session for `plan_name` and returns its hosted URL.
    Reuses the person's existing Stripe customer when known, instead of
    creating a duplicate customer record on every checkout."""
    price_ids = ensure_price_ids()
    who = {"customer": customer_id} if customer_id else {"customer_email": email}
    session = stripe.checkout.Session.create(
        mode="subscription",
        **who,
        line_items=[{"price": price_ids[plan_name], "quantity": 1}],
        success_url=f"{BASE_URL}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/?checkout=cancelled",
        metadata={"plan": plan_name, "email": email},
    )
    return session.url


PORTAL_CACHE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "stripe_portal.json")


def ensure_portal_configuration() -> str:
    """Stripe's hosted billing portal, configured once to allow switching
    between the three plans (Stripe's default portal can't switch plans).
    Cached like the price IDs so it's created only once."""
    if os.path.exists(PORTAL_CACHE):
        with open(PORTAL_CACHE) as f:
            return json.load(f)["configuration"]
    prices = ensure_price_ids()
    products = [{"product": stripe.Price.retrieve(pid).product, "prices": [pid]} for pid in prices.values()]
    cfg = stripe.billing_portal.Configuration.create(
        business_profile={"headline": "Trochiá -- manage your subscription"},
        features={
            "payment_method_update": {"enabled": True},
            "invoice_history": {"enabled": True},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
            "subscription_update": {"enabled": True, "default_allowed_updates": ["price"],
                                    "proration_behavior": "create_prorations", "products": products},
        },
    )
    os.makedirs(os.path.dirname(PORTAL_CACHE), exist_ok=True)
    with open(PORTAL_CACHE, "w") as f:
        json.dump({"configuration": cfg.id}, f, indent=2)
    return cfg.id


def create_portal_session(customer_id: str) -> str:
    """Stripe-hosted page to change plan, update the card, cancel, or see
    invoices. Plan changes go through here rather than a new checkout -- a
    second checkout would start a second subscription and bill twice."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id, configuration=ensure_portal_configuration(),
        return_url=f"{BASE_URL}/?checkout=portal")
    return session.url


# Stripe statuses where the customer still has access. past_due = a renewal
# failed and Stripe is retrying the card; access continues meanwhile.
_ACCESS_STATUSES = ("active", "trialing", "past_due")


def sync_subscription(email: str) -> dict | None:
    """Asks Stripe for this person's current subscription and returns the
    account fields to store -- Stripe is the source of truth, so plan changes,
    failed renewals, and cancellations made in the portal or by Stripe itself
    all reach the site the next time they sign in or open Billing.
    Returns None if Stripe has never seen this email (never checked out)."""
    customers = stripe.Customer.list(email=email, limit=10).data
    if not customers:
        return None
    subs = [s for c in customers
            for s in stripe.Subscription.list(customer=c.id, status="all", limit=20).data]
    live = sorted((s for s in subs if s.status in _ACCESS_STATUSES),
                  key=lambda s: s.created, reverse=True)
    if not live:
        return {"plan": "Trial", "billing_status": "cancelled", "next_bill": None, "card_last4": None,
                "stripe_subscription_id": None, "stripe_customer_id": customers[0].id}

    sub = live[0]
    item = sub["items"].data[0]  # sub.items would hit the dict-method name
    end = getattr(sub, "current_period_end", None) or getattr(item, "current_period_end", None)
    plan = {pid: name for name, pid in _load_price_cache().items()}.get(item.price.id)
    fields = {
        "billing_status": ("past_due" if sub.status == "past_due"
                           else "cancelling" if sub.cancel_at_period_end else "active"),
        "next_bill": datetime.fromtimestamp(end, tz=timezone.utc).strftime("%Y-%m-%d") if end else None,
        "stripe_subscription_id": sub.id,
        "stripe_customer_id": sub.customer if isinstance(sub.customer, str) else sub.customer.id,
    }
    if plan:  # an unrecognised price: don't guess a plan name
        fields["plan"] = plan
    return fields


def retrieve_paid_session(session_id: str) -> dict | None:
    """
    Verifies a Checkout Session actually completed with Stripe (never trust
    the redirect alone -- a URL can be typed or replayed by hand) and
    returns the plan/customer/subscription/card details to persist, or None
    if the session isn't a genuine, paid checkout.
    """
    session = stripe.checkout.Session.retrieve(
        session_id, expand=["subscription", "customer"]
    )
    if session.payment_status != "paid":
        return None

    # stripe-python v12+ objects are not dicts: obj.get() raises AttributeError.
    # getattr(obj, field, None) is the safe form for a possibly-missing field.
    card_last4 = None
    sub = session.subscription
    pm_id = getattr(sub, "default_payment_method", None) if sub else None
    if pm_id:
        pm = stripe.PaymentMethod.retrieve(pm_id)
        card = getattr(pm, "card", None)
        card_last4 = getattr(card, "last4", None) if card else None

    return {
        # Who paid comes from Stripe's own record of the checkout (set by
        # create_checkout_session), never from the browser session -- Stripe's
        # redirect back lands in a fresh, signed-out Streamlit session.
        "email":               getattr(session.metadata, "email", None),
        "plan":                getattr(session.metadata, "plan", None),
        "stripe_customer_id":  session.customer["id"] if session.customer else None,
        "stripe_subscription_id": sub["id"] if sub else None,
        "card_last4":          card_last4,
    }


def cancel_stripe_subscription(subscription_id: str) -> str | None:
    """Cancels the real subscription on Stripe's side (end of current billing
    period). Returns None on success, else the error to show. This used to
    swallow every Stripe error, so the site said "cancelled" while Stripe kept
    billing -- a refused cancel must never look like a successful one."""
    if not subscription_id:
        return None
    try:
        sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    except stripe.error.StripeError as e:
        return f"Stripe refused the cancellation: {getattr(e, 'user_message', None) or e}"
    if not getattr(sub, "cancel_at_period_end", False):
        return "Stripe did not confirm the cancellation."
    return None
