# nz-vehicle-resolver

Resolves messy New Zealand vehicle strings to canonical Motor Vehicle Register
records. NZ's fleet is heavily used-Japanese-import, so a dismantler's listing
says "Toyota Celsoir - UCF10" where the register says `TOYOTA | CELSIOR` — and
the JDM name, the export name and the chassis code all disagree with each other.

Returning `None` is a first-class outcome.

**Status: pre-v0.1.0.** Instrument built, corpus collected, gold set drawn and
awaiting labels. No resolution logic yet — that is Rep 1.

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
| Canonical side | NZTA Motor Vehicle Register | 5,850,736 rows, 149,666 distinct make/model | CC-BY 4.0 |

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

`build_canonical.py` aggregates in DuckDB and prints the fleet coverage its
cut achieves, so the number is reportable rather than assumed. Default cut is
`fleet_count >= 10`; pass a different minimum as an argument.

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
| 1 | exact match | TODO | 100 |

Reported as point estimates until small-n results make intervals necessary.

## Limitations

- TODO: label-noise ceiling — measured Week 4, caps everything above.
- TODO: held-out independence — the split is random over distinct vehicle
  strings, but strings from one make are not independent of each other.
- The canonical cut discards long-tail make/model pairs; `build_canonical.py`
  prints exactly how much fleet that loses.
- Partsworld's catalogue is semi-structured (`Make Model - Variant`), so it is
  a cleaner noisy side than free-text marketplace listings would be.

## Licence

Vehicle data © NZ Transport Agency Waka Kotahi, CC-BY 4.0.
