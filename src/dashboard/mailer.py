"""
Sends transactional email (password resets) over SMTP -- Python's standard
library only. Defaults to Gmail; set SMTP_HOST/SMTP_PORT to switch providers.

Settings (.env locally, Streamlit Cloud's Secrets box when deployed):
  SMTP_USER      the sending address, e.g. trochia.app@gmail.com
  SMTP_PASSWORD  a Gmail *app password* (16 chars) -- never the account's real
                 login password; Gmail refuses those for SMTP anyway
"""
import os
import smtplib
from email.message import EmailMessage


def _setting(name: str, default: str | None = None) -> str | None:
    if os.getenv(name):
        return os.getenv(name)
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


def is_configured() -> bool:
    return bool(_setting("SMTP_USER") and _setting("SMTP_PASSWORD"))


def send_email(to: str, subject: str, body: str):
    """Raises on failure -- callers decide what the user sees."""
    msg = EmailMessage()
    msg["From"] = f"Trochiá <{_setting('SMTP_USER')}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    host = _setting("SMTP_HOST", "smtp.gmail.com")
    port = int(_setting("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=20) as s:
        s.login(_setting("SMTP_USER"), _setting("SMTP_PASSWORD").replace(" ", ""))
        s.send_message(msg)
