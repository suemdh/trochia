"""Trochia - Commodity Intelligence Platform"""
import os, sys, warnings, base64
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as _components
from PIL import Image

warnings.filterwarnings("ignore")

import shutil as _sh
for _cache in [os.path.join(os.path.dirname(__file__), "__pycache__"),
               os.path.join(os.path.dirname(__file__), "views", "__pycache__")]:
    _sh.rmtree(_cache, ignore_errors=True)

_DASH = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_DASH, "..", ".."))
_SRC  = os.path.abspath(os.path.join(_DASH, ".."))
for _p in [_DASH, _SRC, _ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from styles import DARK_CSS
from auth import get_current_user, logout, PLAN_COMMODITY_LIMIT, PREVIEW_COUNT, has_full_access
from views import home, market, billing, chat
from views import commodities as commodities_view
from views import help_page, pricing, account, legal
from commodity_maps import TOTAL_COMMODITIES
from decision.engine import evaluate, ForecastInput

# â”€â”€ Transparent PNG conversion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ASSETS = os.path.join(_DASH, "assets")

def _make_transparent_png(src_jpg: str, dst_png: str):
    if os.path.exists(dst_png):
        return
    if not os.path.exists(src_jpg):
        return
    img = Image.open(src_jpg).convert("RGBA")
    data = img.getdata()
    new = []
    for r, g, b, a in data:
        if r > 235 and g > 235 and b > 235:
            new.append((r, g, b, 0))
        else:
            new.append((r, g, b, a))
    img.putdata(new)
    img.save(dst_png, "PNG")

_make_transparent_png(
    os.path.join(ASSETS, "trochia_logo.jpg"),
    os.path.join(ASSETS, "trochia_logo.png"),
)
_make_transparent_png(
    os.path.join(ASSETS, "wreath_favicon.jpg"),
    os.path.join(ASSETS, "wreath_favicon.png"),
)

# â”€â”€ Page config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_wreath_png = os.path.join(ASSETS, "wreath_favicon.png")
_wreath_jpg = os.path.join(ASSETS, "wreath_favicon.jpg")
_icon_path  = _wreath_png if os.path.exists(_wreath_png) else _wreath_jpg
_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else "leaf"

st.set_page_config(
    page_title="Trochia",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": "Trochia - Commodity Intelligence Platform"},
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

# â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FORECASTS_PATH = os.path.join(_DASH, "..", "..", "outputs", "forecasts.csv")


@st.cache_data(ttl=300)
def load_forecasts():
    if not os.path.exists(FORECASTS_PATH):
        return None
    return pd.read_csv(FORECASTS_PATH)

def build_commodities():
    df           = load_forecasts()

    # Apply commodity_prefs filter for logged-in users
    user  = get_current_user()
    prefs = (user or {}).get("commodity_prefs", [])
    limit = PLAN_COMMODITY_LIMIT.get((user or {}).get("plan"))
    if limit:
        prefs = prefs[:limit]  # e.g. Starter: only their chosen 5, even if more are saved

    # Build from forecasts.csv if available
    if df is not None and not df.empty:
        result = {}
        for _, row in df.iterrows():
            name = row["commodity"]

            price_as_of  = str(row.get("price_as_of", ""))
            current      = float(row["current_price"])
            is_estimated = bool(row.get("is_estimated", True))
            forecast     = float(row["forecast_price"])

            from audit_log import log_price_fetch
            log_price_fetch(name, str(row.get("source", "")), current, None, price_as_of, True)

            # Signal, %, and alert text all come from ONE engine call, on the
            # price actually being displayed -- for every row, not just live
            # ones. Reading the training-time signal/message from the CSV
            # while recomputing % separately is exactly what made the card
            # header and alert text disagree; and evaluating here means
            # engine fixes (e.g. the no-skill RED cap) apply immediately
            # instead of waiting for the next multi-hour retrain.
            bn = row.get("beat_naive")
            rec = evaluate(ForecastInput(
                commodity=name, current_price=current, forecast_price=forecast,
                horizon_weeks=int(row.get("horizon_steps", row.get("horizon_weeks", 8))),
                confidence=float(row["confidence"]), weekly_usage_units=10,
                unit_label=str(row.get("unit", "")),
                horizon_unit=str(row.get("horizon_unit", "weeks")),
                days_per_step=int(row.get("step_days", 7)),
                rmse_pct=float(row["rmse_pct"]) if pd.notna(row.get("rmse_pct")) else float("inf"),
                # Unknown skill is not demonstrated skill.
                beats_naive=bool(bn) if pd.notna(bn) and str(bn) != "False" else False,
            ))
            pct, sig, message = rec.pct_change, rec.signal, rec.message

            from audit_log import log_alert
            log_alert(name, sig, pct, current, forecast, float(row["confidence"]),
                      float(row["rmse_pct"]) if pd.notna(row.get("rmse_pct")) else None,
                      bool(bn) if pd.notna(bn) and str(bn) != "False" else False,
                      message, False)

            result[name] = {
                "current":      current,
                "forecast":     forecast,
                "lower_bound":  float(row["lower_bound"]) if "lower_bound" in row and pd.notna(row["lower_bound"]) else None,
                "upper_bound":  float(row["upper_bound"]) if "upper_bound" in row and pd.notna(row["upper_bound"]) else None,
                "pct":          pct,
                "signal":       sig,
                "confidence":   float(row["confidence"]),
                "horizon":      int(row.get("horizon_steps", row.get("horizon_weeks", 8))),
                "horizon_unit": str(row.get("horizon_unit", "weeks")),
                "step_days":    int(row.get("step_days", 7)),
                "message":      message,
                "unit":         str(row.get("unit", "")),
                "beat_naive":   row.get("beat_naive", None),
                "rmse_pct":     float(row["rmse_pct"]) if pd.notna(row.get("rmse_pct")) else None,
                "naive_rmse":   row.get("naive_rmse", None),
                "is_estimated": is_estimated,
                "price_as_of":  price_as_of,
                "volatility_flag":   bool(row.get("volatility_flag", False)),
                "volatility_zscore": row.get("volatility_zscore", None),
                "recent_move_pct":   row.get("recent_move_pct", None),
                "sector_flag":       bool(row.get("sector_flag", False)),
            }
        if prefs or limit:
            result = {k: v for k, v in result.items() if k in prefs}
        result = dict(sorted(result.items(),
                             key=lambda x: ({"RED":0,"YELLOW":1,"GREEN":2}.get(x[1]["signal"],3), -abs(x[1]["pct"]))))
        if not has_full_access(user):
            result = dict(list(result.items())[:PREVIEW_COUNT])  # the most urgent few, as a preview
        return result, True

    # No forecasts on disk: say so. This used to fall back to a hardcoded
    # table of placeholder prices (Gold at $2,350, discontinued items like
    # Tuna) rendered in the same cards as real data, labeled only by small
    # sidebar text -- a business could easily have acted on a fake number.
    return {}, False

# â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NAV = ["Home", "Market", "Commodities", "Chat", "Help", "Pricing", "Billing", "Profile", "Legal"]

def _logo_b64() -> str | None:
    png = os.path.join(ASSETS, "trochia_logo.png")
    jpg = os.path.join(ASSETS, "trochia_logo.jpg")
    path = png if os.path.exists(png) else (jpg if os.path.exists(jpg) else None)
    if not path:
        return None
    return base64.b64encode(open(path, "rb").read()).decode()

def render_sidebar(is_live: bool):
    with st.sidebar:
        # Logo â€” clicking navigates Home (JS wired via component below)
        b64 = _logo_b64()
        if b64:
            ext = "png" if os.path.exists(os.path.join(ASSETS, "trochia_logo.png")) else "jpg"
            st.markdown(f"""
            <img id="trochia-logo-img" src="data:image/{ext};base64,{b64}"
                 style="width:100%;border-radius:6px;display:block;cursor:pointer;margin-bottom:0.25rem;">
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:1.4rem;font-weight:800;letter-spacing:0.1em;'
                        'color:#FFFFFF;padding:0.5rem 0;">TROCHIA</div>', unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#1E3A5F;margin:0.4rem 0;">', unsafe_allow_html=True)

        current = st.session_state.get("page", "Home")
        if current not in NAV:
            current = "Home"

        # Pure button nav â€” no radio widget, no circles
        # Active state is handled by injecting one targeted style block
        active_styles = "".join(
            f'[data-testid="stSidebar"] [data-testid="stButton"]:has(button[data-testid="baseButton-secondary"][aria-label="{item}"]) button {{'
            f'background:#0D2035!important;color:#FFFFFF!important;font-weight:600!important;border-left-color:#007A8E!important;}}'
            for item in NAV if item == current
        )
        if active_styles:
            st.markdown(f"<style>{active_styles}</style>", unsafe_allow_html=True)

        for item in NAV:
            if st.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state.page = item; st.rerun()

        page = current

        st.markdown('<hr style="border-color:#1E3A5F;margin:0.6rem 0;">', unsafe_allow_html=True)

        user = get_current_user()
        if user:
            plan = user.get("plan", "Trial")
            plan_colors = {"Starter":"#007A8E","Pro":"#21C55D","Business":"#F0B429","Trial":"#A8DBB9"}
            c = plan_colors.get(plan, "#007A8E")
            trial_days = user.get("trial_days_left", None)
            trial_html = (f'<div style="font-size:0.7rem;color:#F0B429;margin-top:2px;">'
                          f'{trial_days} days left in trial</div>' if trial_days is not None else "")
            st.markdown(f"""
            <div style="padding:0.4rem 0;">
                <div style="font-size:0.82rem;font-weight:600;color:#FFFFFF;">{user['name']}</div>
                <div style="font-size:0.72rem;color:#8BA0B0;">{user['email']}</div>
                <div style="margin-top:0.35rem;">
                    <span style="background:{c};color:#fff;padding:1px 8px;border-radius:10px;
                    font-size:0.68rem;font-weight:700;">{plan}</span>
                </div>
                {trial_html}
            </div>
            """, unsafe_allow_html=True)
            if st.button("Sign Out", use_container_width=True, key="sb_signout"):
                logout(); st.rerun()
        else:
            if st.button("Sign In / Register", use_container_width=True, type="primary", key="sb_signin"):
                st.session_state.page = "Profile"; st.rerun()

        st.markdown('<hr style="border-color:#1E3A5F;margin:0.6rem 0;">', unsafe_allow_html=True)

        refresh_choice = st.selectbox("Auto-refresh", ["Off","5 min","15 min","1 hour"],
                                      label_visibility="collapsed")
        refresh_map = {"Off":None,"5 min":300,"15 min":900,"1 hour":3600}

        st.markdown('<hr style="border-color:#1E3A5F;margin:0.6rem 0;">', unsafe_allow_html=True)
        st.markdown(f"""
        <div style='font-size:0.7rem;color:#4A6A80;line-height:1.7;'>
        {"Forecasts loaded" if is_live else "Forecast data unavailable"}<br>
        Futures: ~15 min delay &nbsp;·&nbsp; USDA: ~1-2 wk lag &nbsp;·&nbsp; FRED/BLS: ~4-8 wk lag
        </div>
        """, unsafe_allow_html=True)

    return page, refresh_map[refresh_choice]

# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    if "page" not in st.session_state:
        st.session_state.page = "Home"

    # Stripe redirects back to this app's base URL with ?checkout=success/cancelled
    # -- land on Billing so billing.py's own handler can pick it up and verify
    # the session, rather than silently dropping the confirmation on Home.
    if "checkout" in st.query_params:
        st.session_state.page = "Billing"
    # Password-reset links from email land on Profile, where the form lives.
    if "reset" in st.query_params:
        st.session_state.page = "Profile"

    commodities, is_live = build_commodities()
    page, refresh_secs = render_sidebar(is_live)

    user = get_current_user()
    if commodities and not has_full_access(user) and page in ("Market", "Commodities"):
        if user:
            st.warning(f"Your free trial has ended. Choose a plan to see all {TOTAL_COMMODITIES} commodities "
                       f"-- your account and saved picks are kept.")
            if st.button("Choose a plan", type="primary"):
                st.session_state.page = "Billing"; st.rerun()
        else:
            st.info(f"You're seeing a preview: {len(commodities)} of {TOTAL_COMMODITIES} commodities. "
                    f"Start a free 14-day trial to see them all -- no credit card needed.")
            if st.button("Start free trial", type="primary"):
                st.session_state.page = "Profile"; st.rerun()

    plan_limit = PLAN_COMMODITY_LIMIT.get((user or {}).get("plan"))
    if plan_limit and not (user or {}).get("commodity_prefs") and page in ("Home", "Market", "Commodities"):
        st.info(f"Your {user['plan']} plan includes up to {plan_limit} commodities. "
                f"Choose yours on the Profile page to see their prices and forecasts.")
        if st.button("Choose my commodities", type="primary"):
            st.session_state.page = "Profile"; st.rerun()
    elif not commodities and page in ("Home", "Market", "Commodities"):
        st.error("Forecast data is unavailable right now -- no prices or signals are "
                 "shown rather than showing stale or placeholder numbers. Please check "
                 "back shortly.")
    elif page == "Home":
        home.render(commodities)
    elif page == "Market":
        market.render(commodities)
    elif page == "Commodities":
        commodities_view.render(commodities)
    elif page == "Chat":
        chat.render()
    elif page == "Help":
        help_page.render()
    elif page == "Pricing":
        pricing.render()
    elif page == "Billing":
        billing.render()
    elif page == "Profile":
        account.render()
    elif page == "Legal":
        legal.render()

    _render_logo_click_handler()

    if refresh_secs:
        import time; time.sleep(refresh_secs); st.rerun()


def _render_logo_click_handler():
    """Wire the sidebar logo image to navigate Home when clicked.

    This used to be bundled inside a much bigger component that also drew a
    floating chat widget with its own hardcoded, drifting FAQ text -- while a
    complete, working Claude-API-backed chat page (views/chat.py) sat unused
    because it was never added to NAV. That page is now wired in as the real
    "Chat" nav item instead of duplicating a second, fake chat UI here.
    """
    _components.html("""
<script>
(function() {
  var P = window.parent;
  if (!P || P === window) return;

  (function wireLogo() {
    var logo = P.document.getElementById('trochia-logo-img');
    if (logo && !logo._wired) {
      logo._wired = true;
      logo.addEventListener('click', function() {
        var btns = P.document.querySelectorAll('[data-testid="stSidebar"] button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].innerText.trim() === 'Home') { btns[i].click(); break; }
        }
      });
    } else if (!logo) {
      setTimeout(wireLogo, 500);
    }
  })();
})();
</script>
""", height=0, scrolling=False)


main()
