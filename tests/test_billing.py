"""
Payment-path checks: Stripe's return link and cancellation. No network, no real
Stripe account -- Stripe API calls are replaced, but with REAL stripe-python
objects (StripeObject.construct_from), because the first version of these tests
used plain dicts and so missed a crash: stripe-python v12+ objects don't
support .get(). Accounts go to a throwaway file, never data/users.json or the DB.

    python tests/test_billing.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = os.path.abspath(os.path.join(ROOT, "src", "dashboard", "app.py"))
sys.path[:0] = [os.path.join(ROOT, "src", "dashboard"), os.path.join(ROOT, "src"), ROOT]
os.environ.pop("SUPABASE_DB_URL", None)

import stripe
import auth
import billing_stripe
from streamlit.testing.v1 import AppTest

TMP = os.path.join(tempfile.mkdtemp(), "users.json")
auth.USERS_FILE = TMP
_real_retrieve = billing_stripe.retrieve_paid_session
_real_cancel = billing_stripe.cancel_stripe_subscription


def _obj(d):
    return stripe.StripeObject.construct_from(d, "sk_test_x")


def _reset(**payer):
    base = {"name": "X", "password_hash": "x", "plan": "Trial", "joined": "2026-11-01",
            "billing_status": "trial", "card_last4": None, "next_bill": None, "commodity_prefs": []}
    json.dump({"payer@test.com": {**base, **payer}, "other@test.com": dict(base)}, open(TMP, "w"))


def _users():
    return json.load(open(TMP))


def test_retrieve_paid_session_on_real_stripe_objects():
    stripe.checkout.Session.retrieve = lambda *a, **k: _obj({
        "payment_status": "paid", "metadata": {"email": "payer@test.com", "plan": "Pro"},
        "customer": {"id": "cus_1"},
        "subscription": {"id": "sub_1", "default_payment_method": "pm_1"}})
    stripe.PaymentMethod.retrieve = lambda *a, **k: _obj({"card": {"last4": "4242"}})
    r = _real_retrieve("cs_x")
    assert r == {"email": "payer@test.com", "plan": "Pro", "stripe_customer_id": "cus_1",
                 "stripe_subscription_id": "sub_1", "card_last4": "4242"}, r

    # No saved card on the subscription: no crash, just no last-4.
    stripe.checkout.Session.retrieve = lambda *a, **k: _obj({
        "payment_status": "paid", "metadata": {"email": "payer@test.com", "plan": "Pro"},
        "customer": {"id": "cus_1"}, "subscription": {"id": "sub_1"}})
    assert _real_retrieve("cs_x")["card_last4"] is None

    stripe.checkout.Session.retrieve = lambda *a, **k: _obj({"payment_status": "unpaid"})
    assert _real_retrieve("cs_x") is None


def test_cancel_reports_stripe_refusal():
    def refuse(*a, **k):
        raise stripe.error.PermissionError("no permission")
    stripe.Subscription.modify = refuse
    assert "refused" in _real_cancel("sub_1")
    stripe.Subscription.modify = lambda *a, **k: _obj({"cancel_at_period_end": True})
    assert _real_cancel("sub_1") is None


PAID = {"email": "payer@test.com", "plan": "Pro", "stripe_customer_id": "cus_1",
        "stripe_subscription_id": "sub_1", "card_last4": "4242"}


def _return(result, session_user=None):
    _reset()
    billing_stripe.retrieve_paid_session = lambda sid: result
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["checkout"] = "success"
    at.query_params["session_id"] = "cs_test_fake"
    if session_user:
        at.session_state["user"] = auth._build_session_user(session_user, _users()[session_user])
    at.run()
    assert not at.exception, at.exception
    sess = (at.session_state["user"] or {}).get("email") if "user" in at.session_state else None
    return sess, [m.value for m in at.success] + [m.value for m in at.error]


def test_return_link_signed_out_records_payment_and_signs_nobody_in():
    sess, msgs = _return(PAID)
    assert _users()["payer@test.com"]["plan"] == "Pro"
    assert sess is None, "return link must never sign anyone in"
    assert any("Sign in as payer@test.com" in m for m in msgs), msgs


def test_return_link_credits_payer_not_whoever_is_signed_in():
    sess, _ = _return(PAID, session_user="other@test.com")
    assert _users()["payer@test.com"]["plan"] == "Pro"
    assert _users()["other@test.com"]["plan"] == "Trial"
    assert sess == "other@test.com"


def test_unpaid_return_upgrades_nobody():
    _, msgs = _return(None)
    assert all(u["plan"] == "Trial" for u in _users().values())
    assert any("Could not confirm payment" in m for m in msgs), msgs


def _cancel(stripe_result):
    _reset(plan="Pro", billing_status="active", stripe_subscription_id="sub_1")
    billing_stripe.cancel_stripe_subscription = lambda sid: stripe_result
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Billing"
    at.session_state["user"] = auth._build_session_user("payer@test.com", _users()["payer@test.com"])
    at.run()
    next(b for b in at.button if b.label == "Cancel Subscription").click().run()
    next(b for b in at.button if b.key == "confirm_cancel_yes").click().run()
    assert not at.exception, at.exception
    return _users()["payer@test.com"]["plan"], [m.value for m in at.info] + [m.value for m in at.error]


def test_refused_cancel_keeps_plan_and_says_so():
    plan, msgs = _cancel("Stripe refused the cancellation: no permission")
    assert plan == "Pro", "marked cancelled while Stripe keeps billing"
    assert any("refused" in m for m in msgs), msgs


def test_confirmed_cancel_downgrades_and_message_is_shown():
    plan, msgs = _cancel(None)
    assert plan == "Trial"
    assert any("Subscription cancelled" in m for m in msgs), msgs


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_")]
    failed = 0
    for n, f in tests:
        try:
            f(); print(f"PASS  {n}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {n}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
