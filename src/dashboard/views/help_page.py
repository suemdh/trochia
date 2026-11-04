"""Trochiá - Help & Onboarding page."""
import os, sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from commodity_maps import (
    TOTAL_COMMODITIES, FRED_COMMODITY_MAP, USDA_COMMODITY_MAP, YFINANCE_COMMODITY_MAP,
)


def render():
    st.markdown('<div class="sec-header">Help Center</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8BA0B0;font-size:0.9rem;">Learn how to get the most out of Trochiá - from reading signals to managing your subscription.</p>',
                unsafe_allow_html=True)

    tabs = st.tabs([
        "Getting Started",
        "Reading Signals",
        "Price Charts",
        "Scenario Calculator",
        "AI Chat",
        "Billing & Trial",
        "Data Sources",
    ])

    with tabs[0]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">Welcome to Trochiá</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                Trochiá is a commodity price intelligence platform built for small business owners -
                restaurants, bakeries, food distributors, and anyone who buys food or energy inputs regularly.
                It tracks 40+ commodities and uses machine learning to forecast whether prices will
                rise or fall over each item's forecast horizon (shown on its detail page -- weeks for
                exchange-traded futures, months for grocery items sourced from government data),
                giving you time to act before a spike hits your margins.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Navigation")
        st.markdown(f"""
        Use the **sidebar on the left** to move between pages.

        | Page | What it does |
        |---|---|
        | **Home** | Overview snapshot - top signals and feature summary |
        | **Market** | All {TOTAL_COMMODITIES} commodities with signals and expandable details |
        | **Commodities** | Deep-dive on one commodity - chart, metrics, calculator |
        | **AI Chat** | Ask any question about the data or the platform |
        | **Pricing** | View and compare subscription plans |
        | **Billing** | Manage your subscription, trial, and payment |
        | **Profile** | Sign in, register, and manage your profile |
        """)

        st.markdown("#### Your first 3 minutes")
        for n, step in enumerate([
            "**Open Market** - scan the signal list. RED = act now, YELLOW = watch, GREEN = stable.",
            "**Click any commodity** to expand it - see current price, forecast, and what to do.",
            "**Click 'View chart'** to open the full price history with the forecast line.",
            "**Try the Scenario Calculator** - enter your weekly usage and see how much pre-buying saves.",
            "**Ask AI Chat** anything you don't understand - it's there to help in plain English.",
        ], 1):
            st.markdown(f"**Step {n}.** {step}")

    with tabs[1]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">What the signals mean</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                Every commodity gets a RED, YELLOW, or GREEN signal based on its price
                forecast from our ML models, over that commodity's own forecast horizon
                (weeks for exchange-traded futures, months for grocery items sourced from
                government data). Signals update whenever new data arrives.
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
            <div class="sig-card sig-card-red">
                <div style="font-size:0.92rem;font-weight:700;color:#FF4B4B;margin-bottom:0.4rem;">RED - Buy Now</div>
                <div style="font-size:0.8rem;color:#8BA0B0;line-height:1.6;">
                    Forecast increase of 10%+ that is also larger than 1.5x this model's own
                    typical backtest error, from a model that has beaten a "no change"
                    forecast in backtesting.<br><br>
                    <strong style="color:#FFFFFF;">Do:</strong> Pre-purchase inventory, lock in
                    supplier contracts, or hedge cost exposure before the spike arrives.
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="sig-card sig-card-yellow">
                <div style="font-size:0.92rem;font-weight:700;color:#F0B429;margin-bottom:0.4rem;">YELLOW - Watch</div>
                <div style="font-size:0.8rem;color:#8BA0B0;line-height:1.6;">
                    Forecast increase of 5%+ that doesn't meet the RED bar -- including any
                    increase from a model that hasn't beaten a "no change" forecast.<br><br>
                    <strong style="color:#FFFFFF;">Do:</strong> Monitor daily. Consider partial
                    pre-purchasing to reduce risk without overcommitting.
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown("""
            <div class="sig-card sig-card-green">
                <div style="font-size:0.92rem;font-weight:700;color:#21C55D;margin-bottom:0.4rem;">GREEN - Stable</div>
                <div style="font-size:0.8rem;color:#8BA0B0;line-height:1.6;">
                    Forecast increase under 5%, or a forecast that prices will fall.<br><br>
                    <strong style="color:#FFFFFF;">Do:</strong> No urgent action needed.
                    Buy at your normal pace and revisit next week.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### Methodology, reliability, and limitations")
        st.markdown("""
        **Models.** Trochiá runs three forecasting models on each commodity and blends them:
        **SARIMA** (seasonal/trend statistics), **LSTM** (neural network on price history,
        plus food-inflation and interest-rate indicators for grocery items), and a
        **linear trend** baseline. Each is weighted by its backtest accuracy.

        **Backtesting.** Each model is scored walk-forward on 3 historical windows it never
        saw during fitting. Two numbers come out of that, shown on every card:
        - **Typical error** -- the model's average miss, as a % of price.
        - **Beats a no-change forecast?** -- whether the model did better than simply
          assuming today's price holds. Models that don't are capped at a YELLOW watch
          signal and can never trigger a RED buy alert.

        **Track record.** Every forecast is logged when it's made and scored against the
        real price once it comes due, so accuracy will be shown from real outcomes, not
        just backtests, as that history builds up.

        **Data and updates.** Futures (oil, grains, metals, livestock): Yahoo Finance,
        ~15 min exchange delay. Grocery retail prices: FRED/BLS, published monthly with a
        ~4-8 week lag (shown as "~est."). Cash wheat and cream: USDA AMS, ~1-2 week lag.
        Forecasts are retrained weekly. Horizon: 8 steps of each source's own reporting
        interval -- 8 weeks for weekly data (futures, fuel), 8 months for monthly grocery
        data, 8 days for daily USDA cash wheat. Each card states its horizon.

        **Limitations.** Forecasts extrapolate historical patterns only -- they can't see
        breaking news, wars, weather events, or slow structural shifts (like a shrinking
        cattle herd). Unusual recent moves are flagged, but treat every forecast as one
        input, not a decision.

        **Disclaimer.** Informational only, not financial advice. Futures and
        national-average retail prices are not what your supplier will charge you -- your
        delivered cost includes local basis, freight, and markup.
        """)

    with tabs[2]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">Reading the price chart</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                The Commodities page shows a full interactive chart for any commodity.
                It combines real historical prices with the ML forecast for that
                commodity's own horizon.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### Chart elements

        | Element | What it means |
        |---|---|
        | **Teal solid line** | Historical price data - real prices from FRED, USDA, or Yahoo Finance |
        | **Dashed colored line** | Forecast - model-predicted future prices over that commodity's horizon |
        | **Shaded band around forecast** | Likely range - based on the model's own backtest error, not a guaranteed bound |
        | **Color of dashed line** | Matches signal: red = RED, amber = YELLOW, green = GREEN |

        #### Interacting with the chart
        - **Hover** over any point to see the exact price and date
        - **Click and drag** to zoom into a specific time range
        - **Double-click** to zoom back out to full view
        - **Click legend items** to show or hide individual lines

        #### About the data lag
        FRED retail price data is published with a **4–6 week lag** - the most recent point
        on the chart may be from 4–6 weeks ago, not today. Yahoo Finance futures prices are
        exchange-delayed **~15 minutes**. The forecast extends from the most recent available
        data point across a horizon that depends on the commodity's own data frequency -
        weeks for exchange-traded futures, months for grocery items sourced from government data.
        """)

    with tabs[3]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">Scenario Calculator</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                The Scenario Calculator answers one practical question:
                <em>How much money would I save by buying ahead right now, before the forecasted price increase?</em>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### Step-by-step

        1. Go to **Commodities** and select the commodity you want to analyze
        2. Scroll down to the **Scenario Calculator** section
        3. Enter your **weekly usage** in the unit shown (lbs, gallons, MT, etc.)
        4. Set **how many weeks ahead** you want to pre-buy (1–26 weeks)
        5. Read the three output metrics:

        | Output | Meaning |
        |---|---|
        | **Buy now total** | Cost to purchase your supply today at the current price |
        | **Projected later** | Estimated cost if you wait until after the forecasted price increase |
        | **Potential savings** | The dollar difference - your maximum cost avoidance |

        #### Real example
        > **Ground Beef - RED signal (+12% forecast)**
        > You use 500 lbs/week and want to pre-buy 6 weeks of supply.
        >
        > - Buy now: 3,000 lbs × $6.74 = **$20,220**
        > - Wait until after spike: 3,000 lbs × ~$7.55 = **$22,650**
        > - **Potential savings: $2,430**

        #### Important caveats
        - Forecasts are estimates, not guarantees - actual prices may differ
        - Factor in storage costs, shelf life, and cash flow before committing
        - The calculator works best as a directional guide when combined with a RED or YELLOW signal
        """)

    with tabs[4]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">AI Chat Assistant</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                The AI Chat lets you ask questions in plain English - about the platform, your commodity data,
                or general market context. No technical knowledge required.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        #### What you can ask

        **About signals:**
        - "Why is coffee showing a RED signal?"
        - "What does 'typical error' mean?"
        - "Is beef price usually seasonal?"

        **About the platform:**
        - "How do I use the Scenario Calculator?"
        - "How often are prices updated?"
        - "What's the difference between Starter and Pro?"

        **About your business situation:**
        - "I run a bakery - which commodities matter most to me?"
        - "Should I pre-buy diesel for my delivery trucks?"
        - "How far ahead can I trust the forecast?"

        #### FAQ mode vs full AI mode
        - **FAQ mode** (default): Answers from a curated library of common questions. Fast, accurate for standard questions.
        - **Full AI mode**: Activated by adding `ANTHROPIC_API_KEY` to your `.env` file.
          Powered by Claude - handles any question with context and nuance.

        #### Tips
        - Click the **suggested question buttons** on the chat page for instant answers
        - Be specific - "Why is wheat YELLOW?" gets a better answer than "Why?"
        - You can reference specific commodities by name
        """)

    with tabs[5]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">Free Trial & Billing</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                Every Trochiá account starts with a 14-day free trial with full Pro features.
                No credit card required to start.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        #### Your 14-day free trial
        - Starts the moment you create your account - no credit card needed
        - Full access to all {TOTAL_COMMODITIES} commodities, daily updates, AI Chat, charts, and the Scenario Calculator
        - At day 14, access pauses until you pick a plan - your account and history are saved

        #### Choosing a plan

        | Plan | Price | Best for |
        |---|---|---|
        | **Starter** | $19/mo | Individual buyers, 5 commodities, weekly updates |
        | **Pro** | $49/mo | All {TOTAL_COMMODITIES} commodities, daily updates, AI Chat, charts |
        | **Business** | $99/mo | Teams, API access, up to 10 seats, dedicated support |

        #### Subscribing
        Go to the **Billing page** in the sidebar. Enter your card number, expiry, and CVC.
        You'll see your next billing date and can change or cancel at any time.

        #### Cancelling
        Cancel anytime from the Billing page. Access continues until the end of your current
        billing period - you will not be charged again.

        #### Questions
        Use AI Chat for billing questions or email support@trochia.com.
        """)
        _, c, _ = st.columns([1,1,1])
        with c:
            if st.button("Go to Billing", use_container_width=True, type="primary"):
                st.session_state.page = "Billing"; st.rerun()

    with tabs[6]:
        st.markdown("""
        <div class="sig-card sig-card-blue" style="margin-bottom:1rem;">
            <div style="font-size:1rem;font-weight:700;color:#FFFFFF;margin-bottom:0.5rem;">Data sources</div>
            <div style="font-size:0.88rem;color:#8BA0B0;line-height:1.7;">
                Trochiá pulls from three live data sources that actually feed the forecasts you see.
                All data is from free-tier APIs - no cost to you. Each has a different update
                frequency and lag.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        #### FRED / Bureau of Labor Statistics
        **Commodities ({len(FRED_COMMODITY_MAP)}):** {", ".join(FRED_COMMODITY_MAP.keys())}

        The Federal Reserve Economic Data (FRED) system publishes retail price surveys from the BLS.
        These are average U.S. retail prices - real consumer prices, not futures or wholesale.
        **Lag: 4–6 weeks.** Data is collected monthly and published with a delay.

        #### USDA AMS Market News
        **Commodities ({len(USDA_COMMODITY_MAP)}):** {", ".join(USDA_COMMODITY_MAP.keys())}

        Cash bids and wholesale dairy prices reported directly by USDA market reporters,
        filtered to one consistent grade/class per commodity. **Lag: same day to a few days.**

        #### Yahoo Finance (yfinance)
        **Commodities ({len(YFINANCE_COMMODITY_MAP)}):** {", ".join(YFINANCE_COMMODITY_MAP.keys())}

        Exchange-traded futures prices - grains, energy, metals, and softs. No API key required.
        **Lag: ~15 minutes** (standard exchange delay).

        #### Refreshing data
        To pull the latest data and retrain forecasts, run this from the project root:
        ```
        python main.py
        python src/models/train_pipeline.py
        ```
        The sidebar shows "Live forecasts" when fresh data is loaded, or "Demo data" if not.
        """)
