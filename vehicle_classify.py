"""Exact-match classifier for vehicle resolution.

Rep 1 (see LEARNING_LOG.md): for each listing, find canonical (Make, Model)
pairs from CANONICAL_PATH where both the make and the model appear verbatim
(case-insensitive substring) in the listing title. Among candidates sharing
a make, the longest model string wins (most specific); ties break on
fleet_count, highest first, then alphabetically for determinism.

Returns "MAKE|MODEL" (both upper-cased, as they appear in the canonical
file), or the string "NONE" if no candidate matches — not Python None, so a
gold row labelled NONE can be scored correct by harness.score().
"""

import csv

CANONICAL_PATH = "data/mvr_canonical_vehicles.csv"

_vehicles = None


def load_canonical(path):
    """Return [(make, model, fleet_count)] from the canonical CSV, upper-cased."""
    vehicles = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vehicles.append(
                (row["make"].upper(), row["model"].upper(), int(row["fleet_count"]))
            )
    return vehicles


def _get_vehicles():
    global _vehicles
    if _vehicles is None:
        _vehicles = load_canonical(CANONICAL_PATH)
    return _vehicles


def match(title):
    """Return "MAKE|MODEL" for the best exact-match candidate, else "NONE"."""
    upper_title = title.upper()

    candidates = [
        (make, model, fleet_count)
        for make, model, fleet_count in _get_vehicles()
        if make in upper_title and model in upper_title
    ]
    if not candidates:
        return "NONE"

    candidates.sort(key=lambda c: (-len(c[1]), -c[2], c[0], c[1]))
    make, model, _ = candidates[0]
    return f"{make}|{model}"


def main():
    import sys

    if len(sys.argv) > 1:
        print(match(" ".join(sys.argv[1:])))
        return

    with open("data/gold_vehicles_dev.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["Listing"]
            print(f"{title} -> {match(title)}")


if __name__ == "__main__":
    main()
