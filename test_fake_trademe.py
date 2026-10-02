"""Assertions for fake_trademe.py: each injected failure behaves as specified.

* With no failure, create / edit / withdraw / read-back round-trip
* Every injectable FAILURE_MODES.md row does what its row says, including
  whether the listing was actually saved
* --at fires once on the Nth matching call; failure 12 stays on from there
* State survives a restart, and failure 3 drops a listing between runs
"""

import threading

import pytest
import requests

import fake_trademe as fake

AUTH = {"Authorization": 'OAuth oauth_consumer_key="k", oauth_token="t"'}
PART = {"Category": "0001-0877-", "Title": "Air Cond Pump Assy",
        "Description": ["Toyota Noah"], "StartPrice": 10.0}


@pytest.fixture
def start(tmp_path):
    """start(fail=None, at=None, ...) -> base URL of a fake on a free port."""
    servers = []

    def _start(**kw):
        kw.setdefault("state", str(tmp_path / "state.json"))
        kw.setdefault("slow", 1.0)
        server = fake.serve(port=0, **kw)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}/v1"

    yield _start
    for s in servers:
        s.shutdown()
        s.server_close()


def post(base, path, body, **kw):
    return requests.post(f"{base}{path}", json=body, headers=AUTH, timeout=5, **kw)


def live(base):
    r = requests.get(f"{base}/MyTradeMe/SellingItems/All.json", headers=AUTH, timeout=5)
    return [x["ListingId"] for x in r.json()["List"]]


def test_round_trip(start):
    base = start()
    assert post(base, "/Selling/Validate.json", PART).json()["Success"]
    lid = post(base, "/Selling.json", PART).json()["ListingId"]
    assert live(base) == [lid]

    post(base, "/Selling/Edit.json", {"ListingId": lid, "StartPrice": 12.0})
    r = requests.get(f"{base}/Listings/{lid}.json", headers=AUTH, timeout=5)
    assert r.json()["StartPrice"] == 12.0

    post(base, "/Selling/Withdraw.json", {"ListingId": lid, "Type": 2})
    assert live(base) == []


def test_needs_oauth_and_valid_listing(start):
    base = start()
    assert requests.post(f"{base}/Selling.json", json=PART, timeout=5).status_code == 401
    r = post(base, "/Selling.json", {**PART, "StartPrice": 0.1})
    assert r.status_code == 400 and live(base) == []


def test_1_ping_down(start):
    base = start(fail=1)
    r = post(base, "/Selling/Validate.json", PART)
    assert r.status_code == 400 and r.json() == fake.PING_ERROR
    assert post(base, "/Selling.json", PART).status_code == 400
    assert live(base) == []


def test_2_connection_drops_before_arrival(start):
    base = start(fail=2, at=1)
    with pytest.raises(requests.ConnectionError):
        post(base, "/Selling.json", PART)
    assert live(base) == []


@pytest.mark.parametrize("row,status", [(4, 401), (5, 503), (9, 429)])
def test_rejected_and_nothing_saved(start, row, status):
    base = start(fail=row, at=1)
    assert post(base, "/Selling.json", PART).status_code == status
    assert live(base) == []


def test_6_wrong_id(start):
    base = start(fail=6)
    lid = post(base, "/Selling.json", PART).json()["ListingId"]
    assert live(base) != [] and lid not in live(base)


def test_7_wrong_json_but_saved(start):
    base = start(fail=7, at=1)
    r = post(base, "/Selling.json", PART)
    assert r.status_code == 200 and "ListingId" not in r.json()
    assert len(live(base)) == 1


def test_8_saved_but_no_reply(start):
    base = start(fail=8)
    with pytest.raises(requests.ConnectionError):
        post(base, "/Selling.json", PART)
    assert len(live(base)) == 1


def test_11_slow_reply_times_out_but_saved(start):
    base = start(fail=11, at=1, slow=2.0)
    with pytest.raises(requests.Timeout):
        requests.post(f"{base}/Selling.json", json=PART, headers=AUTH, timeout=0.5)
    assert len(live(base)) == 1


def test_12_token_expires_and_stays_expired(start):
    base = start(fail=12, at=2)
    assert post(base, "/Selling.json", PART).status_code == 200
    assert post(base, "/Selling.json", PART).status_code == 401
    assert post(base, "/Selling.json", PART).status_code == 401


def test_14_success_but_never_appears(start):
    base = start(fail=14)
    r = post(base, "/Selling.json", PART)
    assert r.json()["Success"] and live(base) == []


def test_15_unmapped_listing_on_read_back(start):
    base = start(fail=15, at=1)
    lid = post(base, "/Selling.json", PART).json()["ListingId"]
    ids = live(base)
    assert lid in ids and len(ids) == 2


def test_at_fires_once(start):
    base = start(fail=8, at=2)
    assert post(base, "/Selling.json", PART).status_code == 200
    with pytest.raises(requests.ConnectionError):
        post(base, "/Selling.json", PART)
    assert post(base, "/Selling.json", PART).status_code == 200
    assert len(live(base)) == 3


def test_3_listing_dropped_between_runs(start, tmp_path):
    base = start()
    a = post(base, "/Selling.json", PART).json()["ListingId"]
    b = post(base, "/Selling.json", PART).json()["ListingId"]
    base2 = start(fail=3, listing=a)  # same state file, new run
    assert live(base2) == [b]
    assert requests.get(f"{base2}/Listings/{a}.json", headers=AUTH,
                        timeout=5).status_code == 404
