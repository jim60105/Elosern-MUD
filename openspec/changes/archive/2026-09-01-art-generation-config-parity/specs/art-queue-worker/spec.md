# art-queue-worker delta specification

## MODIFIED Requirements

### Requirement: The internal worker contract generates every output through the sd-webui client and confines paths to the store root
`world/art/worker.py` SHALL generate one image per claimed record by calling the configured
internal sd-webui client (`world.art.sd_worker.SDWebUIClient` via the settings `ART_SD_CLIENT`
dotted path) on a background thread with a bounded timeout, and SHALL write the returned image
bytes to the engine pre-computed exact expected relative identity for that subject (the
`out_path` equivalent, `expected_output_identity(subject)`). The client SHALL return a
`GeneratedImage` result carrying the validated PNG bytes and the server-reported generation seed
(a non-negative integer parsed from the response `info` JSON, or `None` when `info` is absent,
unparseable, or carries no non-negative integer `seed`); a missing or invalid seed SHALL never
fail an otherwise valid generation. A job SHALL settle `done` only when the client returns PNG
bytes and the engine writes them to exactly the pre-computed expected identity, resolving to an
existing regular file under the configured `ART_STORE_ROOT` (symlink-resolved), and a successful
settle SHALL persist the returned seed on the record (nullable). The output write SHALL be
atomic: bytes SHALL be written to a unique temporary file inside the store directory and moved
onto the final identity with an atomic replace, so a failed or interrupted regeneration never
corrupts or replaces the record's prior valid output. A named client error
(`sd_connection_error`, `sd_timeout`, `sd_http_error`, `sd_malformed_response`, `sd_no_image`,
`sd_decode_error`, `sd_not_png`, `sd_response_too_large`, `sd_image_dimensions_too_large`), a
prompt-render or client-config error (`sd_prompt_error`, `sd_client_config_error`), an internal
error (`sd_internal_error`), or any rejected or timed-out item SHALL settle the record `failed`
with a bounded error code and SHALL retain the record's prior valid output; no file outside the
store root is ever written or honored. Lease reclaim SHALL bound `in_progress` records by the
worst-case duration of a claimed batch (`batch size × timeout + margin`), never by a flat
per-item timeout, so a legitimately slow batch is not reclaimed mid-generation.

#### Scenario: A valid generation completes a scene job
- **WHEN** the internal client returns valid PNG bytes for a scene subject and the engine writes
  the exact expected identity under the store root
- **THEN** the record becomes `done` with the validated relative output identity

#### Scenario: The server-reported seed is persisted on the record
- **WHEN** the client's transport returns an envelope whose `info` JSON carries `seed: 42` and
  the job settles `done`
- **THEN** the record stores seed `42` and `@art status` shows it for that record

#### Scenario: A missing or malformed seed never fails the job
- **WHEN** the envelope has no `info`, unparseable `info`, or an `info` whose `seed` is absent,
  negative, boolean, or non-integer, and the PNG bytes are otherwise valid
- **THEN** the job still settles `done` with seed `None`

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
- **WHEN** a batch of `N` claimed records is generating and the elapsed time exceeds a single
  per-item timeout but not `N × timeout + margin`
- **THEN** the batch is not reclaimed to `pending`, and after it finishes every claimed job
  reaches a terminal `done` or `failed` state

#### Scenario: No claimed job is left stuck
- **WHEN** a claimed batch completes with any combination of success, named client errors,
  prompt-render errors, client-config errors, and internal errors
- **THEN** every claimed job reaches a terminal `done` or `failed` state with a bounded error
  code, and none stays `in_progress`
