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

### Session 02 / Task 4 — harness against the re-labelled gold set

Not a rep: no error sample, no single change. Recorded for the calibration
table because a number is being predicted before it is observed.

**Date:** 02/09

**Initial setup**
- Data: Labels.csv, 40 rows, re-labelled under vocab.md V2 (12 values, frozen at Task 1)
- System: classify.py, unchanged except SPELLING_FIXES removed
- Metric: accuracy, computed in SQL by the Task 2 harness

**Prediction** — written before the harness was run
- Predicted score: 36/40 (0.90)
- Reasoning: The updated vocab set covers the majority of parts on a car.
- Written at: 02/09 04:06 NZST

**Result**
- Observed score: 3/40 (0.075) — harness printed `score=0.07 n=40`, hand count 3/40, exact agreement
- Signed error (observed - predicted): -0.825 (predicted 0.90, observed 0.075) — optimistic
- Measured at: 03/09 04:54 NZST

**Explanation**
- Why the gap: 37/40 listings were predicted as other
- What this says about my model of the system: Choosing categories to cover the entire car doesn't align with the keywords used in most parts listings.
- What I'd predict next, and why: An LLM element will need to be added to the system to improve the accuracy score

---

### Note — Trade Me API access

Not a rep: no prediction, no measurement. Recorded because it constrains what
the system can be built against.

**Date:** 05/09

- The sandbox key works against `api.tmsandbox.co.nz`.
- Search requires a full OAuth token; the consumer key alone is insufficient.
- Applied for production API access 05/09, pending approval.

---

### Note — constant-label baseline, and two values gold does not cover

Not a rep: no prediction was written before these numbers were observed, so no
calibration row. Recorded because both findings change what a score means.

**Date:** 05/09

**How measured:** a throwaway module (since deleted) built `(Listing, Predicted)`
pairs and passed them to `harness.score()` directly. `harness.py` was not edited
— `score()` takes pairs, so any callable can be measured without touching it.
`harness.classify()` is a convenience wrapper, not a required path.

**Finding 1 — classify.py is below the do-nothing baseline.**

A function that ignores the title and returns the same label every time was run
once per vocab value, against the same 40-row gold set:

| Constant | Score | Constant | Score |
|---|---|---|---|
| Moveable panels | 7/40 | Mirrors | 3/40 |
| Fixed panels | 7/40 | Interior | 3/40 |
| Exterior trim | 7/40 | Lighting | 2/40 |
| Structural | 5/40 | Drivetrain | 2/40 |
| Engine | 3/40 | Transmission | 1/40 |

`classify.py` scores 3/40. Three constants score 7/40. A function with no
inputs beats the dictionary lookup by more than 2x, so **7/40 (17%) is the
floor** any real classifier must clear to be worth having. The 3/40 in the
Session 02 / Task 4 entry above is not a weak result — it is worse than nothing.

**Finding 2 — `Electronics` and `Other` cannot score above 0.**

*Cause corrected 05/09. The original wording of this finding blamed the
harness's validity rule. That was wrong — see below.*

Both score a hard 0/40 as constants. The reason is simply that **neither value
occurs anywhere in the gold set**: Labels.csv uses 10 of the 12 vocab values,
and `Electronics` and `Other` are the two it never uses. No gold row carries
those labels, so the equality test cannot match on any of the 40 rows. 0/40 is
the arithmetic, not a rejection.

`score()` does also refuse labels absent from `SELECT DISTINCT Label FROM gold`,
and that guard fires here too — but it is not what produces the zero. Verified
by re-running the join with the guard removed entirely: `Electronics` still
scores 0/40. The two causes coincide, and I mistook the incidental one for the
operative one.

This compounds Task 4's result. `classify.py` returns `other` for 37/40
listings, and every one is wrong against this gold set — not as a scoring
artifact, but because no row in it is labelled `Other`. That is a statement
about gold's coverage, and the harness is reporting it correctly. Whether those
37 listings *should* have been labelled `Other` is a question the gold set
cannot currently answer either way.

**What this says about my model of the system:** two things. First, accuracy
here measures the classifier and the gold set's coverage together, not the
classifier alone. Second, and more usefully: I read the harness's validity
check, saw it fire, and stopped — without asking whether the score would differ
if it did not. When two mechanisms predict the same observation, noting the
first one is not a finding. The one-line check that separated them (drop the
guard, re-run) is the cheapest thing I skipped.

**What I'd predict next, and why:** adding `Electronics` and `Other` rows to
gold will move the score with no change to classify.py at all — some of the 37
`other` predictions would land on rows actually labelled `Other` and start
scoring as correct. The classifier would look better without having changed.
That confounds the next rep, so extending gold's coverage should be its own
change, with its own prediction, before any LLM work.

---

### Note — Task 7: eval harness complete

Not a rep: no prediction, no measurement, no calibration row.

**Date:** 05–06/09. Five commits, `41183d2`..`3141e41`.

`harness.py` knows nothing about any classifier. `REPS` maps a name to a
one-argument function; `score_reps()` scores every registered rep in one run;
`sample_errors()` draws a seeded random sample of wrong rows; `label_counts()`
counts every (gold, predicted) pair in SQL. Adding a rep is one dictionary
line. 10 tests, clean.

Two fixes worth remembering, both the same mistake — making output look
complete at the cost of it being true: the sampler originally took the first 20
titles alphabetically (repeatable but biased, late-alphabet brands never read),
and the count table originally printed an invented zero row.

Rep 1 predicts against the **7/40 (17%) constant-label floor**, not against
`classify.py`'s 3/40.

---


### Note — Rep 1's substrate is built; Rep 1 is not run

Not a rep: no prediction, no measurement, no calibration row. Recorded because
it changes what is being measured from here on.

**Date:** 07/09

**The field changed.** Everything measured so far was `part_type`. That was the
Day One Miniature's field. The terminus resolves *vehicle* strings, and all
five of Week 2's reps are vehicle resolution — nothing in the part_type line
feeds that ladder. Rep 1 is exact match on vehicles.

**Noisy side.** 1,721 distinct vehicles crawled from partsworld.co.nz
(31 makes, 491 models). Strings look like `Toyota Celsoir - UCF10`,
`Nissan Tiida - C11 2004-2012`, `Toyota Landcruiser100 - HZJ100`. Under the
3,000 cap, so iteration stays fast.

**Canonical side.** NZTA Motor Vehicle Register, built from the all-years file
(31 Aug 2026): **5,880,234 rows**, **193,948 distinct MAKE|MODEL pairs**.
Coverage by cut:

| Cut | Pairs kept | % of fleet |
|---|---|---|
| n>=1 | 193,948 | 100.00% |
| n>=3 | 35,409 | 96.96% |
| n>=5 | 22,246 | 96.21% |
| n>=10 | 12,728 | 95.16% <- using |
| n>=25 | 6,539 | 93.58% |
| n>=100 | 2,607 | 90.37% |

**Pre-1990 is 6.5% of the fleet but 26% of the distinct pairs.** 380,380 rows
carry 50,615 pairs, and **44,338 of those appear nowhere after 1989** —
Kingswood, Cortina, Valiant, Morris Minor, Model A. So the canonical side's
long tail is not mostly typos, as assumed: a quarter of it is classic
vehicles that are genuinely on the register. That changes what the cut is
throwing away, and it is worth re-checking in Week 4 whether n>=10 quietly
deletes the classics Partsworld actually stocks.

**Gold set.** 200 vehicles, seed 20260907, split 100 dev / 100 held-out.
Random over distinct strings, so the hand-selection bias in the 40-row
part_type set is gone. Held-out is touched twice: at labelling, and Week 4.

**Two things this does not fix.** The 40-row part_type gold set stays in
history but is no longer scored against. And Partsworld's catalogue is
semi-structured (`Make Model - Variant`), so it is a cleaner noisy side than
free-text marketplace listings — worth a line in the limitations.

---

<!-- Paste the next entry below this line. Newest at the bottom. -->

### Rep 1 — exact match, vehicles

**Date:** 10/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, labelled MAKE|MODEL (1 row labelled NONE). Frozen at 3dce7a7.
- System:          exact match against data/mvr_canonical_vehicles.csv (12,728 pairs, fleet_count >= 10)
- Metric:          accuracy, correct / n, computed in SQL by harness.score()
- No-match:        the rep returns the string "NONE", not Python None, so the one
                   NONE-labelled row is scorable. Ceiling is 100/100, not 99/100.

**Prediction** — written before running
- Predicted score: 93/100 (0.93)
- Reasoning (one or two lines): I hand-labelled them myself, and only a few of them weren't obvious.
- Written at: 10/09 05:30 NZST

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

**Result**
- Observed score:
- Signed error (observed - predicted):
- Measured at:

**Explanation**
- Why the gap:
- What this says about my model of the system:
- What I'd predict next, and why:


---

## Calibration table

Signed error = observed − predicted. Positive = under-predicted (pessimistic). Negative = over-predicted (optimistic).

Fill the row at the same time as the entry. Never backfill from memory.

| Week | Rep | Prediction | Result | Signed error |
|---|---|---|---|---|
| 0 | 0 | 32% | 32% | 0 |
| 1 | S02/T4 | 90% | 7.5% | -82.5pp |
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
