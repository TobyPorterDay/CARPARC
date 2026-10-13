"""Terminal labeller: messy vehicle string -> canonical MVR record, or NONE.

Reads a gold file with columns Listing,Label and fills in Label. Saves after
every decision, so quitting mid-session loses nothing; re-running resumes at
the first unlabelled row.

The label you store is 'MAKE|MODEL' exactly as the MVR spells it, or the
literal NONE when no canonical record is right. NONE is a real answer, not a
skip -- press s to skip a row you want to come back to.

Search is a plain substring match over the canonical table, ranked by fleet
count, so the common answer surfaces first. It deliberately does no fuzzy
matching: guessing for you would put the resolver's job inside the labeller.

Usage:
    python3 label_vehicles.py                      # labels the dev set
    python3 label_vehicles.py data/gold_vehicles_heldout.csv

Keys at the prompt:
    <text>   search the canonical table
    <number> pick that result
    n        no canonical match -> NONE
    s        skip for now
    b        back one row
    q        save and quit
"""

import csv
import os
import sys

CANON = "nz_vehicle_resolver/data/mvr_canonical_vehicles.csv"
DEFAULT_GOLD = "data/gold_vehicles_dev.csv"
PAGE = 12


def load_canon():
    if not os.path.exists(CANON):
        sys.exit(
            f"{CANON} not found.\n"
            "The canonical vehicle table has to exist before labelling: the\n"
            "label you pick is a row from it. See README for how to build it."
        )
    with open(CANON, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["_n"] = int(r.get("fleet_count") or 0)
        r["_key"] = f"{r['make']}|{r['model']}"
        r["_hay"] = r["_key"].lower()
    rows.sort(key=lambda r: -r["_n"])
    return rows


def search(canon, q):
    terms = q.lower().split()
    if not terms:
        return []
    return [r for r in canon if all(t in r["_hay"] for t in terms)][:PAGE]


def load_gold(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_gold(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Listing", "Label"])
        for r in rows:
            w.writerow([r["Listing"], r["Label"]])
    os.replace(tmp, path)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GOLD
    canon = load_canon()
    rows = load_gold(path)

    print(f"{path}: {len(rows)} rows, {sum(1 for r in rows if r['Label'])} labelled")
    print(f"canonical table: {len(canon)} make/model pairs\n")

    i = 0
    while i < len(rows):
        row = rows[i]
        if row["Label"]:
            i += 1
            continue

        done = sum(1 for r in rows if r["Label"])
        print("=" * 66)
        print(f"[{done}/{len(rows)}]  {row['Listing']}")
        print("=" * 66)

        results = []
        while True:
            cmd = input("search/number/n/s/b/q > ").strip()

            if cmd == "q":
                save_gold(path, rows)
                print(f"saved {path} ({done} labelled)")
                return
            if cmd == "b":
                i = max(0, i - 1)
                rows[i]["Label"] = ""
                break
            if cmd == "s":
                i += 1
                break
            if cmd == "n":
                row["Label"] = "NONE"
                save_gold(path, rows)
                i += 1
                break
            if cmd.isdigit() and results:
                k = int(cmd) - 1
                if 0 <= k < len(results):
                    row["Label"] = results[k]["_key"]
                    save_gold(path, rows)
                    i += 1
                    break
                print("  no such result")
                continue

            results = search(canon, cmd)
            if not results:
                print("  no match - try fewer words, or n for NONE")
                continue
            for k, r in enumerate(results, 1):
                print(
                    f"  {k:2d}. {r['_key']:<38} "
                    f"fleet={r['_n']:<7} used_import={r['used_import_count']}"
                )

    save_gold(path, rows)
    print(f"\nall {len(rows)} rows labelled. saved {path}")


if __name__ == "__main__":
    main()
