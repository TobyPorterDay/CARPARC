# FAILURE_MODES.md

Spec for the Week 3 failure injector. One row per failure.

- **Failure:** what goes wrong, in one plain sentence.
- **Which call:** auth / create / edit / withdraw / read-back / between runs.
- **Did Trade Me make the change?** Yes / No / Unknown.
- **Source:** Real (it happened) or Imagined.

No predictions or fixes here. Those go in LEARNING_LOG.md, one failure at a time, once the injector exists.

| # | Failure (plain words) | Which call | Did Trade Me make the change? | Source |
|---|---|---|---|---|
| 1 | Ping is down, so Trade Me rejects new listings | Validate / Selling (create) | No | Real, seen 03/10 |
| 2 | Internet connection goes down before the request reaches Trade Me | any | No | Imagined |
| 3 | The listing map shows a listing that's not on Trade Me | between runs | Changed outside sync | Imagined |
| 4 | The authorisation header is wrong | any | No | Imagined |
| 5 | Trade Me's own servers are down | any | No | Imagined |
| 6 | The new Trade Me listing sends the wrong Id | create | Yes | Imagined |
| 7 | Trade Me sends back the wrong JSON content | any | Unknown | Imagined |
| 8 | Trade Me saves the listing, but the reply never reaches me (connection drops after the request arrives) | create | Unknown | Imagined |
| 9 | A rate-limit is activated by Trade Me | any | No | Imagined |
| 10 | My code crashes after Trade Me creates the listing, before writing listing_map | create | Yes | Imagined |
| 11 | The request times out because Trade Me is slow | any | Unknown | Imagined |
| 12 | The token expires partway through a run | any | No | Imagined |
| 13 | The same item gets sent twice | create | Yes | Imagined |
| 14 | Trade Me says it succeeded, but the listing never appears | create | No | Imagined |
| 15 | Trade Me shows a listing that is not mapped after a sync | read-back | Yes | Imagined |
