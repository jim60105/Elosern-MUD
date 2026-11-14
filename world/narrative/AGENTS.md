# world/narrative guide

This package owns persistent narrative state: events, memory, recall, story
threads, letters, dream sessions, attention, context snapshots, authoring
records and beat scheduling. It is a writer package and a Django app
(`models.py`, `migrations/`).

Everything here is deterministic. No module imports `world.ai` or opens a
transport, so every operation works with all generation services offline.
Generated prose reaches this package only as a validated value handed in by a
composition root (`server/dream_service.py`, `server/dream_dispatch_service.py`,
`server/correspondence_service.py`).

Background reading: `docs/development/narrative-memory-and-recall.md`.

## Find the owner

| You are changing | Modules |
| --- | --- |
| Turning a settled action or combat into narrative events | `action_adapters.py`, `projector.py`, `events.py` |
| What a character remembers | `memory.py`, `correspondence_memory.py`, `adult_projection.py` |
| Retrieving memories for a prompt | `recall.py`, `ranker.py` (BM25), `tokenizer.py` (Traditional Chinese) |
| Assembling a prompt context within a token budget | `context.py`, `epochs.py` |
| Story threads | `threads.py` |
| Which story direction is eligible next | `attention.py`, `director.py`, `quest_beats.py` |
| Player dialogue history with an NPC | `dialogue.py`, `dialogue_reading.py`, `replies.py` |
| Letters | `correspondence.py`, `player_correspondence.py` |
| Dream collaboration | `dream_session.py` (the six-exchange budget), `dream_proposal.py`, `dream_surface.py`, `dream_track.py`, `dispatch.py`, `dispatch_runner.py`, `dispatch_status.py` |
| Player-authored creative requests | `authoring.py` |
| Epithet nomination inputs | `recent_deeds.py` |
| Operator memory interventions | `gm.py` |
| Recall and attention calibration | `calibration_corpus.py`, `calibration_runner.py`, `attention_calibration.py`, and the two committed `*_report.json` files |

## How code here is written

- **Knowledge is permissioned per owner.** A memory, thread or letter belongs
  to an owner and has a visibility. Every read that feeds a prompt or a client
  filters by what that owner is allowed to know *before* any ranking or
  scoring. `private` content never crosses to another character. Reading a
  presentation surface never establishes knowledge.
- **History is appended, not rewritten.** An effective change adds a revision
  row and advances the revision that readers use. Do not update a past row in
  place.
- **Settlement is idempotent.** An operation that can be replayed (a delivered
  reply, a dispatch stage, a letter) records a receipt and is a no-op the
  second time.
- **Records store identifiers, counts and references**, not generated prose or
  explicit content, unless the module's docstring says it owns that text.
- **Budgets are measured on the rendered text.** `context.py` counts headings
  and attribution. Mandatory sections are never dropped silently: exceeding a
  hard bound rejects before generation.
- **Nothing infers intent from silence.** Inactivity may mark a thread dormant;
  it never marks it abandoned, and a completed quest never resolves its parent
  thread.
- **Schema changes need a migration** in `migrations/`. The project has no
  released users, so write a forward migration only; do not add a data
  backfill unless the task asks for one. After a migration, the retained test
  database is stale: run once without `--keepdb` and with `--noinput`.

## Tests

- One module is one label:
  `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.narrative.tests.<module>`
- The calibration sets are synthetic and labelled. A change to tokenisation or
  ranking is checked against them with `calibration_runner.py`; do not tune a
  threshold to make one case pass.
- A test that asserts a log event patches the binding in the caller module
  (for example `world.narrative.dispatch.log_warn`), never `world.observability.*`.

## Mistakes that have happened here

- A dream panel was published before the transaction that ended the dream
  committed, so the client saw state that was then rolled back. Publish from an
  on-commit callback.
- A departure left the panel it had emptied on screen. A change that removes a
  surface must republish that surface.
- A held request was not released when a new one was sent. When an operation
  replaces another, settle or release the one it replaces in the same
  transaction.
- A finalized proposal contained an event that happened after it was confirmed.
  A confirmed version is immutable; later input creates a new version.
