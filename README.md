# nz-vehicle-resolver

Resolves messy New Zealand vehicle strings to canonical Motor Vehicle Register
records. NZ's fleet is heavily used-Japanese-import, so a dismantler's listing
says "Toyota Celsoir - UCF10" where the register says `TOYOTA | CELSIOR` — and
the JDM name, the export name and the chassis code all disagree with each other.

Returning `None` is a first-class outcome.

**Status: pre-v0.1.0.** Instrument built, corpus collected, gold set drawn and
labelled, 100 dev / 100 held-out. Week 2 complete: five reps measured on the
dev set. Next: Week 3, Trade Me sandbox sync and failure injection. TODO:
held-out score (Week 4).

## The two functions

```python
resolve(s: str) -> CanonicalVehicle | None
resolve_batch(strings: Iterable[str]) -> list[CanonicalVehicle | None]
```

That is the entire public surface. Nothing else ships in v0.1.0.

## Data

| | Source | Size | Licence |
|---|---|---|---|
| Noisy side | partsworld.co.nz vehicle catalogue | 1,721 distinct vehicles | scraped, titles only |
| Canonical side | NZTA Motor Vehicle Register | 5,880,234 rows, 193,948 distinct make/model | CC-BY 4.0 |

The register's own documentation notes its free-text fields carry "spelling
mistakes and inconsistent wording" that survived NZTA's algorithmic cleaning.
That is the point: it is a genuinely dirty national-scale canonical side.

### Building the canonical table

The register is not redistributed here. Download it and build:

```bash
# ~309MB, all 37 vehicle years
curl -L -o data/mvr/Fleet-data-all-vehicle-years.zip \
  https://wksprdgisopendata.blob.core.windows.net/motorvehicleregister/Fleet-data-all-vehicle-years.zip

python3 build_canonical.py        # -> data/mvr_canonical_vehicles.csv
```

The zip is expanded once to `.csv.gz` (DuckDB reads `.csv`, `.csv.gz` and
`.csv.zst`, but not `.zip`), then aggregated in SQL. Takes about 30 seconds.
Default cut is `fleet_count >= 10` — 12,728 pairs, 95.16% of the fleet — and
the script prints coverage at every candidate cut so the threshold is chosen
against numbers.

## Measuring

The harness was built before anything it measures, and it knows nothing about
any classifier: `REPS` maps a name to a one-argument function, `score()` takes
`(Listing, Predicted)` pairs, and accuracy is computed in SQL.

```bash
python3 harness.py                                   # part_type miniature set
CARPARC_GOLD=data/gold_vehicles_dev.csv python3 harness.py
```

## Gold set

200 vehicles drawn from the corpus with a fixed seed, split 100 dev / 100
held-out. **The held-out set is touched exactly twice: once at labelling, once
in Week 4.**

```bash
python3 sample_gold.py            # seeded, refuses to overwrite
python3 label_vehicles.py         # labels the dev set
```

## Results

| Rep | Approach | Accuracy | n |
|---|---|---|---|
| — | constant-label floor (part_type) | 7/40 (0.17) | 40 |
| 1 | contains model anywhere | 91/100 (0.91) | 100 |
| 2 | fuzzy match, make and model scored separately, threshold 95 | 89/100 (0.89) | 100 |
| 3 | alias table (top 40 vehicles, 39.6% of fleet) name match first, chassis code only when no name matches; alias names that are separate register models dropped | 94/100 (0.94) | 100 |
| 4 | LLM copies make, model and chassis code verbatim from the title; Rep 3's matcher does the lookup | 95/100 (0.95) | 100 |
| 5 | Rep 4, returning `NONE` on any tie between candidate vehicles | 93/100 (0.93); precision 92/92 (1.00), coverage 92/100 (0.92) | 100 |

The dev gold changed between Rep 2 and Rep 3: labels were split into model and
variant, and three BMW rows moved to the parent line (3 Series, 5 Series).
Reps 1 and 2 above were scored on the earlier labels. On the current gold they
score 94/100 and 92/100, so Rep 3 ties Rep 1 rather than beating it.

Rep 5 turned all three of Rep 4's wrong answers into `NONE`, and two correct
answers as well (Honda Inspire, Land Rover Discovery), where a spurious
candidate tied with the right one. Every answer it gave was right; it answered
92 of 100.

Reported as point estimates until small-n results make intervals necessary.

The full evaluation method, including known weaknesses, is in
[METHODOLOGY_REVIEW.md](METHODOLOGY_REVIEW.md).

Rep 2's threshold is inert on this dev set: 100, 95 and 80 produce identical
predictions, because every decision is made at a similarity of exactly 100 once
punctuation is normalised away. The gain over Rep 1 came from normalisation, not
from fuzzy matching.

## Sync errors

Each failure injected into the fake Trade Me, with the cause, whether the
customer can fix it, and what support should tell them. Evidence for every row
is in LEARNING_LOG.md.

| # | Failure | Cause | Customer-fixable? | Support message | Status |
|---|---|---|---|---|---|
| 1 | Ping is down, so Trade Me rejects new listings | Trade Me requires Ping on every marketplace listing, and Ping is unavailable on the sandbox, so it rejects every create. | No | Ping is down. Please try again later | known |
| 2 | Internet connection goes down before the request reaches Trade Me | The connection drops before the request reaches Trade Me, so Trade Me never sees it. | Yes | Your request failed. Please reconnect to the internet and try again | known |
| 3 | The listing map shows a listing that's not on Trade Me | The sync reads only the listing map, not Trade Me, so it never compares mapped rows to Trade Me. | No | Trade Me hasn't saved a listing. Please don't run the sync again. Contact support to check your listings. | known |
| 4 | The authorisation header is wrong | The saved Trade Me login is wrong or out of date, so Trade Me rejects every call. | Yes | Your request failed. Try logging out of your Trade Me account, then log back in and try again | known |
| 5 | Trade Me's own servers are down | Trade Me's servers are down for maintenance, so every call gets a 503. | No | Your request failed. Please try again later | known |
| 6 | The new Trade Me listing sends the wrong Id | The sync trusts every reply from Trade Me, so it maps the wrong Id without raising an alarm. | No | The Trade Me listing was saved incorrectly. Please don't run the sync again. Contact support to correct the listing. | known |
| 7 | Trade Me sends back the wrong JSON content | The sync only catches errors on the way to Trade Me, not on the way back, so a bad reply crashes the run after the listing is created. | No | The Trade Me listing was saved incorrectly. Please don't run the sync again. Contact support to check for a duplicate. | known |
| 8 | Trade Me saves the listing, but the reply never reaches me (connection drops after the request arrives) | The sync can't tell a lost reply from a request that never arrived (same error as failure 2), so a retry without checking Trade Me duplicates the listings. | No | The sync didn't save correctly, please don't run it again and contact support | known |
| 14 | Trade Me says it succeeded, but the listing never appears | The sync treats a success reply and a ListingId as proof the listing exists, and never removes mapped rows. | No | Trade Me didn't save the listing. Please contact support to re-create the listing. | known |
| 15 | Trade Me shows a listing that is not mapped after a sync | The sync reads only the inventory and the listing map, not Trade Me, so changes made on Trade Me are not picked up. | No | The Trade Me listing didn't save correctly. Please contact support to check the extra listing on Trade Me. | known |

## Limitations

- TODO: label-noise ceiling — measured Week 4, caps everything above.
- TODO: held-out independence — the split is random over distinct vehicle
  strings, but strings from one make are not independent of each other.
- The canonical cut discards long-tail pairs. Note that the tail is not all
  noise: pre-1990 vehicles are 6.5% of the fleet but 26% of distinct pairs,
  and 44,338 pairs appear nowhere after 1989. Re-check in Week 4 whether the
  cut deletes classics the corpus actually contains.
- The register carries punctuated and unpunctuated spellings of the same model
  as separate canonical rows (`CR-V` and `CRV`, `MX-5` and `MX5`). Once
  punctuation is normalised the two are indistinguishable, so which row wins is
  decided by the tie-break, not by the match. TODO: quantify how many of the
  12,728 pairs collide this way.
- Partsworld's catalogue is semi-structured (`Make Model - Variant`), so it is
  a cleaner noisy side than free-text marketplace listings would be.

## Licence

Vehicle data © NZ Transport Agency Waka Kotahi, CC-BY 4.0.
