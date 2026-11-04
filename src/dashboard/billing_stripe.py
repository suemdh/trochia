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

import stripe
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

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


def create_checkout_session(email: str, plan_name: str) -> str:
    """Creates a Stripe Checkout Session for `plan_name` and returns its hosted URL."""
    price_ids = ensure_price_ids()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": price_ids[plan_name], "quantity": 1}],
        success_url=f"{BASE_URL}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/?checkout=cancelled",
        metadata={"plan": plan_name, "email": email},
    )
    return session.url


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

    card_last4 = None
    sub = session.subscription
    if sub and sub.get("default_payment_method"):
        pm = stripe.PaymentMethod.retrieve(sub["default_payment_method"])
        card_last4 = pm.card.last4 if pm.card else None

    return {
        "plan":                session.metadata.get("plan"),
        "stripe_customer_id":  session.customer["id"] if session.customer else None,
        "stripe_subscription_id": sub["id"] if sub else None,
        "card_last4":          card_last4,
    }


def cancel_stripe_subscription(subscription_id: str):
    """Cancels the real subscription on Stripe's side (end of current billing period)."""
    if not subscription_id:
        return
    try:
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    except stripe.error.StripeError:
        pass
