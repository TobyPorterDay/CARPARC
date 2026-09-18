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

### Rep 1 — Contains model anywhere, vehicles

**Date:** 10/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, labelled MAKE|MODEL (1 row labelled NONE). Frozen at 3dce7a7.
- System:          model exists in data/mvr_canonical_vehicles.csv (12,728 pairs, fleet_count >= 10)
- Metric:          accuracy, correct / n, computed in SQL by harness.score()
- No-match:        the rep returns the string "NONE", not Python None, so the one
                   NONE-labelled row is scorable. Ceiling is 100/100, not 99/100.

**Prediction** — written before running
- Predicted score: 93/100 (0.93)
- Reasoning (one or two lines): I hand-labelled them myself, and only a few of them weren't obvious.
- Written at: 10/09 05:30 NZST

**Baseline results**
- Score: 91/100 (0.91)
- n: 100
- Notes: 9 errors across 4 categories, none uncategorised.

**Error categories** (sample of 9, all errors)
| # | Category | Count | Example |
|---|---|---|---|
| 1 | Prediction is the parent model line; gold is the specific variant | 3 | Listing: BMW 3 Series E36 - 318i, Gold: BMW\|318, Predicted: BMW\|3 SERIES |
| 2 | A short model name matched characters belonging to another word — a year, or the make itself | 3 | Listing: Mazda CX7 - ER 2006-2012, Gold: MAZDA\|CX-7, Predicted: MAZDA\|2 |
| 3 | A make named inside the listing won the tie-break over the actual make | 1 | Listing: Dodge Ram 1500 - 94-01, Gold: DODGE\|RAM, Predicted: RAM\|1500 |
| 4 | Listing uses the JDM name, the register uses the export name — no substring can match | 2 | Listing: Toyota Surf - RZN130, Gold: TOYOTA\|4RUNNER, Predicted: NONE |
Uncategorised / other: 0

**Result**
- Observed score: 91/100 (0.91)
- Signed error (observed - predicted): -2pp
- Measured at: 11/09 05:46 NZST

**Explanation**
- Why the gap: The predictions were at a higher level than the gold label. General model vs the specific submodel. The wrong sections of the string were selected. The gold label is different to the registry.
- What this says about my model of the system: The rule for selecting the closest model string is wrong
- What I'd predict next, and why: Adding a rule that recognises the main model string should lower the error rate

---

### Rep 2 — Fuzzy match on model, threshold 95

**Date:** 17/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, same frozen dev set as Rep 1 (3dce7a7)
- System:          rep2_fuzzy — rapidfuzz best match of the model string against
                   data/mvr_canonical_vehicles.csv (12,728 pairs, fleet_count >= 10),
                   returning "NONE" when the best score is below the threshold.
                   Registered as a new entry in REPS; Rep 1's function is unchanged.
- Metric:          accuracy, correct / n, computed in SQL by harness.score()
- Baseline to beat: Rep 1, 91/100 (0.91)

**The one specific change**
- Replace substring containment with rapidfuzz similarity, single threshold of 95.

**Prediction** — written before running
- Predicted score: 84/100 (0.84)
- Predicted fixes: 3 of Rep 1's 9 errors
- Predicted new breaks: 10 of Rep 1's 91 correct rows
- Reasoning (one or two lines): 91 - 10 + 3 = 84. Fuzzy addresses the short-model
  mismatches (Rep 1 category 2) but is expected to break more currently-correct
  rows than it fixes at this threshold.
- Written at: 17/09 06:37 NZST

**Result** — **VOID**
- **VOID:** this run scored `token_set_ratio` against the whole title — not the
  system this entry describes. Superseded by Iteration 2a. Not carried to the
  calibration table; the prediction it consumed is graded there against the
  repaired rep instead.
- Observed score: 91/100 (0.91)
- Observed fixes (Rep 1 errors now correct): 0
- Observed new breaks (Rep 1 correct rows now wrong): 0
- Signed error (observed - predicted): +7pp
- Measured at: 17/09 06:51 NZST
- Note: the same 9 rows are wrong as in Rep 1. Two of them changed their wrong
  answer (MAZDA|2 -> NONE, FORD|D -> NONE); the other seven are unchanged.

**Error categories** — n/a. This run's predictions were identical to Rep 1's
on all 100 rows, so its errors are Rep 1's errors. The table for the measured
system is in Iteration 2a below.

**Explanation** (of the void run)
- Why the gap: Predicted 10 breaks and 3 fixes, got 0 and 0.
- What this says about my model of the system: token_set_ratio scored the whole
  title, so a match was decided by whether the words were present, the same
  variable as test 1.
- What I'd predict next, and why: Score make and model separately against short
  runs of words and delete punctuation, so similarity has something to decide.

#### Iteration 2a — same rep, repaired scorer

The first run did not measure what this entry says it measures. It scored
"MAKE MODEL" against the whole title with token_set_ratio, which compares
whole strings built from the shared words — so the chassis code and the year
range sat inside the comparison and dominated it. Every dev row scored
exactly 100 or below the threshold, nothing in between: a whole-word
containment check wearing a similarity threshold. "Corrolla" against COROLLA
scored 78, and CX-7 could never match "CX7" because default_process turns a
hyphen into a word break. 5,015 of 12,728 canonical models contain a space or
punctuation.

**The repair** (one change, threshold still 95)
- Score make and model separately with fuzz.ratio, both must clear 95.
- Compare against runs of up to 4 adjacent listing words, not the whole title.
- Delete punctuation instead of turning it into a word break, so CX-7, CX7 and
  "CX 7" reduce to the same key.

Similarity now actually operates: CX7 -> MAZDA|CX-7, Xtrail -> NISSAN|X-TRAIL,
CR-V and C-HR resolve. At 95 one typo in a seven-letter model still misses
(CORROLLA vs COROLLA scores 93.3), so the threshold, not the scorer, is what
now decides the near misses.

**Prediction** — written before running the repaired rep
- Predicted score: 84/100 (0.84)
- Predicted fixes (Rep 1 errors now correct): 3
- Predicted new breaks (Rep 1 correct rows now wrong): 10
- Reasoning (one or two lines): carried over unchanged from the Rep 2 prediction
  above — 91 - 10 + 3 = 84 — and deliberately not revised after seeing the first
  run's 91/100. The repaired rep is the system that prediction was written for.
- Written at: 17/09 06:37 NZST (carried over), reused for the repair 18/09 NZST

**Result** (threshold 95, the entry's threshold)
- Observed score: 89/100 (0.89)
- Observed fixes: 1 (Mazda CX7 -> MAZDA|CX-7, the punctuation case the repair targeted)
- Observed new breaks: 3 (Honda CRV -> HONDA|CR-V, Mazda MX5 -> MAZDA|MX-5,
  Toyota Mr2 -> TOYOTA|MR 2)
- Signed error (observed - predicted): +5pp
- Measured at: 18/09 06:55 NZST

**Threshold sweep** (same repaired rep, threshold varied)
| Threshold | Score | NONE predictions | Rows differing from 95 |
|---|---|---|---|
| 100 | 89/100 (0.89) | 4 | none — identical predictions |
| 95 | 89/100 (0.89) | 4 | — |
| 80 | 89/100 (0.89) | 3 | 1: Ford XR6, NONE -> OXFORD|200 (still wrong) |

The threshold does not move the score on this dev set. 100 and 95 produce
byte-identical predictions on all 100 rows, and 80 changes one row from one
wrong answer to another. Every decision here is made at a score of exactly
100 after punctuation is stripped; the near-miss band the threshold governs
is empty, because these titles spell the model correctly.

The three new breaks are the repair's own doing and they are all one
mechanism: stripping punctuation makes CRV and CR-V identical keys, so both
canonical rows score 100 and the longest-model tie-break takes the
punctuated one. Gold uses the unpunctuated form for those three and the
punctuated form for CX-7, because the register carries both spellings as
separate rows. The register disagrees with itself, and no threshold can
settle that — the tie-break decides it.

**Error categories** (11 errors, all read — split survivors vs new)
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | New | 3 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 3 | Prediction is the parent model line; gold is the specific variant | Survivor | 3 | BMW 3 Series E36 - 318i, gold=BMW\|318, predicted=BMW\|3 SERIES |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
| 5 | A number from the year range matched a canonical model that is itself a number | Survivor | 1 | Mitsubishi FTO - DE2A 1994-2000, gold=MITSUBISHI\|FTO, predicted=MITSUBISHI\|2000 |
| 6 | Listing names the trim/variant; gold is the parent model line — the parent's name is absent from the listing | Survivor | 1 | Ford XR6 - FG-FGX 2008-2016, gold=FORD\|FALCON, predicted=NONE |
Uncategorised / other: 0

Balances: 8 survivors (Rep 1's 9 minus the CX7 fix) + 3 new breaks = 11.

Two corrections against the first pass at this table. Category 2 was recorded as
3; Ford XR6 was sitting in it and is a different mechanism — the JDM/export pair
is two names for the same model, whereas XR6 is a trim name standing in for the
model line. And the Mitsubishi FTO row was missed entirely; it is the second of
Rep 1's short-model mismatches, the one the CX7 fix did not touch.

**Categories 3 and 6 are the same inconsistency pointing in opposite
directions.** In 3, gold takes the variant (BMW|318) and the prediction takes
the parent (BMW|3 SERIES). In 6, gold takes the parent (FORD|FALCON) and the
listing only offers the variant (XR6). Four of the eleven errors turn on which
level of the model hierarchy counts as correct, and that is not settled by the
matcher — it is a question about what the gold labels mean. Nothing downstream
can score better than that decision is consistent.

**Explanation**
- Why the gap: Predicted 10 breaks, got 3. I expected a threshold of 95 to let
  loose matches through. It let none through after punctuation is stripped so
  every match scores exactly 100.
- What this says about my model of the system: The gain came from normalisation,
  not from fuzzy matching, and the threshold is inert. Of the 11 remaining
  errors only 2 are cases where the listing and the register share no string.
- What I'd predict next, and why: An alias table mapping JDM names to export
  names, plus chassis codes. Predicted score: 93/100.

*Explanations for this entry were drafted in review with the coach and edited by
me. The predictions, the measurements and the error reading are my own.*

---

## Calibration table

Signed error = observed − predicted. Positive = under-predicted (pessimistic). Negative = over-predicted (optimistic).

Fill the row at the same time as the entry. Never backfill from memory.

| Week | Rep | Prediction | Result | Signed error |
|---|---|---|---|---|
| 0 | 0 | 32% | 32% | 0 |
| 1 | S02/T4 | 90% | 7.5% | -82.5pp |
| 1 | 1 | 93% | 91% | -2pp |
| 2 | 2 | 84% | 89% | +5pp |
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

**Note on the Rep 2 row.** The 84% prediction was written on 17/09 before any
Rep 2 run, then carried over unrevised to the repaired rep on 18/09 — after the
void run's 91/100 had been seen. It is graded once, against the repaired rep
(84% -> 89%, +5pp). The void run consumed the same prediction and landed at
91/100 (+7pp); it gets no row, because one prediction cannot be counted twice.
This row is weaker calibration evidence than Rep 1's: the prediction was not
written in ignorance of a related result.
