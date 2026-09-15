"""Command: print 20 sample errors for a rep in harness.REPS against the gold set.

Each row is (Listing, Gold, Predicted). The rep is looked up by name in
harness.REPS rather than calling classify.classify directly, so this stays
in sync with whatever reps are registered there. harness.sample_errors() is
seeded, so the same 20 rows print every run — required for the "sample 20
errors, read all 20" step in LEARNING_LOG.md to compare across reps.
"""

import duckdb

import harness

N = 20
REP = "exact_match"


def get_samples(n=N):
    con = duckdb.connect()
    listings = harness.load_gold(con)
    classify_fn = harness.REPS[REP]
    predictions = [(listing, classify_fn(listing)) for (listing,) in listings]
    return harness.sample_errors(con, predictions, n)


def main():
    for title, gold, predicted in get_samples():
        print(f"{title} | gold={gold} | predicted={predicted}")


if __name__ == "__main__":
    main()
