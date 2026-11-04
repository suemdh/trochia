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


# report_id -> (needs allSections to reach the detail rows, extractor fn)
REPORTS = {
    "cream": ("1100", False, _extract_cream),
    "wheat": ("3223", True,  _extract_wheat),
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
                          end_date: str | None = None) -> list:
    """Page through a report's full history in <=180-day chunks. Returns raw
    detail records (unfiltered)."""
    if not USDA_API_KEY:
        raise ValueError("USDA_API_KEY not set. Check your .env file.")

    end_date = end_date or date.today().isoformat()
    all_records = []
    for win_start, win_end in _date_windows(start_date, end_date):
        params = {
            "q": f"report_begin_date={win_start.strftime('%m/%d/%Y')}:{win_end.strftime('%m/%d/%Y')}",
        }
        if needs_all_sections:
            params["allSections"] = "true"
        url = f"{BASE_URL}/{report_id}"
        resp = requests.get(url, auth=(USDA_API_KEY, ""), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if needs_all_sections:
            # Response is a list of sections; the detail section holds the
            # actual per-item rows (the header section is just metadata).
            detail = next((s for s in data if s.get("reportSection") != "Report Header"), None)
            records = detail.get("results", []) if detail else []
        else:
            records = data.get("results", [])
        all_records.extend(records)
        time.sleep(0.2)  # be polite to the API across ~15-25 chunked requests
    return all_records


def fetch_all() -> dict:
    """Fetch all configured USDA reports, filtered down to one clean (date, value)
    series each. Returns dict of {name: DataFrame[date, value]}."""
    results = {}
    for name, (report_id, needs_all_sections, extractor) in REPORTS.items():
        try:
            raw = fetch_report_history(report_id, needs_all_sections)
            rows = extractor(raw)
            if not rows:
                print(f"WARNING: {name} (report {report_id}) returned no matching rows -- "
                      f"the report's field values may have changed. Paste this to Claude Code.")
                continue
            df = pd.DataFrame(rows, columns=["date", "value"])
            df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
            df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
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
