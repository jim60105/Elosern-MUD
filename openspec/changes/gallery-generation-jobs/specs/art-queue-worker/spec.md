## MODIFIED Requirements

### Requirement: Asset records carry the full contract and never a live object reference
`world/art/store.py` SHALL persist one record per subject key containing the subject kind and
un-prefixed key, a deterministic source-description hash, a status (`missing` / `pending` /
`in_progress` / `done` / `failed`), a same-store relative output identity (never a worker-supplied
public URL and never an absolute path), an attempt count, a last error code, enqueued/claimed/
completed timestamps, the expected aspect ratio (`16:9` for scenes, `3:4` for portraits), and a prior
output identity retained across a failed forced regeneration. A record SHALL NOT hold a live object
reference.

A record that carries a non-empty gallery image id is a GALLERY JOB record: it additionally carries
that image id, the pending card's binding, face rectangle, and requested field ids, and its expected
output identity is the per-image gallery path rather than the subject's fixed identity. A gallery job
record SHALL carry no `output_identity` and no `prior_output_identity`: its published artifact is a
gallery card, not a record field. Gallery job records SHALL be deleted when they reach a terminal
settle, so the scanned record set is bounded by the jobs actually in flight.

#### Scenario: A gallery job record carries the pending card metadata
- **WHEN** a gallery image is requested for a subject
- **THEN** one record is created carrying the subject kind and key, a fresh gallery image id, the
  pending binding, face rectangle, and requested field ids, and no output identity

#### Scenario: A settled gallery job record is removed
- **WHEN** a gallery job settles `done` or `failed`
- **THEN** the job record no longer exists and the queue scan sees only jobs still in flight

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

Gallery generation SHALL NOT go through `ensure`. `world/art/queue.py` SHALL expose a separate
gallery enqueue that creates one record per REQUESTED IMAGE under the key
`art:<full-subject-key>:gen:<image-id>` with a freshly minted image id, so two requests for the same
subject produce two independent jobs and a gallery request is never collapsed into an existing
record. The gallery key shape SHALL NOT collide with the subject key `art:<full-subject-key>`, so
subject consolidation, `ensure`, and forced requeue never see a gallery job. `failed_keys()` and the
staff retry path SHALL exclude gallery job records, because a gallery retry is a new request, not a
re-enqueue. Both queues SHALL share the one process-wide queue lock, the one pending ordering, and
the one worker concurrency slot.

#### Scenario: Two gallery requests for one subject produce two jobs
- **WHEN** a gallery image is requested twice for the same subject
- **THEN** two records exist under two distinct `art:<full-subject-key>:gen:<image-id>` keys, both
  pending, and neither replaced the other

#### Scenario: A gallery job never disturbs the subject record
- **WHEN** a subject has both a classic asset record and an in-flight gallery job
- **THEN** `ensure`, forced requeue, and duplicate consolidation act on the classic record only, and
  the gallery job is untouched

#### Scenario: Gallery jobs are excluded from the staff retry set
- **WHEN** the failed-key listing is taken while gallery job records exist
- **THEN** no gallery job key appears in it and the staff retry path re-enqueues only subject records

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

For a GALLERY JOB record the pre-computed expected identity SHALL be the per-image gallery path
`gallery/<kind-directory>/<subject-key>/<image-id><extension>` derived from the record — never
`expected_output_identity(subject)` — and the publication SHALL be a card append rather than a record
field transition: under the queue lock, while the claim's generation token is still current, the
engine atomically replaces the temporary file onto that identity and appends exactly one card to the
subject's `GalleryRecord` through the gallery write API, carrying the verbatim prompt pair and the
server-reported seed from the returned `GeneratedImage`, the configured checkpoint when one is set,
and the job record's pending binding, face rectangle, and requested field ids. The file write SHALL
precede the card append, so an interruption leaves an orphan FILE (reclaimed by the startup prune)
and never a card pointing at a missing file. A gallery job SHALL NOT delete any prior file and SHALL
NOT touch any classic record's committed output. A gallery job that fails for any bounded reason
SHALL append NO card, SHALL record the bounded error code on the subject's `GalleryRecord`, and SHALL
leave every existing card intact.

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

#### Scenario: A gallery job publishes exactly one card at its per-image identity
- **WHEN** a claimed gallery job's generation succeeds
- **THEN** the encoded bytes are written to `gallery/<kind-directory>/<subject-key>/<image-id><extension>`
  under the store root and exactly one card carrying that identity, the returned prompt pair, and the
  returned seed is appended to the subject's gallery

#### Scenario: A failed gallery job appends no card
- **WHEN** a claimed gallery job settles `failed` with any bounded error code
- **THEN** the subject's gallery holds the same cards it held before, the bounded error code is
  recorded on the gallery record, and no file is left referenced by any card

#### Scenario: A crash between the file write and the card append leaves an orphan file
- **WHEN** the process is interrupted after the gallery file is written and before the card is appended
- **THEN** no card references the file, the gallery is unchanged, and the startup prune reclaims the
  orphan file
