"""
Single source of truth for which commodities are tracked and where their raw
data lives on disk.

Shared by train_pipeline.py (which trains forecasts from this data) and the
dashboard's commodities.py (which charts history from this data), so the two
can never silently drift apart again. They used to: the dashboard kept its
own hand-maintained copy of this mapping, which fell out of sync as
commodities were added -- by the time it was audited, ~34 of 44 tracked
commodities had no chart mapping at all and were silently rendering
fabricated random-walk "history" next to real current/forecast numbers.

Keep this module free of heavy imports (torch, statsmodels, sklearn, ...) --
the dashboard imports it directly and should not pay for the training stack
just to know which CSV holds a commodity's history.
"""

# Display name -> (fred_data.csv column, unit)
FRED_COMMODITY_MAP = {
    "Ground Beef":      ("ground_beef_price", "$/lb"),
    "Chicken":          ("chicken_price",     "$/lb"),
    "Pork / Bacon":     ("bacon_price",       "$/lb"),
    "Pork Chops":       ("pork_chops",        "$/lb"),
    "Ham":              ("ham",               "$/lb"),
    "Eggs":             ("eggs_price",        "$/dozen"),
    "Butter":           ("butter_price",      "$/lb"),
    "Milk":             ("milk_price",        "$/gal"),
    "Cheese":           ("cheese_price",      "$/lb"),
    "White Bread":      ("bread_price",       "$/lb"),
    "Flour":            ("flour_price",       "$/bag"),
    "Sugar (Retail)":   ("sugar_retail",      "$/lb"),
    "Coffee (Retail)":  ("coffee_retail",     "$/lb"),
    "Bananas":          ("bananas",           "$/lb"),
    "Potatoes":         ("potatoes",          "$/lb"),
    "Tomatoes":         ("tomatoes",          "$/lb"),
    "Oranges":          ("oranges",           "$/lb"),
    "Diesel / Freight": ("diesel_price",      "$/gal"),
    "Gasoline":         ("gasoline_retail",   "$/gal"),
    # NOTE: Tuna (Canned), Apples, and Peanut Butter were removed from this
    # map -- all three are real FRED/BLS series, but BLS discontinued all
    # three in 2017 (see fetch_fred.py's SERIES_IDS, which still fetches them
    # for the record) and there's no live data to forecast from. Tuna/Apples
    # fail the fixed "not enough data" row-count check; Peanut Butter had
    # just enough historical rows (48) to clear that bar but was getting
    # caught by lag_compensator's staleness check instead (~460 weeks lag --
    # see MAX_REASONABLE_LAG_WEEKS) and producing a confident-looking RED
    # signal off a 2017 price. Keeping dead entries here just meant every
    # count of "commodities we track" had to remember to subtract 3.
}

# Display name -> (usda_<key>.csv suffix, unit)
USDA_COMMODITY_MAP = {
    "Wheat (USDA Cash)": ("wheat", "$/bushel"),
    "Cream (USDA)":      ("cream", "$/lb"),
}

# Display name -> (yfinance ticker, unit)
YFINANCE_COMMODITY_MAP = {
    "Crude Oil (Brent)":  ("BZ=F", "$/barrel"),
    "Crude Oil (WTI)":    ("CL=F", "$/barrel"),
    "Natural Gas":        ("NG=F", "$/MMBtu"),
    "Gasoline (RBOB)":    ("RB=F", "$/gal"),
    "Heating Oil":        ("HO=F", "$/gal"),
    "Wheat":              ("ZW=F", "$/bushel"),
    "Corn":               ("ZC=F", "$/bushel"),
    "Soybeans":           ("ZS=F", "$/bushel"),
    "Soybean Oil":        ("ZL=F", "$/lb"),
    "Oats":               ("ZO=F", "$/bushel"),
    "Rough Rice":         ("ZR=F", "$/cwt"),
    "Coffee (Arabica)":   ("KC=F", "$/lb"),
    "Cocoa":              ("CC=F", "$/metric ton"),
    "Sugar (11)":         ("SB=F", "$/lb"),
    "Cotton":             ("CT=F", "$/lb"),
    "Orange Juice":       ("OJ=F", "$/lb"),
    "Live Cattle":        ("LE=F", "$/lb"),
    "Lean Hogs":          ("HE=F", "$/lb"),
    "Feeder Cattle":      ("GF=F", "$/lb"),
    "Copper":             ("HG=F", "$/lb"),
    "Gold":               ("GC=F", "$/troy oz"),
    "Silver":             ("SI=F", "$/troy oz"),
}


TOTAL_COMMODITIES = len(FRED_COMMODITY_MAP) + len(USDA_COMMODITY_MAP) + len(YFINANCE_COMMODITY_MAP)


def yfinance_safe_name(name: str) -> str:
    """Match the exact filename-sanitizing rule fetch_yfinance.py uses when
    saving history, so lookups always agree on the filename."""
    return name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")


def strip_unit(unit: str) -> str:
    """'$/lb' -> 'lb', '$/troy oz' -> 'troy oz'. The one place this string
    cleanup happens -- used to live duplicated (and once, buggily skipped
    entirely) in market.py and decision/engine.py separately."""
    return (unit or "").replace("$/", "").replace("per ", "").strip() or "unit"


# Display name -> (plausible_min, plausible_max), same unit as the maps above.
# Computed once from each commodity's own full historical range (0.5x the
# observed min to 2x the observed max) -- wide enough to span a realistic
# multi-year price cycle without flagging ordinary volatility, tight enough
# to still catch an order-of-magnitude error: wrong unit, wrong contract,
# cents-vs-dollars, or a stale/bad tick from the data source. Regenerate by
# rerunning the derivation in scripts/compute_plausible_ranges.py if a
# commodity's real range permanently shifts (e.g. after a multi-year rally).
PLAUSIBLE_RANGE = {
    "Ground Beef": (1.7335, 13.846),
    "Chicken": (0.681, 4.172),
    "Pork / Bacon": (2.47, 15.216),
    "Pork Chops": (1.593, 8.904),
    "Ham": (1.862, 11.796),
    "Eggs": (0.6015, 12.454),
    "Butter": (1.6625, 10.008),
    "Milk": (1.4195, 8.634),
    "Cheese": (2.374, 12.266),
    "White Bread": (0.6305, 4.066),
    "Flour": (0.178, 1.15),
    "Sugar (Retail)": (0.2865, 2.108),
    "Coffee (Retail)": (2.0265, 19.446),
    "Bananas": (0.272, 1.34),
    "Potatoes": (0.3165, 2.188),
    "Tomatoes": (0.772, 5.378),
    "Oranges": (0.559, 3.61),
    "Diesel / Freight": (0.99, 13.058),
    "Gasoline": (0.819, 9.688),
    "Wheat (USDA Cash)": (2.58, 31.44),
    "Cream (USDA)": (0.6375, 9.001),
    "Crude Oil (Brent)": (10.72, 244.02),
    "Crude Oil (WTI)": (8.47, 241.34),
    "Natural Gas": (0.7475, 18.672),
    "Gasoline (RBOB)": (0.2869, 8.5044),
    "Heating Oil": (0.3234, 10.1156),
    "Wheat": (1.9375, 26.96),
    "Corn": (1.5388, 16.365),
    "Soybeans": (3.985, 34.91),
    "Soybean Oil": (0.1252, 1.7834),
    "Oats": (0.8912, 15.89),
    "Rough Rice": (4.565, 41.13),
    "Coffee (Arabica)": (0.4367, 8.395),
    "Cocoa": (904.5, 23908.0),
    "Sugar (11)": (0.0486, 0.5554),
    "Cotton": (0.2549, 3.0466),
    "Orange Juice": (0.4678, 11.11),
    "Live Cattle": (0.4249, 5.149),
    "Lean Hogs": (0.1896, 2.4535),
    "Feeder Cattle": (0.5413, 7.51),
    "Copper": (1.0417, 13.553),
    "Gold": (565.95, 10495.7998),
    "Silver": (6.1745, 201.85),
}
