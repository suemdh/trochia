"""Trochiá — Market page: sortable commodity list."""
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from commodity_maps import strip_unit

SIG_COLOR = {"RED":"#FF4B4B","YELLOW":"#F0B429","GREEN":"#21C55D"}
SIG_ORDER  = {"RED":0,"YELLOW":1,"GREEN":2}


def render(commodities: dict, search_query: str = ""):
    st.markdown('<div class="sec-header">Market Overview</div>', unsafe_allow_html=True)

    now_utc = datetime.now(timezone.utc).strftime("%H:%M UTC")
    n_live = sum(1 for v in commodities.values() if v.get("is_live"))
    st.markdown(
        f'<p style="color:#8BA0B0;font-size:0.82rem;margin-bottom:1rem;">'
        f'Price forecasts across all tracked commodities (horizon varies by source -- '
        f'see each item for its exact forecast window). '
        f'<span style="color:#21C55D;font-weight:600;">{n_live} live prices</span> '
        f'(exchange-delayed ~15 min) &nbsp;·&nbsp; refreshed at {now_utc}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#4A6A80;font-size:0.75rem;margin-top:-0.5rem;margin-bottom:1rem;">'
        'Forecasts are statistical extrapolations of historical price patterns -- they have no '
        'real-time awareness of breaking news, geopolitical events, or supply shocks, so during '
        'an active event a forecast can run counter to what current news coverage suggests. Items '
        'with an unusually large recent move are called out explicitly below.</p>',
        unsafe_allow_html=True,
    )

    # ── Controls ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        q = st.text_input("Filter", value=search_query, placeholder="Search by name...",
                          label_visibility="collapsed")
    with c2:
        sort_by = st.selectbox("Sort", ["Risk (High → Low)", "Name A–Z", "Change %", "Current Price"],
                               label_visibility="collapsed")
    with c3:
        sig_filter = st.selectbox("Signal", ["All", "RED", "YELLOW", "GREEN"],
                                  label_visibility="collapsed")

    # ── Summary counts ─────────────────────────────────────────────────────────
    n_red    = sum(1 for v in commodities.values() if v["signal"]=="RED")
    n_yellow = sum(1 for v in commodities.values() if v["signal"]=="YELLOW")
    n_green  = sum(1 for v in commodities.values() if v["signal"]=="GREEN")

    s1, s2, s3 = st.columns(3)
    for col, label, count, color in [
        (s1,"High Risk",  n_red,    "#FF4B4B"),
        (s2,"Watch",      n_yellow, "#F0B429"),
        (s3,"Stable",     n_green,  "#21C55D"),
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

    if sort_by == "Risk (High → Low)":
        rows.sort(key=lambda r: (r["_sig_rank"], -abs(r["Change"])))
    elif sort_by == "Name A–Z":
        rows.sort(key=lambda r: r["Commodity"])
    elif sort_by == "Change %":
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
            tip   = f"Est. from data as of {as_of}" if as_of else "Lag-compensated estimate"
            price_badge = f'<span style="background:#4A6A80;color:#fff;font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;vertical-align:middle;margin-left:6px;" title="{tip}">~est.</span>'
        else:
            price_badge = ""

        vol_suffix = "  ⚠ Volatile" if r["_volatility_flag"] else ""
        with st.expander(f"{r['Commodity']}  ·  {pct_str}  ·  {sig}{vol_suffix}"):
            st.markdown(price_badge, unsafe_allow_html=True)
            if r["_contract"]:
                ticker_note = f"Source: {r['_contract']} (via {r['_ticker']})"
            elif r["_ticker"]:
                ticker_note = f"Source: {r['_ticker']}"
            else:
                ticker_note = "Source: FRED/USDA"
            st.caption(f"{ticker_note}  ·  as of {r['_price_as_of'] or 'unknown'}")

            if r["_price_rejected"]:
                st.markdown("""
                <div class="sig-card sig-card-red" style="padding:0.65rem 1rem;margin-bottom:0.75rem;">
                    <span style="font-size:0.85rem;color:#FFFFFF;font-weight:600;">⚠ Live price unavailable</span><br>
                    <span style="font-size:0.8rem;color:#8BA0B0;">
                        The live feed returned a price outside this commodity's plausible range, so it
                        was rejected rather than shown. Displaying the last known-good estimate instead.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            if r["_volatility_flag"]:
                move = r["_recent_move_pct"]
                move_str = f"{move*100:+.1f}%" if move is not None else "an unusual amount"
                if r["_sector_flag"]:
                    reason = ("The whole energy complex is moving the same direction at once -- "
                              "individually that's not always extreme for any one of these commodities, "
                              "but several ordinarily-volatile series leaning the same way together "
                              "usually means a shared event (e.g. a supply shock), not routine noise.")
                else:
                    reason = ("a statistical outlier vs. its own price history.")
                st.markdown(f"""
                <div class="sig-card sig-card-yellow" style="padding:0.65rem 1rem;margin-bottom:0.75rem;border-left:4px solid #F0B429;">
                    <span style="font-size:0.85rem;color:#FFFFFF;font-weight:600;">⚠ Unusual recent price move</span><br>
                    <span style="font-size:0.8rem;color:#8BA0B0;">
                        {r['Commodity']} moved {move_str} over the last {r['_horizon']} {r['_horizon_unit']} --
                        {reason} The forecast below is a pure extrapolation of historical patterns and has
                        no real-time awareness of news or events, so treat it with extra caution while this holds.
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
            forecast_label = f"{horizon} {horizon_word} Forecast"
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"Current Price ({unit_label})" if unit_label else "Current Price",
                      _fmt(r['Price']))
            m2.metric(f"{forecast_label} ({unit_label})" if unit_label else forecast_label,
                      _fmt(r['Forecast']))
            m3.metric("Change",         pct_str)
            # Backtest-backed reliability instead of the old "Confidence 90%",
            # which was a cosmetic transform of error (0.95 - error/2), not a
            # probability -- and read 80-92% even for models that couldn't
            # beat a simple "no change" forecast.
            err = r["_rmse_pct"]
            m4.metric("Typical error", f"±{err*100:.0f}%" if err is not None else "n/a",
                      help="Average size of this model's miss in backtesting, as % of price.")

            skill = ("Beats a no-change forecast in backtesting" if r["_beats_naive"]
                     else "Has not beaten a no-change forecast in backtesting -- treat as a watch signal only")
            rng = (f"Likely range: {_fmt(r['_lo'])} – {_fmt(r['_hi'])}  ·  "
                   if r["_lo"] is not None and r["_hi"] is not None else "")
            st.caption(f"{rng}{skill}")

            st.markdown(f"""
            <div class="sig-card {css}" style="padding:0.65rem 1rem;margin-top:0.5rem;">
                <span style="font-size:0.85rem;color:#FFFFFF;">{r['_message']}</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"View chart", key=f"chart_{r['Commodity']}", type="primary"):
                st.session_state.page = "Commodities"
                st.session_state.selected_commodity = r["Commodity"]
                st.rerun()
