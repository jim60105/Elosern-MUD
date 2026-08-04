# art-queue-worker Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
## Requirements
### Requirement: Asset records carry the full contract and never a live object reference
`world/art/store.py` SHALL persist one record per subject key containing the subject kind and
un-prefixed key, a deterministic source-description hash, a status (`missing` / `pending` /
`in_progress` / `done` / `failed`), a same-store relative output identity (never a worker-supplied
public URL and never an absolute path), an attempt count, a last error code, enqueued/claimed/
completed timestamps, the expected aspect ratio (`16:9` for scenes, `3:4` for portraits), and a prior
output identity retained across a failed forced regeneration. A record SHALL NOT hold a live object
reference.

#### Scenario: A completed record contains only the contract fields
- **WHEN** a worker successfully completes a scene job
- **THEN** the record has status `done`, a relative `output_identity` under the store root, a 16:9
  aspect ratio, a completed timestamp, and no live object reference

#### Scenario: A claimed record is in_progress with a lease
- **WHEN** a drain claims a `pending` record for the worker
- **THEN** the record becomes `in_progress`, records a `claimed_at` lease timestamp, and increments its
  attempt count

#### Scenario: An expired lease is reclaimed to pending
- **WHEN** a record remains `in_progress` past its lease (worker timeout plus margin)
- **THEN** the next drain, startup recovery, or `@art run` reclaims it to `pending` so the job is not
  lost and never stays stuck

### Requirement: The queue is keyed by subject identity and enqueue is idempotent
`world/art/queue.py::ensure(...)` SHALL be keyed by the full subject key and SHALL be idempotent for an
existing `pending`, `in_progress`, or `done` record. A `missing` record SHALL become `pending`; a
`failed` record SHALL re-enqueue to `pending` on the next ensure or staff retry. Forced staff
regeneration SHALL reset the record to `pending` under the queue lock and SHALL preserve the prior
valid output.

#### Scenario: Re-ensuring a pending, in-progress, or done subject is a no-op
- **WHEN** `ensure` is called again for a subject whose record is already `pending`, `in_progress`, or
  `done`
- **THEN** the record is unchanged and no new job is queued

#### Scenario: Missing and failed records become pending
- **WHEN** `ensure` runs for a `missing` record and then for a `failed` record
- **THEN** both become `pending`, and the failed record's attempt count increments

#### Scenario: Forced regeneration resets and preserves the prior output
- **WHEN** a staff requeue resets a `done` subject
- **THEN** the record becomes `pending`, the prior valid output identity is preserved, and a later
  invalid worker result leaves the prior output intact

### Requirement: Scenes and portraits share one serialization lock and one worker concurrency slot
`world/art/` SHALL expose a single queue lock shared by scene and portrait operations. Claiming,
settling, and forced requeues SHALL acquire the lock, while the external worker subprocess SHALL run
on a background Twisted thread with the lock released, so concurrent drains, `@art` commands, and
`on_commit` enqueues serialize on fast DB transactions and never block one another across a worker
wait. The external worker SHALL run at most one job at a time.

#### Scenario: Concurrent drains serialize and never block on the worker wait
- **WHEN** two drains are attempted on the shared queue while a worker is running
- **THEN** the second drain claims its batch only after the first settles, no record is mutated
  concurrently, and neither drain holds the lock across the worker subprocess wait

### Requirement: The external worker contract validates every output against its input and confines paths to the store root
`world/art/worker.py` SHALL build a job `{"kind", "key", "description", "out_path", "aspect_ratio"}`
per claimed record, where `out_path` is the engine pre-computed exact expected relative identity for
that subject, run the external command from the settings `ART_WORKER_CMD` with JSON input and JSON
output on a background thread, and apply a bounded timeout. A result SHALL be accepted only when its
key matches an input job, its status is `success`/`failed`, and its `output_identity` exactly equals
the pre-computed expected identity for that job, resolving to an existing regular file under the
configured `ART_STORE_ROOT` (symlink-resolved). The batch protocol SHALL be one-to-one: every input
job must reach exactly one terminal result; a missing, duplicated, or unparseable result SHALL mark
the unfinished claimed jobs `failed` with a bounded protocol error. Any rejected or timed-out item
SHALL record a bounded failure and retain the record's prior valid output; no file outside the store
root is ever honored.

#### Scenario: A valid fixture worker completes a scene job
- **WHEN** the fixture worker writes the exact expected identity under the store root and reports
  success for a matching key
- **THEN** the record becomes `done` with the validated relative output identity

#### Scenario: A mismatched or malformed result is rejected
- **WHEN** a result names a key that was not an input job, reports a status outside `success`/`failed`,
  or returns an output identity that differs from the job's exact expected identity
- **THEN** the item is rejected with a bounded failure and the record's prior valid output is retained

#### Scenario: An out-of-root output identity is rejected
- **WHEN** a worker result's output identity resolves outside `ART_STORE_ROOT`
- **THEN** the item is rejected with a bounded failure, nothing is written outside the store root, and
  the record does not become `done`

#### Scenario: A timed-out worker produces a bounded failure
- **WHEN** the worker subprocess exceeds the configured timeout
- **THEN** the record becomes `failed` with a bounded error code and no gameplay path blocks on the
  worker wait

#### Scenario: A worker crash or malformed batch leaves no job stuck
- **WHEN** the worker emits fewer, duplicate, or non-JSON results for a claimed batch
- **THEN** every claimed job that lacks a valid terminal result becomes `failed` with a bounded
  protocol error, and none stays `in_progress`

### Requirement: A changed source-description hash is reported, never silently applied
`world/art/queue.py` SHALL compare the enqueued `source_hash` against the record's stored hash. A
changed hash for a `done` record SHALL be recorded for staff review and SHALL NOT silently replace the
completed image during ordinary play; an unchanged or absent prior hash proceeds normally.

#### Scenario: A changed hash is staff-noted without replacing the image
- **WHEN** a subject whose record is `done` is re-ensured with a different source description
- **THEN** the completed image is left untouched and the hash change is surfaced in the record's
  staff-visible review signal

### Requirement: The scheduler is settings-configurable and disableable
`world/art/scheduler.py` SHALL provide a persistent Script that drains up to the configured limit of
pending jobs at the configured interval. When `ART_SCHEDULER_ENABLED` is false the scheduler SHALL run
no drain, records SHALL remain `missing`/`pending`, placeholders SHALL remain, and gameplay SHALL
proceed unchanged.

#### Scenario: The disabled scheduler never drains
- **WHEN** the scheduler is disabled and pending records exist
- **THEN** no drain runs, the records stay `pending`, and gameplay proceeds

#### Scenario: The enabled scheduler drains up to its limit per interval
- **WHEN** the scheduler is enabled with a limit and pending records exist
- **THEN** each interval drains at most the configured limit of pending records through the worker

### Requirement: Media serving maps validated stored identities to same-origin URLs without exposing the store root
`web/art_media.py` SHALL expose a same-origin route that serves only an output identity referenced by a
`done` asset record — never an arbitrary path under the store root — after applying the same
confinement check the worker uses, and SHALL reject `..`, symlinks, unexpected directories or
extensions, absolute paths, and missing or out-of-root identities with a 404. The read-only presenter
SHALL build URLs only from validated stored identities and SHALL never expose `out_path` or the store
root.

#### Scenario: A valid done-record identity is served same-origin
- **WHEN** an output identity referenced by a `done` record and resolving under the store root is
  requested
- **THEN** the file is served same-origin with a 200 status

#### Scenario: Out-of-root, path-traversal, symlinked, and unreferenced identities return 404
- **WHEN** an identity that resolves outside the store root, contains `..`, is a symlink, is not
  referenced by any `done` record, or names a missing file is requested
- **THEN** the route returns 404 and never exposes the store root

#### Scenario: The presenter URL comes only from a validated stored identity
- **WHEN** the presenter resolves a `done` record
- **THEN** it returns a same-origin URL built from the validated stored identity and never the raw
  `out_path` or an absolute path

