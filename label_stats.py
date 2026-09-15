"""Command: count every (gold, predicted) pair for a rep in harness.REPS.

Prints a Gold / Predicted / Count table over the whole gold set, most
common pairing first. Rows where Gold == Predicted are the ones score()
counts as correct; the rest show which label the rep reaches for instead.

The rep is looked up by name in harness.REPS, like sample_errors.py, so
this stays in sync with whatever reps are registered there. Pass a rep name
as the first argument to count a different one:

    python3 label_stats.py stub
"""

import sys

import duckdb

import harness

REP = "exact_match"


def get_counts(rep=REP):
    con = duckdb.connect()
    listings = harness.load_gold(con)
    classify_fn = harness.REPS[rep]
    predictions = [(listing, classify_fn(listing)) for (listing,) in listings]
    return harness.label_counts(con, predictions), harness.score(con, predictions)


def to_cells(rows):
    """Render label_counts() rows for printing, as (Gold, Predicted, Count) strings.

    A rep that returns None gets None rows straight from the data; a rep
    that never returns None gets no None row at all.
    """
    return [(gold, str(predicted), count) for gold, predicted, count in rows]


def main():
    rep = sys.argv[1] if len(sys.argv) > 1 else REP
    if rep not in harness.REPS:
        sys.exit(f"unknown rep {rep!r}; known reps: {', '.join(harness.REPS)}")

    rows, (correct, n, accuracy) = get_counts(rep)
    cells = to_cells(rows)

    gold_w = max(len("Gold"), max(len(gold) for gold, _, _ in cells))
    pred_w = max(len("Predicted"), max(len(pred) for _, pred, _ in cells))

    print(f"rep: {rep}\n")
    print(f"{'Gold':<{gold_w}}  {'Predicted':<{pred_w}}  Count")
    for gold, predicted, count in cells:
        print(f"{gold:<{gold_w}}  {predicted:<{pred_w}}  {count:>5}")
    print(f"\noverall: {correct}/{n} ({accuracy:.2f})")


if __name__ == "__main__":
    main()
