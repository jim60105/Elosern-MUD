## 1. Protocol and Presentation Core

- [x] 1.1 Create `web/webclient/presentation/` with protocol constants, exact validators for every client/server envelope and server-time object, common available/unavailable panel discriminators, JSON-safety and global bound checks, presentation context types, and pure tests covering every valid/invalid version-1 branch.
- [x] 1.2 Implement the duplicate-rejecting presenter registry with only the production `status` panel name, plus tests for duplicate names, unknown output panels, and isolated test registries.
- [x] 1.3 Implement the session-scoped snapshot coordinator with cryptographic epoch creation, monotonic per-epoch revisions, full snapshots, complete panel replacements, server calendar serialization, puppet-change reset, and tests proving that no epoch or revision is persisted.
- [x] 1.4 Add registry-owned unavailable builders, presenter exception isolation, exact common unavailable payloads, correlation-ID logging, and tests proving one broken presenter does not suppress another panel or narrative output and leaks no exception/path data.
- [x] 1.5 Implement authenticated WebSocket-only `ui_sync` in `server/conf/inputfuncs.py`, resolving the actor solely from `session.puppet`, and add Evennia integration tests for anonymous, unpuppeted, puppeted, malformed, unsupported-version, client-actor, WebSocket, and Telnet cases.
- [x] 1.6 Implement the project `text` input function around Evennia 6.1's Deferred command handler with an observer that preserves callback values and errback Failures while preserving idle, MXP, nickname, output, and counter semantics; test safe post-settlement WebClient refresh on both paths, presentation failure isolation, and unchanged text-only Telnet behavior.

## 2. Action Dispatch Infrastructure

- [x] 2.1 Create `web/webclient/actions/` with duplicate-rejecting action registration, exact per-action payload validation, an empty production registry, and tests proving unknown actions never enter the command parser and test adapters cannot leak into production registration.
- [x] 2.2 Implement global action-envelope validation and authenticated session actor binding, with tests for every field/type/size bound, unknown fields, actor-like fields, non-WebSocket sessions, and missing authentication or puppet state.
- [x] 2.3 Implement epoch/base-revision equality checks before action-specific validation and adapter invocation; test stale revision and old epoch call no adapter and each emits a fresh canonical snapshot.
- [x] 2.4 Implement the bounded insertion-ordered completed-result cache per transport-and-puppet sequence and duplicate replay; test one execution per request ID, deterministic eviction, disposal on transport or puppet replacement, and no old-puppet result publication after sequence retirement.
- [x] 2.5 Implement one in-flight marker and one coordinator publication lock per active sequence while keeping `ui_sync` available; serialize sync against completion publication, clear markers on sequence retirement, and test concurrent busy rejection plus every success/rejection/error/retirement path.
- [x] 2.6 Implement exact version-1 `ui_action_result` and `ui_protocol_error` serialization for all discriminated outcomes/codes, conditional correlation IDs, Traditional Chinese messages, and declared presentation revisions; test every required/forbidden field and no traceback, path, exception, payload, actor, or panel leakage.
- [x] 2.7 Add an isolated proof adapter and integration tests demonstrating session actor delivery, exactly-once invocation, domain revalidation, canonical completion presentation sent before same-revision result, server unlock only after both sends, serialized concurrent sync, and no direct persistent writes from dispatcher/presenter modules.

## 3. Canonical Status Presentation

- [x] 3.1 Refactor `world/rules/combat_modifiers.py` to expose an immutable read-only sequence of matched rule IDs and exact adjustment bundles, keep `evaluate_combat_modifiers()` behavior identical by merging that sequence, and add regression tests for every rule and merged combination.
- [x] 3.2 Add immutable status display metadata for current buff and combat-modifier IDs, with a coverage test requiring every displayable current rule/buff to have one stable Traditional Chinese label and severity.
- [x] 3.3 Implement `world/rules/status_query.py` as a frozen no-create read model over existing trait, optional buff, sexual baseline/materialized state, creation, and combat records, then implement the exact status presenter from that model; test unmaterialized baselines remain unmaterialized and active disguise never changes true resources.
- [x] 3.4 Implement canonical `creation`/`combat`/`exploration` mode selection and valid combat mode/round output using `creation_pending` and `read_session()`, with tests for all modes and malformed combat records.
- [x] 3.5 Add mutation-boundary tests comparing raw Attribute storage, traits, gauges, optional buff storage, sexual state, combat record, location, Script count, and world tick before/after repeated status/snapshot reads; verify missing/malformed required state produces unavailable status rather than default materialization or zero values.
- [x] 3.6 Add `read_world_clock()` as a no-create query, explicitly ensure the clock from deterministic server startup, make presentation fail safely with `presentation_unavailable` when it is absent, and test that synchronization against a missing clock creates no Script.

## 4. Local Desktop WebClient Shell

- [x] 4.1 Select and vendor the minimal compatible pinned jQuery and GoldenLayout 1.x JavaScript/CSS assets under project static paths, record source versions and licenses, and add a contract test that the project template references no remote runtime URL.
- [x] 4.2 Add project WebClient template overrides that retain Evennia connection variables and transport loading while removing unused CDN Bootstrap, Popper, Favico, and stock free-form layout dependencies.
- [x] 4.3 Implement the version-1 GoldenLayout configuration and project layout plugin with non-closable header, primary narrative, art placeholder, status, local-map placeholder, action dock, and command drawer components; placeholders must explicitly identify unavailable later delivery units.
- [x] 4.4 Implement `elosern.css` with the ink-night/vermilion desktop theme, visible non-color focus, numeric resource labels, accessible disabled descriptions/live region, safe overflow at 1440x900 and 1280x720, and reduced-motion behavior.
- [x] 4.5 Implement `elosern/protocol.js` and `plugins/elosern_state.js` with explicit `beginTransport(generation)`, bounded in-memory retired epochs, current-generation first-snapshot adoption, same-generation different-epoch rejection, exact envelope/panel validation, complete replacement, subscriptions, and bounded one-sync renderer recovery.
- [x] 4.6 Add Node tests for every exact server schema/discriminator, atomic multi-panel rejection, lower-revision new-generation adoption, retired-epoch and prior-generation discard, same-active-generation different-epoch rejection, non-newer revision rejection, complete replacement, and one-sync failure-loop prevention.
- [x] 4.7 Implement versioned local layout persistence/migrations that store only bounded dimensions/tab state and harmless preferences, ignore stock layout keys, preserve required components, migrate known project versions, and reset malformed/oversized/unknown versions.
- [x] 4.8 Add Node tests for known layout migration, unknown/malformed/oversized reset, required-component restoration, and rejection of canonical state, identity, request, command, epoch, revision, or panel fields from persistence.

## 5. Keyboard, Narrative, and Action Client

- [x] 5.1 Implement the DOM-independent `KeyboardRouter` focus stack with arrow movement, Enter confirmation, one-level Escape, reserved Space multi-select transition, `/` drawer transition, disabled-item focus, repeated-Enter suppression, and in-flight mutation locking.
- [x] 5.2 Add Node tests for list/grid focus geometry, submenu return focus, disabled explanations without send, drawer transitions, repeated key events, and action locking until both a result and accepted state at or above its declared presentation revision exist.
- [x] 5.3 Implement `plugins/elosern_actions.js` using `Evennia.msg` for exact `ui_sync`/`ui_action` envelopes, bounded sequence-local request IDs, one in-flight request, completion-revision gating, cached-result handling, no disconnect retry, stale recovery, safe result live announcements, and uncertain-result notice after reconnect.
- [x] 5.4 Implement the command drawer on Evennia's ordinary text transport with existing command history, editable-field-safe `/`, send/Escape close behavior, and action-dock focus restoration; verify no drawer path constructs `ui_action`.
- [x] 5.5 Implement narrative routing with preserved scrollback position and unread count when not at bottom, plus text-only fallback when state/render plugins fail; insert every server-authored label or description through text APIs rather than HTML interpolation.
- [x] 5.6 Implement connection-open sync, synchronizing lock, non-dismissible offline overlay, mutation suppression while disconnected, and overlay removal only after valid new-epoch snapshot adoption.

## 6. Isolated Browser Acceptance Harness

- [x] 6.1 Add Playwright through `uv add --dev playwright`, commit synchronized `pyproject.toml` and `uv.lock`, and confirm `uv sync --locked` resolves the development environment.
- [x] 6.2 Create browser-test-only Evennia settings and fixture helpers that allocate temporary SQLite, log, media/static/runtime paths, dynamic loopback Telnet/HTTP/WebSocket ports, and deterministic account/character state without reading or writing the developer database or assuming port 4001.
- [x] 6.3 Implement the repeatable `unittest` managed-server harness with process ownership, non-interactive startup, bounded allocated-URL readiness polling, diagnostics, registered cleanup, and bounded shutdown; test startup failure, timeout, repeated discovery, distinct dynamic ports, and no stale process/path state.
- [x] 6.4 Add Playwright request guards that fail every non-local request and deterministic fixture helpers that never invoke an LLM, image generator, or other external service.
- [x] 6.5 Add shell acceptance at 1440x900 and 1280x720 for every required surface, explicit unavailable placeholders, numeric status, keyboard-only drawer send/cancel, scrollback unread behavior, and focus restoration.
- [x] 6.6 Add browser tests for UI action locking with the proof fixture, disabled control safety, safe rendering of HTML-like player text, and ordinary text usability when structured status/OOB rendering fails.
- [x] 6.7 Add end-to-end WebSocket interruption/reconnect tests proving offline locking, no action retry, uncertain-result notice, lower-revision adoption only in a new transport generation, rejection of retired/prior-generation messages, and rejection of a different-epoch full snapshot on one active socket.
- [x] 6.8 Add browser tests for known layout migration, unknown/malformed layout reset, one-sync malformed-panel degradation, and incompatible protocol locking while ordinary text commands continue.

## 7. Quality Gate and Regression Contracts

- [x] 7.1 Extend `.github/workflows/quality-gate.yml` after locked sync/runtime preparation to install Chromium before any Python runner that can discover browser tests, run the Node suite, and run `uv run --locked python -m unittest discover -s web/tests/browser -t .` before traceability evidence verification.
- [x] 7.2 Pass the existing `OPENSPEC_TEST_EVIDENCE` path to annotated browser tests and preserve strict OpenSpec validation, both required Python entry points, coverage combination/root verification, the aggregate 90% branch gate, and Codecov failure behavior.
- [x] 7.3 Add repository contract tests for local browser assets/licenses, exact workflow commands and Chromium-before-Python ordering, locked Playwright dependency, supported Node version, dynamic browser isolation settings/process ownership, repeatable discovery, and absence of failure suppression or remote fixtures.
- [x] 7.4 Run focused server protocol/action/status tests, Node tests, and the Playwright browser suite while iterating; record and fix every regression without weakening bounds, isolation, accessibility, or cleanup assertions.

## 8. Spec Sync, Traceability, and Final Verification

- [x] 8.1 Compare implementation and tests against all six delta specs plus both approved WebClient design documents; remove fake panel behavior and confirm combat, map, services, creation forms, dialogue, and art remain outside the change.
- [x] 8.2 Sync the five new capability specs and the `world-clock` delta into `openspec/specs/`, verify the merged main-spec content matches the deltas, run `uv run --locked python -m tools.spec_traceability list`, and annotate every substantively matching Python behavior/integration/browser test with the resulting literal canonical requirement IDs.
- [x] 8.3 Run `uv run --locked python -m tools.spec_traceability check`, the Node test command, and the Playwright browser command with the shared evidence path; fix every uncovered or unsuccessful foundation requirement without adding skipped, placeholder, or assertion-free evidence.
- [x] 8.4 Run `OPENSPEC_TEST_EVIDENCE=<shared-path> uv run --locked evennia test --settings settings.py commands server typeclasses web world` and `OPENSPEC_TEST_EVIDENCE=<shared-path> uv run --locked -m unittest discover -s tests -t .`, then run `uv run --locked python -m tools.spec_traceability verify --evidence <shared-path>`.
- [x] 8.5 Run the exact two-file aggregate branch-coverage sequence for `commands`, `server`, `typeclasses`, `web`, and `world`, verify coverage roots, and confirm the combined report remains at or above 90% with only `*/tests/*` omitted.
- [x] 8.6 Run `openspec validate webclient-oob-foundation --strict`, `openspec validate --all --strict`, `uv run --locked python -m compileall -q world typeclasses commands server web`, and `git diff --check`; confirm no test or runtime path contacts an LLM, image service, remote CDN, or developer database.
