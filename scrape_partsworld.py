"""Scrape parts listing titles from partsworld.co.nz into a raw data file.

The site browses as make -> model -> variant -> category, and only the
category pages carry listings.  There is no pagination anywhere on the
site, so the "page" a listing came from is recorded as its source URL
(plus the make/model/variant/category that URL decodes to).

Usage: python3 scrape_partsworld.py [target_count] [output_csv]
"""

import csv
import html
import random
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

BASE = "https://partsworld.co.nz"
UA = "Mozilla/5.0 (compatible; CARPARC-research-scraper)"
WORKERS = 6
DELAY = 0.15  # per-request politeness delay, spread across workers

TITLE_RE = re.compile(
    r'<h3 class="h6 part-title[^"]*"[^>]*>\s*<a\b[^>]*>(.*?)</a>\s*</h3>', re.S
)
SUB_RE = re.compile(r'<span class="part-sub-title">(.*?)</span>', re.S)

session = requests.Session()
session.headers["User-Agent"] = UA
session.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=WORKERS * 2))


def get(path):
    """Fetch a site-relative path, retrying a couple of times on failure."""
    for attempt in range(3):
        try:
            time.sleep(DELAY)
            r = session.get(BASE + path, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1 + attempt)
    return ""


def links_under(page, prefix):
    """Unique hrefs one level below `prefix`."""
    pat = re.compile(r'href="(' + re.escape(prefix) + r'/[^"/]+)"')
    return sorted(set(pat.findall(page)))


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def extract_listings(page):
    """Title/subtitle pairs for the listings on a category page.

    Each listing also appears inside a modal, but the modal copies carry no
    part-title heading, so this regex picks up each listing exactly once.
    """
    out = []
    for m in TITLE_RE.finditer(page):
        block = m.group(1)
        sub = SUB_RE.search(block)
        out.append((clean(SUB_RE.sub("", block)), clean(sub.group(1)) if sub else ""))
    return out


def label(segment):
    """Turn a URL segment such as '66_engine' or 'land+parts' into a name."""
    text = html.unescape(urllib.parse.unquote(segment)).replace("+", " ")
    return re.sub(r"^\d+_", "", text).strip()


def main(target, out_path):
    rng = random.Random(20260907)

    makes = links_under(get("/parts"), "/parts")
    print(f"{len(makes)} makes", flush=True)

    models = []
    for make in makes:
        models.extend(links_under(get(make), make))
    rng.shuffle(models)
    print(f"{len(models)} models", flush=True)

    rows = []
    seen = set()
    pages_fetched = 0
    # Round-robin one variant per model per pass, so a handful of
    # deep-stocked models cannot dominate the sample.
    pending = {}
    exhausted = set()

    while len(rows) < target and len(exhausted) < len(models):
        for model in models:
            if len(rows) >= target:
                break
            if model in exhausted:
                continue
            if model not in pending:
                variants = links_under(get(model), model)
                rng.shuffle(variants)
                pending[model] = variants
            if not pending[model]:
                exhausted.add(model)
                continue
            variant = pending[model].pop()

            categories = links_under(get(variant), variant)
            rng.shuffle(categories)
            _, _, make_s, model_s, variant_s = variant.split("/")

            with ThreadPoolExecutor(WORKERS) as pool:
                results = list(pool.map(lambda c: (c, extract_listings(get(c))), categories))
            pages_fetched += len(categories)

            for cat, listings in results:
                for title, subtitle in listings:
                    # A few listings on the site carry no title at all; skip them.
                    if not title:
                        continue
                    key = (title, cat)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "title": title,
                            "subtitle": subtitle,
                            "category": label(cat.rsplit("/", 1)[1]),
                            "make": label(make_s),
                            "model": label(model_s),
                            "variant": label(variant_s),
                            "page_url": BASE + cat,
                        }
                    )
            print(f"  {len(rows):5d} titles / {pages_fetched} pages  {variant}", flush=True)

    # Shuffle before truncating so the cut-off is not one model's tail.
    rng.shuffle(rows)
    rows = rows[:target]
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fields = ["title", "subtitle", "category", "make", "model", "variant", "page_url", "scraped_at"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            row["scraped_at"] = scraped_at
            w.writerow(row)
    print(f"wrote {len(rows)} rows to {out_path} ({pages_fetched} pages fetched)")


if __name__ == "__main__":
    main(
        int(sys.argv[1]) if len(sys.argv) > 1 else 4000,
        sys.argv[2] if len(sys.argv) > 2 else "data/partsworld_titles_raw.csv",
    )
