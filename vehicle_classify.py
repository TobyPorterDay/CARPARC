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

Rep 3b: chassis_match() is Rep 3a with JDM and export names scoped to the
chassis codes of the table rows that give them. A register name (one in
mvr_model) resolves as before. A JDM or export name resolves only when the
listing also carries one of that row's chassis codes, so "Honda Inspire -
CP2" is HONDA|ACCORD but "Honda Inspire - UA1" is left to Rep 2. The
fallback maps Rep 2's answer to the fixed name through register names only.

The listing's chassis code is read first and outranks the name: when the
table gives the code to one vehicle, that vehicle is the answer, even if
the listing names another model or no model the table knows. A code the
table gives to two vehicles of one make is settled by the name in the
listing. Range notation ("CB-CC") is matched by prefix, so a partial code
reaches the full codes it starts.

Rep 3c: name_first_match() is Rep 3a with 3b's chassis code as a last
resort. The listing's name is tried first, exactly as in Rep 3a (the alias
table, then Rep 2); only when that finds nothing does the chassis code get
a say, and then only when it points at a single vehicle. So "Toyota Allex -
ZZE122" stays TOYOTA|ALLEX, but "Ford XR6 - FG-FGX", which names no model,
is FORD|FALCON.

Rep 3d: distinct_name_match() is Rep 3c with a smaller alias table. A JDM
or export name that the register (CANONICAL_PATH) holds as a separate model
under the same make is dropped from the table: RVR, Inspire and Ignis are
their own vehicles, not other names for the ASX, Accord and Swift. So
"Honda Inspire - CB-CC" stays HONDA|INSPIRE instead of becoming
HONDA|ACCORD. Chassis codes are unchanged.

Rep 4: llm_extract_match() is Rep 3d run on an LLM's reading of the listing
instead of the raw title. The LLM copies the make, model and chassis code
out of the title as written (no translation, no respelling, no parent
model); the three fields are rebuilt as "MAKE MODEL - CHASSIS" and handed
to distinct_name_match() unchanged. Year ranges and trim notes are left
out of the fields, so they never reach the matcher. Every LLM answer is
kept in LLM_CACHE_PATH, keyed by title, so a rerun scores the same
extractions instead of asking again. Each entry also records which model
answered (llm_model) and whether that was the fallback after LLM_MODEL
declined (llm_fallback); llm_fallback_titles() lists those titles.

Rep 5: abstain_match() is Rep 4 with a confidence number on each answer,
taken from how the Rep 3d matcher reached it (distinct_name_confidence()):
1 / the number of different vehicles still in contention at the step that
decided, times the winning fuzzy score / 100 on the Rep 2 fallback. An
answer below CONFIDENCE_THRESHOLD comes back as NONE. The LLM extractions
are Rep 4's, read from the same cache; no new calls are made.
"""

import csv
import json
import os
import re

from rapidfuzz import fuzz, process

# Anchored to this file so the paths hold whatever the working directory is.
_HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL_PATH = os.path.join(_HERE, "nz_vehicle_resolver/data/mvr_canonical_vehicles.csv")
ALIAS_PATH = os.path.join(_HERE, "nz_vehicle_resolver/data/alias_vehicles.csv")
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
    candidates = _fuzzy_candidates(title, threshold)
    if not candidates:
        return "NONE"
    make, model, _ = candidates[0][1]
    return f"{make}|{model}"


def _fuzzy_candidates(title, threshold=FUZZY_THRESHOLD):
    """Return fuzzy_match()'s candidates as (model score, vehicle), best first."""
    vehicles = _get_vehicles()
    make_keys, model_keys = _get_fuzzy_keys()
    windows = _windows(title)

    make_scores = _best_scores(windows, make_keys, threshold)
    if not make_scores:
        return []
    model_scores = _best_scores(windows, model_keys, threshold)

    candidates = [
        (model_scores[i], vehicles[i]) for i in model_scores if i in make_scores
    ]
    candidates.sort(key=lambda c: (-c[0], -len(c[1][1]), -c[1][2], c[1][0], c[1][1]))
    return candidates


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


def load_aliases(path, drop=frozenset()):
    """Return {make_key: {name_key: "MAKE|MODEL"}} from the alias table.

    MODEL is the first name of the merged mvr_model. A name that points at
    two different vehicles under one make is ambiguous and left out. A JDM or
    export name whose (make_key, name_key) is in drop is left out too.
    """
    aliases = {}
    ambiguous = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            make = row["make"].strip().upper()
            merged = row["mvr_model"].split(";")
            label = f"{make}|{merged[0].strip().upper()}"
            alias_names = _alias_names(row["jdm_name"]) + _alias_names(row["export_name"])
            own_names = {_key(name) for name in merged}
            by_name = aliases.setdefault(_key(make), {})
            for name in merged + alias_names:
                name_key = _key(name)
                if not name_key:
                    continue
                if name_key not in own_names and (_key(make), name_key) in drop:
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


def alias_lookup(title, aliases=None):
    """Return "MAKE|MODEL" for the longest alias name in title, else None.

    aliases defaults to Rep 3a's table.
    """
    best = None
    for name_key, label in _alias_hits(title, aliases):
        if best is None or len(name_key) > len(best[0]):
            best = (name_key, label)
    return best[1] if best else None


def _alias_hits(title, aliases=None):
    """Return every (name_key, "MAKE|MODEL") the alias table finds in title."""
    windows = set(_windows(title))
    return [
        (name_key, label)
        for make_key, by_name in (aliases or _get_aliases()).items()
        if make_key in windows
        for name_key, label in by_name.items()
        if name_key in windows
    ]


def fixed_label(label, aliases=None):
    """Return label under its vehicle's fixed name, or unchanged if not in the table."""
    make, _, model = label.partition("|")
    return (aliases or _get_aliases()).get(_key(make), {}).get(_key(model), label)


def alias_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 3a: the alias table's vehicle if the listing names one, else Rep 2.

    Either way a vehicle in the alias table comes back under its fixed name.
    """
    return alias_lookup(title) or fixed_label(fuzzy_match(title, threshold))


def load_chassis_aliases(path):
    """Return (register, scoped, codes, names) from the alias table, for Rep 3b.

    register is {make_key: {name_key: "MAKE|MODEL"}} from the mvr_model
    names alone, built the way load_aliases() builds it: a name pointing at
    two vehicles under one make is left out.

    scoped is {make_key: {name_key: [("MAKE|MODEL", {chassis_key})]}} — one
    entry per table row that gives the name as its JDM or export name,
    carrying that row's chassis codes. A JDM or export name that is already
    one of the same vehicle's register names is not scoped; it stays a
    register name.

    codes is {make_key: {chassis_key: {"MAKE|MODEL"}}} — every vehicle a
    chassis code is given to under that make (Subaru's BR9 is both Legacy's
    and Outback's).

    names is {"MAKE|MODEL": {name_key}} — every name the table gives a
    vehicle: register, JDM and export.
    """
    register = {}
    ambiguous = set()
    scoped = {}
    codes = {}
    names = {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        make = row["make"].strip().upper()
        merged = row["mvr_model"].split(";")
        label = f"{make}|{merged[0].strip().upper()}"
        by_name = register.setdefault(_key(make), {})
        for name in merged:
            name_key = _key(name)
            if not name_key:
                continue
            if by_name.get(name_key, label) != label:
                ambiguous.add((_key(make), name_key))
            by_name[name_key] = label
    for make_key, name_key in ambiguous:
        del register[make_key][name_key]

    for row in rows:
        make = row["make"].strip().upper()
        merged = row["mvr_model"].split(";")
        label = f"{make}|{merged[0].strip().upper()}"
        own_names = {_key(name) for name in merged}
        chassis = {_key(code) for code in row["chassis_codes"].split(";") if _key(code)}
        by_code = codes.setdefault(_key(make), {})
        for code in chassis:
            by_code.setdefault(code, set()).add(label)
        by_name = scoped.setdefault(_key(make), {})
        alias_names = _alias_names(row["jdm_name"]) + _alias_names(row["export_name"])
        names.setdefault(label, set()).update(
            _key(name) for name in merged + alias_names if _key(name)
        )
        for name in alias_names:
            name_key = _key(name)
            if not name_key or name_key in own_names:
                continue
            by_name.setdefault(name_key, []).append((label, chassis))
    return register, scoped, codes, names


_chassis_aliases = None


def _get_chassis_aliases():
    global _chassis_aliases
    if _chassis_aliases is None:
        _chassis_aliases = load_chassis_aliases(ALIAS_PATH)
    return _chassis_aliases


def chassis_lookup(title):
    """Return "MAKE|MODEL" for the longest name in title Rep 3b accepts, else None.

    A register name is accepted as in Rep 3a. A JDM or export name is
    accepted only when the listing also carries a chassis code from a table
    row that gives that name, and it resolves to that row's vehicle. The
    chassis code is one of the listing's word runs, compared as a _key(), so
    "CU2W" and "CU-2W" are the same code. If the chassis codes found point
    the name at two different vehicles, the name is not used.
    """
    windows = set(_windows(title))
    register, scoped, _, _ = _get_chassis_aliases()
    best = None
    for make_key in register.keys() | scoped.keys():
        if make_key not in windows:
            continue
        found = [
            (name_key, label)
            for name_key, label in register.get(make_key, {}).items()
            if name_key in windows
        ]
        for name_key, entries in scoped.get(make_key, {}).items():
            if name_key not in windows:
                continue
            labels = {label for label, chassis in entries if chassis & windows}
            if len(labels) == 1:
                found.append((name_key, labels.pop()))
        for name_key, label in found:
            if best is None or len(name_key) > len(best[0]):
                best = (name_key, label)
    return best[1] if best else None


def register_fixed_label(label):
    """Return label under its vehicle's fixed name, using register names only.

    Rep 3b's version of fixed_label(): a Rep 2 answer that is a JDM or export
    name (HONDA|INSPIRE) is not moved onto another vehicle, because the
    fallback has no chassis code to scope it with.
    """
    make, _, model = label.partition("|")
    register, _, _, _ = _get_chassis_aliases()
    return register.get(_key(make), {}).get(_key(model), label)


def _is_range(parts):
    """True when a hyphenated chunk's parts read as a chassis range ("CB-CC").

    Both ends must hold a letter, so a year range (1989-1995) or a
    punctuated model number (CX-7) is not a range.
    """
    return len(parts) == 2 and all(re.search(r"[A-Z]", part) for part in parts)


def chassis_vehicles(title):
    """Return the set of "MAKE|MODEL" the listing's chassis codes point at.

    Only the codes of a make named in the listing are looked at. The listing
    is split on whitespace into chunks; a chunk that is one of the make's
    model names (CR-V) is not a chassis code. A chunk matches a code exactly,
    as a whole (CP-2 is CP2) or by one of its hyphenated parts (GA4W in
    "GA4W-xxx"). A chunk in range notation ("CB-CC", "FG-FGX") also matches
    every code that starts with either end, so a partial code like CB
    reaches CB3, CB4 ...
    """
    windows = set(_windows(title))
    _, _, codes, names = _get_chassis_aliases()
    found = set()
    for make_key, by_code in codes.items():
        if make_key not in windows:
            continue
        make_names = {
            name_key
            for label in {l for labels in by_code.values() for l in labels}
            for name_key in names[label]
        }
        for chunk in title.upper().split():
            chunk_key = _key(chunk)
            if not chunk_key or chunk_key in make_names:
                continue
            parts = [_key(part) for part in chunk.split("-") if _key(part)]
            for key in {chunk_key, *parts}:
                found |= by_code.get(key, set())
            if _is_range(parts):
                for code, labels in by_code.items():
                    if any(code.startswith(part) for part in parts):
                        found |= labels
    return found


def chassis_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 3b: the listing's chassis code picks the vehicle, names second.

    - The chassis codes point at one vehicle: that vehicle, whether or not
      the model name in the listing agrees, and whether or not any name
      matched at all.
    - They point at several (a code shared by two vehicles, or codes from
      different vehicles): the one whose name, any of its table names,
      appears in the listing, longest name first. If none does, the chassis
      code decides nothing.
    - No chassis code decides: chassis_lookup()'s name match, with JDM and
      export names scoped to their chassis, then Rep 2 as in Rep 3a.
    """
    vehicles = chassis_vehicles(title)
    if len(vehicles) == 1:
        return next(iter(vehicles))
    if vehicles:
        windows = set(_windows(title))
        _, _, _, names = _get_chassis_aliases()
        named = [
            (len(name_key), label)
            for label in vehicles
            for name_key in names[label]
            if name_key in windows
        ]
        if named:
            return max(named)[1]
    return chassis_lookup(title) or register_fixed_label(fuzzy_match(title, threshold))


def name_first_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 3c: Rep 3a's name match, and the chassis code only if that finds none.

    A chassis code the table gives to several vehicles decides nothing,
    since there is no name to settle it.
    """
    label = alias_match(title, threshold)
    if label != "NONE":
        return label
    vehicles = chassis_vehicles(title)
    if len(vehicles) == 1:
        return next(iter(vehicles))
    return "NONE"


def register_model_aliases(path=ALIAS_PATH, canonical_path=CANONICAL_PATH):
    """Return {(make_key, name_key)} for the JDM and export names Rep 3d drops.

    These are names the alias table gives a vehicle that the register holds
    as a separate model under the same make (Mitsubishi RVR, given to the
    ASX). A name that is one of the row's own mvr_model names is not
    dropped: the Corolla row's "Corolla" is the Corolla.
    """
    register = {(_key(make), _key(model)) for make, model, _ in load_canonical(canonical_path)}
    dropped = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            make_key = _key(row["make"])
            own_names = {_key(name) for name in row["mvr_model"].split(";")}
            for name in _alias_names(row["jdm_name"]) + _alias_names(row["export_name"]):
                name_key = _key(name)
                if name_key and name_key not in own_names and (make_key, name_key) in register:
                    dropped.add((make_key, name_key))
    return dropped


_distinct_aliases = None


def _get_distinct_aliases():
    global _distinct_aliases
    if _distinct_aliases is None:
        _distinct_aliases = load_aliases(ALIAS_PATH, drop=register_model_aliases())
    return _distinct_aliases


def distinct_name_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 3d: Rep 3c with register models dropped from the alias table.

    The name match is Rep 3a's (the table, then Rep 2, then the fixed name),
    run on the smaller table; the chassis code is read only when it finds
    nothing, exactly as in Rep 3c.
    """
    aliases = _get_distinct_aliases()
    label = alias_lookup(title, aliases) or fixed_label(fuzzy_match(title, threshold), aliases)
    if label != "NONE":
        return label
    vehicles = chassis_vehicles(title)
    if len(vehicles) == 1:
        return next(iter(vehicles))
    return "NONE"


LLM_MODEL = "claude-opus-5"
LLM_FALLBACK_MODEL = "claude-opus-4-8"
LLM_CACHE_PATH = os.environ.get("NZ_VEHICLE_RESOLVER_CACHE") or os.path.join(
    _HERE, "nz_vehicle_resolver/data/rep4_llm_cache.json"
)
LLM_FIELDS = ("make", "model", "chassis")

LLM_SYSTEM = """\
You read one vehicle listing title from a New Zealand car parts catalogue \
and copy three fields out of it: the make, the model and the chassis code.

Copy each field exactly as the title writes it. Do not translate a name into \
another market's name, correct its spelling, or replace it with a parent \
model or a variant. Leave a field as an empty string when the title does not \
state it. Year ranges, generation notes and trim descriptions go in none of \
the fields."""

LLM_SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in LLM_FIELDS},
    "required": list(LLM_FIELDS),
    "additionalProperties": False,
}

_llm_client = None
_llm_cache = None


def _get_llm_cache():
    global _llm_cache
    if _llm_cache is None:
        if os.path.exists(LLM_CACHE_PATH):
            with open(LLM_CACHE_PATH, encoding="utf-8") as f:
                _llm_cache = json.load(f)
        else:
            _llm_cache = {}
    return _llm_cache


def _save_llm_cache():
    with open(LLM_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_llm_cache, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def _ask_llm(title):
    """Return {"make", "model", "chassis", "llm_model", "llm_fallback"} for title.

    One LLM call. llm_model is the model that produced the answer;
    llm_fallback is True when LLM_MODEL declined and LLM_FALLBACK_MODEL
    answered instead.

    Raises on a refusal or a failed call rather than answering NONE, so a
    broken run can't pass itself off as a score.
    """
    global _llm_client
    if _llm_client is None:
        # Imported here so the other reps run without the SDK installed.
        import anthropic

        _llm_client = anthropic.Anthropic()

    response = _llm_client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=1024,
        betas=["server-side-fallback-2026-06-01"],
        fallbacks=[{"model": LLM_FALLBACK_MODEL}],
        system=LLM_SYSTEM,
        messages=[{"role": "user", "content": title}],
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": LLM_SCHEMA},
        },
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"LLM stopped with {response.stop_reason!r} on {title!r}")
    text = next(block.text for block in response.content if block.type == "text")
    fields = json.loads(text)
    answer = {field: fields[field].strip() for field in LLM_FIELDS}
    answer["llm_model"] = response.model
    answer["llm_fallback"] = any(
        entry.type == "fallback_message" for entry in response.usage.iterations or []
    )
    return answer


def llm_extract(title):
    """Return the LLM's {"make", "model", "chassis"} for title, from the cache if held."""
    cache = _get_llm_cache()
    if title not in cache:
        cache[title] = _ask_llm(title)
        _save_llm_cache()
    return cache[title]


def llm_fallback_titles():
    """Return the cached titles the fallback model answered, in title order."""
    return sorted(title for title, entry in _get_llm_cache().items() if entry.get("llm_fallback"))


def llm_extract_match(title, threshold=FUZZY_THRESHOLD):
    """Rep 4: Rep 3d on the make, model and chassis the LLM copies out of title."""
    return distinct_name_match(_llm_rebuilt(title), threshold)


def _llm_rebuilt(title):
    """Return the LLM's fields for title rebuilt as "MAKE MODEL - CHASSIS"."""
    fields = llm_extract(title)
    rebuilt = " ".join(part for part in (fields["make"], fields["model"]) if part)
    if fields["chassis"]:
        rebuilt += f" - {fields['chassis']}"
    return rebuilt


CONFIDENCE_THRESHOLD = 0.9


def distinct_name_confidence(title, threshold=FUZZY_THRESHOLD):
    """Return (label, confidence) for Rep 3d's answer on title.

    The label is distinct_name_match()'s, reached by the same steps; the
    confidence says how contested the step that decided it was:

    - Alias table: 1 / the number of different vehicles its names found in
      the listing.
    - Rep 2 fallback: the winning model score / 100, divided by the number
      of different vehicles among its candidates (after the fixed name).
    - Chassis code: 1 / the number of vehicles the code points at, which is
      1.0 whenever it decides.
    - NONE: confidence 0.0.
    """
    aliases = _get_distinct_aliases()
    hits = _alias_hits(title, aliases)
    if hits:
        return alias_lookup(title, aliases), 1 / len({label for _, label in hits})
    candidates = _fuzzy_candidates(title, threshold)
    if candidates:
        labels = {fixed_label(f"{make}|{model}", aliases) for _, (make, model, _) in candidates}
        label = fixed_label(fuzzy_match(title, threshold), aliases)
        return label, candidates[0][0] / 100 / len(labels)
    vehicles = chassis_vehicles(title)
    if len(vehicles) == 1:
        return next(iter(vehicles)), 1.0
    return "NONE", 0.0


def rep5_confidence(title, threshold=FUZZY_THRESHOLD):
    """Return Rep 4's (label, confidence) for title."""
    return distinct_name_confidence(_llm_rebuilt(title), threshold)


def abstain_match(title, threshold=FUZZY_THRESHOLD, min_confidence=CONFIDENCE_THRESHOLD):
    """Rep 5: Rep 4's label, or NONE when its confidence is below min_confidence."""
    label, confidence = rep5_confidence(title, threshold)
    return label if confidence >= min_confidence else "NONE"


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
