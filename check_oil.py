import requests, os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("FRED_API_KEY")

# Check what WPSID6112 actually is, and test butter + other oils
import json

# First, get the series info for WPSID6112
r = requests.get("https://api.stlouisfed.org/fred/series",
    params={"series_id":"WPSID6112","api_key":key,"file_type":"json"}, timeout=15)
if r.status_code == 200:
    info = r.json().get("seriess",[{}])[0]
    print(f"WPSID6112 title: {info.get('title')}, units: {info.get('units')}")

# Test butter and other retail food oil alternatives
candidates = {
    "butter":        "APU0000710411",
    "margarine":     "APU0000714311",
    "soybean_wps":   "WPSID6112",
}
for name, sid in candidates.items():
    r = requests.get("https://api.stlouisfed.org/fred/series/observations",
        params={"series_id":sid,"api_key":key,"file_type":"json","observation_start":"2023-01-01"}, timeout=15)
    if r.status_code == 200:
        obs = [o for o in r.json().get("observations",[]) if o["value"] != "."]
        if obs:
            last = obs[-1]
            print(f"OK  {name} ({sid}): last={last['value']} ({last['date']})")
    else:
        print(f"FAIL {name} ({sid}): {r.status_code}")
