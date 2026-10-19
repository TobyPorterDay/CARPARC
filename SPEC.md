# nz-vehicle-resolver — Requirements Spec

## Problem

The intended users for CARPARC are car wreckers who need to categorise the parts they sell with the correct make and model of the car it was taken from. Another use case is for a listing website, a second-hand marketplace, like Trade Me. It would be part of the listing pipeline, creating listings with the correct details, making it easier for customers to find what they need.

The input is the messy vehicle string that is used in the listing title. It usually will be incomplete, misspelled, and may have the wrong chassis code or year range.

The current issue with the pipeline is when a listing has a JDM and export model name in the NZTA registry, the system defaults to the export name, even if the input listing specified the JDM name. Also, spelling and formatting issues with the listing string causes it to fail, resulting in the output being `None`.

A wrong match is much worse than a `None` output because the wrong car part will be purchased. So, a listing that outputs `None` is a valid result. It helps to prevent the high cost of an error.

## Interface

**Install and import**

```
pip install .        # from the repo root; Python >= 3.10; not on PyPI
from nz_vehicle_resolver import resolve, resolve_batch, CanonicalVehicle
```

A listing string is input into resolve(s) and returns CanonicalVehicle or `None`.
Resolve_batch(strings) takes the iterable list of strings, returns a list of the same length.
CanonicalVehicle returns the make and model only. It uses the NZTA spelling.
`None` is the output when the listing is empty, no match can be made, or when there is a tie between multiple vehicles.
An Anthropic API key is required to run the pipeline. The key is not required for the completed listings in the cache.
Cached listing strings return the same output every time once saved.

**Errors**

| Condition | Behaviour |
|---|---|
| Empty or whitespace-only string | Returns `None`. No error. |
| Unseen string, no `ANTHROPIC_API_KEY` | Raises `TypeError` ("Could not resolve authentication method"). Does not return `None`. |
| LLM call fails or the model refuses | Raises (`anthropic` API error or `RuntimeError`). Does not return `None`. |
| Any string in `resolve_batch()` raises | The whole batch raises. No partial results are returned. |

## Acceptance criteria

Quality on the held-out set.
- Precision is the key measurement given the high cost of a wrong match. Current measurement: 83/87. Point estimate pass threshold: 95%
- Coverage is how many listings get a canonical vehicle match. Current measurement: 87/100. Point estimate pass threshold: 87%
- Score is the total number of correct outputs, a match, or a `None` when that matches the gold set. Current measurement: 86/100.Point estimate pass threshold: 86%

When a listing returns a contested match, the pipeline returns `None` instead of a guess. The tie break must be below the confidence threshold to produce `None`.

The batch order for in the resolver always keeps the same order as what was input.

Once the listing has been run through the resolver and an output has been given, the result is cached so it returns the same result if run again.

After a result is cached, no API call is required if run again.

The tests in the resolver must pass.

## Edge cases

| Input | Expected | Why |
|---|---|---|
| `Toyota Vitz - KSP90` | `TOYOTA / YARIS` | Alias joins JDM/export names; export wins. Gold says VITZ. |
| `Mitsubishi Emmeraude - E53A 1992-1997` | `None` | JDM name absent from register; no string match. |
| `Honda CRV - RD4-RD8 2002-2006` | `HONDA / CRV` | Register holds CRV and CR-V as separate models. |
| `Toyota Celsoir - UCF10` | `None` | Misspelling not recovered; confidence below threshold. |
| `Porsche Cayenne S - Cayenne S 2003-2006` | `None` | Nested names (Cayenne / Cayenne S) tie; abstains. |
| `Dodge Ram 2500 - 02-08` | `None` | RAM as make ties with DODGE RAM; abstains. |
| `Lexus All Series - All Series 1997-2017` | `None` | No specific model named. |
| `""` or `"   "` | `None`, no LLM call | Blank input short-circuits before matching. |
| Unseen string, no `ANTHROPIC_API_KEY` | Raises `TypeError` | Missing key is a setup error, not "no answer". |
| `resolve_batch(["", "Honda CRV - RD4-RD8 2002-2006", "Lexus All Series - All Series 1997-2017"])` | `[None, HONDA / CRV, None]` | Order preserved; `None` stays in position. |

## Non-goals

Interface: The pipeline only includes two functions, the input of the listing string and the canonical vehicle output or `None`.

Output: Make and model only. No variants, chassis code. No confidence score accompanies the output.

Scope: The type of part the listing is for isn’t included in the package’s functionality. There is no sync to Trade Me. It uses a downloaded version of the NZ motor vehicle registry so it doesn’t update when NZTA update it.

Behavior: New strings that haven’t been run cannot be run offline, they need the API call. If one string fails, the batch function won’t print partial results.

## Open questions

How should the JDM vs export model name be selected if both exist in the registry? A rule that chooses the registry model that matches what the listing has.
How should spelling and format issues be addressed? Possibly an additional LLM layer to match the format to the registry.
Should an error result in a failed run or `None`? No. `None` would be misleading so the specific row should be noted as an error and then the run moves on to the next row without stopping.


