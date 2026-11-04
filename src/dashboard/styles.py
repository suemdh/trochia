"""Trochiá dark theme CSS and brand constants."""

C_BG       = "#0B1929"   # app background
C_PANEL    = "#112233"   # card / panel background
C_SIDEBAR  = "#071420"   # sidebar background
C_NAVY     = "#003B5C"   # brand primary
C_TEAL     = "#005B5C"   # brand secondary
C_BLUE     = "#007A8E"   # brand accent / buttons
C_MINT     = "#A8DBB9"   # brand light accent
C_ICE      = "#E0F7FA"   # brand lightest
C_WHITE    = "#FFFFFF"
C_TEXT     = "#FFFFFF"
C_MUTED    = "#8BA0B0"
C_RED      = "#FF4B4B"
C_YELLOW   = "#F0B429"
C_GREEN    = "#21C55D"

DARK_CSS = """
<style>
/* ── Global dark background ───────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #0B1929 !important;
    color: #FFFFFF !important;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    background-color: #071420 !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: #1E3A5F !important; }

/* ── Sidebar nav buttons (replaces radio widget entirely) ─────── */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: transparent !important;
    color: #8BA0B0 !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 6px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 400 !important;
    font-size: 0.875rem !important;
    padding: 0.48rem 0.85rem !important;
    margin-bottom: 1px !important;
    box-shadow: none !important;
    outline: none !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button div,
[data-testid="stSidebar"] [data-testid="stButton"] button span,
[data-testid="stSidebar"] [data-testid="stButton"] button p {
    justify-content: flex-start !important;
    text-align: left !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: #0D2035 !important;
    color: #FFFFFF !important;
    border-left-color: #1E3A5F !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:focus,
[data-testid="stSidebar"] [data-testid="stButton"] button:active,
[data-testid="stSidebar"] [data-testid="stButton"] button:focus-visible {
    box-shadow: none !important;
    outline: none !important;
}

/* ── Radio nav: hide dots, style as clean pill rows ──────────── */
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 0 !important; }

/* Hide the circle: targets the first div inside label[data-baseweb="radio"]
   which is the BaseWeb radio indicator (confirmed via DOM inspection) */
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] input[type="radio"] {
    display: none !important;
}

[data-testid="stSidebar"] label[data-baseweb="radio"] {
    display: flex !important;
    align-items: center !important;
    padding: 0.48rem 0.85rem !important;
    border-radius: 6px !important;
    border-left: 3px solid transparent !important;
    cursor: pointer !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    color: #8BA0B0 !important;
    transition: background .15s, color .15s, border-color .15s !important;
    margin-bottom: 1px !important;
    width: 100% !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    background: #0D2035 !important;
    color: #FFFFFF !important;
    border-left-color: #1E3A5F !important;
}
/* Selected state — BaseWeb adds aria-checked="true" to the input,
   and marks the label with a checked class; target both */
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
    background: #0D2035 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-left-color: #007A8E !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] p {
    color: inherit !important;
    font-size: inherit !important;
    font-weight: inherit !important;
    margin: 0 !important;
}

/* ── Headings ─────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
p, span, label, div { color: #FFFFFF; }

/* ── Metrics ──────────────────────────────────────────────────── */
[data-testid="stMetricValue"]       { color: #FFFFFF !important; font-size: 1.6rem !important; }
[data-testid="stMetricLabel"]       { color: #8BA0B0 !important; font-size: 0.8rem !important; }
[data-testid="stMetricDelta"]       { color: #A8DBB9 !important; }
[data-testid="metric-container"]    { background: #112233; border-radius: 8px; padding: 1rem !important; }

/* ── Buttons ──────────────────────────────────────────────────── */
button[kind="primary"] {
    background: #007A8E !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
}
button[kind="primary"]:hover { background: #005B5C !important; }
button[kind="secondary"] {
    background: transparent !important;
    color: #A8DBB9 !important;
    border: 1px solid #1E3A5F !important;
    border-radius: 6px !important;
}
button[kind="secondary"]:hover { border-color: #007A8E !important; color: white !important; }

/* ── Inputs / text boxes ──────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select,
textarea {
    background: #112233 !important;
    color: #FFFFFF !important;
    border: 1px solid #1E3A5F !important;
    border-radius: 6px !important;
}
[data-testid="stTextInput"] input::placeholder { color: #8BA0B0 !important; }

/* ── Selectbox ────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #112233 !important;
    color: white !important;
    border: 1px solid #1E3A5F !important;
}

/* ── Dataframe / table ────────────────────────────────────────── */
[data-testid="stDataFrame"] { background: #112233 !important; border-radius: 8px; }
[data-testid="stDataFrame"] * { color: #FFFFFF !important; }

/* ── Expanders ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #112233 !important;
    border: 1px solid #1E3A5F !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: #FFFFFF !important; }

/* ── Tabs ─────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-testid="stTab"] {
    background: transparent !important;
    color: #8BA0B0 !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: #A8DBB9 !important;
    border-bottom: 2px solid #007A8E !important;
}

/* ── Chat messages ────────────────────────────────────────────── */
[data-testid="stChatMessage"] { background: #112233 !important; border-radius: 8px !important; }

/* ── Info / warning / error boxes ────────────────────────────── */
[data-testid="stAlert"] { background: #112233 !important; border-radius: 8px !important; }

/* ── Plotly chart background ──────────────────────────────────── */
.js-plotly-plot .plotly { background: #0B1929 !important; }

/* ── Signal card component ────────────────────────────────────── */
.sig-card {
    background: #112233;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.sig-card-red    { border-left: 4px solid #FF4B4B; }
.sig-card-yellow { border-left: 4px solid #F0B429; }
.sig-card-green  { border-left: 4px solid #21C55D; }
.sig-card-blue   { border-left: 4px solid #007A8E; }

/* Signal badge pills */
.badge-red    { background:#FF4B4B; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.badge-yellow { background:#F0B429; color:#000; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.badge-green  { background:#21C55D; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }

/* Section header */
.sec-header {
    color: #FFFFFF;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #1E3A5F;
    padding-bottom: 0.4rem;
    margin: 1.25rem 0 0.75rem;
    text-transform: uppercase;
}

/* Divider */
.dark-divider { border: none; border-top: 1px solid #1E3A5F; margin: 1.5rem 0; }

/* Pricing card */
.price-card {
    background: #112233;
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
}
.price-card-featured {
    background: #0D2035;
    border: 2px solid #007A8E;
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
}
.price-amount { font-size: 2.2rem; font-weight: 700; color: #FFFFFF; }
.price-period { font-size: 0.85rem; color: #8BA0B0; }
.price-feature { font-size: 0.85rem; color: #FFFFFF; padding: 0.25rem 0; border-bottom: 1px solid #1E3A5F; }
.price-check { color: #21C55D; font-weight: 700; margin-right: 0.4rem; }
.price-x     { color: #3A5070; margin-right: 0.4rem; }

/* Footer */
.trochia-footer {
    background: #071420;
    border-top: 1px solid #1E3A5F;
    padding: 1.5rem 2rem;
    border-radius: 8px;
    margin-top: 3rem;
    text-align: center;
    font-size: 0.82rem;
    color: #8BA0B0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #071420; }
::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 3px; }
</style>
"""
