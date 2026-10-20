# Retrospective

Source: LEARNING_LOG.md (calibration table, Week 3 failure summary, entry
Explanation sections). Signed error = observed − predicted.
Negative = optimistic (predicted too high). Positive = pessimistic.

---

## Data

### Calibration — Week 2 (entity resolution, percentage points)

| Rep | Predicted | Observed | Signed error |
|---|---|---|---|
| 2 | 84% | 89% | +5 |
| 3a | 97% | 91% | −6 |
| 3b | 95% | 87% | −8 |
| 3c | 94% | 92% | −2 |
| 3d | 94% | 94% | 0 |
| 4 | 75% | 95% | +20 |
| 5 | 92% | 93% | +1 |
| 5 precision | 97.9% | 100% | +2.1 |
| 5 coverage | 94% | 92% | −2 |

| | MAE | Bias |
|---|---|---|
| All 9 rows | 5.12pp | +1.12pp |
| 7 main reps only (no precision/coverage rows) | 6.00pp | +1.43pp |
| Without Rep 4 | 3.26pp | −1.24pp |

Rep 4 alone turns the bias from optimistic to pessimistic.

### Calibration — Week 3 (sync failures, counts)

Each prediction is six counts: TM listings / map rows / duplicates, after run 1
and run 2. Error per failure = sum over those six.

| # | Failure | Signed error | Abs error | Prediction right? (logged) |
|---|---|---|---|---|
| 1 | Ping down | −10 | 10 | N |
| 2 | Internet down before request | 0 | 0 | N (behaviour wrong, counts right) |
| 3 | Map row not on Trade Me | −1 | 1 | N |
| 4 | Auth header wrong | 0 | 0 | Y |
| 5 | Trade Me servers down | 0 | 0 | Y |
| 6 | Wrong Id returned | 0 | 0 | Y |
| 7 | Wrong JSON returned | −7 | 11 | N |
| 8 | Saved, reply lost | +10 | 10 | N |
| 14 | Success, listing never appears | +10 | 10 | N |
| 15 | Unmapped listing on Trade Me | 0 | 0 | Y |

| | Value |
|---|---|
| Hit rate (logged Y/N) | 4 / 10 |
| MAE | 4.2 listings or rows per failure |
| Bias | +0.2 (errors in both directions cancel) |

### Comparing Week 2 and Week 3

The units differ (percentage points vs counts), so the MAEs can't be compared
directly. The common scale is hit rate:

| | Hit rate |
|---|---|
| Week 2, exact (0pp) | 1 / 9 |
| Week 2, within ±2pp | 4 / 9 |
| Week 3, exact (logged Y) | 4 / 10 |

The tolerance for a Week 2 "hit" is a choice — state which one you use.

### Calibration — Week 4 (for reference; the original plan question was W2 → W4)

| Row | Predicted | Observed | Signed error |
|---|---|---|---|
| Label noise Make+Model | 96.7% | 100% | +3.3pp |
| Label noise full | 93.3% | 100% | +6.7pp |
| Held-out score | 90% | 86% | −4pp |
| Held-out precision | 100% | 95.4% | −4.6pp |
| Held-out coverage | 88% | 87% | −1pp |
| Held-out relabel, rows changed | 0 | 2 | +2 rows |
| Collision groups | 382 | 625 | +243 |

Percentage rows only: MAE 3.92pp, bias +0.08pp.

### Furthest-off predictions (your own Explanation lines)

| Entry | Signed error | Why the gap (from the log) |
|---|---|---|
| W1 S02/T4 — part-type harness | −82.5pp | 37/40 listings predicted as "other"; categories didn't match the keywords used in listings. |
| W4 Collision count | +243 groups (+64%) | Most collisions are trailers; the prediction was based on the dev set, which only has vehicles. |
| W2 Rep 4 — LLM extraction | +20pp | Assumed every at-risk row would break; none did. |
| W3 Failure 7 — wrong JSON | 11 off | Run crashed instead of logging and continuing; prediction and reasoning contradicted each other. |
| W3 Failure 8 — reply lost | 10 off | Forgot run 2 has no failure, so it writes map rows; a lost reply looks the same as failure 2. |
| W3 Failure 14 — listing never appears | 10 off | Sync only checks map ids, not Trade Me, so mapped rows stayed. |
| W3 Failure 1 — Ping down | 10 off | Predicted listings would be created in run 1; Trade Me rejected them. |
| W2 Rep 3b — chassis codes | −8pp | Chassis code overrode the model name in 6 rows. |

### Logged predictions per sub-skill

| Sub-skill | Entries with a prediction | Entries |
|---|---|---|
| Entity resolution | 9 | Rep 1, 2, 3a, 3b, 3c, 3d, 4, 5, held-out run |
| API integration under failure | 11 | Failures 1–8, 14, 15, no-failure gate |
| Eval design | 5 | Rep 0, S02/T4, label noise, held-out relabel, collision count |

The harness build (Week 1 Task 7) has no prediction. Reassign entries if you
categorise them differently.

### Not graded

- SPEC.md was not sent for critique.
- Failures 9–13 not exercised.

---

## 1. Which predictions were furthest off, and what does that reveal about your model of the system?

The biggest errors came from making predictions about the entire data set. The initial set of parts categories didn't match the keywords from the listings and I didn't anticpate the number of trailers in the registry. Misinterpreting the functionality of the system caused the rest of the predictions.

## 2. Did your prediction accuracy improve from Week 2 to Week 3?

My accuracy rate did improve from 11% to 40%. But, the predictions in week three were much easier so this confidence of this comparison is low.

## 3. Which of the three target sub-skills got the fewest actual reps, and why?

Eval design got the fewest reps. The scope of the project had to be cut because of schedule overruns.

## 4. What would you do differently with the same 72 hours?

Cut the scope back to allow more time for each section. Accurately assess how much time I can dedicate each week so the scope of the project is managable with my current skill level. 
