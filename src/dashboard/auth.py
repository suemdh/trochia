"""Trochiá authentication — user store with trial tracking.

Accounts live in Postgres (Supabase) when SUPABASE_DB_URL is set -- required on
the hosted site, whose disk is wiped on every restart -- and in a local JSON
file otherwise (laptop dev). Same data shape either way: {email: {...fields}}.
"""
import hashlib, hmac, json, os
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.json")
TRIAL_DAYS = 14
PBKDF2_ITERATIONS = 600_000  # OWASP's current recommendation for PBKDF2-SHA256


def _hash(pw: str) -> str:
    """Salted, slow hash. Replaces plain unsalted SHA-256, which a leaked
    users.json would have given up in seconds via precomputed tables."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _verify(pw: str, stored: str) -> bool:
    if stored.startswith("pbkdf2$"):
        _, iters, salt, dk = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(got.hex(), dk)
    # Legacy unsalted SHA-256 from before the upgrade; login_form() rehashes on success.
    return hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), stored)


def _db_url() -> str | None:
    """.env locally; Streamlit Cloud's Secrets box when deployed."""
    if os.getenv("SUPABASE_DB_URL"):
        return os.getenv("SUPABASE_DB_URL")
    try:
        return st.secrets.get("SUPABASE_DB_URL")
    except Exception:
        return None


_schema_ready = False


def _db():
    """New connection per call -- simple, and login/signup only touch the DB
    a couple of times. Deliberately no fallback to the local file if the DB is
    configured but unreachable: on the hosted site that file is wiped on every
    restart, so "falling back" would silently lose new accounts."""
    global _schema_ready
    import psycopg
    conn = psycopg.connect(_db_url(), connect_timeout=10)
    if not _schema_ready:
        # Own schema, not "public": Supabase exposes "public" through its REST
        # API to anyone with the publishable key. RLS with no policies is a
        # second lock -- only this server's postgres role can read the table.
        conn.execute("CREATE SCHEMA IF NOT EXISTS app")
        conn.execute("CREATE TABLE IF NOT EXISTS app.users (email text PRIMARY KEY, data jsonb NOT NULL)")
        conn.execute("ALTER TABLE app.users ENABLE ROW LEVEL SECURITY")
        conn.commit()
        _schema_ready = True
    return conn


def _load_users() -> dict:
    if _db_url():
        with _db() as conn:
            return {email: data for email, data in conn.execute("SELECT email, data FROM app.users")}
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        return json.load(f)


def _save_users(users: dict):
    if _db_url():
        from psycopg.types.json import Jsonb
        # Upsert, never delete: two people signing up at once each save their
        # own row without wiping the other's.
        with _db() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO app.users (email, data) VALUES (%s, %s) "
                    "ON CONFLICT (email) DO UPDATE SET data = EXCLUDED.data",
                    [(email, Jsonb(data)) for email, data in users.items()])
        return
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _trial_days_left(joined_str: str) -> int | None:
    """Returns days remaining in trial, or None if trial has ended/user is paid."""
    try:
        joined = datetime.strptime(joined_str, "%Y-%m-%d")
        end    = joined + timedelta(days=TRIAL_DAYS)
        left   = (end - datetime.now()).days
        return max(0, left)
    except Exception:
        return None


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def _build_session_user(email: str, stored: dict) -> dict:
    plan   = stored.get("plan", "Trial")
    joined = stored.get("joined", datetime.now().strftime("%Y-%m-%d"))
    trial_days = _trial_days_left(joined) if plan == "Trial" else None
    return {
        "email":           email,
        "name":            stored["name"],
        "plan":            plan,
        "joined":          joined,
        "trial_days_left": trial_days,
        "billing_status":  stored.get("billing_status", "trial"),
        "card_last4":      stored.get("card_last4"),
        "next_bill":       stored.get("next_bill"),
        "commodity_prefs": stored.get("commodity_prefs", []),
        "stripe_customer_id":     stored.get("stripe_customer_id"),
        "stripe_subscription_id": stored.get("stripe_subscription_id"),
    }


def save_commodity_prefs(email: str, prefs: list):
    """Persist selected commodity names for a user."""
    users = _load_users()
    key   = email.lower().strip()
    if key not in users:
        return
    users[key]["commodity_prefs"] = prefs
    _save_users(users)
    if st.session_state.get("user", {}).get("email") == key:
        st.session_state.user["commodity_prefs"] = prefs


def login_form():
    st.markdown("### Sign In to Trochiá")
    with st.form("login_form"):
        email    = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
    if submitted:
        if not email or not password:
            st.error("Please fill in all fields."); return
        users = _load_users()
        user  = users.get(email.lower().strip())
        if not user or not _verify(password, user["password_hash"]):
            st.error("Incorrect email or password."); return
        if not user["password_hash"].startswith("pbkdf2$"):
            user["password_hash"] = _hash(password)
            _save_users(users)
        key = email.lower().strip()
        user = sync_billing(key) or user
        st.session_state.user = _build_session_user(key, user)
        st.success(f"Welcome back, {user['name']}!")
        st.rerun()


def sync_billing(email: str) -> dict | None:
    """Refresh this account's plan from Stripe, the source of truth -- this is
    how failed renewals, plan changes and cancellations made in Stripe's portal
    reach the site (a Streamlit app can't receive Stripe's webhooks). Returns
    the stored account, or None if unknown. Never blocks sign-in: if Stripe is
    unreachable, the stored plan is kept."""
    users = _load_users()
    if email not in users:
        return None
    try:
        import billing_stripe
        fields = billing_stripe.sync_subscription(email) if billing_stripe.is_stripe_enabled() else None
    except Exception:
        fields = None
    if fields and any(users[email].get(k) != v for k, v in fields.items()):
        users[email].update(fields)
        _save_users(users)
        if (st.session_state.get("user") or {}).get("email") == email:
            st.session_state.user = _build_session_user(email, users[email])
    return users[email]


def signup_form():
    st.markdown("### Start Your Free Trial")
    st.markdown('<p style="color:#8BA0B0;font-size:0.85rem;">14-day free trial - no credit card required.</p>',
                unsafe_allow_html=True)
    with st.form("signup_form"):
        name     = st.text_input("Full name")
        email    = st.text_input("Email address")
        password = st.text_input("Password (min 8 chars)", type="password")
        confirm  = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Start Free Trial", use_container_width=True, type="primary")
    if submitted:
        if not all([name, email, password, confirm]):
            st.error("Please fill in all fields."); return
        if password != confirm:
            st.error("Passwords do not match."); return
        if len(password) < 8:
            st.error("Password must be at least 8 characters."); return
        users = _load_users()
        key   = email.lower().strip()
        if key in users:
            st.error("An account with this email already exists."); return
        joined = datetime.now().strftime("%Y-%m-%d")
        users[key] = {
            "name":            name.strip(),
            "password_hash":   _hash(password),
            "plan":            "Trial",
            "joined":          joined,
            "billing_status":  "trial",
            "card_last4":      None,
            "next_bill":       None,
            "commodity_prefs": [],
        }
        _save_users(users)
        st.session_state.user = _build_session_user(key, users[key])
        st.success(f"Welcome to Trochiá, {name.strip()}! Your 14-day free trial starts now.")
        st.rerun()


def update_plan(email: str, new_plan: str, card_last4: str = None,
                 stripe_customer_id: str = None, stripe_subscription_id: str = None):
    users = _load_users()
    if email not in users:
        return
    users[email]["plan"]           = new_plan
    users[email]["billing_status"] = "active"
    next_bill = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    users[email]["next_bill"]      = next_bill
    if card_last4:
        users[email]["card_last4"] = card_last4
    if stripe_customer_id:
        users[email]["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id:
        users[email]["stripe_subscription_id"] = stripe_subscription_id
    _save_users(users)
    # Refresh the session only if this person is the one signed in. Called from
    # Stripe's return link too, and that link must never sign anyone in --
    # anyone holding the URL would become them.
    if (st.session_state.get("user") or {}).get("email") == email:
        st.session_state.user = _build_session_user(email, users[email])


def cancel_subscription(email: str, at_period_end: bool = True):
    """at_period_end=True (the Stripe case): Stripe keeps a cancelled
    subscription running until the end of the month already paid for, so the
    account keeps its plan until then; sync_billing() downgrades it once Stripe
    actually ends it. Downgrading on the spot took away access people had paid
    for. at_period_end=False ends access immediately (no Stripe billing)."""
    users = _load_users()
    if email not in users:
        return
    if at_period_end:
        users[email]["billing_status"] = "cancelling"
    else:
        users[email]["plan"]                    = "Trial"
        users[email]["billing_status"]          = "cancelled"
        users[email]["card_last4"]              = None
        users[email]["next_bill"]               = None
        users[email]["stripe_subscription_id"]  = None
    _save_users(users)
    st.session_state.user = _build_session_user(email, users[email])


def logout():
    st.session_state.pop("user", None)
    st.session_state.page = "Home"
    st.rerun()
