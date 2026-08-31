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

### Requirement: The internal worker contract generates every output through the sd-webui client and confines paths to the store root

`world/art/worker.py` SHALL generate one image per claimed record by calling the configured
internal sd-webui client (`world.art.sd_worker.SDWebUIClient` via the settings `ART_SD_CLIENT`
dotted path) on a background thread with a bounded timeout, SHALL convert the returned
`GeneratedImage` PNG bytes to the configured output format through
`world/art/formats.py::encode(...)`, and SHALL write the encoded bytes to the engine
pre-computed exact expected relative identity for that subject (`expected_output_identity(subject)`)
whose extension is the store extension of the configured output format (`.png`, `.webp`, `.jpg`,
`.avif`).
The client result carries the validated PNG bytes, the server-reported generation seed (a
non-negative integer parsed from the response `info` JSON, or `None` when `info` is absent,
unparseable, or carries no non-negative integer `seed`), and the exact prompt pair and
generation parameters (steps, CFG scale, width/height, and the sampler/scheduler/checkpoint
values when set) that built the request — the worker encodes provenance from those returned
values and SHALL NOT re-render the prompt library after the response, so embedded metadata can
never describe a different generation than the bytes it ships with; a missing or invalid seed
SHALL never fail an otherwise valid generation. A job SHALL settle `done` only when the encoded
bytes are written to exactly the pre-computed expected identity, resolving to an existing
regular file
under the configured `ART_STORE_ROOT` (symlink-resolved), and a successful settle SHALL persist
the returned seed on the record (nullable). The output write SHALL be atomic: bytes SHALL be
written to a unique temporary file inside the store directory and moved onto the final identity
with an atomic replace, so a failed or interrupted regeneration never corrupts or replaces the
record's prior valid output. When a successful settle's identity extension differs from the
prior committed identity's extension, the worker SHALL follow strict order: under the queue
lock, the settlement validates BOTH the new target and the record's current committed
`output_identity` (the authoritative prior — never the transient `prior_output_identity`
recovery field) under the store root; installs the new file; transitions the record's
committed identity/status in the same critical section; and only after that record transition
commits, deletes exactly the prior identity file (re-checking under-root confinement) — a
deletion error never reverts the committed transition and leaves the prior file as an
unreferenced orphan (logged, cleaned by the next regeneration), while any failure at or before
the record transition leaves the prior file on disk AND referenced. So one subject never has
two stored files referenced by a record, and no settle order can strand a record pointing at a
deleted file; a same-extension regeneration replaces in place and deletes nothing.

A named client error
(`sd_connection_error`, `sd_timeout`, `sd_http_error`, `sd_malformed_response`, `sd_no_image`,
`sd_decode_error`, `sd_not_png`, `sd_response_too_large`, `sd_image_dimensions_too_large`,
`sd_format_error`), a prompt-render or client-config error (`sd_prompt_error`,
`sd_client_config_error`), an internal error (`sd_internal_error`), or any rejected or
timed-out item SHALL settle the record `failed` with a bounded error code and SHALL retain the
record's prior valid output; no file outside the store root is ever written, deleted, or
honored. Lease reclaim SHALL bound `in_progress` records by the worst-case duration of a
claimed batch (`batch size × (generation timeout + per-item local-conversion allowance) +
margin`), never by a flat per-item timeout, so neither a slow generation nor a slow local
encode reclaims a legitimately slow batch mid-work.

#### Scenario: A valid generation completes a scene job
- **WHEN** the internal client returns valid PNG bytes for a scene subject, the configured
  format is `webp`, and the engine writes the encoded bytes to `scene/<key>.webp` under the
  store root
- **THEN** the record becomes `done` with the validated WebP output identity and the returned
  seed

#### Scenario: The server-reported seed is persisted on the record
- **WHEN** the client's transport returns an envelope whose `info` JSON carries `seed: 42` and
  the job settles `done`
- **THEN** the record stores seed `42` and `@art status` shows it for that record

#### Scenario: A missing or malformed seed never fails the job
- **WHEN** the envelope has no `info`, unparseable `info`, or an `info` whose `seed` is absent,
  negative, boolean, or non-integer, and the PNG bytes are otherwise valid
- **THEN** the job still settles `done` with seed `None`

#### Scenario: A format change replaces the prior-extension file
- **WHEN** a `done` record's prior identity is `scene/<key>.png` and its regeneration completes
  with the format configured as `webp`
- **THEN** `scene/<key>.webp` is the committed identity and `scene/<key>.png` is deleted after
  the commit, leaving exactly one stored file for the subject

#### Scenario: A same-extension regeneration deletes nothing
- **WHEN** a `done` `webp` record is regenerated while the format remains `webp`
- **THEN** the identity is atomically replaced and no file deletion occurs

#### Scenario: A format conversion failure retains the prior output
- **WHEN** `encode` raises `sd_format_error` for a claimed job whose record already has a valid
  prior output
- **THEN** the record settles `failed` with `sd_format_error`, the prior file remains intact at
  the prior identity, and nothing new is written

#### Scenario: A named client error is a bounded failure
- **WHEN** the client raises a named `SDError` (for example a connection error or timeout) for a
  claimed job
- **THEN** the item settles `failed` with the bounded error code and the record's prior valid
  output is retained

#### Scenario: An out-of-root output path is rejected
- **WHEN** the expected output identity would resolve outside `ART_STORE_ROOT`
- **THEN** the item is rejected with a bounded failure, nothing is written outside the store root,
  and the record does not become `done`

#### Scenario: A timed-out generation produces a bounded failure
- **WHEN** the sd-webui call exceeds the configured timeout
- **THEN** the record becomes `failed` with `sd_timeout` and no gameplay path blocks on the
  generation wait

#### Scenario: A failed regeneration never corrupts the prior output
- **WHEN** a regeneration of a subject with an existing valid image fails after the worker began
  writing
- **THEN** the previous image file remains intact and readable at the expected identity, no
  partial file replaces it, and the record's prior output is retained

#### Scenario: A slow batch is not reclaimed while its worker thread is running
- **WHEN** a batch of `N` claimed records is generating or locally converting and the elapsed
  time exceeds a single per-item (timeout + conversion allowance) but not
  `N × (timeout + conversion allowance) + margin`
- **THEN** the batch is not reclaimed to `pending`, and after it finishes every claimed job
  reaches a terminal `done` or `failed` state

#### Scenario: No claimed job is left stuck
- **WHEN** a claimed batch completes with any combination of success, named client errors,
  prompt-render errors, client-config errors, and internal errors
- **THEN** every claimed job reaches a terminal `done` or `failed` state with a bounded error
  code, and none stays `in_progress`

#### Scenario: Embedded provenance is the request's own prompt pair
- **WHEN** the prompt library's rendered text changes between a claim's request construction and
  its post-response conversion
- **THEN** the stored metadata carries the prompt pair from the original request, and the worker
  performs no second prompt-library render for encoding

### Requirement: A changed source-description hash is reported, never silently applied
`world/art/queue.py` SHALL compare the enqueued `source_hash` and the enqueued rendered-prompt
digest (sha256 of the rendered positive/negative prompt pair) against the record's stored values.
A changed hash for a `done` record SHALL be recorded for staff review and SHALL NOT silently
replace the completed image during ordinary play; an unchanged or absent prior hash proceeds
normally.

#### Scenario: A changed hash is staff-noted without replacing the image
- **WHEN** a subject whose record is `done` is re-ensured with a different source description or
  a different rendered-prompt digest (for example after an admin edits `art.scene_prompt`)
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

`web/art_media.py` SHALL expose a same-origin route that serves only an output identity
referenced by a `done` asset record — never an arbitrary path under the store root — after
applying the same confinement check the worker uses, and SHALL reject `..`, symlinks,
unexpected directories or extensions, absolute paths, and missing or out-of-root identities
with a 404. The accepted extensions are exactly the store extensions of the supported output
formats (`.png`, `.webp`, `.jpg`, `.avif`) — the closed set of ALL store extensions, never the
currently configured format alone, so a store mid-way through a format switch stays servable —
each served with its fixed media type (`image/png`, `image/webp`, `image/jpeg`, `image/avif`
respectively) from a closed extension-to-type map. The read-only presenter SHALL build URLs
only from validated stored identities — a `done` record's stored identity validated against the
subject's directory/key shape and the same closed four-extension set, NOT against the currently
configured output extension — and SHALL never expose `out_path` or the store root.

#### Scenario: A valid done-record identity is served same-origin with its type
- **WHEN** a `done` record references `scene/<key>.webp` resolving under the store root and it
  is requested
- **THEN** the file is served same-origin with a 200 status and `Content-Type: image/webp`

#### Scenario: An unsupported extension returns 404
- **WHEN** an identity ending in `.jxl`, `.txt`, or no extension is requested even if such a
  file exists under the store root
- **THEN** the route returns 404

#### Scenario: Out-of-root, path-traversal, symlinked, and unreferenced identities return 404
- **WHEN** an identity that resolves outside the store root, contains `..`, is a symlink, is not
  referenced by any `done` record, or names a missing file is requested
- **THEN** the route returns 404 and never exposes the store root

#### Scenario: The presenter URL comes only from a validated stored identity
- **WHEN** the presenter resolves a `done` record
- **THEN** it returns a same-origin URL built from the validated stored identity and never the
  raw `out_path` or an absolute path

#### Scenario: A mixed store keeps presenting during a format switch
- **WHEN** the configured output format is `webp` and a `done` record still references an
  existing `scene/<key>.png` from before the switch
- **THEN** the presenter returns that record as an `asset` with the same-origin
  `/art/scene/<key>.png` URL (not a placeholder), and the route serves the PNG

### Requirement: In-flight generation exposes a wire-stable status
The art presenter SHALL normalize the internal `in_progress` record status to a wire-accepted value
(`pending`) so a panel snapshot taken while a worker holds a claim never fails validation.

#### Scenario: Snapshot during generation shows a valid pending state
- **WHEN** a worker has claimed a record (status `in_progress`) and a full art snapshot is requested
- **THEN** the panel payload carries the wire-stable `pending` status (or an explicitly supported
  generating status) and the panel renders normally

#### Scenario: Settled statuses pass through unchanged
- **WHEN** a record is `missing`, `pending`, `failed`, or `done`
- **THEN** the presenter emits that status without normalization

