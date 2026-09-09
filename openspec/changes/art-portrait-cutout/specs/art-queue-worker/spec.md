## MODIFIED Requirements

### Requirement: The internal worker contract generates every output through the sd-webui client and confines paths to the store root

`world/art/worker.py` SHALL generate one image per claimed record by calling the configured
internal sd-webui client (`world.art.sd_worker.SDWebUIClient` via the settings `ART_SD_CLIENT`
dotted path) on a background thread with a bounded timeout, SHALL apply the portrait
background-removal stage to the returned PNG bytes when and only when that stage's own
enablement and subject-kind conditions hold (see the `art-portrait-cutout` capability),
SHALL convert the resulting PNG bytes to the configured output format through
`world/art/formats.py::encode(...)`, and SHALL write the encoded bytes to the engine
pre-computed exact expected relative identity for that subject (`expected_output_identity(subject)`)
whose extension is the store extension of the configured output format (`.png`, `.webp`, `.jpg`,
`.avif`). The stage order SHALL be generate, then background removal, then encode, then write,
then publish: the removal operates on the transport PNG bytes so the encoder's PNG-container
contract, sanitization, metadata policy, and format selection are unchanged, and exactly one
artifact is published per job. When the stage does not apply, the bytes reach `encode` exactly as
they do today.
The client result carries the validated PNG bytes, the server-reported generation seed (a
non-negative integer parsed from the response `info` JSON, or `None` when `info` is absent,
unparseable, or carries no non-negative integer `seed`), and the exact prompt pair and
generation parameters (steps, CFG scale, width/height, and the sampler/scheduler/checkpoint
values when set) that built the request — the worker encodes provenance from those returned
values and SHALL NOT re-render the prompt library after the response, so embedded metadata can
never describe a different generation than the bytes it ships with; a missing or invalid seed
SHALL never fail an otherwise valid generation. The background-removal stage SHALL NOT alter that
provenance: it is a local post-process, not a generation parameter, and the embedded
parameters block continues to describe the request sd-webui served. A job SHALL settle `done`
only when the encoded
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
leave every existing card intact. The background-removal stage applies to a gallery job on exactly
the same subject-kind terms as to a classic record, and its failures settle through this gallery
path.

A named client error
(`sd_connection_error`, `sd_timeout`, `sd_http_error`, `sd_malformed_response`, `sd_no_image`,
`sd_decode_error`, `sd_not_png`, `sd_response_too_large`, `sd_image_dimensions_too_large`,
`sd_format_error`), a background-removal error (`art_cutout_unavailable`,
`art_cutout_error`), a prompt-render or client-config error (`sd_prompt_error`,
`sd_client_config_error`), an internal error (`sd_internal_error`), or any rejected or
timed-out item SHALL settle the record `failed` with a bounded error code and SHALL retain the
record's prior valid output; no file outside the store root is ever written, deleted, or
honored. Lease reclaim SHALL bound `in_progress` records by the worst-case duration of a
claimed batch (`batch size × (generation timeout + per-item local-conversion allowance +
per-item background-removal allowance) + margin`), never by a flat per-item timeout, so
neither a slow generation, a slow local encode, nor a slow background-removal pass reclaims a
legitimately slow batch mid-work. The background-removal allowance SHALL be
`ART_REMBG_ALLOWANCE_SECONDS` when that stage is enabled and zero when it is disabled, so a
deployment that does not run the stage keeps today's bound exactly. A lease that nevertheless
expires mid-flight — the one-time model download is deliberately outside the bound — SHALL
remain safe by the claim-token rule APPLIED SYMMETRICALLY: every worker-owned terminal settle —
the successful publication AND the terminal failure — SHALL carry the claim-time `generation_token`
snapshot and SHALL reject a mismatch as a no-op, so a stale worker's late result, whether success
or failure, publishes nothing, settles nothing, and never touches a record another claim now owns.
The worst outcome is one wasted generation, never a double publish, a corrupted output, or a
stale failure stealing a live claim. (This change adds the guard to the classic terminal-failure
path, which is status-only today; the gallery-failure path already carries the token.)

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

#### Scenario: A background-removal failure is a bounded failure
- **WHEN** the background-removal stage raises for a claimed portrait job whose record already
  has a valid prior output
- **THEN** the record settles `failed` with `art_cutout_unavailable` or `art_cutout_error`, the
  prior file remains intact at the prior identity, and nothing new is written

#### Scenario: The removal runs between generation and encoding
- **WHEN** an enabled portrait job generates successfully with an injected removal backend and
  an observed `encode`
- **THEN** `encode` received the backend's returned bytes rather than the client's, the client
  was called exactly once, and exactly one artifact was published

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
- **WHEN** a batch of `N` claimed records is generating, removing backgrounds, or locally
  converting and the elapsed time exceeds a single per-item (timeout + conversion allowance +
  removal allowance) but not `N × (timeout + conversion allowance + removal allowance) + margin`
- **THEN** the batch is not reclaimed to `pending`, and after it finishes every claimed job
  reaches a terminal `done` or `failed` state

#### Scenario: A disabled removal stage keeps today's lease bound
- **WHEN** the lease bound is computed with `ART_REMBG_ENABLED` false
- **THEN** it equals `ART_SCHEDULER_LIMIT × (ART_SD_TIMEOUT_SECONDS + conversion allowance) +
  margin` exactly, and with the stage enabled it is larger by
  `ART_SCHEDULER_LIMIT × ART_REMBG_ALLOWANCE_SECONDS`

#### Scenario: A stale classic failure cannot steal a reclaimed claim
- **WHEN** a classic portrait job's cutout overruns the lease, the record is reclaimed to
  `pending` and re-claimed under a new generation token, and the obsolete worker then settles
  its bounded `art_cutout_*` failure with its stale claim-time token
- **THEN** that settle is a no-op: the record's status, error code, and outputs are exactly what
  the current claim leaves them, and the obsolete worker's temporary artifacts are removed

#### Scenario: No claimed job is left stuck
- **WHEN** a claimed batch completes with any combination of success, named client errors,
  background-removal errors, prompt-render errors, client-config errors, and internal errors
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
