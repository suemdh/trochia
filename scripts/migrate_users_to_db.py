"""
One-time copy of local data/users.json accounts into the Supabase database.
Safe to re-run: it upserts, so existing database rows are updated, never duplicated.

Usage (with SUPABASE_DB_URL in .env):
    python scripts/migrate_users_to_db.py
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [os.path.join(ROOT, "src", "dashboard"), os.path.join(ROOT, "src")]

import auth

if not auth._db_url():
    sys.exit("SUPABASE_DB_URL not set -- nothing to migrate to.")
if not os.path.exists(auth.USERS_FILE):
    sys.exit("No local users.json -- nothing to migrate.")

with open(auth.USERS_FILE) as f:
    local = json.load(f)
auth._save_users(local)
in_db = auth._load_users()
missing = set(local) - set(in_db)
print(f"Local accounts: {len(local)} | in database now: {len(in_db)} | missing: {len(missing)}")
sys.exit(1 if missing else 0)
