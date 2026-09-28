"""Assertions for harness.py.

* Gold labels fed back in as predictions score 1.00
* REPS registry ("stub" always None, "classify" the real classifier) is
  accessible and scores correctly when run through score_reps()
* label_counts()'s (gold, predicted) pairs agree with score()'s totals
* Split vehicle gold (Make, Model, Variant) is scored on MAKE|MODEL, with
  variants scored separately on the rows that have one
* Keys are matched as plain strings, and where the register merges names
  the dev gold uses the fixed one
"""

import csv

import duckdb

import classify as clf
import harness
import label_stats
import sample_errors
import vehicle_classify as vclf


def test_gold_labels_score_one():
    con = duckdb.connect()
    harness.load_gold(con)

    gold_labels = con.execute("SELECT Listing, Label FROM gold").fetchall()
    correct, n, accuracy = harness.score(con, gold_labels)

    assert n == 40, f"expected n=40, got {n}"
    assert correct == 40, f"expected 40/40 correct, got {correct}/{n}"
    print(f"gold labels: score={correct}/{n} ({accuracy:.2f})")


def test_reps_registry_accessible():
    assert "stub" in harness.REPS
    assert "classify" in harness.REPS
    assert "exact_match" in harness.REPS
    assert "rep2_fuzzy" in harness.REPS
    assert "rep3_alias" in harness.REPS
    assert "rep3b_chassis" in harness.REPS
    assert "rep3c_name_first" in harness.REPS
    assert "rep3d_distinct_names" in harness.REPS
    assert harness.REPS["stub"]("anything") is None
    assert harness.REPS["classify"] is clf.classify
    assert harness.REPS["exact_match"] is vclf.match
    assert harness.REPS["rep2_fuzzy"] is vclf.fuzzy_match
    assert harness.REPS["rep3_alias"] is vclf.alias_match
    assert harness.REPS["rep3b_chassis"] is vclf.chassis_match
    assert harness.REPS["rep3c_name_first"] is vclf.name_first_match
    assert harness.REPS["rep3d_distinct_names"] is vclf.distinct_name_match


def test_rep2_fuzzy_is_called_through_registry():
    # The other registry test only checks the binding. This one calls the
    # function the harness would call and asserts a real label comes back,
    # so a rep that is registered but never actually invoked — or invoked
    # and returning something the harness can't score — fails here.
    #
    # The title is deliberately absent from both gold sets, so the test
    # doesn't lean on a row the rep is scored against. The register holds
    # only the punctuated C-HR, so the unpunctuated listing has one right
    # answer — the repaired scorer finds it, the original returned NONE.
    classify_fn = harness.REPS["rep2_fuzzy"]
    label = classify_fn("Toyota CHR - NGX10 2016-2020")

    assert label == "TOYOTA|C-HR", f"expected TOYOTA|C-HR from the repaired rep, got {label!r}"
    assert classify_fn("Nothing matches here at all") == "NONE"


def test_rep3_alias_resolves_jdm_and_export_names():
    # Titles are absent from both gold sets. Airtrek is the JDM name and
    # Outlander the export name of one merged row, so both resolve to it;
    # Vitz/Yaris likewise. The bracketed note in "Tiida / Tiida Latio
    # (sedan)" is stripped, so Tiida Latio is a name.
    classify_fn = harness.REPS["rep3_alias"]
    assert classify_fn("Mitsubishi Airtrek - CU2W") == "MITSUBISHI|OUTLANDER"
    assert classify_fn("Mitsubishi Outlander - CW5W") == "MITSUBISHI|OUTLANDER"
    assert classify_fn("Toyota Vitz - NCP10") == "TOYOTA|YARIS"
    assert classify_fn("Nissan Tiida Latio - SC11") == "NISSAN|TIIDA"
    # The longest name wins: "Legacy Outback" is Outback's, not Legacy's.
    assert classify_fn("Subaru Legacy Outback - BH9") == "SUBARU|OUTBACK"
    # The make must be in the listing too.
    assert vclf.alias_lookup("Airtrek - CU2W") is None


def test_rep3_alias_falls_back_to_rep2():
    # MX-5 is not in the alias table, so the answer is Rep 2's.
    classify_fn = harness.REPS["rep3_alias"]
    assert vclf.alias_lookup("Mazda MX5 - NB") is None
    assert classify_fn("Mazda MX5 - NB") == vclf.fuzzy_match("Mazda MX5 - NB")
    assert classify_fn("Nothing matches here at all") == "NONE"


def test_rep3_alias_returns_one_fixed_name_per_vehicle():
    # Every name of a vehicle comes back as the same label, whether the
    # alias lookup or the Rep 2 fallback found it.
    classify_fn = harness.REPS["rep3_alias"]
    assert classify_fn("Mazda Mazda3 - BK") == classify_fn("Mazda Axela - BK") == "MAZDA|AXELA"
    assert classify_fn("Honda CR-V - RD1") == classify_fn("Honda CRV - RD1") == "HONDA|CRV"
    # Rep 2's own register names are mapped too.
    assert vclf.fixed_label("MAZDA|MAZDA3") == "MAZDA|AXELA"
    assert vclf.fixed_label("NISSAN|DATSUN 4WD") == "NISSAN|NAVARA"
    assert vclf.fixed_label("MAZDA|MX-5") == "MAZDA|MX-5"
    assert vclf.fixed_label("NONE") == "NONE"


def test_rep3b_scopes_jdm_names_to_their_chassis():
    # Titles are absent from both gold sets. RVR and Inspire are JDM names
    # the table gives only to ASX GA1W-GA4W and Accord CP2/CP3: inside that
    # range they resolve to the table's vehicle, outside it (or with no
    # chassis code) they fall back to Rep 2.
    classify_fn = vclf.chassis_match
    assert classify_fn("Mitsubishi RVR - GA4W") == "MITSUBISHI|ASX"
    assert classify_fn("Honda Inspire - CP2") == "HONDA|ACCORD"
    assert classify_fn("Mitsubishi RVR - N23W") == vclf.fuzzy_match("Mitsubishi RVR - N23W")
    assert classify_fn("Honda Inspire") == "HONDA|INSPIRE"
    assert vclf.chassis_lookup("Honda Inspire - UA1") is None
    # Punctuation in the chassis code does not matter.
    assert classify_fn("Honda Inspire - CP-2") == "HONDA|ACCORD"


def test_rep3b_keeps_register_names_unscoped():
    # Names in mvr_model resolve with or without a chassis code, as in 3a,
    # and Rep 2's register names still come back under the fixed name.
    classify_fn = vclf.chassis_match
    assert classify_fn("Mitsubishi Airtrek") == "MITSUBISHI|OUTLANDER"
    assert classify_fn("Toyota Vitz") == "TOYOTA|YARIS"
    assert classify_fn("Mazda Mazda3 - BK") == classify_fn("Mazda Axela - BK") == "MAZDA|AXELA"
    assert vclf.register_fixed_label("MAZDA|MAZDA3") == "MAZDA|AXELA"
    # A JDM-only name is not a register name, so Rep 2's answer is kept.
    assert vclf.register_fixed_label("HONDA|INSPIRE") == "HONDA|INSPIRE"
    assert classify_fn("Nothing matches here at all") == "NONE"


def test_rep3b_chassis_outranks_the_name():
    # Titles are absent from both gold sets. ACA31 is a RAV4 code, so it
    # wins over the Corolla named in the listing. BA is a Falcon code and
    # XR8 is no name in the table, so the chassis alone picks the vehicle.
    classify_fn = vclf.chassis_match
    assert classify_fn("Toyota Corolla - ACA31") == "TOYOTA|RAV4"
    assert classify_fn("Ford XR8 - BA") == "FORD|FALCON"


def test_rep3b_shared_chassis_is_settled_by_the_name():
    # BR9 is both Legacy's and Outback's. The name in the listing picks one,
    # the longest name first; with neither named, the code decides nothing.
    classify_fn = vclf.chassis_match
    assert vclf.chassis_vehicles("Subaru - BR9") == {"SUBARU|LEGACY", "SUBARU|OUTBACK"}
    assert classify_fn("Subaru Legacy - BR9") == "SUBARU|LEGACY"
    assert classify_fn("Subaru Outback - BR9") == "SUBARU|OUTBACK"
    assert classify_fn("Subaru Legacy Outback - BR9") == "SUBARU|OUTBACK"
    assert classify_fn("Subaru Impreza - BR9") == vclf.fuzzy_match("Subaru Impreza - BR9")


def test_rep3b_range_notation_matches_by_prefix():
    # Both ends of a range are prefixes: CB reaches Accord's CB3/CB4/...,
    # CD its CD3/CD4/.... A year range and a punctuated model name are not
    # ranges, and CR-V is a model name, not the Accord's CR5-CR7.
    assert vclf.chassis_vehicles("Honda Ascot - CB-CD") == {"HONDA|ACCORD"}
    assert vclf.chassis_vehicles("Ford Fairmont - BA-BF") == {"FORD|FALCON"}
    assert vclf.chassis_vehicles("Toyota Hilux 1995-2000") == set()
    assert vclf.chassis_vehicles("Honda CR-V") == set()
    assert vclf.chassis_match("Honda CR-V - RD1") == "HONDA|CRV"


def test_rep3c_name_outranks_the_chassis():
    # Titles are absent from both gold sets. Whenever Rep 3a finds a name,
    # its answer stands and the chassis code is not read: ACA31 is a RAV4
    # code, but the listing names a Corolla. The same listings under 3b
    # went to the chassis's vehicle.
    classify_fn = vclf.name_first_match
    for title in [
        "Toyota Corolla - ACA31",
        "Mitsubishi Airtrek - CU2W",
        "Honda Inspire - UA1",
        "Mazda Mazda3 - BK",
        "Subaru Legacy - BR9",
    ]:
        assert classify_fn(title) == vclf.alias_match(title), title
    assert classify_fn("Toyota Corolla - ACA31") == "TOYOTA|COROLLA"
    assert vclf.chassis_match("Toyota Corolla - ACA31") == "TOYOTA|RAV4"


def test_rep3c_chassis_only_when_no_name_matches():
    # XR8 is no name in the table and Rep 2 finds nothing, so the BA code
    # picks the Falcon. A code shared by two vehicles (BR9) has no name to
    # settle it, so it decides nothing.
    classify_fn = vclf.name_first_match
    assert vclf.alias_match("Ford XR8 - BA") == "NONE"
    assert classify_fn("Ford XR8 - BA") == "FORD|FALCON"
    assert vclf.alias_match("Subaru - BR9") == "NONE"
    assert classify_fn("Subaru - BR9") == "NONE"
    assert classify_fn("Nothing matches here at all") == "NONE"


def test_rep3d_drops_exactly_the_register_models():
    # Counted 28/09 against the register: of every JDM and export name in
    # the alias table, only these three are models the register holds
    # separately under the same make. A row's own name ("Corolla" on the
    # Corolla row) is never dropped.
    assert vclf.register_model_aliases() == {
        ("MITSUBISHI", "RVR"),
        ("HONDA", "INSPIRE"),
        ("SUZUKI", "IGNIS"),
    }


def test_rep3d_register_models_resolve_to_themselves():
    # Titles are absent from both gold sets. Under 3c each of these went to
    # the vehicle the alias table gave the name to; under 3d the name is its
    # own register model, even with that vehicle's chassis code (GA4W is an
    # ASX code, CP2 an Accord code), since the name is read first.
    classify_fn = harness.REPS["rep3d_distinct_names"]
    cases = [
        ("Mitsubishi RVR - GA4W", "MITSUBISHI|ASX", "MITSUBISHI|RVR"),
        ("Honda Inspire - CP2", "HONDA|ACCORD", "HONDA|INSPIRE"),
        ("Suzuki Ignis - HT51S", "SUZUKI|SWIFT", "SUZUKI|IGNIS"),
    ]
    for title, rep3c, rep3d in cases:
        assert vclf.name_first_match(title) == rep3c, title
        assert classify_fn(title) == rep3d, title


def test_rep3d_otherwise_matches_rep3c():
    # Titles are absent from both gold sets. Every other alias name, the
    # fixed-name mapping and the chassis-code last resort are unchanged.
    classify_fn = harness.REPS["rep3d_distinct_names"]
    for title in [
        "Mitsubishi Airtrek - CU2W",
        "Toyota Vitz - NCP10",
        "Mazda Mazda3 - BK",
        "Honda CRV - RD1",
        "Suzuki Cultus - HT51S",
        "Mitsubishi ASX - GA4W",
        "Toyota Corolla - ACA31",
        "Ford XR8 - BA",
        "Subaru - BR9",
        "Nothing matches here at all",
    ]:
        assert classify_fn(title) == vclf.name_first_match(title), title
    # Rep 3a's table is untouched.
    assert vclf.alias_match("Mitsubishi RVR - GA4W") == "MITSUBISHI|ASX"


def test_score_reps_invokes_rep2_fuzzy_per_listing():
    # score_reps() must call the rep once for every gold listing, not skip it
    # or reuse a cached prediction. Counting calls proves the function ran.
    calls = []

    def counting_fuzzy(title):
        calls.append(title)
        return vclf.fuzzy_match(title)

    con = duckdb.connect()
    listings = harness.load_gold(con)

    original = harness.REPS["rep2_fuzzy"]
    harness.REPS["rep2_fuzzy"] = counting_fuzzy
    try:
        harness.score_reps(con, listings)
    finally:
        harness.REPS["rep2_fuzzy"] = original

    assert len(calls) == 40, f"expected 40 calls, one per gold listing, got {len(calls)}"
    assert calls == [listing for (listing,) in listings], "calls must follow the gold listings"


def test_loop_over_reps():
    # Hand count (03/09, reading all 40 predictions against gold): classify.py
    # gets 3 correct (Engine, Transmission, Mirrors), 37 wrong ("other"). The
    # stub always returns None, so it scores 0. exact_match is a vehicle
    # (Make|Model) rep scored here against the part_type gold set, so none of
    # its predictions can ever equal a part_type label — it also scores 0.
    # rep2_fuzzy and the rep3 variants are the same kind of vehicle rep, so
    # they score 0 for the same reason.
    expected = {
        "stub": 0,
        "classify": 3,
        "exact_match": 0,
        "rep2_fuzzy": 0,
        "rep3_alias": 0,
        "rep3b_chassis": 0,
        "rep3c_name_first": 0,
        "rep3d_distinct_names": 0,
    }

    con = duckdb.connect()
    listings = harness.load_gold(con)

    results = harness.score_reps(con, listings)

    for name, (correct, n, accuracy) in results.items():
        assert n == 40, f"{name}: expected n=40, got {n}"
        assert correct == expected[name], (
            f"{name}: expected {expected[name]}/{n} correct, got {correct}/{n}"
        )
        print(f"{name}: score={correct}/{n} ({accuracy:.2f})")


def test_sample_errors_deterministic():
    first = sample_errors.get_samples()
    second = sample_errors.get_samples()

    assert len(first) <= 20, f"expected at most 20 sample errors, got {len(first)}"
    assert all(len(row) == 3 for row in first), "each row must be (Listing, Gold, Predicted)"
    assert first == second, "sample_errors returned different rows on the second run"


def test_sample_errors_shrinks_with_fewer_errors():
    con = duckdb.connect()
    listings = harness.load_gold(con)

    # Only the first 5 listings are wrong (predicted None); the rest are fed
    # back their own gold label, so they're correct and not errors.
    gold_by_listing = dict(con.execute("SELECT Listing, Label FROM gold").fetchall())
    predictions = [
        (listing, None if i < 5 else gold_by_listing[listing])
        for i, (listing,) in enumerate(listings)
    ]

    errors = harness.sample_errors(con, predictions, n=20)

    assert len(errors) == 5, f"expected 5 errors, got {len(errors)}"


def test_label_counts_agree_with_score():
    con = duckdb.connect()
    listings = harness.load_gold(con)

    predictions = [(listing, clf.classify(listing)) for (listing,) in listings]
    rows = harness.label_counts(con, predictions)
    correct, n, _ = harness.score(con, predictions)

    assert sum(count for _, _, count in rows) == n, "counts must cover every gold row"
    diagonal = sum(count for gold, predicted, count in rows if gold == predicted)
    assert diagonal == correct, "Gold == Predicted rows must sum to score()'s correct"

    # Hand count (03/09): classify.py's only hits are one Engine, one
    # Mirrors, one Transmission; every other listing is predicted "other",
    # which isn't a gold label.
    pairs = {(gold, predicted): count for gold, predicted, count in rows}
    assert pairs[("Engine", "Engine")] == 1
    assert pairs[("Mirrors", "Mirrors")] == 1
    assert pairs[("Transmission", "Transmission")] == 1
    assert sum(c for (_, p), c in pairs.items() if p == "other") == 37


def test_label_counts_all_correct():
    con = duckdb.connect()
    harness.load_gold(con)

    gold_labels = con.execute("SELECT Listing, Label FROM gold").fetchall()
    rows = harness.label_counts(con, gold_labels)

    assert all(gold == predicted for gold, predicted, _ in rows), "no confusions expected"
    assert sum(count for _, _, count in rows) == 40


def test_stub_predicts_none_for_every_listing():
    rows, (correct, n, _) = label_stats.get_counts("stub")

    assert (correct, n) == (0, 40), f"stub should score 0/40, got {correct}/{n}"
    assert all(predicted is None for _, predicted, _ in rows), (
        "stub returns None for everything, so every row must be a None row"
    )


def test_printed_counts_sum_to_gold_size():
    # Every rep's printed table accounts for all 40 gold listings exactly once.
    for rep in harness.REPS:
        rows, (_, n, _) = label_stats.get_counts(rep)
        cells = label_stats.to_cells(rows)

        assert n == 40, f"{rep}: expected n=40, got {n}"
        total = sum(count for _, _, count in cells)
        assert total == 40, f"{rep}: printed counts sum to {total}, expected 40"


def test_classify_has_no_none_row():
    # classify.py always returns a label, so None should not appear at all —
    # the table reports the None case only when a rep actually produces it.
    rows, _ = label_stats.get_counts("classify")

    assert not any(predicted is None for _, predicted, _ in rows), (
        "classify never returns None, so the table must have no None row"
    )


VEHICLE_DEV = "data/gold_vehicles_dev.csv"


def _vehicle_gold(con):
    """Load the split dev gold. Returns [(Listing, Label, Variant)]."""
    harness.load_gold(con, VEHICLE_DEV)
    return con.execute("SELECT Listing, Label, Variant FROM gold").fetchall()


def test_split_gold_rebuilds_the_key():
    con = duckdb.connect()
    gold = {listing: (label, variant) for listing, label, variant in _vehicle_gold(con)}

    assert len(gold) == 100
    assert gold["Honda Legend - KB1"] == ("HONDA|LEGEND", None)
    assert gold["Ford XR6 - FG-FGX 2008-2016"] == ("FORD|FALCON", "XR6")
    # NONE rows have no model, so the key is the make column alone.
    assert gold["Renault Renault All Series - All Series"] == ("NONE", None)


def test_split_gold_fed_back_scores_one():
    # Gold fed back as MAKE|MODEL|VARIANT scores every key and every variant.
    con = duckdb.connect()
    rows = _vehicle_gold(con)
    predictions = [
        (listing, f"{label}|{variant}" if variant else label) for listing, label, variant in rows
    ]

    assert harness.score(con, predictions)[:2] == (100, 100)
    # Five dev rows carry a variant (hand count, 19/09): two 318i, 520D, XR6, 1500.
    assert harness.score_variant(con, predictions)[:2] == (5, 5)


def test_variant_does_not_affect_key_score():
    # A wrong variant on the right model still scores the key; no variant at
    # all scores the key and misses every variant.
    con = duckdb.connect()
    rows = _vehicle_gold(con)

    # NONE has no model to hang a variant on, so it is left as NONE.
    wrong_variant = [
        (listing, label if label == "NONE" else f"{label}|WRONG") for listing, label, _ in rows
    ]
    assert harness.score(con, wrong_variant)[:2] == (100, 100)
    assert harness.score_variant(con, wrong_variant)[:2] == (0, 5)

    no_variant = [(listing, label) for listing, label, _ in rows]
    assert harness.score(con, no_variant)[:2] == (100, 100)
    assert harness.score_variant(con, no_variant)[:2] == (0, 5)


def test_right_variant_under_wrong_model_is_wrong():
    con = duckdb.connect()
    rows = _vehicle_gold(con)
    predictions = [
        (listing, f"WRONG|MODEL|{variant}" if variant else label)
        for listing, label, variant in rows
    ]

    assert harness.score(con, predictions)[:2] == (95, 100)
    assert harness.score_variant(con, predictions)[:2] == (0, 5)


def test_variant_is_exact_but_case_insensitive():
    # Only case and surrounding whitespace are forgiven; any other difference
    # in the variant string is a miss.
    con = duckdb.connect()
    rows = _vehicle_gold(con)

    def variant_score(transform):
        predictions = [
            (listing, f"{label}|{transform(variant)}" if variant else label)
            for listing, label, variant in rows
        ]
        return harness.score_variant(con, predictions)[:2]

    assert variant_score(str.upper) == (5, 5)
    assert variant_score(str.lower) == (5, 5)
    assert variant_score(lambda v: f" {v} ") == (5, 5)
    assert variant_score(lambda v: v[:-1]) == (0, 5)  # 318i -> 318
    assert variant_score(lambda v: v + "X") == (0, 5)
    assert variant_score(lambda v: v[0] + "-" + v[1:]) == (0, 5)


def test_merged_names_are_not_matched_by_the_harness():
    # The harness compares plain MAKE|MODEL strings: another name of the
    # same vehicle is a miss. Reps are responsible for returning the
    # vehicle's fixed name (vehicle_classify.fixed_label).
    con = duckdb.connect()
    _vehicle_gold(con)

    axela = "Mazda Axela - BL MPS"
    assert harness.score(con, [(axela, "MAZDA|AXELA")])[:2] == (1, 1)
    assert harness.score(con, [(axela, "mazda|axela")])[:2] == (1, 1)
    assert harness.score(con, [(axela, "MAZDA|MAZDA3")])[:2] == (0, 1)
    crv = "Honda CRV - RE4 2007-2011"
    assert harness.score(con, [(crv, "HONDA|CR-V")])[:2] == (0, 1)


def test_dev_gold_uses_fixed_names():
    # Where the register holds one vehicle under several names (mvr_model
    # "AXELA;MAZDA3"), dev gold uses the first — the fixed name alias_match()
    # returns. JDM and export names are not checked: gold labels the vehicle
    # the listing names, so "Honda Inspire" stays HONDA|INSPIRE even though
    # the alias table maps a later Inspire to the Accord.
    fixed = {}
    with open(vclf.ALIAS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            make = row["make"].strip().upper()
            names = [name.strip().upper() for name in row["mvr_model"].split(";")]
            for name in names:
                fixed[f"{make}|{name}"] = f"{make}|{names[0]}"

    con = duckdb.connect()
    rows = _vehicle_gold(con)

    not_fixed = [
        (listing, label, fixed[label.upper()])
        for listing, label, _ in rows
        if fixed.get(label.upper(), label.upper()) != label.upper()
    ]
    assert not_fixed == [], f"dev gold keys not under their fixed name: {not_fixed}"


def test_single_label_gold_has_no_variants():
    # Labels.csv and the held-out vehicle set have one Label column, so no
    # row is applicable and n is 0.
    con = duckdb.connect()
    harness.load_gold(con)
    gold_labels = con.execute("SELECT Listing, Label FROM gold").fetchall()

    assert harness.score_variant(con, gold_labels) == (0, 0, None)


if __name__ == "__main__":
    test_gold_labels_score_one()
    test_reps_registry_accessible()
    test_rep2_fuzzy_is_called_through_registry()
    test_rep3_alias_resolves_jdm_and_export_names()
    test_rep3_alias_falls_back_to_rep2()
    test_rep3_alias_returns_one_fixed_name_per_vehicle()
    test_rep3c_name_outranks_the_chassis()
    test_rep3c_chassis_only_when_no_name_matches()
    test_rep3d_drops_exactly_the_register_models()
    test_rep3d_register_models_resolve_to_themselves()
    test_rep3d_otherwise_matches_rep3c()
    test_score_reps_invokes_rep2_fuzzy_per_listing()
    test_loop_over_reps()
    test_sample_errors_deterministic()
    test_sample_errors_shrinks_with_fewer_errors()
    test_label_counts_agree_with_score()
    test_label_counts_all_correct()
    test_stub_predicts_none_for_every_listing()
    test_printed_counts_sum_to_gold_size()
    test_classify_has_no_none_row()
    test_split_gold_rebuilds_the_key()
    test_split_gold_fed_back_scores_one()
    test_variant_does_not_affect_key_score()
    test_right_variant_under_wrong_model_is_wrong()
    test_variant_is_exact_but_case_insensitive()
    test_merged_names_are_not_matched_by_the_harness()
    test_dev_gold_uses_fixed_names()
    test_single_label_gold_has_no_variants()
    print("\nAll assertions passed.")
