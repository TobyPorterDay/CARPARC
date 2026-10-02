"""A fake Trade Me Selling API on localhost, with the FAILURE_MODES.md failures.

Stands in for api.tmsandbox.co.nz while sandbox Ping is down (LEARNING_LOG
03/10): the real sandbox rejects every listing, so the sync cannot be run
against it at all, let alone against injected failures.

Endpoints, same paths as Trade Me v1:

  POST /v1/Selling/Validate.json         check a listing, change nothing
  POST /v1/Selling.json                  create
  POST /v1/Selling/Edit.json             edit (body carries ListingId)
  POST /v1/Selling/Withdraw.json         withdraw (body carries ListingId)
  GET  /v1/Listings/{id}.json            read back one live listing
  GET  /v1/MyTradeMe/SellingItems/All.json   read back every live listing

Point the sync at http://127.0.0.1:8765/v1 instead of the sandbox.

What is real and what is made up. Taken from the sandbox: the paths, the
OAuth header, and the Ping error body. Made up: listing ids, every other
error body, and the validation rules (Category, Title, Description required;
StartPrice at least 0.50). Withdrawn listings drop out of read-back. A pass
against this fake says the sync handles these replies, not that Trade Me sends
them.

State is a JSON file (data/fake_trademe_state.json), so listings survive
between runs, which failures 3 and 15 need. Delete the file to start empty.

Injecting a failure (numbers are FAILURE_MODES.md rows):

  python3 fake_trademe.py                    no failures
  python3 fake_trademe.py --fail 8           every create: saved, no reply
  python3 fake_trademe.py --fail 8 --at 3    only the 3rd create
  python3 fake_trademe.py --fail 12 --at 4   token expires from the 4th call
  python3 fake_trademe.py --fail 3           drop a live listing, then serve
  python3 fake_trademe.py --list             print the failures

10 and 13 are not injected here. 10 is a crash in the sync's own process, and
13 is the sync sending twice; the fake accepts duplicates, so 13 shows up in
read-back if the sync does it.
"""

import argparse
import json
import os
import re
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = "data/fake_trademe_state.json"
FIRST_ID = 1000001

PING_ERROR = {"ErrorDescription": "Ping is not a valid payment method."}

# row: (plain words, which calls it hits)
FAILURES = {
    1: ("Ping is down, so Trade Me rejects new listings", {"validate", "create"}),
    2: ("Connection drops before the request reaches Trade Me", "any"),
    3: ("A mapped listing is no longer on Trade Me (between runs)", "startup"),
    4: ("The authorisation header is wrong", "any"),
    5: ("Trade Me's own servers are down", "any"),
    6: ("The new listing comes back with the wrong Id", {"create"}),
    7: ("Trade Me sends back the wrong JSON content", "any"),
    8: ("Listing saved, but the reply never arrives", {"create"}),
    9: ("Rate limit hit", "any"),
    10: ("Sync crashes after create, before listing_map (not injectable here)", set()),
    11: ("Trade Me is slow; the request times out", "any"),
    12: ("Token expires partway through a run", "any"),
    13: ("Same item sent twice (sync behaviour; the fake accepts duplicates)", set()),
    14: ("Trade Me says success, but the listing never appears", {"create"}),
    15: ("A listing on Trade Me that the sync did not create", {"read"}),
}

WRITES = {"create", "edit", "withdraw"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    """Listings keyed by id, persisted to a JSON file after every change."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"next_id": FIRST_ID, "listings": {}}
        self.next_id = data["next_id"]
        self.listings = {int(k): v for k, v in data["listings"].items()}

    def save(self):
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"next_id": self.next_id, "listings": self.listings}, f, indent=2
            )
        os.replace(tmp, self.path)

    def create(self, body):
        with self.lock:
            lid = self.next_id
            self.next_id += 1
            self.listings[lid] = {**body, "ListingId": lid, "Status": "live",
                                  "StartDate": now()}
            self.save()
            return lid

    def burn_id(self):
        """Use up an id without storing a listing under it."""
        with self.lock:
            lid = self.next_id
            self.next_id += 1
            self.save()
            return lid

    def edit(self, lid, body):
        with self.lock:
            self.listings[lid] = {**self.listings[lid], **body, "ListingId": lid}
            self.save()

    def withdraw(self, lid):
        with self.lock:
            self.listings[lid]["Status"] = "withdrawn"
            self.save()

    def drop(self, lid):
        with self.lock:
            del self.listings[lid]
            self.save()

    def live(self):
        return {k: v for k, v in self.listings.items() if v["Status"] == "live"}


def validate(body):
    """Fake rules. None if the listing passes, else an error description."""
    for field in ("Category", "Title", "Description"):
        if not body.get(field):
            return f"{field} is required."
    price = body.get("StartPrice")
    if not isinstance(price, (int, float)) or price < 0.5:
        return "StartPrice must be at least $0.50."
    return None


class Injector:
    """Decides, per request, whether the configured failure fires."""

    def __init__(self, row, at):
        self.row = row
        self.at = at
        self.counts = {}
        self.lock = threading.Lock()

    def fires(self, call):
        if self.row is None:
            return False
        hits = FAILURES[self.row][1]
        if hits != "any" and call not in hits:
            return False
        with self.lock:
            n = self.counts[call if hits != "any" else "any"] = (
                self.counts.get(call if hits != "any" else "any", 0) + 1
            )
        if self.at is None:
            return True
        if self.row == 12:  # once the token expires it stays expired
            return n >= self.at
        return n == self.at


def make_handler(store, injector, slow_seconds):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            sys.stderr.write(f"[fake] {self.command} {self.path} {fmt % args}\n")

        # --- plumbing -------------------------------------------------------

        def send_json(self, status, payload, headers=None):
            raw = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(raw)

        def send_raw(self, status, text, ctype):
            raw = text.encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def drop_connection(self):
            """Close the socket with no reply at all."""
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        def read_body(self):
            """Always drain the body, so an early reply cannot leave it on a
            keep-alive connection to be read as the next request."""
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None

        # --- routing --------------------------------------------------------

        def route(self):
            p = self.path.split("?")[0].lower()
            if self.command == "POST":
                return {
                    "/v1/selling/validate.json": "validate",
                    "/v1/selling.json": "create",
                    "/v1/selling/edit.json": "edit",
                    "/v1/selling/withdraw.json": "withdraw",
                }.get(p)
            if self.command == "GET":
                if p == "/v1/mytrademe/sellingitems/all.json":
                    return "read"
                if re.fullmatch(r"/v1/listings/\d+\.json", p):
                    return "read"
            return None

        def do_GET(self):
            self.handle_call()

        def do_POST(self):
            self.handle_call()

        def handle_call(self):
            body = self.read_body()
            call = self.route()
            if call is None:
                return self.send_json(404, {"ErrorDescription": "Not found."})

            row = injector.row if injector.fires(call) else None

            # Failures that happen before the request is processed.
            if row == 2:
                return self.drop_connection()
            if row == 4 or row == 12:
                msg = ("Invalid OAuth signature." if row == 4
                       else "The access token has expired.")
                return self.send_json(401, {"ErrorDescription": msg})
            if row == 5:
                return self.send_raw(
                    503, "<html><body>Trade Me is down for maintenance</body></html>",
                    "text/html")
            if row == 9:
                return self.send_json(
                    429, {"ErrorDescription": "Rate limit exceeded."},
                    {"Retry-After": "60"})
            if not self.headers.get("Authorization", "").startswith("OAuth "):
                return self.send_json(401, {"ErrorDescription": "No OAuth header."})
            if row == 1:  # the sandbox's real reply: auth passes, Ping fails
                return self.send_json(400, PING_ERROR)

            if body is None:
                return self.send_json(400, {"ErrorDescription": "Body is not JSON."})

            status, payload = self.process(call, body, row)

            # Failures that happen after Trade Me has made the change.
            if row == 8:
                return self.drop_connection()
            if row == 11:
                time.sleep(slow_seconds)
            if row == 7:
                return self.send_json(200, {"Foo": "bar", "Listings": None})
            self.send_json(status, payload)

        # --- Trade Me behaviour --------------------------------------------

        def process(self, call, body, row):
            if call == "read":
                return self.read_back(row)

            if call in ("edit", "withdraw"):
                lid = body.get("ListingId")
                if lid not in store.live():
                    return 400, {"ErrorDescription": f"Listing {lid} not found."}

            if call in ("validate", "create", "edit"):
                merged = ({**store.listings[body["ListingId"]], **body}
                          if call == "edit" else body)
                err = validate(merged)
                if err:
                    return 400, {"ErrorDescription": err}

            if call == "validate":
                return 200, {"Success": True, "Description": "Listing is valid."}

            if call == "create":
                if row == 14:  # claims success, stores nothing
                    lid = store.burn_id()
                else:
                    lid = store.create(body)
                if row == 6:
                    lid += 777
                return 200, {"Success": True, "ListingId": lid,
                             "Description": "Listing created."}

            if call == "edit":
                store.edit(body["ListingId"], body)
                return 200, {"Success": True, "ListingId": body["ListingId"],
                             "Description": "Listing updated."}

            if call == "withdraw":
                store.withdraw(body["ListingId"])
                return 200, {"Success": True, "ListingId": body["ListingId"],
                             "Description": "Listing withdrawn."}

        def read_back(self, row):
            if row == 15:  # someone listed by hand on the website
                store.create({"Category": "0001-0877-", "Title": "Listed by hand",
                              "Description": ["Not from the sync"],
                              "StartPrice": 1.0})
            live = store.live()
            m = re.search(r"/listings/(\d+)\.json", self.path.lower())
            if m:
                lid = int(m.group(1))
                if lid not in live:
                    return 404, {"ErrorDescription": f"Listing {lid} not found."}
                return 200, live[lid]
            items = sorted(live.values(), key=lambda x: x["ListingId"])
            return 200, {"TotalCount": len(items), "Page": 1,
                         "PageSize": len(items), "List": items}

    return Handler


def serve(port=8765, fail=None, at=None, slow=35.0, state=STATE, listing=None):
    """Build the server; the caller runs serve_forever(). Used by the tests."""
    store = Store(state)
    if fail == 3:
        live = sorted(store.live())
        lid = listing if listing is not None else (live[0] if live else None)
        if lid not in store.listings:
            sys.exit("--fail 3 needs a live listing to drop; create one first")
        store.drop(lid)
        print(f"[fake] failure 3: dropped listing {lid} from Trade Me", flush=True)
    injector = Injector(fail if fail != 3 else None, at)
    return ThreadingHTTPServer(("127.0.0.1", port),
                               make_handler(store, injector, slow))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--fail", type=int, choices=sorted(FAILURES),
                    help="FAILURE_MODES.md row to inject")
    ap.add_argument("--at", type=int,
                    help="fire only on the Nth matching call (12: from the Nth on)")
    ap.add_argument("--slow", type=float, default=35.0,
                    help="seconds failure 11 waits before replying")
    ap.add_argument("--listing", type=int, help="failure 3: which listing to drop")
    ap.add_argument("--state", default=STATE)
    ap.add_argument("--list", action="store_true", help="print the failures")
    args = ap.parse_args()

    if args.list:
        for row, (words, hits) in FAILURES.items():
            calls = hits if isinstance(hits, str) else ", ".join(sorted(hits)) or "-"
            print(f"{row:3d}  {words}  [{calls}]")
        return
    if args.fail in (10, 13):
        sys.exit(f"failure {args.fail} is not injected by the fake: "
                 f"{FAILURES[args.fail][0]}")

    server = serve(args.port, args.fail, args.at, args.slow, args.state,
                   args.listing)
    what = f"failure {args.fail}" if args.fail else "no failures"
    if args.at:
        what += f" at call {args.at}"
    print(f"[fake] Trade Me on http://127.0.0.1:{args.port}/v1 ({what}), "
          f"state {args.state}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
