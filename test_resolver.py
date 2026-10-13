import pytest

import nz_vehicle_resolver as nzv
from nz_vehicle_resolver import CanonicalVehicle


@pytest.fixture
def fake_rep5(monkeypatch):
    answers = {"Toyota Celsoir - UCF10": "TOYOTA|CELSIOR"}
    fake = lambda s: answers.get(s, "NONE")
    monkeypatch.setattr(nzv.vehicle_classify, "abstain_match", fake)
    monkeypatch.setattr(nzv, "_prepare_cache", lambda: None)
    monkeypatch.setattr(nzv.vehicle_classify, "_get_llm_cache", lambda: {})
    monkeypatch.setattr(nzv, "_load_dotenv_key", lambda: None)


def test_resolve_returns_canonical_vehicle(fake_rep5):
    assert nzv.resolve("Toyota Celsoir - UCF10") == CanonicalVehicle("TOYOTA", "CELSIOR")


def test_resolve_returns_none_not_the_string(fake_rep5):
    assert nzv.resolve("gibberish") is None


@pytest.mark.parametrize("s", ["", "   "])
def test_resolve_blank_is_none_without_matching(s):
    assert nzv.resolve(s) is None


def test_resolve_batch_keeps_order(fake_rep5):
    assert nzv.resolve_batch(iter(["gibberish", "Toyota Celsoir - UCF10"])) == [
        None,
        CanonicalVehicle("TOYOTA", "CELSIOR"),
    ]


def test_shipped_cache_resolves_dev_titles_without_a_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    assert nzv.resolve("BMW 3 Series E36 - 318i") == CanonicalVehicle("BMW", "3 SERIES")


def test_user_cache_is_outside_the_install():
    assert ".cache" in nzv.vehicle_classify.LLM_CACHE_PATH


# --- packaged data and cache ---

import csv
import json
import os

import vehicle_classify as vclf


def test_packaged_data_exists_whatever_the_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for path in (vclf.CANONICAL_PATH, vclf.ALIAS_PATH, nzv._SEED_CACHE):
        assert os.path.isabs(path) and os.path.exists(path)
        assert "nz_vehicle_resolver" in path


def test_shipped_cache_holds_dev_titles_only():
    def titles(path):
        with open(path, newline="", encoding="utf-8") as f:
            return {row["Listing"] for row in csv.DictReader(f)}

    with open(nzv._SEED_CACHE, encoding="utf-8") as f:
        shipped = set(json.load(f))
    assert shipped == titles("data/gold_vehicles_dev.csv")
    assert not shipped & titles("data/gold_vehicles_heldout.csv")


@pytest.fixture
def user_cache(monkeypatch, tmp_path):
    path = tmp_path / "sub" / "llm_cache.json"
    monkeypatch.setattr(vclf, "LLM_CACHE_PATH", str(path))
    monkeypatch.setattr(nzv, "_cache_ready", False)
    return path


def test_prepare_cache_seeds_the_user_cache(user_cache):
    nzv._prepare_cache()
    with open(nzv._SEED_CACHE, encoding="utf-8") as f:
        assert json.loads(user_cache.read_text()) == json.load(f)


def test_prepare_cache_keeps_user_entries_and_shipped_answers_win(user_cache):
    with open(nzv._SEED_CACHE, encoding="utf-8") as f:
        seeded = json.load(f)
    title = next(iter(seeded))
    user_cache.parent.mkdir()
    user_cache.write_text(json.dumps({"my title": {"make": "X"}, title: {"make": "STALE"}}))
    nzv._prepare_cache()
    merged = json.loads(user_cache.read_text())
    assert merged["my title"] == {"make": "X"}
    assert merged[title] == seeded[title]


def test_dotenv_key_is_read_only_when_the_environment_has_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TRADEME_TOKEN=a\nANTHROPIC_API_KEY='sk-ant-test'\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    nzv._load_dotenv_key()
    assert os.environ["ANTHROPIC_API_KEY"] == "from-env"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    nzv._load_dotenv_key()
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-test"
    monkeypatch.delenv("ANTHROPIC_API_KEY")  # undo the write for later tests


def test_key_is_not_loaded_for_a_cached_title(monkeypatch):
    loaded = []
    monkeypatch.setattr(nzv, "_prepare_cache", lambda: None)
    monkeypatch.setattr(nzv, "_load_dotenv_key", lambda: loaded.append(1))
    monkeypatch.setattr(vclf, "_get_llm_cache", lambda: {"cached": {}})
    monkeypatch.setattr(vclf, "abstain_match", lambda s: "NONE")
    nzv.resolve("cached")
    assert not loaded
    nzv.resolve("uncached")
    assert loaded
