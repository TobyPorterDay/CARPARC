"""Check classify.py's predictions against the hand-labelled Labels.csv.

Prints which listings the classifier got right and which it got wrong,
then an overall accuracy line.
"""

import csv
import os
import sys

LABELS_PATH = "Labels.csv"
PREDICTIONS_PATH = "data/predictions.csv"


def load_csv(path, value_col):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["Listing"]: row[value_col] for row in reader}


def main():
    if not os.path.exists(PREDICTIONS_PATH):
        sys.exit(
            f"{PREDICTIONS_PATH} not found. Run classify.py first: "
            "python3 classify.py"
        )

    gold = load_csv(LABELS_PATH, "Label")
    predicted = load_csv(PREDICTIONS_PATH, "Predicted")

    gold_only = gold.keys() - predicted.keys()
    predicted_only = predicted.keys() - gold.keys()

    correct = []
    wrong = []
    for listing in gold.keys() & predicted.keys():
        if gold[listing] == predicted[listing]:
            correct.append(listing)
        else:
            wrong.append(listing)

    print(f"CORRECT ({len(correct)})")
    for listing in correct:
        print(f"  {listing}  [{gold[listing]}]")

    print(f"\nWRONG ({len(wrong)})")
    for listing in wrong:
        print(f"  {listing}  expected={gold[listing]!r} predicted={predicted[listing]!r}")

    if gold_only:
        print(f"\nIn Labels.csv but missing from predictions ({len(gold_only)}):")
        for listing in gold_only:
            print(f"  {listing}")

    if predicted_only:
        print(f"\nIn predictions but missing from Labels.csv ({len(predicted_only)}):")
        for listing in predicted_only:
            print(f"  {listing}")

    total = len(correct) + len(wrong)
    if total:
        pct = 100 * len(correct) / total
        print(f"\n{len(correct)}/{total} correct ({pct:.1f}%)")
    else:
        print("\nNo overlapping listings to compare.")


if __name__ == "__main__":
    main()
