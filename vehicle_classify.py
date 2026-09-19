"""Classifiers for vehicle resolution.

Rep 1 (see LEARNING_LOG.md): for each listing, find canonical (Make, Model)
pairs from CANONICAL_PATH where both the make and the model appear verbatim
(case-insensitive substring) in the listing title. Among candidates sharing
a make, the longest model string wins (most specific); ties break on
fleet_count, highest first, then alphabetically for determinism.

Returns "MAKE|MODEL" (both upper-cased, as they appear in the canonical
file), or the string "NONE" if no candidate matches — not Python None, so a
gold row labelled NONE can be scored correct by harness.score().

Rep 2: fuzzy_match() replaces containment with rapidfuzz similarity. Make
and model are each scored (0-100) against the listing with fuzz.ratio, and
both must reach FUZZY_THRESHOLD for the pair to be a candidate; survivors
go through Rep 1's tie-break, highest model score first. The score never
leaves this module — the harness still gets a "MAKE|MODEL" label or "NONE".

Similarity is measured against the part of the listing that could be a make
or a model, not the whole title: the listing is cut into runs of adjacent
words (up to WINDOW_TOKENS long) and each run is scored separately, so a
chassis code and a year range can't drag a real match down. Punctuation is
deleted rather than turned into a word break, so CX-7, CX7 and "CX 7" all
reduce to the same key and compare equal.

Rep 3a: alias_match() looks the listing up in ALIAS_PATH before falling
back to Rep 2. Every name the table gives a vehicle (each merged register
name, the JDM name and the export name) points at that vehicle's merged
row, so "Mitsubishi Airtrek" and "Mitsubishi Outlander" both resolve to
MITSUBISHI|OUTLANDER. Names are compared as _key()s against the listing's
word runs, exactly, with the make required too; the longest name found
wins. Chassis codes are not used.

Each vehicle has one fixed name, the first name in its mvr_model, and
alias_match() only ever returns that name for it. When the lookup misses
and Rep 2 answers with another of the vehicle's names (MAZDA|MAZDA3), it
is replaced with the fixed one (MAZDA|AXELA).
"""

import csv
import re

from rapidfuzz import fuzz, process

CANONICAL_PATH = "data/mvr_canonical_vehicles.csv"
ALIAS_PATH = "data/alias_vehicles.csv"
FUZZY_THRESHOLD = 95
# Longest run of adjacent listing words compared against one make or model.
# The longest canonical model is 4 words ("3 SERIES GRAN TURISMO").
WINDOW_TOKENS = 4

_vehicles = None
_fuzzy_keys = None
_aliases = None


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


def _key(text):
    """Reduce text to comparable form: upper-case alphanumerics, nothing else.

    Punctuation is deleted, not turned into a space, so "CX-7" and "CX7"
    give the same key. Word boundaries are dropped too, so the multi-word
    "3 SERIES" matches a listing that writes it as "3Series".
    """
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _windows(title):
    """Return every run of 1..WINDOW_TOKENS adjacent words in title, as keys."""
    words = re.findall(r"[A-Za-z0-9]+", title)
    return [
        _key("".join(words[i : i + n]))
        for n in range(1, WINDOW_TOKENS + 1)
        for i in range(len(words) - n + 1)
    ]


def _get_fuzzy_keys():
    """Return (make_keys, model_keys) aligned index-for-index with _get_vehicles()."""
    global _fuzzy_keys
    if _fuzzy_keys is None:
        vehicles = _get_vehicles()
        _fuzzy_keys = (
            [_key(make) for make, _, _ in vehicles],
            [_key(model) for _, model, _ in vehicles],
        )
    return _fuzzy_keys


def _best_scores(windows, keys, threshold):
    """Return {index: best score} for keys scoring >= threshold against any window."""
    best = {}
    for window in windows:
        for _, score, index in process.extract(
            window, keys, scorer=fuzz.ratio, score_cutoff=threshold, limit=None
        ):
            if score > best.get(index, 0):
                best[index] = score
    return best


def fuzzy_match(title, threshold=FUZZY_THRESHOLD):
    """Return "MAKE|MODEL" for the best fuzzy candidate, else "NONE".

    A pair is a candidate when its make and its model each score at or above
    threshold against some run of words in the listing. Candidates are
    ranked by model score, then by Rep 1's tie-break: longest model, then
    fleet_count, then alphabetically.
    """
    vehicles = _get_vehicles()
    make_keys, model_keys = _get_fuzzy_keys()
    windows = _windows(title)

    make_scores = _best_scores(windows, make_keys, threshold)
    if not make_scores:
        return "NONE"
    model_scores = _best_scores(windows, model_keys, threshold)

    candidates = [
        (model_scores[i], vehicles[i]) for i in model_scores if i in make_scores
    ]
    if not candidates:
        return "NONE"

    candidates.sort(key=lambda c: (-c[0], -len(c[1][1]), -c[1][2], c[1][0], c[1][1]))
    make, model, _ = candidates[0][1]
    return f"{make}|{model}"


def _alias_names(field):
    """Split a jdm_name/export_name cell into names.

    Cells hold several names separated by " / " and carry notes in brackets,
    e.g. "RAV4 / Vanguard (long body)" -> ["RAV4", "Vanguard"].
    """
    names = []
    for part in field.split("/"):
        name = re.sub(r"\([^)]*\)", "", part).strip()
        if name:
            names.append(name)
    return names


def load_aliases(path):
    """Return {make_key: {name_key: "MAKE|MODEL"}} from the alias table.

    MODEL is the first name of the merged mvr_model. A name that points at
    two different vehicles under one make is ambiguous and left out.
    """
    aliases = {}
    ambiguous = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            make = row["make"].strip().upper()
            merged = row["mvr_model"].split(";")
            label = f"{make}|{merged[0].strip().upper()}"
            names = merged + _alias_names(row["jdm_name"]) + _alias_names(row["export_name"])
            by_name = aliases.setdefault(_key(make), {})
            for name in names:
                name_key = _key(name)
                if not name_key:
                    continue
                if by_name.get(name_key, label) != label:
                    ambiguous.add((_key(make), name_key))
                by_name[name_key] = label
    for make_key, name_key in ambiguous:
        del aliases[make_key][name_key]
    return aliases


def _get_aliases():
    global _aliases
    if _aliases is None:
        _aliases = load_aliases(ALIAS_PATH)
    return _aliases


def alias_lookup(title):
    """Return "MAKE|MODEL" for the longest alias name in title, else None."""
    windows = set(_windows(title))
    best = None
    for make_key, by_name in _get_aliases().items():
        if make_key not in windows:
            continue
        for name_key, label in by_name.items():
            if name_key in windows and (best is None or len(name_key) > len(best[0])):
                best = (name_key, label)
    return best[1] if best else None


def fixed_label(label):
    """Return label under its vehicle's fixed name, or unchanged if not in the table."""
    make, _, model = label.partition("|")
    return _get_aliases().get(_key(make), {}).get(_key(model), label)


def alias_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 3a: the alias table's vehicle if the listing names one, else Rep 2.

    Either way a vehicle in the alias table comes back under its fixed name.
    """
    return alias_lookup(title) or fixed_label(fuzzy_match(title, threshold))


def main():
    import sys

    if len(sys.argv) > 1:
        print(fuzzy_match(" ".join(sys.argv[1:])))
        return

    with open("data/gold_vehicles_dev.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["Listing"]
            print(f"{title} -> {fuzzy_match(title)}")


if __name__ == "__main__":
    main()
