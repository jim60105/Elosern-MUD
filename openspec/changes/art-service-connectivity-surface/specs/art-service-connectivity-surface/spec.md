# art-service-connectivity-surface delta specification

## ADDED Requirements

### Requirement: Connectivity probing is bounded, cached by effective configuration, and never raises
`world/art/connectivity.py` SHALL provide `probe(*, force: bool = False) -> ProbeResult`, where
`ProbeResult` is a frozen dataclass carrying `ok: bool`, `code: str | None` (the named `SDError`
code when unreachable, `None` when reachable), `host: str` (the configured URL's
`urlsplit().hostname` plus validated port ONLY — NEVER the raw `netloc`, which would carry any
URL userinfo — and never the full URL), `checked_at`, `age_seconds`, and `from_cache: bool`.
The probe SHALL issue exactly one call to a PUBLIC client seam method
`probe_samplers(*, timeout_seconds: float)` (added to `SDWebUIClient`, the configured
`ART_SD_CLIENT` class: one `GET /sdapi/v1/samplers`, JSON-list validation, `None` on success,
named `SDError`s on failure — the seam the project's fake clients implement), with
`timeout_seconds = ART_SD_PROBE_TIMEOUT_MS / 1000`, and SHALL NEVER raise: every transport,
HTTP-shape, or decode failure becomes an `ok=False` result with the named code. Results SHALL be
cached in a single process-local slot and reused (as `from_cache=True`, no request) only while
`force` is false, the cached entry is younger than `ART_SD_PROBE_CACHE_SECONDS`, and a stored
fingerprint over the effective connectivity settings (base URL, credential presence booleans,
probe timeout) equals the fingerprint recomputed at call time; any change to those settings —
including a settings reload — SHALL miss the cache. `force=True` SHALL always probe fresh and
never consume the cached entry. No credential value SHALL ever appear in a `ProbeResult`, in
cache state, or in any log line.

#### Scenario: A reachable server yields a clean ok verdict
- **WHEN** `probe()` runs against a server whose samplers endpoint returns a JSON list
- **THEN** the result is `ok=True`, `code=None`, and no exception escapes

#### Scenario: An unreachable server yields the named code, never an exception
- **WHEN** `probe()` runs while the server refuses connections
- **THEN** the result is `ok=False` with `code` equal to the client's named error (for example
  `sd_connection_error`) and the caller sees no exception

#### Scenario: A fresh cached verdict is reused without a request
- **WHEN** `probe()` is called twice within `ART_SD_PROBE_CACHE_SECONDS` for unchanged settings
- **THEN** the second call performs no HTTP request and returns `from_cache=True`

#### Scenario: A forced probe bypasses a young cache entry
- **WHEN** `probe(force=True)` is called immediately after a successful probe
- **THEN** exactly one new request is issued and `from_cache=False`

#### Scenario: A settings change invalidates the verdict
- **WHEN** the effective base URL (or credential presence, or probe timeout) changes and
  `probe()` is called with an otherwise still-young cached entry
- **THEN** the fingerprint mismatch forces a fresh probe of the new target

#### Scenario: Credentials never leak through the probe surface
- **WHEN** Basic auth is configured and any `ProbeResult` or cache state is inspected or logged
- **THEN** no username or password value appears anywhere in it

#### Scenario: A base URL with userinfo yields no credential material
- **WHEN** the configured base URL is `http://user:password@example.test:7860/` and any probe
  result or cache state is produced and inspected
- **THEN** the host field is `example.test:7860` and no result, cache entry, or health line
  contains `user`, `password`, `@`, or the raw netloc

### Requirement: Connectivity state never gates generation
No production module under `world/art/` except `connectivity.py` itself SHALL import
`world.art.connectivity` — worker, service, scheduler, queue, store, formats, sd_worker, and
every future module; `commands/art.py` SHALL be the only importer. Enforcement is a
package-wide import-boundary test that AST-parses every production `world/art/**/*.py` file
and fails on any connectivity import outside `connectivity.py` itself, plus an integration
test that seeds a cached failed verdict, recovers the fake server, and proves a claimed job
still settles `done`. A failed or absent probe SHALL NOT block, delay, skip, or fail a queue
job: the worker SHALL attempt server calls for claimed records exactly as the queue contract
requires regardless of the latest probe verdict.

#### Scenario: An unreachable verdict does not stop a successful job
- **WHEN** the last probe verdict is `ok=False` and the server recovers so a claimed job's
  generation succeeds
- **THEN** the job settles `done` with no reference to the stale verdict

#### Scenario: The whole-package import boundary holds
- **WHEN** the import-boundary test parses every production module under `world/art/`
- **THEN** no module other than `connectivity.py` itself imports `world.art.connectivity`,
  and any import from service, scheduler, queue, or a future module fails the test

