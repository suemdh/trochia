"""
Business owners should see plain-English signal names and honest plan features.

    python tests/test_wording.py
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = os.path.abspath(os.path.join(ROOT, "src", "dashboard", "app.py"))
sys.path[:0] = [os.path.join(ROOT, "src", "dashboard"), os.path.join(ROOT, "src"), ROOT]

from streamlit.testing.v1 import AppTest
from decision.engine import SIGNAL_LABEL

RAW_CODES = ("RED", "YELLOW", "GREEN")


def test_market_cards_use_plain_signal_names():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["page"] = "Market"
    at.run()
    assert not at.exception, at.exception
    titles = [e.label for e in at.expander]
    assert titles, "no commodity cards rendered"
    for t in titles:
        assert not any(f"· {code}" in t for code in RAW_CODES), f"raw signal code shown: {t}"
        assert any(label in t for label in SIGNAL_LABEL.values()), f"no plain signal name: {t}"
    captions = [c.value for c in at.caption]
    assert any("average · the latest the U.S. government has published" in c for c in captions), \
        "monthly government prices (e.g. Eggs) should say which month's average they are"
    assert not any("as of 20" in c and "-01" in c and "government" in c for c in captions
                   if "Diesel" not in c), [c for c in captions if "government" in c]


def test_pricing_only_claims_what_exists():
    import views.pricing as pricing
    included = {feat for plan in pricing.PLANS for state, feat in plan["features"] if state is True}
    for unbuilt in ("SMS", "API", "seats", "alerts", "AI chat", "SLA", "Daily"):
        assert not any(unbuilt.lower() in f.lower() for f in included), \
            f"plan claims an unbuilt feature as included: {unbuilt}"


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
