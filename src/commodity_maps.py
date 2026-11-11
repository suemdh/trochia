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
    # Wholesale energy: EIA daily spot prices (public data) -- these replaced
    # Yahoo Finance futures, which can't be shown to paying users without an
    # exchange licence.
    "Crude Oil (Brent)": ("brent_spot",       "$/barrel"),
    "Crude Oil (WTI)":   ("wti_spot",         "$/barrel"),
    "Natural Gas":       ("natgas_spot",      "$/MMBtu"),
    "Gasoline (Wholesale)": ("gasoline_spot", "$/gal"),
    "Heating Oil":       ("heating_oil_spot", "$/gal"),
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
    # Cash prices (see fetch_usda.REPORTS for the exact report behind each).
    "Corn":              ("corn",        "$/bushel"),
    "Soybeans":          ("soybeans",    "$/bushel"),
    "Oats":              ("oats",        "$/bushel"),
    "Soybean Oil":       ("soybean_oil", "$/lb"),
    "Rice (Milled)":     ("rice",        "$/cwt"),
    "Live Cattle":       ("live_cattle", "$/lb"),
    "Lean Hogs":         ("lean_hogs",   "$/lb"),
}

# Yahoo Finance futures were removed 2026-11: Yahoo's terms forbid commercial
# use and exchanges (CME, ICE) charge licence fees to show their prices to
# paying users. Coffee/cocoa/sugar/orange-juice futures (ICE) can come back
# through a licensed vendor; until then BLS retail coffee and sugar (above) cover two.

TOTAL_COMMODITIES = len(FRED_COMMODITY_MAP) + len(USDA_COMMODITY_MAP)


def is_monthly(name: str) -> bool:
    """BLS average prices are monthly; EIA diesel/gasoline are weekly, the
    *_spot series daily, and USDA reports daily or weekly."""
    col = FRED_COMMODITY_MAP.get(name, ("",))[0]
    return bool(col) and not col.endswith("_spot") and col not in ("diesel_price", "gasoline_retail")


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
    "Crude Oil (Brent)": (4.56, 276.42),
    "Crude Oil (WTI)": (5.0, 247.28),  # hand-set floor: spot printed -$37 for one day in Apr 2020
    "Natural Gas": (0.605, 61.44),
    "Gasoline (Wholesale)": (0.217, 9.018),
    "Heating Oil": (0.281, 10.326),
    "Wheat (USDA Cash)": (2.58, 31.44),
    "Cream (USDA)": (0.6375, 9.001),
    "Corn": (1.3931, 16.1155),
    "Soybeans": (4.08, 34.1312),
    "Oats": (1.4425, 16.02),
    "Soybean Oil": (0.1983, 1.8805),
    "Rice (Milled)": (13.4375, 75.0),
    "Live Cattle": (0.4762, 5.2684),
    "Lean Hogs": (0.2539, 2.3722),
}
