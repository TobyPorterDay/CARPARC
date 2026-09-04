"""Assertions for harness.py.

* Gold labels fed back in as predictions score 1.00
* The "always None" stub scores 0.00
* classify.py's real classifier scores 3/40, matching a hand count
"""

import duckdb

import harness


def test_gold_labels_score_one():
    con = duckdb.connect()
    harness.load_gold(con)

    gold_labels = con.execute("SELECT Listing, Label FROM gold").fetchall()
    correct, n, accuracy = harness.score(con, gold_labels)

    assert n == 40, f"expected n=40, got {n}"
    assert correct == 40, f"expected 40/40 correct, got {correct}/{n}"
    print(f"gold labels: score={correct}/{n} ({accuracy:.2f})")


def test_stub_scores_zero():
    con = duckdb.connect()
    listings = harness.load_gold(con)

    stub_predictions = [(listing, None) for (listing,) in listings]
    correct, n, accuracy = harness.score(con, stub_predictions)

    assert n == 40, f"expected n=40, got {n}"
    assert correct == 0, f"expected 0/40 correct, got {correct}/{n}"
    print(f"stub: score={correct}/{n} ({accuracy:.2f})")


def test_hand_count_against_gold_set():
    # Hand count (03/09, reading all 40 predictions against gold): 3
    # correct (Engine, Transmission, Mirrors), 37 wrong ("other").
    HAND_COUNT_CORRECT = 3

    con = duckdb.connect()
    listings = harness.load_gold(con)

    predictions = [(listing, harness.classify(listing)) for (listing,) in listings]

    correct, n, accuracy = harness.score(con, predictions)

    assert n == 40, f"expected n=40, got {n}"
    assert correct == HAND_COUNT_CORRECT, (
        f"expected {HAND_COUNT_CORRECT}/{n} correct, got {correct}/{n}"
    )
    print(f"classify.py: score={correct}/{n} ({accuracy:.2f})")


if __name__ == "__main__":
    test_gold_labels_score_one()
    test_stub_scores_zero()
    test_hand_count_against_gold_set()
    print("\nAll assertions passed.")
