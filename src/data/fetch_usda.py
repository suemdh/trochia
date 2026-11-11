"""
Fetch commodity price data from USDA AMS MARS API (Agricultural Marketing Service).
Used for: cream (wholesale dairy) and wheat (KC cash bids) prices.

Docs: https://mymarketnews.ams.usda.gov/mars-api/getting-started
Auth: HTTP Basic, API key as username, empty password.

Each report below returns many sub-series mixed together (different grades,
classes, pricing units -- some of which aren't actual dollar prices at all,
e.g. "Factor Pricing" or basis differentials). FILTERS pins down the one
consistent, comparable series per report; anything else risks silently
blending incompatible numbers together.

The MARS API caps date-range queries at 180 days per request, so history is
paginated in chunks.
"""
import os
import time
from datetime import date, timedelta

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

USDA_API_KEY = os.getenv("USDA_API_KEY")
BASE_URL = "https://marsapi.ams.usda.gov/services/v1.2/reports"
MAX_WINDOW_DAYS = 180
FETCH_START = "2015-01-01"


def _norm(v) -> str:
    """Case/whitespace-insensitive compare for USDA's free-text field values --
    the exact strings below are correct as of this writing, but USDA has no
    obligation to keep e.g. 'All Classes' from ever becoming 'all classes ' in
    a future report revision. Normalizing means that kind of trivial
    formatting drift doesn't silently zero out the whole series; a genuine
    content change (a different grade, a renamed field) will still show up as
    the "no matching rows" warning in fetch_all() rather than being masked."""
    return str(v).strip().lower() if v is not None else ""


def _extract_cream(records: list) -> list:
    """Filter to Cream / All Classes / Dollars per Pound -- the one series here
    that's an actual absolute $/lb price rather than a basis or 'Factor Pricing'
    differential."""
    out = []
    for r in records:
        if (_norm(r.get("commodity")) == "cream" and _norm(r.get("group")) == "all classes"
                and _norm(r.get("price_Unit")) == "dollars per pound"):
            lo, hi = r.get("price_min"), r.get("price_max")
            if lo is not None and hi is not None:
                out.append((r.get("report_begin_date"), (float(lo) + float(hi)) / 2))
    return out


def _extract_wheat(records: list) -> list:
    """Filter to KC Hard Red Winter, US #1, 11.0% protein, basis bid at mills/
    processors -- one specific, consistently-quoted grade so we get exactly
    one row per day rather than 17 overlapping protein-spec variants."""
    out = []
    for r in records:
        if (_norm(r.get("commodity")) == "wheat" and _norm(r.get("class")) == "hard red winter"
                and _norm(r.get("grade")) == "us #1" and _norm(r.get("protein")) == "11.0%"
                and _norm(r.get("quote_type")) == "basis"
                and _norm(r.get("delivery_point")) == "mills and processors"):
            price = r.get("avg_price")
            if price is not None:
                out.append((r.get("report_date"), float(price)))
    return out


def _price(r) -> float | None:
    """avg_price when the report gives one, else the middle of its low/high."""
    if r.get("avg_price") not in (None, ""):
        return float(r["avg_price"])
    lo = r.get("price Min", r.get("price_min", r.get("low_price")))
    hi = r.get("price Max", r.get("price_max", r.get("high_price")))
    return (float(lo) + float(hi)) / 2 if lo not in (None, "") and hi not in (None, "") else None


def _cash_grain(commodity: str, delivery_point: str | None = None, scale: float = 1.0):
    """One price per day: the average across every region/elevator quoting
    `commodity` in the report (e.g. Iowa's six regions -> a state average)."""
    def extract(records: list) -> list:
        out = []
        for r in records:
            if _norm(r.get("commodity")) != _norm(commodity):
                continue
            if delivery_point and _norm(r.get("delivery_point")) != _norm(delivery_point):
                continue
            p = _price(r)
            if p is not None:
                out.append((r.get("report_date"), p * scale))
        return out
    return extract


def _extract_rice(records: list) -> list:
    """Long-grain white milled rice, Arkansas (the largest US producer), $/cwt."""
    return [(r.get("report_date"), _price(r)) for r in records
            if _norm(r.get("commodity")) == "milled rice" and _norm(r.get("class")) == "long white"
            and _norm(r.get("trade_location")) == "arkansas" and _norm(r.get("period")) == "current"
            and _price(r) is not None]


def _extract_cattle(records: list) -> list:
    """5-Area weekly steers, live FOB, over 80% Choice -- the cash market CME's
    live cattle contract settles against. $/cwt -> $/lb."""
    return [(r.get("report_date"), float(r["weighted_avg_price"]) / 100) for r in records
            if r.get("class_description") == "STEER" and r.get("selling_basis_description") == "LIVE FOB"
            and r.get("grade_description") == "Over 80% Choice" and r.get("weighted_avg_price")]


def _extract_hogs(records: list) -> list:
    """National barrows/gilts, all producer-sold purchase types, carcass basis.
    $/cwt -> $/lb."""
    return [(r.get("report_date"), float(r["avg_net_price"]) / 100) for r in records
            if r.get("purchase_type") == "Prod. Sold (All Purchase Types)" and r.get("avg_net_price")]


# USDA Livestock Mandatory Reporting -- public, no key; packers are required by
# law to report these prices, so they're the most complete cash prices there are.
MPR_URL = "https://mpr.datamart.ams.usda.gov/services/v1.1/reports"

# name -> (report_id, needs allSections, extractor[, base url, section name])
REPORTS = {
    "cream":       ("1100", False, _extract_cream),
    "wheat":       ("3223", True,  _extract_wheat),
    "corn":        ("2850", True,  _cash_grain("Corn", "Country Elevators")),
    "soybeans":    ("2850", True,  _cash_grain("Soybeans", "Country Elevators")),
    "oats":        ("3046", True,  _cash_grain("White Oats")),
    "soybean_oil": ("3511", True,  _cash_grain("Soybean Oil", scale=0.01)),  # cents -> $/lb
    "rice":        ("1655", True,  _extract_rice),
    "live_cattle": ("2477", True,  _extract_cattle, MPR_URL, "Detail"),
    "lean_hogs":   ("2511", True,  _extract_hogs,   MPR_URL, "Barrows/Gilts"),
}


def _date_windows(start_date: str, end_date: str):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=MAX_WINDOW_DAYS - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def fetch_report_history(report_id: str, needs_all_sections: bool,
                          start_date: str = FETCH_START,
                          end_date: str | None = None,
                          base_url: str = BASE_URL, section: str | None = None) -> list:
    """Page through a report's full history in <=180-day chunks. Returns raw
    detail records (unfiltered)."""
    mars = base_url == BASE_URL
    if mars and not USDA_API_KEY:
        raise ValueError("USDA_API_KEY not set. Check your .env file.")

    end_date = end_date or date.today().isoformat()
    all_records = []
    for win_start, win_end in _date_windows(start_date, end_date):
        field = "report_begin_date" if mars else "report_date"
        params = {
            "q": f"{field}={win_start.strftime('%m/%d/%Y')}:{win_end.strftime('%m/%d/%Y')}",
        }
        if needs_all_sections:
            params["allSections"] = "true"
        url = f"{base_url}/{report_id}"
        resp = requests.get(url, auth=(USDA_API_KEY, "") if mars else None, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if needs_all_sections:
            # Response is a list of sections; the detail section holds the
            # actual per-item rows (the header section is just metadata).
            detail = next((s for s in data if (s.get("reportSection") == section if section
                                               else s.get("reportSection") != "Report Header")), None)
            records = detail.get("results", []) if detail else []
        else:
            records = data.get("results", [])
        all_records.extend(records)
        time.sleep(0.2)  # be polite to the API across ~15-25 chunked requests
    return all_records


def fetch_all() -> dict:
    """Fetch all configured USDA reports, filtered down to one clean (date, value)
    series each. Returns dict of {name: DataFrame[date, value]}."""
    results, raw_cache = {}, {}
    for name, (report_id, needs_all_sections, extractor, *where) in REPORTS.items():
        try:
            if report_id not in raw_cache:  # corn + soybeans share one report
                raw_cache[report_id] = fetch_report_history(report_id, needs_all_sections, base_url=where[0] if where else BASE_URL,
                                                            section=where[1] if where else None)
            raw = raw_cache[report_id]
            rows = extractor(raw)
            if not rows:
                print(f"WARNING: {name} (report {report_id}) returned no matching rows -- "
                      f"the report's field values may have changed. Paste this to Claude Code.")
                continue
            df = pd.DataFrame(rows, columns=["date", "value"])
            df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
            df = df.groupby("date", as_index=False)["value"].mean()  # regions/duplicates -> one price per day
            results[name] = df
        except Exception as e:
            print(f"WARNING: failed to fetch {name} (report {report_id}): {e}")
            print("This is a common USDA AMS issue (report ID or auth format). "
                  "Paste this error to Claude Code to fix the exact endpoint.")
    return results


if __name__ == "__main__":
    results = fetch_all()
    for name, df in results.items():
        out_path = f"data/raw/usda_{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} rows to {out_path} ({df['date'].min().date()} to {df['date'].max().date()})")
