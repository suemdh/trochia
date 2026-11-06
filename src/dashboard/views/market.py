"""Trochiá — Market page: sortable commodity list."""
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from commodity_maps import strip_unit
from decision.engine import SIGNAL_LABEL

SIG_COLOR = {"RED":"#FF4B4B","YELLOW":"#F0B429","GREEN":"#21C55D"}
SIG_ORDER  = {"RED":0,"YELLOW":1,"GREEN":2}


def render(commodities: dict, search_query: str = ""):
    st.markdown('<div class="sec-header">Market Overview</div>', unsafe_allow_html=True)

    now_utc = datetime.now(timezone.utc).strftime("%H:%M UTC")
    n_live = sum(1 for v in commodities.values() if v.get("is_live"))
    st.markdown(
        f'<p style="color:#8BA0B0;font-size:0.82rem;margin-bottom:1rem;">'
        f'Where prices are headed for everything we track, and what to do about it. '
        f'<span style="color:#21C55D;font-weight:600;">{n_live} prices are live</span> '
        f'(about 15 minutes behind the market) &nbsp;·&nbsp; updated {now_utc}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#4A6A80;font-size:0.75rem;margin-top:-0.5rem;margin-bottom:1rem;">'
        "Good to know: forecasts are based on past price patterns. They can't see breaking news "
        "like storms, wars, or supply problems, so when something big is happening, check with "
        "your supplier too. We flag items whose prices are moving unusually.</p>",
        unsafe_allow_html=True,
    )

    # ── Controls ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        q = st.text_input("Filter", value=search_query, placeholder="Search by name...",
                          label_visibility="collapsed")
    with c2:
        sort_by = st.selectbox("Sort", ["Most urgent first", "Name A–Z", "Biggest price change", "Current Price"],
                               label_visibility="collapsed")
    with c3:
        sig_filter = st.selectbox("Signal", ["All", "RED", "YELLOW", "GREEN"],
                                  format_func=lambda s: "All items" if s == "All" else SIGNAL_LABEL[s],
                                  label_visibility="collapsed")

    # ── Summary counts ─────────────────────────────────────────────────────────
    n_red    = sum(1 for v in commodities.values() if v["signal"]=="RED")
    n_yellow = sum(1 for v in commodities.values() if v["signal"]=="YELLOW")
    n_green  = sum(1 for v in commodities.values() if v["signal"]=="GREEN")

    s1, s2, s3 = st.columns(3)
    for col, label, count, color in [
        (s1, SIGNAL_LABEL["RED"],    n_red,    "#FF4B4B"),
        (s2, SIGNAL_LABEL["YELLOW"], n_yellow, "#F0B429"),
        (s3, SIGNAL_LABEL["GREEN"],  n_green,  "#21C55D"),
    ]:
        with col:
            st.markdown(f"""
            <div class="sig-card" style="border-left:4px solid {color};text-align:center;padding:0.7rem;">
                <div style="font-size:1.8rem;font-weight:700;color:{color};">{count}</div>
                <div style="font-size:0.78rem;color:#8BA0B0;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<hr class="dark-divider">', unsafe_allow_html=True)

    # ── Build filtered/sorted rows ─────────────────────────────────────────────
    rows = []
    for name, v in commodities.items():
        if q and q.lower() not in name.lower():
            continue
        if sig_filter != "All" and v["signal"] != sig_filter:
            continue
        rows.append({
            "Commodity":    name,
            "Price":        v["current"],
            "Unit":         v.get("unit",""),
            "Forecast":     v["forecast"],
            "Change":       v["pct"]*100,
            "Signal":       v["signal"],
            "_rmse_pct":    v.get("rmse_pct"),
            "_beats_naive": str(v.get("beat_naive")) == "True",
            "_lo":          v.get("lower_bound"),
            "_hi":          v.get("upper_bound"),
            "_sig_rank":    SIG_ORDER.get(v["signal"],3),
            "_message":     v.get("message",""),
            "_is_live":     v.get("is_live", False),
            "_is_estimated":v.get("is_estimated", True),
            "_price_as_of": v.get("price_as_of", ""),
            "_horizon":      v.get("horizon", 8),
            "_horizon_unit": v.get("horizon_unit", "weeks"),
            "_volatility_flag":   v.get("volatility_flag", False),
            "_volatility_zscore": v.get("volatility_zscore", None),
            "_recent_move_pct":   v.get("recent_move_pct", None),
            "_sector_flag":       v.get("sector_flag", False),
            "_price_rejected":    v.get("price_rejected", False),
            "_ticker":            v.get("ticker", None),
            "_contract":          v.get("contract", None),
        })

    if sort_by == "Most urgent first":
        rows.sort(key=lambda r: (r["_sig_rank"], -abs(r["Change"])))
    elif sort_by == "Name A–Z":
        rows.sort(key=lambda r: r["Commodity"])
    elif sort_by == "Biggest price change":
        rows.sort(key=lambda r: -abs(r["Change"]))
    elif sort_by == "Current Price":
        rows.sort(key=lambda r: -r["Price"])

    if not rows:
        st.info("No commodities match your filter.")
        return

    # ── Signal card list ───────────────────────────────────────────────────────
    for r in rows:
        sig   = r["Signal"]
        color = SIG_COLOR[sig]
        css   = f"sig-card-{sig.lower()}"
        pct   = r["Change"]
        pct_str = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"

        if r["_is_live"]:
            price_badge = '<span style="background:#21C55D;color:#fff;font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;vertical-align:middle;margin-left:6px;">LIVE</span>'
        elif r["_is_estimated"]:
            as_of = r["_price_as_of"]
            tip   = (f"Government price data is published with a delay; last data: {as_of}"
                     if as_of else "Estimated from the latest government data")
            price_badge = f'<span style="background:#4A6A80;color:#fff;font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;vertical-align:middle;margin-left:6px;" title="{tip}">ESTIMATE</span>'
        else:
            price_badge = ""

        vol_suffix = "  ·  ⚠ Prices jumping" if r["_volatility_flag"] else ""
        with st.expander(f"{r['Commodity']}  ·  {pct_str}  ·  {SIGNAL_LABEL[sig]}{vol_suffix}"):
            st.markdown(price_badge, unsafe_allow_html=True)
            if r["_contract"]:
                ticker_note = f"Price from the {r['_contract']} futures contract"
            else:
                ticker_note = "Price from U.S. government data (FRED / USDA)"
            st.caption(f"{ticker_note}  ·  as of {r['_price_as_of'] or 'unknown'}")

            if r["_price_rejected"]:
                st.markdown("""
                <div class="sig-card sig-card-red" style="padding:0.65rem 1rem;margin-bottom:0.75rem;">
                    <span style="font-size:0.85rem;color:#FFFFFF;font-weight:600;">⚠ Live price unavailable right now</span><br>
                    <span style="font-size:0.8rem;color:#8BA0B0;">
                        The latest price we received didn't look right, so we're showing the last
                        reliable price instead of a possibly wrong one.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            if r["_volatility_flag"]:
                move = r["_recent_move_pct"]
                move_str = f"{move*100:+.1f}%" if move is not None else "an unusual amount"
                if r["_sector_flag"]:
                    reason = (f"Energy prices are all moving the same way right now ({r['Commodity']}: "
                              f"{move_str} recently). That usually means something big is going on, "
                              f"like a supply disruption.")
                else:
                    reason = (f"{r['Commodity']} moved {move_str} over the last {r['_horizon']} "
                              f"{r['_horizon_unit']}, which is more than usual for it.")
                st.markdown(f"""
                <div class="sig-card sig-card-yellow" style="padding:0.65rem 1rem;margin-bottom:0.75rem;border-left:4px solid #F0B429;">
                    <span style="font-size:0.85rem;color:#FFFFFF;font-weight:600;">⚠ Prices are jumping around</span><br>
                    <span style="font-size:0.8rem;color:#8BA0B0;">
                        {reason} Our forecast is based on past patterns and can't see the news,
                        so double-check with your supplier before acting on it.
                    </span>
                </div>
                """, unsafe_allow_html=True)
            def _fmt(v):
                if v >= 1000:   return f"${v:,.0f}"
                elif v >= 10:   return f"${v:.2f}"
                elif v >= 1:    return f"${v:.3f}"
                else:           return f"${v:.4f}"

            unit_label = strip_unit(r["Unit"]) if r["Unit"] else ""
            horizon, horizon_unit = r["_horizon"], r["_horizon_unit"]
            horizon_word = horizon_unit[:-1].capitalize() if horizon == 1 else horizon_unit.capitalize()
            forecast_label = f"Expected in {horizon} {horizon_word.lower()}"
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"Price today ({unit_label})" if unit_label else "Price today",
                      _fmt(r['Price']))
            m2.metric(f"{forecast_label} ({unit_label})" if unit_label else forecast_label,
                      _fmt(r['Forecast']))
            m3.metric("Expected change", pct_str)
            # Backtest-backed reliability instead of the old "Confidence 90%",
            # which was a cosmetic transform of error (0.95 - error/2), not a
            # probability -- and read 80-92% even for models that couldn't
            # beat a simple "no change" forecast.
            err = r["_rmse_pct"]
            m4.metric("Margin of error", f"±{err*100:.0f}%" if err is not None else "n/a",
                      help="On average, past forecasts for this item were off by about this much.")

            skill = ("Track record: more accurate than assuming prices stay flat." if r["_beats_naive"]
                     else "No proven track record yet -- treat this as a heads-up, not a reason to buy.")
            rng = (f"Likely price in {horizon} {horizon_word.lower()}: {_fmt(r['_lo'])} – {_fmt(r['_hi'])}  ·  "
                   if r["_lo"] is not None and r["_hi"] is not None else "")
            st.caption(f"{rng}{skill}")

            st.markdown(f"""
            <div class="sig-card {css}" style="padding:0.65rem 1rem;margin-top:0.5rem;">
                <span style="font-size:0.85rem;color:#FFFFFF;">{r['_message']}</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("See chart & savings calculator", key=f"chart_{r['Commodity']}", type="primary"):
                st.session_state.page = "Commodities"
                st.session_state.selected_commodity = r["Commodity"]
                st.rerun()
