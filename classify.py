"""Dictionary lookup classifier for part_type.

Reads the 12 vocab values from vocab.md and, for each listing in Labels.csv,
tries to find one of those values as a whole word/phrase in the (lowercased)
title. If more than one value matches, the one appearing earliest in the
title wins. If nothing matches, the listing is labelled "other".

This is a deliberately dumb baseline: no synonyms, no stemming, exact
lowercase match only. It exists to show where a literal dictionary falls
short, not to be a good classifier.
"""

import csv
import re

VOCAB_PATH = "vocab.md"
LABELS_PATH = "Labels.csv"
OUTPUT_PATH = "data/predictions.csv"

ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|")


def load_vocab(path):
    """Parse the '## Values' table in vocab.md and return the list of values."""
    values = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            match = ROW_RE.match(line)
            if not match:
                continue
            value = match.group(2).strip()
            if value == "Value":  # header row
                continue
            values.append(value)
    return values


def classify(title, vocab):
    """Return the vocab value whose keyword appears earliest in title, else 'other'."""
    lower_title = title.lower()
    matches = []
    for value in vocab:
        keyword = value.lower()
        pattern = r"\b" + re.escape(keyword) + r"\b"
        m = re.search(pattern, lower_title)
        if m:
            matches.append((m.start(), value))
    if not matches:
        return "other"
    matches.sort(key=lambda pair: pair[0])
    return matches[0][1]


def main():
    vocab = load_vocab(VOCAB_PATH)

    with open(LABELS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        listings = [row["Listing"] for row in reader]

    predictions = []
    for title in listings:
        label = classify(title, vocab)
        predictions.append((title, label))
        print(f"{title} -> {label}")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Listing", "Predicted"])
        writer.writerows(predictions)

    print(f"\nWrote {len(predictions)} predictions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
