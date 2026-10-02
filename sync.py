"""Minimal sync: create a Trade Me listing for every unmapped inventory row.

For each inventory row with no listing_map row, POST /v1/Selling.json and
write the ListingId from the reply to listing_map. That is all it does:

  - no edits, no withdraws, no read-back of what Trade Me has
  - the reply is trusted as-is
  - a failed call (exception or non-200) is printed and the row is left
    unmapped, so the next run tries it again; the run carries on

Those are the choices FAILURE_MODES.md is there to test.

Points at the fake Trade Me by default (fake_trademe.py). For the sandbox:

    export TRADEME_API=https://api.tmsandbox.co.nz/v1
    export TRADEME_CONSUMER_KEY=... TRADEME_CONSUMER_SECRET=...
    export TRADEME_TOKEN=...        TRADEME_TOKEN_SECRET=...

The fake only checks that the header starts with "OAuth", so none of these
are needed against it. Set CARPARC_DB to run against a copy of the database.

Usage: python3 sync.py
"""

import os
from datetime import datetime, timezone

import duckdb
import requests

DB = os.environ.get("CARPARC_DB", "data/carparc.duckdb")
API = os.environ.get("TRADEME_API", "http://127.0.0.1:8765/v1")
TIMEOUT = 30  # seconds; fake failure 11 waits 35

# Temporary placeholders: inventory.price is NULL for every row, and
# StartPrice must be at least 0.50. Price differs per row (row 1 $11 ...
# row 10 $20) so a listing can be told apart by price as well as title.
# Category is the one sandbox-tested category (BMW > Other), wrong for
# every part here.
CATEGORY = "0001-0877-2738-2744-"


def placeholder_price(local_id):
    return 10.0 + local_id


def auth_header():
    """PLAINTEXT OAuth 1.0a with the member token, as scrape_trademe.py uses."""
    key = os.environ.get("TRADEME_CONSUMER_KEY", "fake")
    secret = os.environ.get("TRADEME_CONSUMER_SECRET", "fake")
    token = os.environ.get("TRADEME_TOKEN", "fake")
    token_secret = os.environ.get("TRADEME_TOKEN_SECRET", "fake")
    return (
        f'OAuth oauth_consumer_key="{key}", oauth_token="{token}", '
        f'oauth_signature_method="PLAINTEXT", '
        f'oauth_signature="{secret}&{token_secret}"'
    )


def listing_body(local_id, title, price, description):
    return {
        "Category": CATEGORY,
        "Title": title,
        "Description": [description or ""],
        "StartPrice": float(price) if price is not None
                      else placeholder_price(local_id),
        "Duration": 7,
        "Pickup": 1,
        "PaymentMethods": [2, 4],
        "ShippingOptions": [{"Type": 1}],
    }


def main():
    session = requests.Session()
    session.headers["Authorization"] = auth_header()
    con = duckdb.connect(DB)

    unmapped = con.execute(
        """
        SELECT local_id, title, price, description
        FROM inventory
        WHERE local_id NOT IN (SELECT local_id FROM listing_map)
        ORDER BY local_id
        """
    ).fetchall()
    print(f"sync against {API}: {len(unmapped)} unmapped rows")

    created = 0
    for local_id, title, price, description in unmapped:
        try:
            r = session.post(f"{API}/Selling.json", timeout=TIMEOUT,
                             json=listing_body(local_id, title, price, description))
        except requests.RequestException as e:
            print(f"  local {local_id}: {type(e).__name__}")
            continue
        if r.status_code != 200:
            print(f"  local {local_id}: HTTP {r.status_code} {r.text[:100]}")
            continue
        listing_id = r.json()["ListingId"]
        con.execute(
            "INSERT INTO listing_map VALUES (?, ?, 'live', ?)",
            [local_id, listing_id, datetime.now(timezone.utc)],
        )
        created += 1
        print(f"  local {local_id}: listing {listing_id}")

    mapped = con.execute("SELECT COUNT(*) FROM listing_map").fetchone()[0]
    print(f"done: created {created}, listing_map {mapped} rows")
    con.close()


if __name__ == "__main__":
    main()
