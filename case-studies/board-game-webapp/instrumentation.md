# Analytics Without Google Analytics

*Sidebar to [the case study](README.md) — how the funnel and churn numbers
in that report were produced with no external analytics SDK, no cookie
banner, and about 150 lines of code.*

## The stack

Three pieces, all already inside the app's own small Express backend:

1. **A client-generated anonymous ID.** On first load, the client checks
   `localStorage` for a UUID; if none exists, it creates one with
   `crypto.randomUUID()` and stores it. No cookie, no account, no
   fingerprinting — just an opaque ID the browser holds onto across visits
   on the same device.
2. **A tiny `track(event, data)` call, fired at a handful of points in the
   UI.** Each call is a fire-and-forget `fetch(..., { keepalive: true })`
   POST — if it fails, the game is unaffected. `keepalive: true` matters:
   it lets the browser finish sending the request even if the tab is being
   closed mid-flight, which is exactly when a lot of churn events fire.
3. **An append-only JSONL log on the server, plus one aggregation
   endpoint.** The server does no real-time processing — it just validates
   the payload, stamps a server-side timestamp, and appends one JSON line
   per event to a log file. A separate, code-gated endpoint reads the whole
   file back, folds it by anonymous ID, and returns aggregate counts.

That's the entire pipeline. No queue, no database, no dashboarding tool —
grep and `JSON.parse` on a text file, called on demand.

## Event schema (field names only)

No raw values are reproduced here — this is the shape, not the data.

| Event | Fired when | Payload fields |
|---|---|---|
| `visit` | App loads | `path` |
| `gameStart` | A new game is configured and begins | `seed`, `difficulty`, `playerCount`, `mapId` |
| `turnStart` | Each new turn begins | `turn`, `mapId` |
| `sessionEnd` | The player navigates away or closes the tab *before* the game finishes | `turn`, `phase`, `mapId` |
| `gameOver` | A game reaches a real end state | outcome fields (winner, scores, turn count) |

Every event envelope also carries `anonId` (the client UUID), an optional
`nickname` (truncated, only present if the player set one), and a
server-stamped `ts`. The aggregation endpoint folds all of this down to,
per anonymous ID: visit count, games started, games finished, turns seen,
last-seen timestamp, and — if the player quit early — a coarse "last exit
point" string like `<map> T<turn>/<phase>`. That last-exit-point field is
exactly what powers the churn-segmentation chart in the case study: bucket
sessions by how far and how long they got before a `sessionEnd` (never
followed by `gameOver`), and the two failure modes fall out of the shape of
that distribution.

## Pros

- **Zero external dependency and zero consent friction.** No cookie banner,
  no data processor agreement with a third party, nothing to block with an
  ad blocker (the /api/telemetry endpoint is first-party and same-origin).
- **The full event log is inspectable in one file.** For a closed beta with
  a few hundred events, `grep gameStart logs/telemetry.jsonl | wc -l` *is*
  a metrics dashboard. Debugging "why does this number look wrong" means
  reading actual lines, not querying an opaque third-party UI.
- **You own the retention policy.** The log rotates, gets deleted, or gets
  archived on your own schedule — not a vendor's.
- **Trivial to extend.** Adding a new event is one `track()` call and one
  new `if (e.event === ...)` branch in the aggregator. No schema migration,
  no new SDK integration.

## Cons

- **No real-time dashboard.** `/api/stats` recomputes from the entire file
  on every request — fine at hundreds of lines, not fine at millions.
  There's no rolling aggregation, no pre-computed daily rollups.
- **No session stitching across devices.** The anonymous ID lives in
  `localStorage`, so the same person on a phone and a laptop shows up as
  two anonymous IDs. A real identity-resolution layer would fix this; this
  approach doesn't try to.
- **No built-in funnel/segmentation UI.** Every question — "what's the
  turn-2 reach rate," "how do churned sessions split by duration" — is a
  bespoke script over the JSONL, not a drag-and-drop report. That's exactly
  how this case study's charts were built, and it doesn't scale past a
  handful of ad hoc questions before you want a proper query layer.
- **Fragile to concurrent writes at scale.** `appendFileSync` is fine for a
  closed beta's request volume; it is not the way to log events under real
  concurrent load without a queue in front of it.
- **No automatic bot/crawler filtering, no de-duplication of a developer's
  own testing traffic.** The case study's own limitations section notes a
  single visitor with 103 of 312 visits, presumed to be the developer — a
  real analytics platform would typically flag or exclude that kind of
  outlier automatically; here it had to be caught by eyeballing the data.

## When this is enough

- Pre-launch through closed beta / early access, where the population is
  small enough that you can read the raw aggregates yourself and the
  questions you're asking are still "where do people drop off," not
  "run a 12-way segmented cohort retention query."
- Any project where avoiding third-party trackers and consent banners is a
  product or ethical goal, not just a cost-saving one.
- A prototype stage where you don't yet know which events matter — this
  setup is cheap enough to throw away or rebuild once you do know.

## When you need a real analytics stack

- Once volume makes "recompute from the whole file on every request"
  too slow, or once you need rolling windows, cohort tables, or dashboards
  that non-technical teammates can self-serve without a script.
- Once you need cross-device identity resolution, server-side event
  validation against a schema registry, or SQL-able event storage (a proper
  warehouse + a tool like PostHog, Amplitude, or a Postgres/BigQuery table
  behind a BI tool).
- Once retention, alerting, or anomaly detection needs to run continuously
  rather than being triggered by a human asking a one-off question.

The honest framing: this approach didn't produce a *worse* analysis for
this stage — it produced a right-sized one. The limiting factor in this
case study wasn't the pipeline, it was sample size (149 unique visitors
over 38 hours), and no amount of tooling upgrades that number.

---
© 2026 BuildnWrite. All rights reserved.
