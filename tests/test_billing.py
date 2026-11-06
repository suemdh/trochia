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
_real_sync = billing_stripe.sync_subscription
# Deterministic, and never a real Stripe call: the Billing page syncs with
# Stripe on every view, so that's replaced unless a test sets it.
billing_stripe.STRIPE_SECRET_KEY = "rk_test_fake"
billing_stripe.sync_subscription = lambda email: None


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


def test_confirmed_cancel_keeps_access_until_period_end():
    plan, msgs = _cancel(None)
    assert plan == "Pro", "took away access the customer already paid for"
    assert _users()["payer@test.com"]["billing_status"] == "cancelling"
    assert any("Subscription cancelled" in m for m in msgs), msgs


# --- Stripe sync: Stripe is the source of truth for each account's plan ---

PRO = "price_pro_test"


def _stripe_has(subs, customers=("cus_1",)):
    billing_stripe._load_price_cache = lambda: {"Starter": "price_s", "Pro": PRO, "Business": "price_b"}
    stripe.Customer.list = lambda **k: _obj({"data": [{"id": c} for c in customers]})
    stripe.Subscription.list = lambda **k: _obj({"data": subs})


def _sub(status, cancel_at_period_end=False, price=PRO, created=1, end_on_item=True):
    end = {"current_period_end": 1796404997}
    return {"id": f"sub_{status}_{created}", "status": status, "created": created, "customer": "cus_1",
            "cancel_at_period_end": cancel_at_period_end, **({} if end_on_item else end),
            "items": {"data": [{"price": {"id": price}, **(end if end_on_item else {})}]}}


def test_sync_reads_plan_status_and_period_end():
    _stripe_has([_sub("active")])
    r = _real_sync("payer@test.com")
    assert r == {"plan": "Pro", "billing_status": "active", "next_bill": "2026-12-04",
                 "stripe_subscription_id": "sub_active_1", "stripe_customer_id": "cus_1"}, r
    _stripe_has([_sub("active", end_on_item=False)])  # older Stripe API: period end on the subscription
    assert _real_sync("payer@test.com")["next_bill"] == "2026-12-04"


def test_sync_cancelling_and_failed_payment():
    _stripe_has([_sub("active", cancel_at_period_end=True)])
    assert _real_sync("payer@test.com")["billing_status"] == "cancelling"
    _stripe_has([_sub("past_due")])
    r = _real_sync("payer@test.com")
    assert r["billing_status"] == "past_due" and r["plan"] == "Pro", "failed renewal must not cut access yet"


def test_sync_ended_subscription_downgrades():
    _stripe_has([_sub("canceled"), _sub("incomplete_expired", created=2)])
    r = _real_sync("payer@test.com")
    assert r["plan"] == "Trial" and r["billing_status"] == "cancelled" and r["stripe_subscription_id"] is None


def test_sync_never_checked_out_and_unknown_price():
    _stripe_has([], customers=())
    assert _real_sync("payer@test.com") is None
    _stripe_has([_sub("active", price="price_someone_else")])
    assert "plan" not in _real_sync("payer@test.com"), "guessed a plan from an unknown price"


def test_sync_picks_newest_live_subscription():
    _stripe_has([_sub("canceled", created=5), _sub("active", created=3), _sub("active", created=4)])
    assert _real_sync("payer@test.com")["stripe_subscription_id"] == "sub_active_4"


def test_stripe_outage_never_blocks_sign_in():
    _reset(plan="Pro", billing_status="active")
    def down(email):
        raise ConnectionError("stripe unreachable")
    billing_stripe.sync_subscription = down
    stored = auth.sync_billing("payer@test.com")
    billing_stripe.sync_subscription = lambda email: None
    assert stored and stored["plan"] == "Pro", "outage changed or lost the account"


def test_sync_billing_applies_stripe_state():
    _reset()  # site thinks Trial -- e.g. the return link was never processed
    billing_stripe.sync_subscription = lambda email: {"plan": "Pro", "billing_status": "active",
                                                      "stripe_customer_id": "cus_1"}
    auth.sync_billing("payer@test.com")
    billing_stripe.sync_subscription = lambda email: None
    assert _users()["payer@test.com"]["plan"] == "Pro"


def _billing_buttons(**payer):
    _reset(**payer)
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Billing"
    at.session_state["user"] = auth._build_session_user("payer@test.com", _users()["payer@test.com"])
    at.run()
    assert not at.exception, at.exception
    return [b.label for b in at.button]


def test_subscriber_gets_portal_not_a_second_checkout():
    labels = _billing_buttons(plan="Pro", billing_status="active", stripe_customer_id="cus_1",
                              stripe_subscription_id="sub_1")
    assert "Manage subscription" in labels and "Cancel Subscription" in labels
    assert not any("Checkout" in l for l in labels), "subscriber offered a second checkout (double billing)"


def test_cancelling_subscriber_has_no_cancel_button():
    labels = _billing_buttons(plan="Pro", billing_status="cancelling", stripe_customer_id="cus_1")
    assert "Cancel Subscription" not in labels and "Manage subscription" in labels


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
