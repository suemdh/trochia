"""Trochia -- Legal page: Terms of Service and Privacy Policy.

Written to match what the app actually does (what auth.py stores, Stripe-hosted
checkout, cancel-at-period-end). When either text changes, bump
auth.TERMS_VERSION so new sign-ups record which version they agreed to.
"""
import streamlit as st

CONTACT = "trochia.connect@gmail.com"
UPDATED = "November 6, 2026"

TERMS = f"""
*Last updated: {UPDATED}*

These Terms of Service ("Terms") govern your use of Trochia ("Trochia", "we", "us"),
including the website at trochia-app.streamlit.app (the "Service"). By creating an
account or using the Service, you agree to these Terms.

#### 1. Who can use Trochia
You must be at least 18 and able to enter a binding agreement. If you use Trochia for a
business, you confirm you're authorized to accept these Terms for it. Keep your login
details private -- you're responsible for activity on your account.

#### 2. Forecasts are information, not advice
Trochia shows commodity prices and statistical forecasts of where they may go. Please
understand what they are:
- **Forecasts are estimates and can be wrong.** They are built from historical price
  patterns and cannot anticipate breaking news, weather, wars, or supply shocks.
- **Prices shown may not be your prices.** Futures and national-average retail prices
  differ from what your supplier charges, which includes local basis, freight, and markup.
- **Data comes from third parties** (including FRED/BLS, USDA, Yahoo Finance, and Alpha
  Vantage) and may be delayed, incomplete, or occasionally wrong.

Nothing on Trochia is financial, investment, legal, or purchasing advice. You are solely
responsible for your business and purchasing decisions.

#### 3. Free trial and subscriptions
- New accounts get a **14-day free trial**; no card is required to start it.
- Paid plans are billed **monthly in advance** through our payment processor, Stripe, at
  the price shown when you subscribe, and **renew automatically** until cancelled.
- **You can cancel anytime** from the Billing page. Cancellation takes effect at the end
  of your current billing period, and you keep access until then. Payments already made
  are **not refunded for partial periods**, except where the law requires it.
- If a renewal payment fails, we may suspend paid features until it's resolved.
- We may change prices with at least 30 days' notice; changes apply from your next
  billing period after the notice.

#### 4. Acceptable use
You agree not to: resell, redistribute, or publicly republish Trochia's data or forecasts;
scrape the Service or access it by automated means; attempt to break or bypass its
security; reverse engineer it; or use it for anything unlawful.

#### 5. Ownership
The Service, its software, and its forecasts belong to Trochia. Underlying market data
belongs to its providers and is subject to their terms. You may use what you see on
Trochia for your own internal business decisions.

#### 6. Ending your account
You can stop using Trochia at any time, and ask us to delete your account by emailing
{CONTACT}. We may suspend or close accounts that violate these Terms.

#### 7. No warranties
The Service is provided **"as is" and "as available."** To the fullest extent the law
allows, we make no warranties of any kind, including accuracy, fitness for a particular
purpose, or uninterrupted availability.

#### 8. Limitation of liability
To the fullest extent the law allows, Trochia will not be liable for any indirect,
incidental, special, or consequential damages, or for lost profits or losses from
purchasing decisions, arising from your use of the Service. Our total liability for any
claim is limited to the amount you paid us in the 12 months before the claim.

#### 9. Governing law
These Terms are governed by the laws of the State of Florida, USA, without regard to
conflict-of-law rules. Any dispute will be handled in the state or federal courts
located in Florida.

#### 10. Changes to these Terms
We may update these Terms. We'll change the "Last updated" date above, and for material
changes we'll make reasonable efforts to notify account holders. Continuing to use the
Service after changes take effect means you accept them.

#### 11. Contact
Questions: **{CONTACT}**
"""

PRIVACY = f"""
*Last updated: {UPDATED}*

This Privacy Policy explains what Trochia ("we") collects, why, and your choices.
Contact: **{CONTACT}**.

#### What we collect
- **Account details:** your name and email address, and your password -- stored only as
  a salted, one-way hash, never in readable form.
- **Preferences:** which commodities you choose to track.
- **Subscription details:** your plan and its status, renewal date, the last 4 digits of
  your card, and the IDs Stripe uses to identify your customer record and subscription.
  **Your full card details are entered on Stripe's own page and never reach us.**
- **Password resets:** if you request one, a temporary, hashed reset code that expires in
  30 minutes.
- **Technical data:** our hosting providers keep standard server logs (such as IP address
  and browser type) to run and secure the site.

#### How we use it
To run your account and the Service, process payments, send password-reset and other
account emails, keep the Service secure, and answer your questions. **We do not sell
your personal information, and we do not use it for advertising.**

#### Who we share it with
Only the service providers needed to run Trochia, each handling data on our behalf:
- **Stripe** -- payment processing
- **Supabase** -- database hosting (where account details are stored)
- **Streamlit** -- website hosting
- **Google** -- sending account emails (Gmail)

We may also disclose information when required by law or to protect our rights.

#### Cookies
The site uses only what's needed to work -- for example, keeping you signed in during a
session. We don't use advertising or cross-site tracking cookies.

#### How long we keep it
While your account is open. If you ask us to delete your account, we'll delete your
personal information within 30 days, except records we must keep for tax, accounting,
or legal reasons (payment records are also kept by Stripe under its own policies).

#### Your choices
You can ask to see, correct, or delete your personal information by emailing
**{CONTACT}**.

#### Security
Passwords are stored as salted hashes, connections are encrypted, and payments are
handled entirely by Stripe. No system is perfectly secure, but we work to protect your
information.

#### Children
Trochia is a business service for adults and is not directed to anyone under 18.

#### Changes
If we update this policy, we'll change the "Last updated" date above, and for material
changes we'll make reasonable efforts to notify account holders.
"""


def render():
    st.markdown('<div class="sec-header">Legal</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Terms of Service", "Privacy Policy"])
    with t1:
        st.markdown(TERMS)
    with t2:
        st.markdown(PRIVACY)
