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

Vehicle gold sets come in two shapes. The held-out set has a single
Label column ("MAKE|MODEL"); the dev set has split Make, Model and Variant
columns. load_gold() rebuilds Label from Make and Model, so the key every
score is taken on is still MAKE|MODEL. A vehicle rep may return
"MAKE|MODEL|VARIANT"; the variant is stripped off before the key is
compared, and scored separately by score_variant() on the rows where gold
has a variant (vocab.md: a variant is only labelled when the listing
includes one).
"""

import csv
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
    "rep3_alias": vclf.alias_match,
    "rep3b_chassis": vclf.chassis_match,
    "rep3c_name_first": vclf.name_first_match,
    "rep3d_distinct_names": vclf.distinct_name_match,
    "rep4_llm_extract": vclf.llm_extract_match,
    "rep5_abstain": vclf.abstain_match,
}

# Reps that answer NONE instead of guessing, each paired with the rep it
# abstains from. main() prints each one's precision and coverage, and lists
# the baseline's wrong rows it turns to NONE.
ABSTAINS_FROM = {
    "rep5_abstain": "rep4_llm_extract",
}

# Reps whose confidence main() records row by row: each maps to a function
# returning (label before the threshold, confidence) for a title, and the
# rows are written to confidence_path().
CONFIDENCE = {
    "rep5_abstain": vclf.rep5_confidence,
}


def confidence_path(name, gold_path=None):
    """Return where main() records name's per-row confidence for a gold set."""
    gold_stem = os.path.splitext(os.path.basename(gold_path or LABELS_PATH))[0]
    return f"data/{name}_confidence_{gold_stem}.csv"


def load_gold(con, path=None):
    path = path or LABELS_PATH
    con.execute(
        f"CREATE OR REPLACE TABLE raw_gold AS SELECT * FROM read_csv_auto('{path}', all_varchar=true)"
    )
    columns = {name for (name,) in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_gold'"
    ).fetchall()}

    if "Label" in columns:
        # Single-label gold (part_type, or a vehicle set not yet split): no
        # variant to score.
        con.execute(
            "CREATE OR REPLACE TABLE gold AS "
            "SELECT Listing, Label, CAST(NULL AS VARCHAR) AS Variant FROM raw_gold"
        )
    else:
        # Split vehicle gold: the key is MAKE|MODEL, or the make alone when
        # no model is given (NONE rows have neither).
        con.execute(
            """
            CREATE OR REPLACE TABLE gold AS
            SELECT
                Listing,
                CASE
                    WHEN NULLIF(TRIM(Model), '') IS NULL THEN TRIM(Make)
                    ELSE TRIM(Make) || '|' || TRIM(Model)
                END AS Label,
                NULLIF(TRIM(Variant), '') AS Variant
            FROM raw_gold
            """
        )

    n_rows, n_distinct = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT LOWER(TRIM(Listing))) FROM gold"
    ).fetchone()
    if n_rows != n_distinct:
        raise ValueError(
            f"{path} has duplicate titles (case/whitespace-insensitive): "
            f"{n_rows} rows but only {n_distinct} distinct titles"
        )
    return con.execute("SELECT Listing FROM gold").fetchall()


def load_predictions(con, predictions):
    """Load (Listing, Predicted) pairs, splitting Predicted into key and variant.

    PredictedKey is Predicted with anything after a second "|" removed, so
    "MAKE|MODEL|VARIANT" is keyed as "MAKE|MODEL". A part_type label or a
    plain "MAKE|MODEL" passes through unchanged. PredictedVariant is the
    third segment, or NULL when there isn't one.
    """
    con.execute("CREATE OR REPLACE TABLE raw_predictions (Listing VARCHAR, Predicted VARCHAR)")
    con.executemany("INSERT INTO raw_predictions VALUES (?, ?)", predictions)
    con.execute(
        r"""
        CREATE OR REPLACE TABLE predictions AS
        SELECT
            Listing,
            Predicted,
            regexp_replace(Predicted, '^([^|]*\|[^|]*)\|.*$', '\1') AS PredictedKey,
            NULLIF(TRIM(split_part(Predicted, '|', 3)), '') AS PredictedVariant
        FROM raw_predictions
        """
    )
    return con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]


def score(con, predictions):
    """Score (Listing, Predicted) pairs against gold. Returns (correct, n, accuracy).

    A predicted label counts as wrong if it isn't one of the labels
    actually present in gold — derived from gold.Label, not vocab.md.
    Accuracy (correct / n) is computed in SQL, not Python. Only the key is
    compared — a predicted variant neither helps nor hurts this score.
    """
    n_predictions = load_predictions(con, predictions)

    correct, n, accuracy = con.execute(
        """
        SELECT
            CAST(SUM(
                CASE
                    WHEN p.PredictedKey IS NULL THEN 0
                    WHEN v.Label IS NULL THEN 0
                    WHEN LOWER(TRIM(p.PredictedKey)) = LOWER(TRIM(g.Label)) THEN 1
                    ELSE 0
                END
            ) AS INTEGER) AS correct,
            COUNT(*) AS n,
            CAST(SUM(
                CASE
                    WHEN p.PredictedKey IS NULL THEN 0
                    WHEN v.Label IS NULL THEN 0
                    WHEN LOWER(TRIM(p.PredictedKey)) = LOWER(TRIM(g.Label)) THEN 1
                    ELSE 0
                END
            ) AS DOUBLE) / COUNT(*) AS accuracy
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.PredictedKey))
        """
    ).fetchone()

    if n != n_predictions:
        raise ValueError(
            f"join dropped rows: {n_predictions} predictions in, {n} rows after "
            "joining to gold — check for titles that don't match gold.Listing"
        )
    return correct, n, accuracy


def score_variant(con, predictions):
    """Score variants on the rows where gold has one. Returns (correct, n, accuracy).

    Rows with no gold variant are not applicable and are left out of n. A
    variant only counts when the key is also right — the right variant under
    the wrong model is not a match. accuracy is None when n is 0.

    The variant must match exactly, ignoring case and surrounding whitespace
    only: 318I matches 318i, but 318 and 318-i do not.
    """
    load_predictions(con, predictions)

    correct, n = con.execute(
        """
        SELECT
            CAST(COALESCE(SUM(
                CASE
                    WHEN LOWER(TRIM(p.PredictedKey)) = LOWER(TRIM(g.Label))
                     AND LOWER(p.PredictedVariant) = LOWER(g.Variant) THEN 1
                    ELSE 0
                END
            ), 0) AS INTEGER) AS correct,
            CAST(COUNT(*) AS INTEGER) AS n
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        WHERE g.Variant IS NOT NULL
        """
    ).fetchone()
    return correct, n, (correct / n if n else None)


def sample_errors(con, predictions, n=20, seed=0):
    """Return a random sample of up to n (Listing, Gold, Predicted) error rows.

    Fewer than n come back if there are fewer than n errors — the sample
    shrinks as a rep improves rather than padding or erroring.

    "Wrong" matches score()'s definition: no prediction, a prediction not
    among gold's labels, or a mismatch. The sample is seeded, so the same
    seed against the same predictions always draws the same rows — random,
    not first-N, but still reproducible run to run.
    """
    load_predictions(con, predictions)

    errors = con.execute(
        """
        SELECT p.Listing, g.Label, p.Predicted
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.PredictedKey))
        WHERE p.PredictedKey IS NULL
           OR v.Label IS NULL
           OR LOWER(TRIM(p.PredictedKey)) != LOWER(TRIM(g.Label))
        ORDER BY p.Listing
        """
    ).fetchall()

    return random.Random(seed).sample(errors, min(n, len(errors)))


def score_answered(con, predictions):
    """Score only the rows a rep answers. Returns (precision, coverage), each (count, n, rate).

    A row is answered when its predicted key is anything but NONE (or no
    prediction). precision is score()'s correct count over the answered
    rows; coverage is answered rows over all rows. A NONE the gold agrees
    with still counts toward score(), but is not an answer here. The
    precision rate is None when nothing is answered.
    """
    load_predictions(con, predictions)

    answered, answered_correct, n = con.execute(
        """
        SELECT
            CAST(COUNT(*) FILTER (WHERE answered) AS INTEGER),
            CAST(COUNT(*) FILTER (WHERE answered AND correct) AS INTEGER),
            CAST(COUNT(*) AS INTEGER)
        FROM (
            SELECT
                COALESCE(UPPER(TRIM(p.PredictedKey)), 'NONE') != 'NONE' AS answered,
                v.Label IS NOT NULL
                    AND LOWER(TRIM(p.PredictedKey)) = LOWER(TRIM(g.Label)) AS correct
            FROM predictions p
            JOIN gold g
                ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
            LEFT JOIN (SELECT DISTINCT Label FROM gold) v
                ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.PredictedKey))
        )
        """
    ).fetchone()
    return (
        (answered_correct, answered, answered_correct / answered if answered else None),
        (answered, n, answered / n if n else None),
    )


def abstained_errors(con, baseline, predictions):
    """Return the (Listing, Gold, Baseline) rows baseline got wrong that predictions answer NONE.

    baseline and predictions are both (Listing, Predicted) pairs over the
    same listings: the rep before a change, and the rep after it. "Wrong"
    matches score()'s definition, taken on baseline. A row whose gold is
    itself NONE comes back too; there, answering NONE is also a fix.
    """
    load_predictions(con, baseline)
    con.execute("CREATE OR REPLACE TABLE baseline_predictions AS SELECT * FROM predictions")
    load_predictions(con, predictions)

    return con.execute(
        """
        SELECT b.Listing, g.Label, b.Predicted
        FROM baseline_predictions b
        JOIN gold g
            ON LOWER(TRIM(b.Listing)) = LOWER(TRIM(g.Listing))
        JOIN predictions p
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(b.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(b.PredictedKey))
        WHERE (b.PredictedKey IS NULL
               OR v.Label IS NULL
               OR LOWER(TRIM(b.PredictedKey)) != LOWER(TRIM(g.Label)))
          AND UPPER(TRIM(p.PredictedKey)) = 'NONE'
          -- Already NONE before the change: not changed to NONE.
          AND UPPER(TRIM(COALESCE(b.PredictedKey, ''))) != 'NONE'
        ORDER BY b.Listing
        """
    ).fetchall()


def write_confidence(con, rows, path):
    """Write (Listing, Label, Confidence, Predicted) rows to path, with gold. Returns the rows written.

    Label is the rep's answer before its threshold, Predicted the answer it
    gives after. Gold is the row's gold label and Correct whether Predicted
    matches it, as score() counts it. Rows come out in listing order.
    """
    con.execute(
        "CREATE OR REPLACE TABLE confidence "
        "(Listing VARCHAR, Label VARCHAR, Confidence DOUBLE, Predicted VARCHAR)"
    )
    con.executemany("INSERT INTO confidence VALUES (?, ?, ?, ?)", rows)
    load_predictions(con, [(listing, predicted) for listing, _, _, predicted in rows])
    written = con.execute(
        """
        SELECT
            c.Listing,
            g.Label AS Gold,
            c.Label,
            c.Confidence,
            c.Predicted,
            v.Label IS NOT NULL
                AND LOWER(TRIM(p.PredictedKey)) = LOWER(TRIM(g.Label)) AS Correct
        FROM confidence c
        JOIN gold g
            ON LOWER(TRIM(c.Listing)) = LOWER(TRIM(g.Listing))
        JOIN predictions p
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(c.Listing))
        LEFT JOIN (SELECT DISTINCT Label FROM gold) v
            ON LOWER(TRIM(v.Label)) = LOWER(TRIM(p.PredictedKey))
        ORDER BY c.Listing
        """
    ).fetchall()
    if len(written) != len(rows):
        raise ValueError(f"join dropped rows: {len(rows)} in, {len(written)} matched gold")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Listing", "Gold", "Label", "Confidence", "Predicted", "Correct"])
        writer.writerows(written)
    return written


def label_counts(con, predictions):
    """Count every (gold, predicted) pair. Returns (Gold, Predicted, Count) rows.

    One row per distinct pairing, most common first — the diagonal (Gold ==
    Predicted) is what score() counts as correct, everything else is a
    confusion. Predicted comes back as the rep actually returned it,
    including labels outside gold's vocabulary and None, since which wrong
    label a rep reaches for is the point of the table.
    """
    load_predictions(con, predictions)

    return con.execute(
        """
        SELECT g.Label AS Gold, p.PredictedKey AS Predicted, CAST(COUNT(*) AS INTEGER) AS Count
        FROM predictions p
        JOIN gold g
            ON LOWER(TRIM(p.Listing)) = LOWER(TRIM(g.Listing))
        GROUP BY g.Label, p.PredictedKey
        ORDER BY Count DESC, Gold, Predicted
        """
    ).fetchall()


def score_reps(con, listings, variants=False):
    """Score every classifier in REPS against listings. Returns {name: (correct, n, accuracy)}.

    With variants=True, each value is instead (key_score, variant_score),
    both (correct, n, accuracy) tuples.
    """
    results = {}
    for name, classify_fn in REPS.items():
        predictions = [(listing, classify_fn(listing)) for (listing,) in listings]
        key_score = score(con, predictions)
        results[name] = (key_score, score_variant(con, predictions)) if variants else key_score
    return results


def main():
    con = duckdb.connect()
    listings = load_gold(con)

    for name, ((correct, n, accuracy), (v_correct, v_n, v_accuracy)) in score_reps(
        con, listings, variants=True
    ).items():
        line = f"{name}: score={correct}/{n} ({accuracy:.2f})"
        if v_n:
            line += f"  variant={v_correct}/{v_n} ({v_accuracy:.2f})"
        print(line)

    for name, baseline_name in ABSTAINS_FROM.items():
        baseline = [(listing, REPS[baseline_name](listing)) for (listing,) in listings]
        predictions = [(listing, REPS[name](listing)) for (listing,) in listings]
        baseline_correct, baseline_n, _ = score(con, baseline)
        baseline_wrong = baseline_n - baseline_correct
        caught = abstained_errors(con, baseline, predictions)
        (p_correct, p_n, precision), (answered, n, coverage) = score_answered(con, predictions)
        precision_text = f"{precision:.2f}" if precision is not None else "n/a"
        print(
            f"{name}: precision={p_correct}/{p_n} ({precision_text})"
            f"  coverage={answered}/{n} ({coverage:.2f})"
        )
        print(f"{name}: {baseline_name} errors turned to NONE={len(caught)}/{baseline_wrong}")
        for listing, gold, predicted in caught:
            print(f"  {listing} | gold={gold} | {baseline_name}={predicted}")

    for name, confidence_fn in CONFIDENCE.items():
        rows = [
            (listing, *confidence_fn(listing), REPS[name](listing)) for (listing,) in listings
        ]
        path = confidence_path(name)
        write_confidence(con, rows, path)
        print(f"{name}: confidence for {len(rows)} rows written to {path}")


if __name__ == "__main__":
    main()
