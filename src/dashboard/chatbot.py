"""Trochiá AI chatbot — uses Claude API when key is set, FAQ fallback otherwise."""
import os
import re
import sys
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from commodity_maps import TOTAL_COMMODITIES, FRED_COMMODITY_MAP

load_dotenv()
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = f"""You are the Trochiá assistant — a helpful, concise expert on commodity price risk for small businesses.

Trochiá is a commodity intelligence platform that tracks {TOTAL_COMMODITIES} commodities -- retail
grocery items (via FRED/BLS and USDA) and exchange-traded futures (via Yahoo Finance) -- using
machine learning forecasts (SARIMA + LSTM hybrid models). It gives GREEN/YELLOW/RED risk signals
to help restaurants and small food businesses decide when to buy in bulk. Each commodity has its
own forecast horizon: weeks for exchange-traded futures, months for grocery items sourced from
government data (since that data itself is only published monthly).

Answer questions about:
- How to read the signals (GREEN = stable, YELLOW = moderate risk, RED = buy now)
- What each commodity means for a food business
- How the forecasting models work
- How to use the platform features (Market tab, Commodities detail, Scenario Calculator)
- General commodity pricing questions

Keep answers concise — 2-4 sentences unless more detail is needed. Be helpful and professional."""

FAQ = [
    {
        "keywords": ["signal", "color", "red", "green", "yellow", "mean"],
        "answer": "Signals show forecast risk over each commodity's own horizon -- weeks for exchange-traded futures, months for grocery items. GREEN means prices are stable — no action needed. YELLOW means a moderate increase is expected — consider buying slightly ahead. RED means a significant price spike is forecast — buy now or lock in contracts."
    },
    {
        "keywords": ["commodity", "track", "what", "include", "list"],
        "answer": f"Trochiá tracks {TOTAL_COMMODITIES} commodities across proteins, dairy, produce, bakery goods, grains, energy, and metals -- see the Market tab for the full live list. Retail grocery items come from FRED/USDA; exchange-traded futures (grains, energy, metals) come from Yahoo Finance."
    },
    {
        "keywords": ["forecast", "model", "predict", "accurate", "how"],
        "answer": "Forecasts use a hybrid of three models: SARIMA (statistical time-series), LSTM (deep learning neural network), and a baseline linear model. Their outputs are combined using RMSE-weighted averaging — models that performed better historically get more weight."
    },
    {
        "keywords": ["data", "source", "where", "come from", "fred", "usda"],
        "answer": f"Retail grocery prices ({len(FRED_COMMODITY_MAP)} items — beef, chicken, eggs, dairy, produce, bakery, and more) come from FRED/BLS. Cash wheat and wholesale cream prices come from USDA AMS. Exchange-traded futures (energy, grains, metals) come from Yahoo Finance."
    },
    {
        "keywords": ["refresh", "update", "live", "real time", "current"],
        "answer": "FRED and USDA retail data updates on their own schedule (FRED: 4-6 week lag; USDA: same day to a few days). Yahoo Finance futures prices are exchange-delayed about 15 minutes. You can set auto-refresh in the sidebar."
    },
    {
        "keywords": ["scenario", "calculator", "savings", "pre-buy", "bulk"],
        "answer": "The Scenario Calculator (on the Commodities tab) estimates how much you could save by pre-buying inventory before a forecasted price increase. Enter the commodity, your weekly usage, and how many weeks ahead you want to buy."
    },
    {
        "keywords": ["plan", "price", "subscription", "cost", "starter", "pro", "business"],
        "answer": f"Trochiá offers three plans: Starter ($19/mo) for 5 commodities and weekly alerts, Pro ($49/mo) for all {TOTAL_COMMODITIES} commodities, daily updates, and AI Chat, and Business ($99/mo) for up to 10 user seats, API access, and dedicated support."
    },
    {
        "keywords": ["sign in", "account", "login", "register", "sign up"],
        "answer": "Click 'Sign In' in the top navigation bar. You can create a free account and choose a subscription plan. Your account tracks your usage, alert preferences, and subscription tier."
    },
    {
        "keywords": ["help", "tour", "guide", "tutorial", "start", "begin"],
        "answer": "Visit the Help tab in the navigation bar for a full onboarding guide. It covers reading signals, using the Market tab, the AI chat, and how the forecasting models work."
    },
]


def faq_response(message: str) -> str:
    msg = message.lower()
    for item in FAQ:
        if any(kw in msg for kw in item["keywords"]):
            return item["answer"]
    return ("I can help with questions about commodity signals, forecasting models, data sources, the scenario calculator, and subscription plans. "
            "Could you rephrase your question or visit the Help tab for a full guide?")


def get_response(message: str, history: list) -> str:
    if ANTHROPIC_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            messages = []
            for turn in history[-10:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": message})
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return resp.content[0].text
        except Exception as e:
            return f"AI service temporarily unavailable. {faq_response(message)}"
    else:
        return faq_response(message)


def is_ai_enabled() -> bool:
    return bool(ANTHROPIC_KEY)
