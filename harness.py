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

import duckdb

import classify as clf

LABELS_PATH = "Labels.csv"

REPS = {
    "stub": lambda title: None,
    "classify": clf.classify,
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
