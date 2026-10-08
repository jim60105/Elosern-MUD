# art-service-connectivity-surface Specification

## Purpose
Give operators a bounded, cached, diagnostic-only view of sd-webui reachability:
a never-raising connectivity probe (world/art/connectivity.py) keyed by the
effective configuration, the `@art health` staff dashboard that consumes it,
and the two probe budget knobs (`ART_SD_PROBE_TIMEOUT_MS`,
`ART_SD_PROBE_CACHE_SECONDS`) — with the structural guarantee that a
connectivity verdict can never gate, block, or alter deterministic generation.

## Requirements

### Requirement: Connectivity probing is bounded, cached by effective configuration, and never raises
`world/art/connectivity.py` SHALL provide `probe(*, force: bool = False) -> ProbeResult`.
The probe SHALL issue exactly one call to a PUBLIC client seam method
`probe_samplers(*, timeout_seconds: float)`, with
`timeout_seconds = ART_SD_PROBE_TIMEOUT_MS / 1000`, and SHALL NEVER raise: every failure becomes an
`ok=False` result. Results SHALL be cached in a single process-local slot and reused only under the
cache conditions below.

#### Scenario: A reachable server yields a clean ok verdict
- **WHEN** `probe()` runs against a server whose samplers endpoint returns a JSON list
- **THEN** the result is `ok=True`, `code=None`, and no exception escapes

#### Scenario: An unreachable server yields the named code, never an exception
- **WHEN** `probe()` runs while the server refuses connections
- **THEN** the result is `ok=False` with `code` equal to the client's named error (for example
  `sd_connection_error`) and the caller sees no exception

#### Scenario: A forced probe bypasses a young cache entry
- **WHEN** `probe(force=True)` is called immediately after a successful probe
- **THEN** exactly one new request is issued and `from_cache=False`

#### Scenario: A misconfigured client seam yields a failed verdict, never an exception
- **WHEN** `ART_SD_CLIENT` names an unresolvable dotted path (or its constructor raises) and
  `probe()` is called
- **THEN** the result is `ok=False` with `code="sd_internal_error"`, the host field carries no
  URL text, and the caller sees no exception

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
- **AND** the stored cache fingerprint is derived from the userinfo-stripped URL, so it is
  identical to the fingerprint of the same target configured as
  `http://example.test:7860/` and is not an offline-guessable digest of the embedded
  credentials

#### Scenario: URL userinfo is not a cache-identity component
- **WHEN** two probe calls run against configurations differing ONLY in URL userinfo
  (`http://example.test:7860/` versus `http://user:password@example.test:7860/`)
- **THEN** the second call reuses the cached verdict (`from_cache=True`), because userinfo
  never affects a request — the transport derives Basic auth solely from the credential
  settings

#### Scenario: ProbeResult is a frozen dataclass with the diagnostic fields
- **WHEN** `ProbeResult` is inspected
- **THEN** it is a frozen dataclass carrying `ok: bool`, `code: str | None` (the named `SDError`
  code when unreachable, `None` when reachable), `host: str`, `checked_at`, `age_seconds`, and
  `from_cache: bool`

#### Scenario: The host field carries hostname plus validated port only
- **WHEN** a probe result's `host` is derived from the configured URL
- **THEN** it is the URL's `urlsplit().hostname` plus validated port ONLY — NEVER the raw `netloc`,
  which would carry any URL userinfo — and never the full URL

#### Scenario: The probe seam is a public client method with fixed semantics
- **WHEN** `probe_samplers(*, timeout_seconds: float)` is added to `SDWebUIClient`, the configured
  `ART_SD_CLIENT` class
- **THEN** it performs one `GET /sdapi/v1/samplers`, validates the JSON list, returns `None` on
  success and named `SDError`s on failure — the seam the project's fake clients implement

#### Scenario: Every failure class maps to a named code
- **WHEN** a transport, HTTP-shape, decode, settings-snapshot, host-derivation, or
  client-resolution failure occurs
- **THEN** the result is `ok=False` carrying the named `SDError` code verbatim when one is known,
  `sd_connection_error` for an `OSError`, and `sd_internal_error` for any other unexpected failure

#### Scenario: An underivable host yields a placeholder with no URL text
- **WHEN** the host cannot be derived
- **THEN** the result carries a host placeholder carrying no URL text

#### Scenario: Cache reuse requires all three conditions
- **WHEN** a cached probe verdict is considered for reuse
- **THEN** it is reused (as `from_cache=True`, no request) only while `force` is false, the cached
  entry is younger than `ART_SD_PROBE_CACHE_SECONDS`, and a stored fingerprint over the effective
  connectivity settings (base URL, credential presence booleans, probe timeout) equals the
  fingerprint recomputed at call time

#### Scenario: Any effective-settings change including a reload misses the cache
- **WHEN** any of those effective connectivity settings changes — including a settings reload
- **THEN** the cache is missed

#### Scenario: force=True always probes fresh
- **WHEN** `probe(force=True)` is called
- **THEN** it always probes fresh and never consumes the cached entry

#### Scenario: No credential value reaches any probe artifact
- **WHEN** any `ProbeResult`, cache state, or log line is produced
- **THEN** no credential value appears in it

#### Scenario: The fingerprint's base-URL component strips userinfo
- **WHEN** the stored fingerprint's base-URL component is computed
- **THEN** it is a USERINFO-STRIPPED normalisation of the configured URL
  (`scheme://host[:port]/path[?query]`), so no credential value — including one embedded as URL
  userinfo — is ever an input to a stored digest

### Requirement: Connectivity state never gates generation
No production module under `world/art/` except `connectivity.py` itself SHALL import
`world.art.connectivity` — worker, service, scheduler, queue, store, formats, sd_worker, and
every future module; `commands/art.py` SHALL be the only importer. A failed or absent probe
SHALL NOT block, delay, skip, or fail a queue job: the worker SHALL attempt server calls for
claimed records exactly as the queue contract requires regardless of the latest probe verdict.

#### Scenario: An unreachable verdict does not stop a successful job
- **WHEN** the last probe verdict is `ok=False` and the server recovers so a claimed job's
  generation succeeds
- **THEN** the job settles `done` with no reference to the stale verdict

#### Scenario: The whole-package import boundary holds
- **WHEN** the import-boundary test parses every production module under `world/art/`
- **THEN** no module other than `connectivity.py` itself imports `world.art.connectivity`,
  and any import from service, scheduler, queue, or a future module fails the test

#### Scenario: Enforcement is an AST import-boundary test plus a settle-done integration test
- **WHEN** enforcement of this guarantee is inspected
- **THEN** it is a package-wide import-boundary test that AST-parses every production
  `world/art/**/*.py` file and fails on any connectivity import outside `connectivity.py`
  itself, plus an integration test that seeds a cached failed verdict, recovers the fake
  server, and proves a claimed job still settles `done`
