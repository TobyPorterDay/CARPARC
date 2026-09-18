"""Scoring harness for CARPARC.

Loads Labels.csv into DuckDB once, joins predictions to the gold set in SQL,
and computes accuracy in SQL.

score() takes (Listing, Predicted) pairs, so the thing being measured is
supplied by the caller. REPS is the module-level registry of named
classifiers main() loops over; import harness and read harness.REPS to see
or reuse that binding elsewhere (e.g. from tests). Scoring validates
predicted labels against the distinct labels present in gold, not against
vocab.md.

Each function in REPS must obey: one string in (the raw listing title), one
string from the vocab or None out — nothing else.
"""

import os
import random

import duckdb

import classify as clf
import vehicle_classify as vclf

# Which gold set to score against. Defaults to the part_type miniature set;
# set CARPARC_GOLD to point the same harness at another one, e.g.
#   CARPARC_GOLD=data/gold_vehicles_dev.csv python3 harness.py
LABELS_PATH = os.environ.get("CARPARC_GOLD", "Labels.csv")

REPS = {
    "stub": lambda title: None,
    "classify": clf.classify,
    "exact_match": vclf.match,
    "rep2_fuzzy": vclf.fuzzy_match,
}


def load_gold(con):
    con.execute(f"CREATE OR REPLACE TABLE gold AS SELECT * FROM read_csv_auto('{LABELS_PATH}')")

    n_rows, n_distinct = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT LOWER(TRIM(Listing))) FROM gold"
    ).fetchone()
    if n_rows != n_distinct:
        raise ValueError(
            f"Labels.csv has duplicate titles (case/whitespace-insensitive): "
            f"{n_rows} rows but only {n_distinct} distinct titles"
        )
    return con.execute("SELECT Listing FROM gold").fetchall()


def score(con, predictions):
    """Score (Listing, Predicted) pairs against gold. Returns (correct, n, accuracy).

    A predicted label counts as wrong if it isn't one of the labels
    actually present in gold — derived from gold.Label, not vocab.md.
    Accuracy (correct / n) is computed in SQL, not Python.
    """
    con.execute("CREATE OR REPLACE TABLE predictions (Listing VARCHAR, Predicted VARCHAR)")
    con.executemany("INSERT INTO predictions VALUES (?, ?)", predictions)

    n_predictions = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

    correct, n, accuracy = con.execute(
        """
        SELECT
            CAST(SUM(
                CASE
                    WHEN p.Predicted IS NULL THEN 0
                    WHEN v.Label IS NULL THEN 0
                    WHEN LOWER(TRIM(p.Predicted)) = LOWER(TRIM(g.Label)) THEN 1
                    ELSE 0
                END
            ) AS INTEGER) AS correct,
            COUNT(*) AS n,
            CAST(SUM(
                CASE
                    WHEN p.Predicted IS NULL THEN 0
                    WHEN v.Label IS NULL THEN 0
                    WHEN LOWER(TRIM(p.Predicted)) = LOWER(TRIM(g.Label)) THEN 1
                    ELSE 0
                END
            ) AS DOUBLE) / COUNT(*) AS accuracy
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.Predicted))
        """
    ).fetchone()

    if n != n_predictions:
        raise ValueError(
            f"join dropped rows: {n_predictions} predictions in, {n} rows after "
            "joining to gold — check for titles that don't match gold.Listing"
        )
    return correct, n, accuracy


def sample_errors(con, predictions, n=20, seed=0):
    """Return a random sample of up to n (Listing, Gold, Predicted) error rows.

    Fewer than n come back if there are fewer than n errors — the sample
    shrinks as a rep improves rather than padding or erroring.

    "Wrong" matches score()'s definition: no prediction, a prediction not
    among gold's labels, or a mismatch. The sample is seeded, so the same
    seed against the same predictions always draws the same rows — random,
    not first-N, but still reproducible run to run.
    """
    con.execute("CREATE OR REPLACE TABLE predictions (Listing VARCHAR, Predicted VARCHAR)")
    con.executemany("INSERT INTO predictions VALUES (?, ?)", predictions)

    errors = con.execute(
        """
        SELECT p.Listing, g.Label, p.Predicted
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.Predicted))
        WHERE p.Predicted IS NULL
           OR v.Label IS NULL
           OR LOWER(TRIM(p.Predicted)) != LOWER(TRIM(g.Label))
        ORDER BY p.Listing
        """
    ).fetchall()

    return random.Random(seed).sample(errors, min(n, len(errors)))


def label_counts(con, predictions):
    """Count every (gold, predicted) pair. Returns (Gold, Predicted, Count) rows.

    One row per distinct pairing, most common first — the diagonal (Gold ==
    Predicted) is what score() counts as correct, everything else is a
    confusion. Predicted comes back as the rep actually returned it,
    including labels outside gold's vocabulary and None, since which wrong
    label a rep reaches for is the point of the table.
    """
    con.execute("CREATE OR REPLACE TABLE predictions (Listing VARCHAR, Predicted VARCHAR)")
    con.executemany("INSERT INTO predictions VALUES (?, ?)", predictions)

    return con.execute(
        """
        SELECT g.Label AS Gold, p.Predicted, CAST(COUNT(*) AS INTEGER) AS Count
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        GROUP BY g.Label, p.Predicted
        ORDER BY Count DESC, Gold, p.Predicted
        """
    ).fetchall()


def score_reps(con, listings):
    """Score every classifier in REPS against listings. Returns {name: (correct, n, accuracy)}."""
    results = {}
    for name, classify_fn in REPS.items():
        predictions = [(listing, classify_fn(listing)) for (listing,) in listings]
        results[name] = score(con, predictions)
    return results


def main():
    con = duckdb.connect()
    listings = load_gold(con)

    for name, (correct, n, accuracy) in score_reps(con, listings).items():
        print(f"{name}: score={correct}/{n} ({accuracy:.2f})")


if __name__ == "__main__":
    main()
