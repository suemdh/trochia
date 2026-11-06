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
