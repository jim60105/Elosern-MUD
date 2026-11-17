# Spec Delta

## MODIFIED Requirements

### Requirement: Connectivity state never gates generation
Connectivity SHALL remain diagnostic for gallery, automatic ensure, queue and worker paths. Only owned pending `creation.portrait.generate` admission SHALL refuse known service unavailability with retryable `portrait_service_unavailable` before policy, receipt or queue writes. Its server snapshot SHALL drive creation's disabled state. No production `world/art/` module except `connectivity.py` SHALL import that module.

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

#### Scenario: Creation admission is the sole refusal exception
- **WHEN** an owned pending character submits valid draft portrait values and the server probe reports unavailable
- **THEN** only `creation.portrait.generate` rejects with distinct retryable `portrait_service_unavailable`, before any policy/portrait receipt/state/queue write, while canonical creation and play remain unaffected
- **AND** an available verdict admits the ordinary validated enqueue path; no gate has only continue-anyway outcomes

#### Scenario: Production connectivity imports remain narrowly allowlisted
- **WHEN** production importer boundaries are checked
- **THEN** only `commands/art.py`, `connectivity.py` itself and `world/rules/creation_portrait.py` import connectivity; the rules module calls the probe only for creation admission and exposes only a read-only availability snapshot to presentation

#### Scenario: Read-only availability never performs a probe
- **WHEN** `read_cached_probe()` reads the existing single cache
- **THEN** a current configuration-matching verdict is returned immutably, absent/expired/mismatched entries return null, invalid effective settings return the safe internal-error verdict, and no network call, cache write or cache-life extension occurs
- **AND** the server projects a failed current verdict as creation's unavailable reason without sending host, endpoint, credentials, prompt or probe timestamps

#### Scenario: Refusal has no durable unavailable lock
- **WHEN** creation refreshes its server panel after cache expiry/configuration change or a newer successful diagnostic, then the player explicitly retries generation
- **THEN** stale unavailability is not stored on the character, the panel recomputes it from the current server snapshot, and admission re-evaluates its bounded verdict without replaying an earlier request

#### Scenario: Other image paths remain ungated
- **WHEN** a failed probe is cached while a gallery request, automatic ensure or claimed worker job runs
- **THEN** no new connectivity precondition changes its existing request/queue/worker behavior, and an admitted job attempts the server regardless of later probe verdicts

#### Scenario: Art remains optional for deterministic play
- **WHEN** art and generative text services are offline
- **THEN** preset/custom character creation, activation and deterministic gameplay stay available; only optional creation-portrait admission is refused
