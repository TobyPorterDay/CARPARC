"""Draw the vehicle-resolution gold sample from the Partsworld corpus.

Seeded and reproducible: the same seed always draws the same 200 rows and the
same dev/held-out split. Writes three files and never overwrites an existing
one, so a re-run cannot silently change a set you have already labelled.

  data/gold_vehicles_unlabelled.csv  200 rows, the sample, in draw order
  data/gold_vehicles_dev.csv         first 100 - label now, iterate on these
  data/gold_vehicles_heldout.csv     last 100  - touch twice: now, and Week 4

Usage: python3 sample_gold.py [n] [seed]
"""

import csv
import os
import random
import sys

CORPUS = "data/pw_vehicles.csv"
OUT_ALL = "data/gold_vehicles_unlabelled.csv"
OUT_DEV = "data/gold_vehicles_dev.csv"
OUT_HELD = "data/gold_vehicles_heldout.csv"


def write(path, rows):
    if os.path.exists(path):
        print(f"  SKIP {path} (exists - delete it deliberately to redraw)")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Listing", "Label"])
        for r in rows:
            w.writerow([r, ""])
    print(f"  wrote {path}  ({len(rows)} rows)")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260907

    with open(CORPUS, newline="", encoding="utf-8") as f:
        pool = sorted({row["vehicle_string"] for row in csv.DictReader(f)})

    if n > len(pool):
        sys.exit(f"corpus has {len(pool)} distinct vehicles, cannot draw {n}")

    sample = random.Random(seed).sample(pool, n)
    half = n // 2

    print(f"corpus {len(pool)} distinct vehicles, drew {n} with seed {seed}")
    write(OUT_ALL, sample)
    write(OUT_DEV, sample[:half])
    write(OUT_HELD, sample[half:])


if __name__ == "__main__":
    main()
