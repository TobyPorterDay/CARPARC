"""Assertions for harness.py.

* Gold labels fed back in as predictions score 1.00
* REPS registry ("stub" always None, "classify" the real classifier) is
  accessible and scores correctly when run through score_reps()
* label_counts()'s (gold, predicted) pairs agree with score()'s totals
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
    assert harness.REPS["stub"]("anything") is None
    assert harness.REPS["classify"] is clf.classify
    assert harness.REPS["exact_match"] is vclf.match


def test_loop_over_reps():
    # Hand count (03/09, reading all 40 predictions against gold): classify.py
    # gets 3 correct (Engine, Transmission, Mirrors), 37 wrong ("other"). The
    # stub always returns None, so it scores 0. exact_match is a vehicle
    # (Make|Model) rep scored here against the part_type gold set, so none of
    # its predictions can ever equal a part_type label — it also scores 0.
    expected = {"stub": 0, "classify": 3, "exact_match": 0}

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


if __name__ == "__main__":
    test_gold_labels_score_one()
    test_reps_registry_accessible()
    test_loop_over_reps()
    test_sample_errors_deterministic()
    test_sample_errors_shrinks_with_fewer_errors()
    test_label_counts_agree_with_score()
    test_label_counts_all_correct()
    test_stub_predicts_none_for_every_listing()
    test_printed_counts_sum_to_gold_size()
    test_classify_has_no_none_row()
    print("\nAll assertions passed.")
