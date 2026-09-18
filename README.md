# nz-vehicle-resolver

Resolves messy New Zealand vehicle strings to canonical Motor Vehicle Register
records. NZ's fleet is heavily used-Japanese-import, so a dismantler's listing
says "Toyota Celsoir - UCF10" where the register says `TOYOTA | CELSIOR` — and
the JDM name, the export name and the chassis code all disagree with each other.

Returning `None` is a first-class outcome.

**Status: pre-v0.1.0.** Instrument built, corpus collected, gold set drawn and
labelled, 100 dev / 100 held-out. Week 2 in progress: Reps 1 and 2 measured,
Reps 3–5 outstanding. TODO: numbers for alias/chassis, LLM extraction and the
hybrid rep.

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

Reported as point estimates until small-n results make intervals necessary.

Rep 2's threshold is inert on this dev set: 100, 95 and 80 produce identical
predictions, because every decision is made at a similarity of exactly 100 once
punctuation is normalised away. The gain over Rep 1 came from normalisation, not
from fuzzy matching.

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
