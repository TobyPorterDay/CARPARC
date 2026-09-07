"""Collect car part listings from Trade Me's Car parts & accessories category.

Trade Me's browse pages (/a/motors/car-parts-accessories) are a client-side
Angular app: the HTML served to a plain HTTP client contains no listings at
all, only an "Enable JavaScript to continue" shell.  Its robots.txt also
disallows every paginated browse URL (`Disallow: /a/*page=` and an explicit
`/a/motors/car-parts-accessories*?page` rule), which is the only way to reach
listing volume by browsing.

So this uses Trade Me's official API instead, which is the sanctioned route
for bulk access.  The category tree is public; the Search endpoint needs a
free application key from https://developer.trademe.co.nz.  Set:

    export TRADEME_CONSUMER_KEY=...
    export TRADEME_CONSUMER_SECRET=...

Usage: python3 scrape_trademe.py [target_count] [output_csv]
"""

import csv
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests

API = "https://api.trademe.co.nz/v1"
SITE = "https://www.trademe.co.nz"
CAR_PARTS = "0001-0877-"
ROWS = 50           # listings per API request (API maximum)
MIN_DELAY = 1.0     # sequential, single worker: 1-2s between every request
MAX_DELAY = 2.0

session = requests.Session()
session.headers["User-Agent"] = "CARPARC-research-scraper"


def auth_header():
    key = os.environ.get("TRADEME_CONSUMER_KEY")
    secret = os.environ.get("TRADEME_CONSUMER_SECRET")
    if not key or not secret:
        sys.exit(
            "Set TRADEME_CONSUMER_KEY and TRADEME_CONSUMER_SECRET.\n"
            "Register a free app at https://developer.trademe.co.nz to get them."
        )
    return (
        f'OAuth oauth_consumer_key="{key}", '
        f'oauth_signature_method="PLAINTEXT", '
        f'oauth_signature="{secret}&"'
    )


def polite_sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def get_json(url, **params):
    """One sequential request, with the delay applied before every call."""
    for attempt in range(3):
        polite_sleep()
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                sys.exit(f"Auth rejected by Trade Me ({r.status_code}): {r.text[:200]}")
            print(f"    HTTP {r.status_code} on {url}", flush=True)
        except (requests.RequestException, ValueError) as e:
            print(f"    {type(e).__name__} on {url}", flush=True)
        time.sleep(2 * (attempt + 1))
    return None


def leaf_subcategories():
    """Every leaf subcategory under Car parts & accessories, with its full path."""
    tree = get_json(f"{API}/Categories/{CAR_PARTS}.json")
    if not tree:
        sys.exit("Could not fetch the category tree.")
    leaves = []

    def walk(node, trail):
        subs = node.get("Subcategories") or []
        trail = trail + [node["Name"]]
        if subs:
            for s in subs:
                walk(s, trail)
        else:
            leaves.append({"number": node["Number"], "path": " > ".join(trail[1:])})

    walk(tree, [])
    return leaves


def listing_url(item):
    """Canonical listing URL; the API returns a path for most categories."""
    for field in ("ListingPath", "Path", "Url"):
        if item.get(field):
            value = item[field]
            return value if value.startswith("http") else SITE + "/a" + value
    return f"{SITE}/a/marketplace/listing/{item['ListingId']}"


def main(target, out_path):
    rng = random.Random(20260908)
    session.headers["Authorization"] = auth_header()

    subcats = leaf_subcategories()
    rng.shuffle(subcats)
    print(f"{len(subcats)} leaf subcategories", flush=True)

    rows = []
    seen = set()

    # One page per subcategory per pass, so a few big subcategories cannot
    # dominate the sample; keep cycling until the target is reached.
    page_of = {s["number"]: 1 for s in subcats}
    done = set()

    while len(rows) < target and len(done) < len(subcats):
        for sub in subcats:
            if len(rows) >= target:
                break
            num = sub["number"]
            if num in done:
                continue

            data = get_json(
                f"{API}/Search/General.json",
                category=num,
                rows=ROWS,
                page=page_of[num],
                sort_order="Default",
            )
            if not data:
                done.add(num)
                continue

            items = data.get("List") or []
            if not items:
                done.add(num)
                continue

            for item in items:
                lid = item.get("ListingId")
                if not lid or lid in seen:
                    continue
                seen.add(lid)
                rows.append(
                    {
                        "subcategory": sub["path"],
                        "title": (item.get("Title") or "").strip(),
                        "url": listing_url(item),
                    }
                )

            if page_of[num] * ROWS >= data.get("TotalCount", 0):
                done.add(num)
            page_of[num] += 1
            print(f"  {len(rows):5d} listings  {sub['path']}", flush=True)

    rng.shuffle(rows)
    rows = rows[:target]

    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fields = ["subcategory", "title", "url", "scraped_at"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            row["scraped_at"] = scraped_at
            w.writerow(row)
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main(
        int(sys.argv[1]) if len(sys.argv) > 1 else 4000,
        sys.argv[2] if len(sys.argv) > 2 else "data/trademe_car_parts_raw.csv",
    )
