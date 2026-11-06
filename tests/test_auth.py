"""
Password-reset checks. Email is captured instead of sent; accounts go to a
throwaway file, never data/users.json or the database.

    python tests/test_auth.py
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = os.path.abspath(os.path.join(ROOT, "src", "dashboard", "app.py"))
sys.path[:0] = [os.path.join(ROOT, "src", "dashboard"), os.path.join(ROOT, "src"), ROOT]
os.environ.pop("SUPABASE_DB_URL", None)

import auth
import mailer
from streamlit.testing.v1 import AppTest

TMP = os.path.join(tempfile.mkdtemp(), "users.json")
auth.USERS_FILE = TMP
SENT = []
_REAL_SEND = mailer.send_email
mailer.send_email = lambda to, subject, body: SENT.append((to, body))
mailer.is_configured = lambda: True


def _reset_store():
    SENT.clear()
    json.dump({"me@test.com": {"name": "Me", "password_hash": auth._hash("old-password"),
                               "plan": "Trial", "joined": "2026-11-01"}}, open(TMP, "w"))


def _users():
    return json.load(open(TMP))


def _token_from_last_email():
    link = next(w for w in SENT[-1][1].split() if "reset=" in w)
    return parse_qs(urlparse(link).query)["reset"][0]


def test_unknown_email_sends_nothing_but_looks_the_same():
    _reset_store()
    assert auth.request_password_reset("nobody@test.com") is True
    assert SENT == []


def test_reset_email_and_only_a_hash_is_stored():
    _reset_store()
    assert auth.request_password_reset("  ME@test.com ")
    assert SENT and SENT[-1][0] == "me@test.com"
    token = _token_from_last_email()
    stored = _users()["me@test.com"]
    assert stored["reset_token_hash"] != token, "raw token stored -- a leaked table would leak working links"
    assert stored["reset_token_hash"] == auth._token_hash(token)


def test_cooldown_blocks_inbox_flooding():
    _reset_store()
    auth.request_password_reset("me@test.com")
    auth.request_password_reset("me@test.com")
    assert len(SENT) == 1


def test_reset_works_once():
    _reset_store()
    auth.request_password_reset("me@test.com")
    token = _token_from_last_email()
    assert auth.reset_password("me@test.com", token, "new-password-1") is None
    h = _users()["me@test.com"]["password_hash"]
    assert auth._verify("new-password-1", h) and not auth._verify("old-password", h)
    assert "already been used" in auth.reset_password("me@test.com", token, "another-pass-2")


def test_wrong_token_expired_token_short_password():
    _reset_store()
    auth.request_password_reset("me@test.com")
    token = _token_from_last_email()
    assert "invalid" in auth.reset_password("me@test.com", "guess", "new-password-1")
    assert "at least 8" in auth.reset_password("me@test.com", token, "short")
    users = _users()
    users["me@test.com"]["reset_expires"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    json.dump(users, open(TMP, "w"))
    assert "expired" in auth.reset_password("me@test.com", token, "new-password-1")
    assert auth._verify("old-password", _users()["me@test.com"]["password_hash"]), "password changed anyway"


def test_send_failure_is_reported():
    _reset_store()
    def boom(*a):
        raise OSError("smtp down")
    mailer.send_email = boom
    try:
        assert auth.request_password_reset("me@test.com") is False
    finally:
        mailer.send_email = lambda to, subject, body: SENT.append((to, body))


def test_reset_link_opens_form_and_sets_password():
    _reset_store()
    auth.request_password_reset("me@test.com")
    token = _token_from_last_email()
    at = AppTest.from_file(APP, default_timeout=120)
    at.query_params["reset"] = token
    at.query_params["email"] = "me@test.com"
    at.run()
    assert not at.exception, at.exception
    assert any("Set a new password" in m.value for m in at.markdown), "reset link didn't open the form"
    at.text_input[0].input("new-password-1")
    at.text_input[1].input("new-password-1")
    next(b for b in at.button if b.label == "Save new password").click().run()
    assert not at.exception, at.exception
    assert auth._verify("new-password-1", _users()["me@test.com"]["password_hash"])
    assert any("Password updated" in m.value for m in at.success)


def _signup(agree: bool):
    _reset_store()
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Profile"
    at.run()
    field = {t.label: t for t in at.text_input}
    field["Full name"].input("New Person")
    field["Email address"].input("new@test.com")
    field["Password (min 8 chars)"].input("password-123")
    field["Confirm password"].input("password-123")
    if agree:
        next(c for c in at.checkbox if "Terms of Service" in c.label).check()
    next(b for b in at.button if b.label == "Start Free Trial").click().run()
    assert not at.exception, at.exception
    return at


def test_signup_requires_agreeing_to_terms_and_records_it():
    at = _signup(agree=False)
    assert "new@test.com" not in _users(), "account created without agreeing to the Terms"
    assert any("agree" in e.value for e in at.error)
    _signup(agree=True)
    consent = _users()["new@test.com"].get("agreed_terms", {})
    assert consent.get("version") == auth.TERMS_VERSION and consent.get("at"), consent


SEVEN = ["Corn", "Wheat", "Eggs", "Milk", "Butter", "Cheese", "Chicken"]


def _market_as(plan, prefs):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Market"
    at.session_state["user"] = {"email": "s@test.com", "name": "S", "plan": plan, "joined": "2026-11-01",
                                "commodity_prefs": prefs}
    at.run()
    assert not at.exception, at.exception
    return at


def test_starter_sees_at_most_five():
    at = _market_as("Starter", SEVEN)
    shown = [e.label.split("  ·")[0] for e in at.expander]
    assert shown and set(shown) <= set(SEVEN[:5]) and len(shown) <= 5, shown


def test_starter_without_picks_is_asked_to_choose():
    at = _market_as("Starter", [])
    assert not at.expander, "Starter with no picks saw commodities anyway"
    assert any("up to 5" in i.value for i in at.info)


def test_pro_is_not_limited():
    at = _market_as("Pro", SEVEN)
    assert len(at.expander) == 7
    at = _market_as("Pro", [])
    assert len(at.expander) > 5, "Pro with no picks should see everything"


def test_saving_more_than_the_limit_is_trimmed():
    _reset_store()
    users = _users()
    users["me@test.com"]["plan"] = "Starter"
    json.dump(users, open(TMP, "w"))
    auth.save_commodity_prefs("me@test.com", SEVEN)
    assert _users()["me@test.com"]["commodity_prefs"] == SEVEN[:5]


def test_profile_handles_downgrade_with_too_many_picks():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Profile"
    at.session_state["user"] = {"email": "s@test.com", "name": "S", "plan": "Starter", "joined": "2026-11-01",
                                "commodity_prefs": SEVEN}
    at.run()
    assert not at.exception, at.exception


def test_mailer_uses_the_right_connection_and_sender():
    import smtplib
    calls = []

    class FakeServer:
        def __init__(self, host, port, timeout=None): calls.append(("open", type(self).__name__, host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): calls.append(("starttls",))
        def login(self, user, pw): calls.append(("login", user, pw))
        def send_message(self, msg): calls.append(("from", msg["From"]))

    class SMTP(FakeServer): pass
    class SMTP_SSL(FakeServer): pass
    real = (smtplib.SMTP, smtplib.SMTP_SSL)
    smtplib.SMTP, smtplib.SMTP_SSL = SMTP, SMTP_SSL
    env = {"SMTP_USER": "login@relay", "SMTP_PASSWORD": "ab cd ef", "SMTP_FROM": "trochia.connect@gmail.com",
           "SMTP_HOST": "smtp-relay.brevo.com", "SMTP_PORT": "587"}
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        _REAL_SEND("x@test.com", "s", "b")            # Brevo-style: 587 + STARTTLS
        assert ("open", "SMTP", "smtp-relay.brevo.com", 587) in calls and ("starttls",) in calls
        assert ("login", "login@relay", "abcdef") in calls, "spaces in the key not removed"
        assert any(c[0] == "from" and "trochia.connect@gmail.com" in c[1] for c in calls), calls
        calls.clear()
        os.environ.update({"SMTP_PORT": "465", "SMTP_HOST": "smtp.gmail.com"})
        _REAL_SEND("x@test.com", "s", "b")            # Gmail-style: 465, SSL from the start
        assert ("open", "SMTP_SSL", "smtp.gmail.com", 465) in calls and ("starttls",) not in calls
    finally:
        smtplib.SMTP, smtplib.SMTP_SSL = real
        for k, v in saved.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v


def _market(key, user=None):
    import billing_stripe
    billing_stripe.STRIPE_SECRET_KEY = key
    try:
        at = AppTest.from_file(APP, default_timeout=120)
        at.session_state["page"] = "Market"
        if user:
            at.session_state["user"] = {"email": "t@test.com", "name": "T", "joined": "2026-11-01",
                                        "commodity_prefs": [], **user}
        at.run()
        assert not at.exception, at.exception
        return at
    finally:
        billing_stripe.STRIPE_SECRET_KEY = None


def test_no_limits_while_payments_are_not_live():
    at = _market("rk_test_fake")
    assert len(at.expander) > auth.PREVIEW_COUNT, "visitors limited before payments are live"


def test_live_signed_out_visitors_get_a_preview():
    at = _market("rk_live_fake")
    assert len(at.expander) == auth.PREVIEW_COUNT
    assert any("preview" in i.value for i in at.info)


def test_live_active_trial_and_paid_see_everything():
    assert len(_market("rk_live_fake", {"plan": "Trial", "trial_days_left": 5}).expander) > auth.PREVIEW_COUNT
    assert len(_market("rk_live_fake", {"plan": "Pro", "trial_days_left": None}).expander) > auth.PREVIEW_COUNT


def test_live_ended_trial_back_to_preview():
    at = _market("rk_live_fake", {"plan": "Trial", "trial_days_left": 0})
    assert len(at.expander) == auth.PREVIEW_COUNT
    assert any("trial has ended" in w.value for w in at.warning)


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
