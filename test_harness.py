"""Assertions for harness.py.

* Gold labels fed back in as predictions score 1.00
* REPS registry ("stub" always None, "classify" the real classifier) is
  accessible and scores correctly when run through score_reps()
* label_counts()'s (gold, predicted) pairs agree with score()'s totals
* Split vehicle gold (Make, Model, Variant) is scored on MAKE|MODEL, with
  variants scored separately on the rows that have one
"""

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
    assert harness.REPS["stub"]("anything") is None
    assert harness.REPS["classify"] is clf.classify
    assert harness.REPS["exact_match"] is vclf.match
    assert harness.REPS["rep2_fuzzy"] is vclf.fuzzy_match


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
    # rep2_fuzzy is the same kind of vehicle rep, so it scores 0 for the same reason.
    expected = {"stub": 0, "classify": 3, "exact_match": 0, "rep2_fuzzy": 0}

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


def test_alias_names_score_as_one_model():
    # Any name merged in the alias table matches any other name in its row.
    con = duckdb.connect()
    rows = _vehicle_gold(con)
    gold = {listing: label for listing, label, _ in rows}

    def swap(label):
        # Replace a merged name with the last name of its row, e.g.
        # MAZDA|AXELA -> MAZDA|MAZDA3; leave anything unmerged alone.
        found = con.execute(
            "SELECT a2.NameKey FROM alias_names a1 JOIN alias_names a2 USING (CanonKey) "
            "WHERE a1.NameKey = UPPER(?) AND a2.NameKey != a1.NameKey",
            [label],
        ).fetchall()
        return found[-1][0] if found else label

    swapped = [(listing, swap(label)) for listing, label in gold.items()]
    n_swapped = sum(1 for (listing, p) in swapped if p != gold[listing].upper())
    assert n_swapped > 0, "the dev set should have rows with a merged name"
    assert harness.score(con, swapped)[:2] == (100, 100)

    crv = "Honda CRV - RE4 2007-2011"
    assert harness.score(con, [(crv, "HONDA|CR-V")])[:2] == (1, 1)
    # A name from a different row is still wrong: Mazda2 is not an Axela.
    axela = "Mazda Axela - BL MPS"
    assert harness.score(con, [(axela, "MAZDA|MAZDA3")])[:2] == (1, 1)
    assert harness.score(con, [(axela, "MAZDA|MAZDA2")])[:2] == (0, 1)


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
    test_alias_names_score_as_one_model()
    test_single_label_gold_has_no_variants()
    print("\nAll assertions passed.")
