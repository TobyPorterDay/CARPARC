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

### Rep 2 rerun — dev gold relabelled for model and variant

Not a rep: nothing in the system changed and no prediction was written before
the run, so there is no calibration row. Recorded because the dev set changed
under Rep 2, so its 89/100 no longer describes the current gold.

**Date:** 19/09

**What changed** (gold only)
- vocab.md gained a model/variant rule: the model is the parent line (Falcon,
  3 Series), the variant is the sub-model (XR6, 330i), and each is labelled
  only if the listing includes it.
- data/gold_vehicles_dev.csv split `Label` into `Make`, `Model`, `Variant`.
  Same 100 listings; the NONE row stays NONE.
- Five rows relabelled under the rule:

| Listing | Old gold | New key | Variant |
|---|---|---|---|
| BMW 3 Series E46 - 318i | BMW\|318 | BMW\|3 Series | 318i |
| BMW 3 Series E36 - 318i | BMW\|318 | BMW\|3 Series | 318i |
| BMW 5 Series E39 - 520D | BMW\|520D | BMW\|5 Series | 520D |
| Ford XR6 - FG-FGX 2008-2016 | FORD\|FALCON | FORD\|FALCON | XR6 |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | DODGE\|RAM | 1500 |

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, relabelled as above (uncommitted at 2afb9ca)
- System:          rep2_fuzzy, threshold 95, unchanged since Iteration 2a
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
                   — a variant counts only when the key is also right

**Result**
- Key score: 92/100 (0.92), up from 89/100
- Variant score: 0/5 (0.00) — rep2_fuzzy returns MAKE|MODEL only
- Measured at: 19/09 08:53 NZST

**Reconciliation:** 89 + 3 = 92. The three BMW rows (Iteration 2a category 3)
were wrong only because gold took the variant; the rep already predicted the
parent line, and gold now does too. No row that was correct went wrong.

**Remaining errors** (8, all read — every one a survivor from Iteration 2a)
| Listing | Gold | Predicted | 2a category |
|---|---|---|---|
| Honda CRV - RE4 2007-2011 | HONDA\|CRV | HONDA\|CR-V | 1 |
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 | 1 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 | 1 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE | 2 |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE | 2 |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 | 4 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 | 5 |
| Ford XR6 - FG-FGX 2008-2016 | FORD\|FALCON | NONE | 6 |

**VOID: the 93/100 prediction for the alias-table rep** (Rep 2 Explanation
above). It was written against the old gold, where the three BMW rows were
errors. The baseline it was predicted from is gone, so it is not graded. The
next rep needs a fresh prediction against 92/100.

---

### Rep 3a — Alias table

**Date:** 19/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant, relabelled
                   under the vocab.md model/variant rule (see Rep 2 rerun)
- System:          alias table data/alias_vehicles.csv — top 40 MVR vehicles, 192
                   rows of chassis codes, JDM name and export name, with alternate
                   MVR names merged. Covers 39.63% of the MVR (2,340,272 of 5,905,376).
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
- Baseline to beat: Rep 2 on the relabelled gold, 92/100 (0.92)
                   — briefly 90/100 after a gold relabel; relabel reverted, 92/100
                   stands (see Revert below)

**The one specific change**
- Use the merged JDM/import model name for both instances: a listing that names
  either the JDM name or the export name resolves to the same merged model in
  data/alias_vehicles.csv. Chassis codes are not used in this rep.

**Context on the change** — added 19/09, after the prediction, before any run
- How it is applied: vehicle_classify.alias_match() looks the listing up by
  name — every mvr_model name, JDM name and export name in the table points
  at its vehicle, the make must also appear, and the longest name found wins.
  No name found -> Rep 2's answer. Each vehicle comes back under one fixed
  name, the first name in its mvr_model (MAZDA|AXELA for Axela and Mazda3,
  HONDA|CRV for CR-V and CRV), including when Rep 2 answers.
- The harness no longer compares through the alias table: keys are matched
  as plain MAKE|MODEL strings again, so gold must use the fixed name where
  register names are merged (AXELA not MAZDA3, CRV not CR-V). JDM and export
  names are not held to this: gold labels the vehicle the listing names.
- Which dev listings the change can touch: 25 of 100 name a vehicle in the
  table. 23 use a name that is also the register name (Hilux, Corolla,
  Axela, CRV ...), which Rep 2 already matched. Two use a JDM-only name, and
  none an export-only name:

| Listing | Name | Table maps it to | Table rows (chassis) |
|---|---|---|---|
| Honda Inspire - CB-CC 1989-1995 | Inspire (JDM) | HONDA\|ACCORD | CP2;CP3 |
| Mitsubishi RVR - N28W 1991-1997 | RVR (JDM) | MITSUBISHI\|ASX | GA1W-GA4W |

- The table records each name against a chassis range, but the lookup
  ignores chassis codes, so a name is applied to every generation. Neither
  listing's chassis (CB-CC, N28W) is in the range the table gives.
- Gold relabelled to match the table, after the prediction was written
  (**REVERTED 19/09 13:16** — see Revert below):

| Listing | Old gold | New gold |
|---|---|---|
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | HONDA\|ACCORD |
| Mitsubishi RVR - N28W 1991-1997 | MITSUBISHI\|RVR | MITSUBISHI\|ASX |

  These two rows now agree with the alias table by construction. Rep 2's
  92/100 was measured on the old labels and is not re-run here.
  gold_vehicles_heldout.csv also has an Inspire row (UA, 1998-2003),
  left at HONDA|INSPIRE — the held-out set is not touched before Week 4.

**Baseline rerun — Rep 2 on the relabelled gold** (**REVERTED** with the
relabel — see Revert below; kept as a record, no longer the baseline)

Not a rep: rep2_fuzzy is unchanged and no prediction was written, so there is
no calibration row. Run to replace the 92/100 baseline, which was measured on
the old labels.

- Data:            data/gold_vehicles_dev.csv, 100 rows, Inspire and RVR relabelled as above
- System:          rep2_fuzzy, threshold 95, unchanged
- Key score:       90/100 (0.90), down from 92/100
- Variant score:   0/5 (0.00) — rep2_fuzzy returns MAKE|MODEL only
- Measured at:     19/09 13:11 NZST

**Reconciliation:** 92 − 2 = 90. The two relabelled rows were correct under
the old gold (predicted HONDA|INSPIRE and MITSUBISHI|RVR) and are now wrong.
No other row changed.

**Remaining errors** (10, all read)
| Listing | Gold | Predicted |
|---|---|---|
| Honda CRV - RE4 2007-2011 | HONDA\|CRV | HONDA\|CR-V |
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 |
| Ford XR6 - FG-FGX 2008-2016 | FORD\|FALCON | NONE |
| Honda Inspire - CB-CC 1989-1995 | HONDA\|ACCORD | HONDA\|INSPIRE |
| Mitsubishi RVR - N28W 1991-1997 | MITSUBISHI\|ASX | MITSUBISHI\|RVR |

**Revert — gold restored, baseline back to 92/100**

The Inspire and RVR relabel was undone (data/gold_vehicles_dev.csv restored to
05c2e07): gold labels the vehicle the listing names, not the alias table's
mapping for a different generation. Rep 3a runs as specified — names only,
no chassis codes — so the two rows are expected to cost it, and show what
chassis scoping would add in a later rep.

- Rep 2 rerun on the restored gold: 92/100 (0.92), variants 0/5, same 8
  errors as the Rep 2 rerun entry. Measured at 19/09 13:16 NZST.
- Baseline to beat: **92/100 (0.92)**. The 97/100 prediction was written
  against 92/100 on these labels, so it stands.

**Prediction** — written before running
- Predicted score: 97/100 (0.97)
- Reasoning (one or two lines): The harness will recognise both names as one
  model, eliminating the errors caused by a non-matched model.
- Written at: 19/09 09:57 NZST

**Result**
- Observed score: 91/100 (0.91), down 1 from the 92/100 baseline
- Variant score: 0/5 (0.00) — alias_match returns MAKE|MODEL only
- Signed error (observed − predicted): −6pp
- Measured at: 19/09 13:27 NZST

**Reconciliation:** 92 + 1 − 2 = 91. Three rows differ from Rep 2:

| Listing | Gold | Rep 2 | Rep 3a | Effect |
|---|---|---|---|---|
| Honda CRV - RE4 2007-2011 | HONDA\|CRV | HONDA\|CR-V | HONDA\|CRV | +1 — fixed register name, not a JDM/export name |
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | HONDA\|INSPIRE | HONDA\|ACCORD | −1 — JDM name applied to the wrong generation |
| Mitsubishi RVR - N28W 1991-1997 | MITSUBISHI\|RVR | MITSUBISHI\|RVR | MITSUBISHI\|ASX | −1 — JDM name applied to the wrong generation |

**Remaining errors** (9, all read)
| Listing | Gold | Predicted |
|---|---|---|
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | HONDA\|ACCORD |
| Mitsubishi RVR - N28W 1991-1997 | MITSUBISHI\|RVR | MITSUBISHI\|ASX |
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 |
| Ford XR6 - FG-FGX 2008-2016 | FORD\|FALCON | NONE |

The last seven are Rep 2 errors unchanged; none of those vehicles is in the
alias table.

**Error categories** (all 9 errors, all read — split survivors vs new)

Categories 1–6 are Iteration 2a's, numbered as there. Category 3 has no rows:
its three BMW rows were resolved by the Rep 2 rerun relabel.

| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
| 5 | A number from the year range matched a canonical model that is itself a number | Survivor | 1 | Mitsubishi FTO - DE2A 1994-2000, gold=MITSUBISHI\|FTO, predicted=MITSUBISHI\|2000 |
| 6 | Listing names the trim/variant; gold is the parent model line — the parent's name is absent from the listing | Survivor | 1 | Ford XR6 - FG-FGX 2008-2016, gold=FORD\|FALCON, predicted=NONE |
| 7 | The JDM model from the wrong year is predicted instead of the what the listing title and the gold set state | New | 2 | Honda Inspire - CB-CC 1989-1995, gold: HONDA|INSPIRE, predicted:HONDA|ACCORD |
Uncategorised / other:

Balances: 7 survivors (Rep 2's 8 minus the CRV fix, category 1) + 2 new = 9.

**Same run, other reps:** exact_match (Rep 1) scored 94/100 (0.94) on this
gold, against 91/100 when Rep 1 was logged on 11/09.

Why Rep 1 moved: the gold changed, Rep 1 did not. Rerun on the pre-relabel
gold (2afb9ca) it still scores 91/100. The Rep 2 rerun relabel moved three
BMW rows to the parent line, which Rep 1 already predicted, so 91 + 3 = 94 —
the same +3 that took Rep 2 from 89 to 92. No row broke.

| Listing | Old gold | New gold | Rep 1 predicted |
|---|---|---|---|
| BMW 3 Series E36 - 318i | BMW\|318 | BMW\|3 SERIES | BMW\|3 SERIES |
| BMW 3 Series E46 - 318i | BMW\|318 | BMW\|3 SERIES | BMW\|3 SERIES |
| BMW 5 Series E39 - 520D | BMW\|520D | BMW\|5 SERIES | BMW\|5 SERIES |

Rep 1 vs Rep 2 on this gold, 94 vs 92 — they agree on 91 rows:

| Listing | Gold | Rep 1 (exact_match) | Rep 2 (rep2_fuzzy) |
|---|---|---|---|
| Honda CRV - RE4 2007-2011 | HONDA\|CRV | HONDA\|CRV ✓ | HONDA\|CR-V |
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX5 ✓ | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR2 ✓ | TOYOTA\|MR 2 |
| Mazda CX7 - ER 2006-2012 | MAZDA\|CX-7 | MAZDA\|2 | MAZDA\|CX-7 ✓ |

Both miss the other five (Ram 1500, XR6, Emmeraude, FTO, Surf). The gap is
Iteration 2a category 1: Rep 2 deletes punctuation, so CRV/CR-V, MX5/MX-5
and MR2/MR 2 become one key and the tie-break picks the register spelling
gold does not use; Rep 1 matches the listing's own spelling. Rep 2's one
gain, CX7, is the punctuation case its repair targeted — Rep 1 matched the
"2" in "2006".

**Conclusion — Rep 3b fallback**
- Rep 2's layer on this gold: net -2 (1 gained, 3 lost)
- Rep 3b falls back to: Rep 2 (unchanged — the swap to Rep 1 was dropped because it would
  be a second change inside the rep)
- Reason (one line): keeping the fallback fixed means 3b's delta is chassis parsing alone.
- Rep 3b baseline to beat: 91/100 (rep3_alias on this gold)
- Known cost of keeping Rep 2: it loses 3 rows Rep 1 gets right (CRV, MX5, MR2), so
  category 1 stays live rather than disappearing with the fallback.

**Fix list** — one line per category, counted against the 9 Rep 3a errors
| # | Category | Proposed change | Errors it can reach (listings) | Could break (currently correct rows) | Order |
|---|---|---|---|---|---|
| 1 | Punctuation collision | Merge the register's two spellings of the same vehicle so they resolve to one fixed name — MAZDA MX5;MX-5 and TOYOTA MR2;MR 2 — the way CRV;CR-V was merged in 3a. Fixed name = the spelling gold uses. *Not needed if 3b falls back to Rep 1*, which already gets both right. | 2 — Mazda MX5 - NB 1998-2005; Toyota Mr2 - SW20 1990-1994 | 0 found — no dev gold row uses MX-5 or MR 2. Only risk: gold later labelled with the other spelling. | 4 |
| 2 | JDM name, register uses export name | Preference rule first: prefer the export name when a listing uses the JDM name. Surf/4Runner and Emmeraude/Galant are not in the alias table, so both are also added (they sit outside the top 40 by fleet — an exception to the selection rule) | 2 - Toyota Surf - RZN130, Mitsubishi Emmeraude - E52A 1992-1997 | 19 dev rows have a JDM name as gold; for 17 the JDM name is also the fixed name. The preference rule can flip Mazda Axela - BL MPS (MAZDA\|AXELA) and Mazda Atenza - GH 2008-2012 (MAZDA\|ATENZA) — the prediction for this iteration must account for up to −2 | 2 |
| 4 | Make named inside the listing | The leftmost make name in the title is the make, matching the longest make name (so Land Rover beats Land); the model is the longest register model name found in the rest of the title | 1 - Dodge Ram 1500 - 94-01 | 3 currently correct rows contain a second make word: Suzuki Swift - ZC83S; Land Rover Discovery - Series 2 1999-2004; Mazda Titan - U-WGLAH SLT 1989-Present. Also 4 rows have a two-word model (BMW 3 Series x2, BMW 5 Series, Hyundai Santa Fe), which one-word matching would break | 3 |
| 5 | Year-range number matched a numeric model | A digits-only token cannot be a model | 1 - Mitsubishi FTO - DE2A 1994-2000 | 0 in dev — no gold model is digits-only. Limitation: the register does hold digits-only models (BMW 318, 320, MAZDA 121), so this rule is wrong on them and only holds while none is in gold | 3 |
| 6 | Listing names variant, parent absent | Add a variant column to the alias table (XR6 -> FALCON) and resolve a variant name to its parent model | 1 - Ford XR6 - FG-FGX 2008-2016 | 0 | 2 |
| 7 | JDM name mapped to a different vehicle's generation | Stick with the chassis code | 2 - Honda Inspire - CB-CC 1989-1995, Mitsubishi RVR - N28W 1991-1997 | 0 | 1 |

- Categories chassis-code parsing (Rep 3b) can reach: 2 and 6
- Total errors reachable by Rep 3b: 3 of 9

**Explanation**
- Why the gap: The same errors occured, plus two new ones caused by the rule to treat the JDM and Export models are one, but to predict either one. I didn't count the errors when I made the prediction.
- What this says about my model of the system: The resolver always chooses the model name that occur first, even if the listing states the other model name.
- What I'd predict next, and why: 94/100, the chassis code will help the harness make the right choice between the JDM and Export model name.

---

### Rep 3b — Chassis-code parsing

**Date:** 22/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant (Inspire and RVR at
                   their original labels)
- System:          rep3_alias + chassis-code parsing; fallback unchanged (Rep 2, rep2_fuzzy, threshold 95)
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
- Baseline to beat: Rep 3a, 91/100 (0.91)

**The one specific change**
- Read the chassis code in the listing and use it to pick the alias-table row, so a
  JDM name is only applied inside its own chassis range. Everything else unchanged.

**Prediction** — written before running
- Predicted score: 95/100 (0.95)
- Reasoning (one or two lines): Matching the chassis codes should correct the errors caused by selecting the JDM vs the export model.
- Written at: 22/09 05:06 NZST

**Result**
- Observed score: 87/100
- Variant score: 0/5
- Signed error (observed − predicted): -8pp
- Measured at: 06:07 on 22/09

**Reconciliation:** 91 + 2 − 6 = 87. The new correct rows are Mitsubishi RVR - N28W 1991-1997 and Ford XR6 - FG-FGX 2008-2016. Eight rows differ from Rep 3a

**Remaining errors** (13, all read)
| Listing | Gold | Predicted |
|---|---|---|
| Toyota Sprinter - AE110 | TOYOTA\|SPRINTER | TOYOTA\|COROLLA |
| Toyota Sprinter - AE111 | TOYOTA\|SPRINTER | TOYOTA\|COROLLA |
| Toyota Allex - ZZE122 2000-2006 | TOYOTA\|ALLEX | TOYOTA\|COROLLA |
| Toyota Ceres - AE101 1992-1995 | TOYOTA\|CERES | TOYOTA\|COROLLA |
| Ford Futura - BA | FORD\|FUTURA | FORD\|FALCON |
| Ford Fairlane - BA-BF 2003-2006 | FORD\|FAIRLANE | FORD\|FALCON |
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | HONDA\|ACCORD |
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 |

**Error categories**
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
| 5 | A number from the year range matched a canonical model that is itself a number | Survivor | 1 | Mitsubishi FTO - DE2A 1994-2000, gold=MITSUBISHI\|FTO, predicted=MITSUBISHI\|2000 |
| 7 | JDM name mapped to a different vehicle's generation, even with the chassis code. Likely not being read correctly | Survivor | 1 | Honda Inspire - CB-CC 1989-1995, gold=HONDA\|INSPIRE, predicted=HONDA\|ACCORD |
| 8 | The chassis code matches a different model to the listing | New | 6 | Toyota Sprinter - AE110, gold=TOYOTA\|SPRINTER, predicted=TOYOTA\|COROLLA | 

**Explanation**
- Why the gap: 6 new errors caused by the chassis code overiding the model name in the listing. 
- What this says about my model of the system: The chassis code causes the system to default to the main model that uses that chassis.
- What I'd predict next, and why: 93/100, the six new errors should be corrected by only using the chassis code if there is no match for the model name.

---

### Rep 3c — Name first, chassis code only when no name matches

**Date:** 23/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant (commit: 2c841a8 )
- System:          rep3b_chassis with one change (below); fallback unchanged (Rep 2,
                   rep2_fuzzy, threshold 95)
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
- Baseline to beat: Rep 3b, 87/100 (0.87)

**The one specific change**
- The system prioritises a model name match before trying to match the chassis code if it can't find one. It only reads the chassis codes when all of the alias table returns "NONE". A fuzzy name match from rep 2 counts as a match.

**Which rows the change can reach** — counted before running
- Rep 3b errors it should fix (listings): Toyota Allex - ZZE122 2000-2006, Toyota Sprinter - AE110, Toyota Sprinter - AE111, Toyota Ceres - AE101 1992-1995, Ford Futura - BA, Ford Fairlane - BA-BF 2003-2006, Honda Inspire - CB-CC 1989-1995
- Currently correct rows it could break (listings): Ford XR6 - FG-FGX 2008-2016, Mitsubishi RVR - N28W 1991-1997

**Prediction** — written before running
- Predicted score: 94/100 (revised from 93/100 after counting the rows that should be corrected)
- Reasoning (one or two lines): The seven errors listed above should be corrected.
- Written at: 05:35 on 23/09

**Result**
- Observed score: 92/100
- Variant score: 0/5
- Signed error (observed − predicted): -2pp
- Measured at: 06:46 on 23/09

**Reconciliation:** 87 + 6 − 1 = 92
- Rows fixed: Toyota Sprinter - AE110, Toyota Sprinter - AE111, Toyota Allex - ZZE122 2000-2006, Toyota Ceres - AE101 1992-1995, Ford Futura - BA, Ford Fairlane - BA-BF 2003-2006
- Rows broken: Mitsubishi RVR - N28W 1991-1997

**Remaining errors** (all read)
| Listing | Gold | Predicted |
|---|---|---|
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 |
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | HONDA\|ACCORD |
| Mitsubishi RVR - N28W 1991-1997 | MITSUBISHI\|RVR | MITSUBISHI\|ASX |

**Error categories**
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
| 5 | A number from the year range matched a canonical model that is itself a number | Survivor | 1 | Mitsubishi FTO - DE2A 1994-2000, gold=MITSUBISHI\|FTO, predicted=MITSUBISHI\|2000 |
| 7 | JDM name mapped to a different vehicle's generation — the name is matched first, so the chassis code is never read | 1 Survivor (Inspire), 1 New (RVR) | 2 | Mitsubishi RVR - N28W 1991-1997, gold=MITSUBISHI\|RVR, predicted=MITSUBISHI\|ASX |
Uncategorised / other: 0

Balances: 7 survivors (Rep 3b's 13 minus the 6 category 8 fixes) + 1 new (RVR, correct in 3b, back in category 7 as in 3a) = 8. No new categories; category 8 is cleared.

**Explanation**
- Why the gap: The Honda Inspire model name is still mapped to Accord, so it defaults to the model name instead of the chassis code. Same issue for the Mistsubishi RVR row. The XR6 row didn't break, so the system moves to the chassis codes when a model match can't be found.
- What this says about my model of the system: The system is ignoring the chassis codes because the alias table rule is mapping the listing to the other name of the model.
- What I'd predict next, and why: 94/100, removing the alias names that are listed in the MVR should prevent the system swapping to the wrong model name. One more iteration then move on to rep 4. The orginal plan was to change the function to match the model name and then confirm it using the chassis code, but I discovered this wouldn't work when checking which rows would be corrected or broken.

---

### Rep 3d — Drop alias names that are listed in the MVR (final Rep 3 iteration)

Last iteration of Rep 3 (cap set in the Rep 3c explanation). Whatever this
scores is Rep 3's result — the deterministic ceiling Rep 4 is measured against.

**Date:** 28/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant (commit: b82b3fa )
- System:          rep3c_name_first with one change (below); fallback unchanged (Rep 2,
                   rep2_fuzzy, threshold 95)
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
- Baseline to beat: Rep 3c, 92/100 (0.92)

**The one specific change**
- Drop the alias names that are already seperate models in the register. Names dropped: RVR, Inspire, Ignis

**Which rows the change can reach** — counted before running
- Rep 3c errors it should fix (listings): Mitsubishi RVR - N28W 1991-1997, Honda Inspire - CB-CC 1989-1995
- Currently correct rows it could break (listings): Suzuki Swift - ZC83S

**Prediction** — written before running
- Predicted score: 94/100
- Reasoning (one or two lines): The two errors from Rep 3c should be corrected since the alias table will treat the JDM and export model names seperately.
- Written at: 06:59 on 25/09.

**Result**
- Observed score: 94/100
- Variant score: 0/5
- Signed error (observed − predicted): 0pp
- Measured at: 07:49 on 28/09

**Reconciliation:** 92 + 2 − 0 = 94
- Rows fixed: Honda Inspire - CB-CC 1989-1995, Mitsubishi RVR - N28W 1991-1997
- Rows broken: None

**Remaining errors** (all read)
| Listing | Gold | Predicted |
|---|---|---|
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |
| Mitsubishi FTO - DE2A 1994-2000 | MITSUBISHI\|FTO | MITSUBISHI\|2000 |

**Error categories**
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
| 5 | A number from the year range matched a canonical model that is itself a number | Survivor | 1 | Mitsubishi FTO - DE2A 1994-2000, gold=MITSUBISHI\|FTO, predicted=MITSUBISHI\|2000 |
Uncategorised / other: 0

Balances: 8 survivors from Rep 3c minus the 2 category 7 fixes (Inspire, RVR) = 6, + 0 new = 6. No new categories; category 7 is cleared.

**Explanation**
- Why the gap: None, the two errors from rep 3c were fixed with no rows broken.
- What this says about my model of the system: Spelling, missing data, and parsing rules are causing the remaingin errors.
- What I'd predict next, and why: 98/100, using an LLM workflow to match model names against the canonical titles should solve these issues.

**Rep 3 result — the deterministic ceiling**
- Final score: 94/100 (Rep 1: 94, Rep 2: 92, Rep 3a: 91, 3b: 87, 3c: 92, 3d: 94)
- Fleet coverage of the alias table: 39.6%
- Why the ceiling sits where it does (one or two lines): The iterations after rep 1 were focused on fixing other errors than the six remaining ones. Two of the errors are a result of using rep 2 as the fall back.

---

### Rep 4 — LLM Extraction to canonical lookup

**Date:** 29/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant (commit: 311d267)
- System:          rep4_llm_extract (vehicle_classify.py): LLM extracts make, model and
                   chassis from the title; its output is passed to the rep3d matcher.
                   Model: claude-opus-5 (fallback claude-opus-4-8 on a refusal), effort low,
                   JSON schema output; no temperature setting (Opus 5 does not accept one).
                   Prompt: LLM_SYSTEM in vehicle_classify.py (commit: 311d267).
                   Input: title only. Replies cached per title in data/rep4_llm_cache.json.
                   Refused or cut-off reply → the run stops with an error (no NONE).
                   Run: all 100 calls answered by claude-opus-5; fallback used 0 times
                   (data/rep4_llm_cache.json, commit: f862832).
- Metric:          key accuracy on MAKE|MODEL, correct / n, harness.score(); variant
                   accuracy on the 5 rows with a gold variant, harness.score_variant()
- Baseline to beat: Rep 3d, 94/100 (0.94) — the deterministic ceiling

**The one specific change**
- LLM extracts the make, model and chassis from the title before being passed to the matcher.

**Which rows the change can reach** — counted before running
- Rep 3d errors it should fix (listings): Mitsubishi FTO - DE2A 1994-2000, Toyota Surf - RZN130, Dodge Ram 1500 - 94-01, Mitsubishi Emmeraude - E52A 1992-1997
- Currently correct rows it could break (listings): Mazda Atenza - GH 2008-2012, Mazda Axela - BL MPS, Toyota Yaris - NCP10, Toyota Rav4 - ZSA42, Toyota Corolla - AE80 1983-1986, Toyota Corolla 11 - EL30, Mitsubishi Outlander - GF8W 2012-Present, Mitsubishi RVR - N28W 1991-1997, Subaru Legacy - 4th Gen: BP5 2003-2009, Nissan Tiida - C11 2004-2012, Hyundai Tucson - Other, Honda Inspire - CB-CC 1989-1995, Suzuki Swift - ZC83S, Toyota Sprinter - AE110, Toyota Sprinter - AE111, Toyota Allex - ZZE122 2000-2006, Toyota Ceres - AE101 1992-1995, Ford Futura - BA, Ford Fairlane - BA-BF 2003-2006, BMW 3 Series E36 - 318i, BMW 3 Series E46 - 318i, BMW 5 Series E39 - 520D, Ford XR6 - FG-FGX 2008-2016

**Prediction** — written before running
- Predicted score: 75/100
- Reasoning (one or two lines): 94 + 4 - 23 = 75
- Written at: 04:28 on 29/09

**Result**
- Observed score: 95/100
- Variant score: 0/5
- Signed error (observed − predicted): +20pp
- Measured at: 05:56 on 29/09

**Reconciliation:** 94 + 1 − 0 = 95
- Rows fixed: Mitsubishi FTO - DE2A 1994-2000
- Rows broken: None

**Remaining errors** (all read)
| Listing | Gold | Predicted |
|---|---|---|
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | MAZDA\|MX-5 |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | TOYOTA\|MR 2 |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | RAM\|1500 |

**Error categories**
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=MAZDA\|MX-5 |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=RAM\|1500 |
Uncategorised / other: 0

Balances: 6 survivors from Rep 3d minus the 1 category 5 fix (FTO) = 5, + 0 new = 5. No new categories; category 5 is cleared.

**Explanation**
- Why the gap: None of the rows at risk of being broken ended up breaking. I assumed all the possible breaks would happen when making the prediction. Only one of the remaining errors was fixed. Three of the possible fixes couldn't happen with the design of rep 4. The LLM prompt was instructed not to change the extracted details before inputting to the rep 3d function.
- What this says about my model of the system: The chassis codes doesn't overide the model name when it covers many different models. The remaining fixable errors are spelling and parsing issues. Expecting all possible breaks to occur doesn't result in an accurate prdediction.
- What I'd predict next, and why: 97/100, getting the LLM to decide tie-breaks should solve the errors caused by spelling. 

---

### Rep 5 —  hybrid with abstention + confidence calibration

**Date:** 30/09

**Initial setup**
- Data:            data/gold_vehicles_dev.csv, 100 rows, Make/Model/Variant (commit: dde35a7)
- System:          rep5_abstain (vehicle_classify.abstain_match): Rep 4's label
                   (rep4_llm_extract) with a confidence number; below
                   CONFIDENCE_THRESHOLD = 0.9 the output is NONE. The label itself
                   is unchanged. Confidence (distinct_name_confidence) is taken from
                   the Rep 3d step that decided the label: alias table = 1 / number
                   of different vehicles its names found; Rep 2 fallback = winning
                   score / 100 / number of different candidate vehicles; chassis
                   code = 1.0 (it only decides on one vehicle); no match = 0.0.
                   LLM extractions read from Rep 4's cache (data/rep4_llm_cache.json,
                   commit: f862832); no new LLM calls. (code commit: dde35a7)

**The one specific change**
- A confidence number is generated for the label of each row. If it is below a certain threshold, no answer is given. 

**Which rows the change can reach** — counted before running
- Rep 4 errors it should fix (listings): None
- Currently correct rows it could break (listings): Honda Inspire - CB-CC 1989-1995, Land Rover Discovery - Series 2 1999-2004, Ford XR6 - FG-FGX 2008-2016
- Rep 4 wrong answers predicted to become NONE (candidates: Mazda MX5 - NB 1998-2005, Toyota Mr2 - SW20 1990-1994, Dodge Ram 1500 - 94-01; Surf and Emmeraude are already NONE): 1 - Dodge Ram 1500 - 94-01

**Prediction** — written before running
- Predicted score: 92/100
- Predicted precision: 92/94 / coverage: 94/100 /  (written at: 06:11 on 30/09)
- Reasoning (one or two lines): No new fixes can be made since there is no change in the selection function from rep 4. Three rows are at risk of breaking if the confidence threshold is low enough.
- Written at: 04:31 on 30/09

**Calibration prediction** — written before running
(Source after the run: data/rep5_abstain_confidence_gold_vehicles_dev.csv. "Correct" here means the label before the threshold matches gold.)
- Rows at confidence 1.0: predicted count = 94; predicted correct = 92/94
- Rows below 0.9 (abstained): predicted count = 6; predicted correct if they had answered = 3/6
- Reasoning (one line): There are six rows in total that are already NONE or could become NONE.
- Written at: 06:23 on 30/09.

**Result**
- Observed score: 93/100
- Variant score: 0/5
- Observed precision 92/92 coverage: 92/100 
- Signed error (observed − predicted): +1pp (score: 92/100 → 93/100)
- Signed error, precision: +2.1pp (92/94 = 97.9% → 92/92 = 100%)
- Signed error, coverage: −2pp (94/100 → 92/100)
- Rep 4 wrong answers turned to NONE: predicted 1/3 (Dodge) → observed 3/3 (Dodge, MX5, MR2)
- Measured at: 06:25 on 30/09.

**Calibration result**
- Rows at confidence 1.0: observed count = 92; observed correct = 92/92
- Rows below 0.9 (abstained): observed count = 8; correct if they had answered = 3/8

**Reconciliation:** 95 + 0 − 2 = 93
- Rows fixed: None
- Rows broken: Honda Inspire - CB-CC 1989-1995, Land Rover Discovery - Series 2 1999-2004

**Remaining errors** (all read)
| Listing | Gold | Predicted |
|---|---|---|
| Mazda MX5 - NB 1998-2005 | MAZDA\|MX5 | NONE (Rep 4: MAZDA\|MX-5, confidence 0.5) |
| Toyota Mr2 - SW20 1990-1994 | TOYOTA\|MR2 | NONE (Rep 4: TOYOTA\|MR 2, confidence 0.5) |
| Toyota Surf - RZN130 | TOYOTA\|4RUNNER | NONE |
| Mitsubishi Emmeraude - E52A 1992-1997 | MITSUBISHI\|GALANT | NONE |
| Dodge Ram 1500 - 94-01 | DODGE\|RAM | NONE (Rep 4: RAM\|1500, confidence 0.5) |
| Honda Inspire - CB-CC 1989-1995 | HONDA\|INSPIRE | NONE (Rep 4: HONDA\|INSPIRE, confidence 0.5) |
| Land Rover Discovery - Series 2 1999-2004 | LAND ROVER\|DISCOVERY | NONE (Rep 4: LAND ROVER\|DISCOVERY, confidence 0.25) |

**Error categories**
| # | Category | Survivor / New | Count | Example |
|---|---|---|---|---|
| 1 | Punctuation collision: prediction and gold are the same vehicle spelled differently, and the tie-break picked the other spelling — now abstained on, since the two spellings tie | Survivor | 2 | Mazda MX5 - NB 1998-2005, gold=MAZDA\|MX5, predicted=NONE (Rep 4: MAZDA\|MX-5) |
| 2 | Listing uses the JDM name, the register uses the export name — no string match is possible | Survivor | 2 | Toyota Surf - RZN130, gold=TOYOTA\|4RUNNER, predicted=NONE |
| 4 | A make named inside the listing won the tie-break over the actual make — now abstained on, since the two makes tie | Survivor | 1 | Dodge Ram 1500 - 94-01, gold=DODGE\|RAM, predicted=NONE (Rep 4: RAM\|1500) |
| 9 | The right answer tied with a spurious candidate — part of the chassis code or the make's own words matched a register model — so confidence fell below 0.9 and the correct label was dropped | New | 2 | Honda Inspire - CB-CC 1989-1995, gold=HONDA\|INSPIRE, predicted=NONE (Rep 4: HONDA\|INSPIRE; "CB" matched HONDA\|CB) |
Uncategorised / other: 0

Balances: 5 survivors from Rep 4 minus 0 fixes = 5, + 2 new (category 9: Inspire, Discovery) = 7. Categories 1 and 4 are still errors but now answer NONE instead of a wrong label.

**Explanation**
- Why the gap: Only two of the correct rows I predicted to break did. I didn't expect MX5 and MR2 to abstain. The Renault All Series listing is NONE from the gold.
- What this says about my model of the system: I assumed MX5 and MR2 would get a clear choice. They scored as ties even though the error is a spelling issue. The confidence predictions below 0.9 can't be judged accuratley because the groups are to small (1/4 at 0.5 and 1 at 0.25).
- What I'd predict next, and why: 98/100. When the system's confidence is less that 0.9, an LLM call will be used to improve it.

---

### Note — External feedback ask (methodology, not results)

**Date:** 03/10

Not a rep: nothing in the system changed, no prediction, no calibration row.

- What was sent: METHODOLOGY_REVIEW.md / .pdf — data, gold set, scoring rules,
  how the dev set was used, known weaknesses. No scores.
- Posted publicly: DataTalks.Club Slack
- Sent directly: an engineer friend
- Questions asked:
  1. What should the key metric be to optimise for the fewest wrong vehicle matches?
  2. I tried five different approaches on the same 100 dev rows. Are these results trustworthy when applied to the rest of the data?
  3. Any other errors I haven't mentioned in the weaknesses section?
- Written up while drafting it: the held-out set still carries the pre-19/09
  labelling rules and will be relabelled to the current rules before the Week 4
  run (logged as an extra look); the JDM/export rule is now in vocab.md.
- Replies and what changed because of them: TODO — log when they arrive.

---

### Note — Trade Me OAuth token

Not a rep: no prediction, no measurement. Follows the 05/09 API access note.

**Date:** 03/10

- Token route: Trade Me token generator.
- Error hit on the way:

  ```
  HTTP/1.1 400 BadRequest

  Your application is set up to use oob as the default callback (Client). If you
  want to redirect to a URL then please update your settings to Browser.
  ```

---

### Note — Sandbox Ping outage blocks listing validation

Not a rep: no prediction, no measurement. Follows the 03/10 OAuth token note.

**Date:** 03/10

- `POST /v1/Selling/Validate.json` on the sandbox, inventory row 1
  ("Air Cond Pump Assy", category `0001-0877-2738-2744-`, Car parts &
  accessories → BMW → Other). Auth worked; validation did not:

  ```
  HTTP 400
  {"ErrorDescription":"Ping is not a valid payment method."}
  ```

- Same error with `PaymentMethods` set to `[1,2]`, `[2,4]`, `[1]`, `[3]`,
  `[4]`, `[32]` (Ping), and omitted; and with and without a `StartPrice`. The
  request is not the cause.
- The sandbox site shows "Ping is currently unavailable".
- Trade Me requires Ping on every marketplace listing, so no car-parts listing
  can validate or be created on the sandbox until Ping is back.
- No API method sets Ping up; the Ping methods only read the balance and make
  refunds.
- Also outstanding before a listing can pass: every `inventory.price` is NULL
  (StartPrice must be at least 50c), and the test category is BMW for a Toyota
  Noah part.

---

### Note — Edit and withdraw dropped from the sync

Not a rep: no prediction, no measurement. Follows the 03/10 Ping outage note.

**Date:** 03/10

- The sync (`sync.py`) is create-only: one listing per unmapped inventory
  row, Id from the reply written to `listing_map`. Edit and withdraw have
  been dropped.
- The fake Trade Me (`fake_trademe.py`) still serves the Edit and Withdraw
  endpoints; nothing in the sync calls them.

---

## Week 3 — Failure mode predictions

One block per FAILURE_MODES.md row. Same rule as every rep: the prediction
is written **before** the failure is injected. A block with no prediction
does not count towards the 15.

Gate: all 15 exercised, each with a logged prediction. Full sync run twice
→ zero duplicates.

### Failure mode summary

Fill the row in the same sitting as the block.

| # | Failure | Predicted (TM listings / map rows / duplicates) | Observed (TM listings / map rows / duplicates; from #6 also Ids matched = mapped Ids on TM / map rows) | Prediction right? |
|---|---|---|---|---|
| 1 | Ping down, Trade Me rejects new listings | run 1: 10 / 0 / 0; run 2: 10 / 10 / 0 | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | N |
| 2 | Internet down before request reaches Trade Me | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | N |
| 3 | listing_map has a listing that's not on Trade Me | run 1: 9 / 10 / 0; run 2: 10 / 10 / 0 | run 1: 9 / 10 / 0; run 2: 9 / 10 / 0 | N |
| 4 | Authorisation header is wrong | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | Y |
| 5 | Trade Me's servers are down | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | run 1: 0 / 0 / 0; run 2: 10 / 10 / 0 | Y |
| 6 | New listing comes back with the wrong Id | run 1: 10 / 10 / 0; run 2: 10 / 10 / 0 | run 1: 10 / 10 / 0, Ids matched 0 / 10; run 2: 10 / 10 / 0, Ids matched 0 / 10 | Y |
| 7 | Trade Me sends back the wrong JSON |  |  |  |
| 8 | Trade Me saves it, reply never reaches me |  |  |  |
| 9 | Rate limit hit |  |  |  |
| 10 | My code crashes after create, before listing_map |  |  |  |
| 11 | Request times out, Trade Me is slow |  |  |  |
| 12 | Token expires partway through a run |  |  |  |
| 13 | Same item sent twice |  |  |  |
| 14 | Trade Me says success, listing never appears |  |  |  |
| 15 | Trade Me has a listing that isn't mapped after a sync |  |  |  |

Prediction right: Y / N. Hit rate at the end = calibration for Week 3.

### Block template — copy once per failure

```markdown
#### Failure [#] — [plain words from FAILURE_MODES.md]

**Date:**

**Setup**
- How it was injected:   (exact command)
- Starting state:        inventory rows __ / TM listings __ / listing_map rows __

**Prediction** — written before injecting
- What the sync does:    (crashes / logs an error and carries on / says nothing)
- After run 1 (failure on):   TM listings __ / map rows __ / duplicates __
- After run 2 (failure off):  TM listings __ / map rows __ / duplicates __
- Reasoning (one or two lines):
- Written at: [time]

**Result**
- What the sync did:
- After run 1:   TM listings __ / map rows __ / duplicates __
- After run 2:   TM listings __ / map rows __ / duplicates __
- Measured at: [time]

**Explanation**
- Why the gap:
- What this says about my model of the sync:
- One change to make (if any):
```

### Entries

#### Failure 1 — Ping is down, so Trade Me rejects new listings

**Date:** 06/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 1`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (no data/fake_trademe_state.json yet, so the fake starts empty)

**Prediction** — written before injecting
- What the sync does: The rows are printed, but left unmapped.
- After run 1 (failure on):   TM listings 10 / map rows 0 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): The Trade Me listings are created, but since Ping is down the prices can't be mapped.
- Written at: 04:57 on 06/10

**Result**
- What the sync did:     run 1 printed `HTTP 400 {"ErrorDescription": "Ping is not a valid payment method."}`
                         for each of the 10 rows, left them all unmapped and exited normally
                         ("created 0, listing_map 0 rows"). Run 2 created 1000001–1000010 and mapped all 10.
- After run 1:   TM listings 0 / map rows 0 / duplicates 0
- After run 2:   TM listings 10 / map rows 10 / duplicates 0
- Measured at: 05:01 on 06/10 (TM listings from SellingItems/All read-back; duplicates = repeated titles)

**Explanation**
- Why the gap: No Trade Me listings were created since Ping was unavaliable at the time.
- What this says about my model of the sync: I thought a listing would be created without the price. Instead, it rejects the listing without creating it. 
- One change to make (if any): None. No discrepancies were created. Trade Me and the map match.

---

#### Failure 2 — Internet connection goes down before the request reaches Trade Me

**Date:** 06/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 2`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
                         The fake closes the socket with no reply on every call, read-back included,
                         so run 1's TM listings are counted from data/fake_trademe_state.json.
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (listing_map cleared and data/fake_trademe_state.json deleted after Failure 1)

**Prediction** — written before injecting
- What the sync does: Sync doesn't print anything because the request never reaches Trade Me
- After run 1 (failure on):   TM listings 0 / map rows 0 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): The chain breaks from the first step, so nothing is created or mapped.
- Written at: 06:31 on 06/10

**Result**
- What the sync did:     run 1 printed `local N: ConnectionError` for each of the 10 rows, left them all
                         unmapped and exited normally ("created 0, listing_map 0 rows"). The fake never
                         wrote a state file. Run 2 created 1000001–1000010 and mapped all 10.
- After run 1:   TM listings 0 / map rows 0 / duplicates 0
- After run 2:   TM listings 10 / map rows 10 / duplicates 0
- Measured at: 06:33 on 06/10 (run 1 TM listings: no data/fake_trademe_state.json; run 2: SellingItems/All
               read-back; duplicates = repeated titles)

**Explanation**
- Why the gap: No gap in the numbers. But I got the output of the sync wrong. Errors are picked up based on what Trade Me sends back.
- What this says about my model of the sync: I predicted the sync wouldn't print anything. It printed the conection error for each row. I thought what the sync prints depends on what Trade Me sends back.
- One change to make (if any): None, Trade Me and the map match.

---

#### Failure 3 — The listing map shows a listing that's not on Trade Me

**Date:** 07/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 3`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
                         On start-up the fake deletes the lowest live listing (1000001, local 1) from its
                         state file, then serves normally. The deletion is saved, so it stays gone in run 2.
- Starting state:        inventory rows 10 / TM listings 10 / listing_map rows 10
                         (carried over from Failure 2 run 2: listings 1000001–1000010, all mapped)

**Prediction** — written before injecting
- What the sync does: The mapped row deletes a live listing.
- After run 1 (failure on):   TM listings 9 / map rows 10 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): The mapped listing thats not on Trade Me deletes one that is.
- Written at: 20:36 on 07/10

**Result**
- What the sync did:     both runs printed "0 unmapped rows" and "created 0, listing_map 10 rows" and
                         made no calls to Trade Me at all (the fake's log shows only my read-back).
                         Nothing was deleted or recreated: 1000001 stayed missing from Trade Me and
                         stayed in listing_map, mapped to local 1, through both runs.
- After run 1:   TM listings 9 / map rows 10 / duplicates 0
- After run 2:   TM listings 9 / map rows 10 / duplicates 0
- Measured at: 20:37 on 07/10 (TM listings from SellingItems/All read-back; duplicates = repeated titles)

**Explanation**
- Why the gap: The missing listing was not corrected in the second run. It was still mapped so the sync didn't send any calls to TM.
- What this says about my model of the sync: I thought the mapped rows would be compared to TM, only the listing map is read.
- One change to make (if any): Check the TM and mapped listings match before completing the sync. If they don't match, make changes on the map side only to match the listings on TM.

---

#### Failure 4 — The authorisation header is wrong

**Date:** 08/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 4`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (data/fake_trademe_state.json deleted and listing_map cleared after Failure 3)

**Prediction** — written before injecting
- What the sync does: No listings are created and each map row prints an error message.
- After run 1 (failure on):   TM listings 0 / map rows 0 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): The wrong authorisation header is created at the start, so every call after that fails.
- Written at: 06:25 on 08/10

**Result**
- What the sync did:     run 1 printed `HTTP 401 {"ErrorDescription": "Invalid OAuth signature."}` for each
                         of the 10 rows, left them all unmapped and exited normally ("created 0, listing_map
                         0 rows"). The fake never wrote a state file. Run 2 created 1000001–1000010 and
                         mapped all 10.
- After run 1:   TM listings 0 / map rows 0 / duplicates 0
- After run 2:   TM listings 10 / map rows 10 / duplicates 0
- Measured at: 06:26 on 08/10 (run 1 TM listings: read-back also got 401, so counted from the absent
               data/fake_trademe_state.json; run 2: SellingItems/All read-back; duplicates = repeated titles)

**Explanation**
- Why the gap: None, the prediction matched the result. No listings were created or rows mapped. TM didn't make the change so nothing was created or mapped. The sync doc outlines the error protocol.
- What this says about my model of the sync: Since TM rejects all calls, no listing or map row is created. No discrepancy is created, so every row is retried on the second run.
- One change to make (if any): None, no errors were created.

---

#### Failure 5 — Trade Me's own servers are down

**Date:** 09/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 5`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (data/fake_trademe_state.json deleted and listing_map cleared after Failure 4)

**Prediction** — written before injecting
- What the sync does: Sync displays the error reply (non-200) for each row.
- After run 1 (failure on):   TM listings 0 / map rows 0 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): Every TM call result in a browser-level failure message.
- Written at: 04:23 on 09/10

**Result**
- What the sync did:     run 1 printed `HTTP 503 <html><body>Trade Me is down for maintenance</body></html>`
                         for each of the 10 rows, left them all unmapped and exited normally ("created 0,
                         listing_map 0 rows"). The fake never wrote a state file. Run 2 created
                         1000001–1000010 and mapped all 10.
- After run 1:   TM listings 0 / map rows 0 / duplicates 0
- After run 2:   TM listings 10 / map rows 10 / duplicates 0
- Measured at: 04:24 on 09/10 (run 1 TM listings: read-back also got 503, so counted from the absent
               data/fake_trademe_state.json; run 2: SellingItems/All read-back; duplicates = repeated titles)

**Explanation**
- Why the gap: No gaps in the prediction. An error reply (non-200) was printed for every row.
- What this says about my model of the sync: I thought the body of the HTTP reply affected what the sync printed. It prints the message regardless of the format, HTML or JSON.
- One change to make (if any): None, no errors created.

---

#### Failure 6 — The new Trade Me listing sends the wrong Id

**Date:** 09/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 6`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
                         Hits create calls only, so read-back works normally in run 1.
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (data/fake_trademe_state.json deleted and listing_map cleared after Failure 5)

**Prediction** — written before injecting
- What the sync does: Prints a success reply (200) for each row, but maps the wrong listing id.
- After run 1 (failure on): TM listings 10 / map rows 10 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): No duplicate listings will be created since they were mapped in the first run, but with the wrong listing id. There will be two different sets of listing ids - this is the measurement.
- Written at: 06:05 on 09/10

**Result**
- What the sync did:     run 1 printed `local N: listing 1000778` … `1000787` for the 10 rows and mapped
                         those Ids ("created 10, listing_map 10 rows"). Trade Me actually holds
                         1000001–1000010, so 0 of the 10 mapped Ids exist on Trade Me and all 10 real
                         listings are unmapped. Run 2 printed "0 unmapped rows", made no create calls
                         and changed nothing.
- After run 1:   TM listings 10 / map rows 10 / duplicates 0
- After run 2:   TM listings 10 / map rows 10 / duplicates 0
- Measured at: 06:06 on 09/10 (SellingItems/All read-back; duplicates = repeated titles; mapped Ids
               compared with data/fake_trademe_state.json)

**Explanation**
- Why the gap: No gap. 10 listings were mapped with wrong listing id.
- What this says about my model of the sync: It trusts all responses from the TM side so it maps the wrong id without raising alarm.
- One change to make (if any): Add a function to check the listing id matches one on TM before mapping the row. Change the id to match the TM listing before mapping it.

---

#### Failure 7 — Trade Me sends back the wrong JSON content

**Date:** 09/10

**Setup**
- How it was injected:   terminal 1: `python3 fake_trademe.py --fail 7`
                         terminal 2: `python3 sync.py`
                         (run 2: stop the fake, restart with `python3 fake_trademe.py`, run `python3 sync.py` again)
                         Hits every call, read-back included, so count run 1's TM listings from
                         data/fake_trademe_state.json (absent = 0).
- Starting state:        inventory rows 10 / TM listings 0 / listing_map rows 0
                         (data/fake_trademe_state.json deleted and listing_map cleared after Failure 6)

**Prediction** — written before injecting
- What the sync does: It display an error code for each row and leaves them unmapped.
- After run 1 (failure on):   TM listings 10 / map rows 0 / duplicates 0
- After run 2 (failure off):  TM listings 10 / map rows 10 / duplicates 0
- Reasoning (one or two lines): 
- Written at:

**Result**
- What the sync did:
- After run 1:   TM listings __ / map rows __ / duplicates __
- After run 2:   TM listings __ / map rows __ / duplicates __
- Measured at:

**Explanation**
- Why the gap:
- What this says about my model of the sync:
- One change to make (if any):

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
| 2 | 3a | 97% | 91% | -6pp |
| 2 | 3b | 95% | 87% | -8pp |
| 2 | 3c | 94% | 92% | -2pp |
| 2 | 3d | 94% | 94% | 0pp |
| 2 | 4 | 75% | 95% | +20pp |
| 2 | 5 | 92% | 93% | +1pp |
| 2 | 5 precision | 97.9% | 100% | +2.1pp |
| 2 | 5 coverage | 94% | 92% | -2pp |
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
