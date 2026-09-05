"""Assertions for harness.py.

* Gold labels fed back in as predictions score 1.00
* REPS registry ("stub" always None, "classify" the real classifier) is
  accessible and scores correctly when run through score_reps()
"""

import duckdb

import classify as clf
import harness
import sample_errors


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
    assert harness.REPS["stub"]("anything") is None
    assert harness.REPS["classify"] is clf.classify


def test_loop_over_reps():
    # Hand count (03/09, reading all 40 predictions against gold): classify.py
    # gets 3 correct (Engine, Transmission, Mirrors), 37 wrong ("other"). The
    # stub always returns None, so it scores 0.
    expected = {"stub": 0, "classify": 3}

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


if __name__ == "__main__":
    test_gold_labels_score_one()
    test_reps_registry_accessible()
    test_loop_over_reps()
    test_sample_errors_deterministic()
    test_sample_errors_shrinks_with_fewer_errors()
    print("\nAll assertions passed.")
