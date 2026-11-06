# Notes for the designer

Thanks for helping with Trochiá's look. The live site is
https://trochia-app.streamlit.app and it's built with Streamlit (Python).

## The one important rule

**Don't push changes straight to `main`.** Anything on `main` goes live on the
public site within minutes. Instead:

1. Create a new branch (for example `redesign`).
2. Push your changes to that branch.
3. Open a **pull request** on GitHub so it can be checked and merged.

## Where the look lives

| What | File |
|---|---|
| Colors, fonts, card and button styles (CSS) | `src/dashboard/styles.py` |
| Sidebar, page layout | `src/dashboard/app.py` |
| Each page | `src/dashboard/views/` (`home.py`, `market.py`, `commodities.py`, `pricing.py`, `billing.py`, `account.py`, `help_page.py`, `legal.py`, `chat.py`) |
| Logo and images | `src/dashboard/assets/` |

## Please don't change the meaning, only the look

These hold safety checks and real money logic, so leave them alone (styling the
text they produce on the page is fine):

- `src/decision/engine.py` -- what each signal says and when it fires
- `src/dashboard/auth.py`, `src/dashboard/billing_stripe.py`, `src/dashboard/mailer.py` -- accounts, payments, email
- `src/models/`, `src/data/` -- the forecasts and price data

The signal names are **Buy ahead**, **Watch**, and **No action needed**. They're
defined once in `src/decision/engine.py`; please keep those exact words.

## Prefer to design in Figma instead?

Totally fine. Send mockups and they'll be built into the site.

## Running it on your computer

You need Python 3.12.

```
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

It opens at http://localhost:8501. It runs without any passwords or API keys;
payments just show "Coming soon" and accounts are saved in a local file.
