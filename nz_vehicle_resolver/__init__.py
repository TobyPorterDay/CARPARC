"""Resolve messy New Zealand vehicle strings to canonical register records.

    resolve(s)        -> CanonicalVehicle | None
    resolve_batch(ss) -> list[CanonicalVehicle | None]

Returning None means "no answer", and is a first-class outcome.

The resolver is Rep 5 (see README): an LLM copies the make, model and chassis
code out of the string, the alias/fuzzy matcher looks them up, and any
contested answer comes back as None.

Reproducibility: the package ships the LLM's recorded answers for the 100 dev
titles (data/rep4_llm_cache.json), so those resolve identically with no key.
Any other string needs ANTHROPIC_API_KEY, in the environment or in a .env file
in the working directory; its answer is then recorded in
~/.cache/nz-vehicle-resolver/llm_cache.json (override the location with
NZ_VEHICLE_RESOLVER_CACHE) and reused on every later call. The shipped answers
win over the user cache if both hold a title.

Vehicle data in nz_vehicle_resolver/data is derived from the NZTA Motor Vehicle
Register, (c) NZ Transport Agency Waka Kotahi, CC-BY 4.0.
"""

import json
import os
from collections.abc import Iterable
from typing import NamedTuple

import vehicle_classify

__all__ = ["CanonicalVehicle", "resolve", "resolve_batch"]

_SEED_CACHE = vehicle_classify.LLM_CACHE_PATH  # the shipped answers
_cache_ready = False

if not os.environ.get("NZ_VEHICLE_RESOLVER_CACHE"):
    vehicle_classify.LLM_CACHE_PATH = os.path.join(
        os.path.expanduser("~"), ".cache", "nz-vehicle-resolver", "llm_cache.json"
    )


class CanonicalVehicle(NamedTuple):
    make: str
    model: str


def _load_dotenv_key():
    """Set ANTHROPIC_API_KEY from ./.env when it is not already in the environment."""
    if os.environ.get("ANTHROPIC_API_KEY") or not os.path.exists(".env"):
        return
    with open(".env", encoding="utf-8") as f:
        for line in f:
            name, _, value = line.strip().partition("=")
            if name == "ANTHROPIC_API_KEY" and value:
                os.environ[name] = value.strip("'\"")


def _prepare_cache():
    """Once per process: write the shipped answers into the user cache."""
    global _cache_ready
    if _cache_ready:
        return
    path = vehicle_classify.LLM_CACHE_PATH
    if path != _SEED_CACHE:
        with open(_SEED_CACHE, encoding="utf-8") as f:
            merged = json.load(f)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                merged = {**json.load(f), **merged}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    _cache_ready = True


def resolve(s: str) -> CanonicalVehicle | None:
    """Return the register make/model for s, or None if there is no confident answer."""
    if not s or not s.strip():
        return None
    s = s.strip()
    _prepare_cache()
    if s not in vehicle_classify._get_llm_cache():
        _load_dotenv_key()
    label = vehicle_classify.abstain_match(s)
    if label == "NONE":
        return None
    make, model = label.split("|", 1)
    return CanonicalVehicle(make, model)


def resolve_batch(strings: Iterable[str]) -> list[CanonicalVehicle | None]:
    """resolve() each string, in order."""
    return [resolve(s) for s in strings]
