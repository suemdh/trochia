"""
Sends transactional email (password resets) over SMTP -- Python's standard
library only. Works with Gmail or a relay service such as Brevo.

Settings (.env locally, Streamlit Cloud's Secrets box when deployed):
  SMTP_USER      the SMTP login (Gmail: the address; Brevo: the login on its SMTP page)
  SMTP_PASSWORD  Gmail: a 16-letter *app password*, never the real login password.
                 Brevo: an SMTP key from its SMTP & API page.
  SMTP_FROM      the address emails come from (defaults to SMTP_USER)
  SMTP_HOST      default smtp.gmail.com; Brevo: smtp-relay.brevo.com
  SMTP_PORT      465 = encrypted from the start (Gmail); 587 = STARTTLS (Brevo)
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
    msg["From"] = f"Trochiá <{_setting('SMTP_FROM') or _setting('SMTP_USER')}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    host = _setting("SMTP_HOST", "smtp.gmail.com")
    port = int(_setting("SMTP_PORT", "465"))
    login = (_setting("SMTP_USER"), _setting("SMTP_PASSWORD").replace(" ", ""))
    if port == 465:  # encrypted from the first byte (Gmail's default)
        with smtplib.SMTP_SSL(host, port, timeout=20) as s:
            s.login(*login)
            s.send_message(msg)
    else:            # 587/2525: plain connection upgraded with STARTTLS (Brevo)
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(*login)
            s.send_message(msg)
