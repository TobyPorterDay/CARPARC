# LEARNING_LOG.md

Rules for this file:

1. The prediction is written **before** the measurement is run. No exceptions.
2. A rep with no prediction is not a rep. Redo it.
3. Sample 20 errors, read all 20, categorise, *then* predict, *then* change one thing.
4. One change per rep. If two things changed, the delta means nothing.
5. Fill the calibration table at the bottom in the same sitting.

---

## Entry template — copy this block for each rep

```markdown
### Rep [N] — [short name]

**Date:**

**Initial setup**
- Data:            (what records, how many, which file)
- System:          (what is being measured — version/commit)
- Metric:          (what number, computed how)

**Baseline results**
- Score:
- n:
- Notes:

**Error categories** (sample of 20, all read)
| # | Category | Count | Example |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
Uncategorised / other:

**The one specific change**
-                  (one sentence, one change)

**Prediction** — written before running
- Predicted score:
- Reasoning (one or two lines):
- Written at: [time]

**Result**
- Observed score:
- Signed error (observed − predicted):
- Measured at: [time]

**Explanation**
- Why the gap:
- What this says about my model of the system:
- What I'd predict next, and why:
```

---

## Entries

### Rep 0 — Day One Miniature

**Date:25/08**

**Initial setup**
- Data: 40 hand-selected listing titles on lables.csv
- System: V1 of vocab.md
- Metric: accuracy only

**Baseline results**
- Score: 13/40
- n: 40
- Notes: 32%

**Error categories** (all wrong predictions read)
| # | Category | Count | Example |
|---|---|---|---|
| 1 | None | 26 | Toyota Rav4 Front Strut Bar Upper Brace Stabiliser Balancer (4T371)  expected='Bumper' predicted='other' |
| 2 | Locking | 1 |  |
| 3 |  |  |  |
| 4 |  |  |  |
Uncategorised / other: N/A

**The one specific change**
- Changed "side panel" to "Other", changed classify.py to default to "other" if no keyword matches

**Prediction** — written before running
- Predicted score: 13/40
- Reasoning: The 26 "none" errors would change to "other"
- Written at: 4:30am

**Result**
- Observed score: 13/40
- Signed error (observed − predicted): 0
- Measured at: 4:39

**Explanation**
- Why the gap: no gap, the errors changed categories
- What this says about my model of the system: The categories are not specific enough to the keywords in the listing titles
- What I'd predict next, and why: Changing the labels to match the general location of each part will map closer to the keywords in the titles

---

<!-- Paste the next entry below this line. Newest at the bottom. -->

---

## Calibration table

Signed error = observed − predicted. Positive = under-predicted (pessimistic). Negative = over-predicted (optimistic).

Fill the row at the same time as the entry. Never backfill from memory.

| Week | Rep | Prediction | Result | Signed error |
|---|---|---|---|---|
| 0 | 0 | 32% | 32% | 0 |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
