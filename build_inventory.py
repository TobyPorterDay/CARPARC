"""Create the local inventory and its Trade Me listing map in DuckDB.

Week 3 sync state. Two tables in data/carparc.duckdb:

  inventory    local_id, title, price, description, status
               N parts drawn from the Partsworld corpus with a fixed seed,
               all status 'active'.
  listing_map  local_id, listing_id, remote_status, last_synced_at
               Empty. One row per local part once it has a Trade Me listing.

The corpus has no prices, so price is NULL. description is the Partsworld
subtitle, which is the vehicle fitment ("KIA Carnival - 2nd Gen 2006-2014").

Seeded and reproducible, and never overwrites: if either table already exists
the script stops, so a re-run cannot silently replace synced state.

Usage: python3 build_inventory.py [n] [seed]
"""

import csv
import random
import sys

import duckdb

CORPUS = "data/partsworld_titles_raw.csv"
DB = "data/carparc.duckdb"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261003

    with open(CORPUS, newline="", encoding="utf-8") as f:
        pool = sorted(
            {(row["title"].strip(), row["subtitle"].strip()) for row in csv.DictReader(f)}
        )
    if n > len(pool):
        sys.exit(f"corpus has {len(pool)} distinct parts, cannot draw {n}")
    sample = random.Random(seed).sample(pool, n)

    con = duckdb.connect(DB)
    existing = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('inventory', 'listing_map')"
        ).fetchall()
    }
    if existing:
        sys.exit(
            f"{DB} already has {', '.join(sorted(existing))} - "
            "drop deliberately to rebuild"
        )

    con.execute(
        """
        CREATE TABLE inventory (
            local_id    INTEGER PRIMARY KEY,
            title       VARCHAR NOT NULL,
            price       DECIMAL(10, 2),
            description VARCHAR,
            status      VARCHAR NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE listing_map (
            local_id       INTEGER PRIMARY KEY REFERENCES inventory (local_id),
            listing_id     BIGINT,
            remote_status  VARCHAR,
            last_synced_at TIMESTAMPTZ
        )
        """
    )
    con.executemany(
        "INSERT INTO inventory VALUES (?, ?, NULL, ?, 'active')",
        [(i, title, desc) for i, (title, desc) in enumerate(sample, start=1)],
    )

    print(f"corpus {len(pool)} distinct parts, drew {n} with seed {seed} -> {DB}")
    for row in con.execute("SELECT * FROM inventory ORDER BY local_id").fetchall():
        print(" ", row)
    print(f"  listing_map: {con.execute('SELECT COUNT(*) FROM listing_map').fetchone()[0]} rows")
    con.close()


if __name__ == "__main__":
    main()
