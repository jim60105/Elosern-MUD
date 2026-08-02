## Context

Elosern currently uses Evennia 6.1.0's stock WebClient. The repository has only placeholder WebClient override directories, and `server/conf/inputfuncs.py` contains no active input functions. Ordinary text commands and Telnet are functional, but there is no project protocol, presentation registry, client state store, or graphical panel contract for later UI changes to consume.

The approved suite design makes the desktop browser the first-class graphical client while retaining complete text play. This foundation is deliberately independent of Narrator, NPC dialogue, map knowledge, services, creation forms, and art. It must remain deterministic and useful when every LLM, image service, and remote network service is unavailable.

Two upstream constraints affect the implementation. Evennia's stock `text` input function invokes the Deferred-returning command handler without returning that Deferred, so a wrapper that merely calls the stock function cannot know when a synchronous command has completed. The stock WebClient template also loads jQuery, GoldenLayout, Bootstrap-related assets, and Favico from remote CDNs. A localhost-only browser test and an offline-capable client therefore require a project template and local browser assets rather than the unmodified upstream page.

Presentation ordering is connection state, not game state. No protocol epoch, revision, request cache, or browser layout belongs in persistent character attributes. Presenters may read canonical state but may not mutate it. UI action adapters are the only presentation-side components allowed to invoke public deterministic mutation APIs, and this change ships no production action adapter.

## Goals / Non-Goals

**Goals:**

- Establish exact version-1 OOB envelopes on Evennia's existing WebSocket transport.
- Recover correctly across reconnects and puppet changes, including a new epoch whose first snapshot has a lower revision than the prior connection.
- Authenticate synchronization and action ingress, derive the actor from the session, and bound every client-controlled value.
- Isolate presenter failures and keep narrative text usable when structured presentation fails.
- Prove the dispatcher architecture with tests without inventing a placeholder game mutation.
- Render canonical HP, MP, SP, conditions, mode, location, and world time in the approved desktop shell.
- Provide DOM-independent client modules, keyboard-first interaction, safe layout persistence, and mandatory Node and Playwright verification.
- Eliminate production and test dependence on remote WebClient CDN assets.

**Non-Goals:**

- Combat, movement, map, quest, guild, shop, inventory, dialogue, creation-form, scene, portrait, or image-queue actions and panels.
- A mobile or touch-first layout.
- A REST API, arbitrary command execution through `ui_action`, or client-side rule evaluation.
- Persisting presentation epochs, revisions, request results, panel state, or canonical game state in the browser.
- Telnet OOB or a dedicated third-party client package.
- Compatibility adapters for prior project-authored browser protocols or layouts; none have shipped.

## Decisions

### D1. Use Evennia transport triples with one exact logical envelope

The protocol uses Evennia's existing `['command', args, kwargs]` WebSocket representation. Each Elosern message carries exactly one JSON object as `args[0]`; no domain field is split into transport kwargs. Client modules call `Evennia.msg`, and server output uses `session.msg`/`data_out` with the corresponding message name. This preserves the supported transport while keeping protocol validation independent from the GUI plugin system.

Version 1 defines `ui_sync` and `ui_action` from client to server, and `ui_snapshot`, `ui_update`, `ui_action_result`, and `ui_protocol_error` from server to client. Every envelope has an exact field set. Unknown fields, booleans where integers are required, non-finite numbers, excessive depth, excessive fields, long strings, large lists, and oversized canonical JSON are rejected before dispatch. Shared constants define a 65,536-byte UTF-8 canonical JSON limit, maximum nesting depth 8, maximum 64 fields per object, maximum 128 items per list, maximum 2,048 Unicode code points for a generic string, and JavaScript-safe integer range `0..9,007,199,254,740,991`. Field-specific smaller limits override these global ceilings.

The exact server envelope shapes are:

| Message | Required fields | Conditional fields | Rules |
|---|---|---|---|
| `ui_snapshot` | `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, `server_time` | none | `panels` contains every production-registered panel; revision is positive |
| `ui_update` | `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, `server_time` | none | same metadata as a snapshot; `panels` is a nonempty registered subset and each value fully replaces one panel |
| `ui_action_result` | `protocol_version`, `presentation_epoch`, `request_id`, `outcome`, `code`, `message`, `presentation_revision` | `correlation_id` is required only for `outcome: error` and forbidden otherwise | outcome is `success`, `rejected`, `stale`, or `error`; busy is `rejected` with code `busy` |
| `ui_protocol_error` | `protocol_version`, `code`, `message`, `reload_required` | `correlation_id` is required only for code `internal_error` and forbidden otherwise | contains no actor, panel, epoch, revision, request payload, exception, or local path |

`protocol_version` is exactly integer 1 in every server message and identifies the schema the server used, even when reporting an unsupported client version. An epoch is exactly 22 URL-safe ASCII characters generated from 128 random bits. Request IDs are 1..64 characters from ASCII letters, digits, colon, underscore, and hyphen. Action IDs and stable codes are 1..64 lowercase dotted or underscored identifiers. Player messages are 1..512 Unicode code points. Correlation IDs are exactly 32 lowercase hexadecimal characters. Panel names are 1..64 lowercase identifiers and panel count is at most 32. Revision fields use the safe integer range, with snapshot/update revisions positive. `mode` is the fixed enum; `layout_version` is `1..65,535`. `server_time` is exactly `{year, season_index, season_label, day_in_season, hour, minute, second}` using `year` in the safe range, `season_index` in `0..3`, a 1..32 code-point Traditional Chinese label, `day_in_season` in `1..90`, `hour` in `0..23`, and minute/second in `0..59`. Result messages never carry panel data; protocol errors never carry presentation or actor data.

Every panel value is a schema-versioned discriminated union. The common unavailable form is exactly `{schema_version, available: false, reason}`, where `reason` contains bounded `code` and safe Traditional Chinese `message`, plus a bounded `correlation_id` only for an internal presenter failure. An available payload has `available: true` and the exact fields owned by that panel schema. Registry metadata supplies the schema version and unavailable builder, so the coordinator never guesses a panel shape.

Alternative considered: encode structured state as tagged narrative output. This would couple behavior to translated prose and ANSI rendering and is prohibited by the suite design.

### D2. Scope epochs and revisions to the live transport and puppet

The coordinator stores ephemeral presentation state on the live server session. A cryptographically random, bounded epoch identifies one transport-and-puppet sequence. A new WebSocket transport and every puppet change create a new epoch and reset its revision counter. Epochs and revisions are never written to `entity.db`, Accounts, Scripts, or browser persistence.

The client state store has an explicit transport-generation lifecycle. Each `connection_open` increments a local generation, calls `beginTransport(generation)`, retires the formerly active epoch in a bounded in-memory set, clears panel state, locks mutations, and enters `awaiting_initial_snapshot`. Only the first valid `ui_snapshot` delivered by the receiver for that current generation, with an epoch absent from the retired set, may establish an epoch and accept a lower revision. Updates and results cannot establish an epoch. Once active, every snapshot or update with a different epoch is rejected, including a full snapshot received on the same open socket. Receiver calls tagged with an older local generation are also rejected.

Thereafter, only messages from the adopted epoch with a strictly newer revision can replace presentation state. Delayed messages from every retired epoch are discarded before and after adoption. A full snapshot contains all registered panels for the current mode; an update completely replaces each named included panel and is never JSON Patch. The retired-epoch set is presentation-only, bounded, and discarded on page unload; it is never localStorage state.

Alternative considered: one monotonic revision without epochs. That rejects valid lower revisions after reconnect and cannot distinguish delayed packets from an old transport.

### D3. Keep one coordinator and isolated read-only presenters

`web/webclient/presentation/registry.py` owns a duplicate-rejecting allowlist of stable panel names. `coordinator.py` owns epoch creation, revisions, snapshot/update construction, correlation IDs, and output. Presenters receive an immutable presentation context containing the authenticated actor and read-only session facts. They return JSON-safe values and have no coordinator or dispatcher reference.

Each presenter call is isolated. An exception is logged with panel name and correlation ID, then converted through that registry entry's unavailable builder to the common discriminated shape. Missing canonical data uses a stable non-internal unavailable reason without a correlation ID. Other presenters still complete. Registry construction and protocol serialization fail closed on duplicate or unknown panel names.

Only the version-1 `status` panel is registered in this delivery unit. The shell's header consumes mode and server time from the snapshot plus actor/location display context from status. Art, map, and action surfaces render explicit unavailable placeholders rather than fabricated data.

Alternative considered: let panels query state directly from browser-triggered endpoints. This would duplicate authorization, make snapshots inconsistent, and weaken presenter isolation.

### D4. Make synchronization authenticated and command completion observable

`ui_sync` accepts only an authenticated WebSocket session with an active puppet and only `{protocol_version: 1}`. It never accepts an actor ID. Anonymous sessions, logged-in sessions without a puppet, Telnet sessions, malformed payloads, and unsupported versions receive a safe protocol response or normal login text without state disclosure.

The project `text` input function preserves Evennia 6.1's idle handling, MXP stripping, nickname replacement, command dispatch, and session counters, but it invokes the Deferred-returning command handler through a project helper that attaches an `addBoth`-style observer. After a WebClient command settles on either its callback or errback path, the observer attempts a full snapshot from then-current canonical state and returns the original success value or Failure unchanged. Snapshot failure is logged separately and never consumes or replaces the command Failure. Telnet follows the same command path without presentation output. Tests pin both completion paths so an Evennia upgrade cannot silently bypass command completion, alter error propagation, or break text play.

Login/puppet readiness, explicit `ui_sync`, reload, reconnect, and puppet change all converge on full-snapshot construction. The browser also requests a full snapshot on `connection_open`; duplicate sync requests are harmless. Later changes may request affected-panel updates through the coordinator after their own public APIs commit.

Alternative considered: call Evennia's stock `text` function and schedule a zero-delay snapshot. The stock function discards the command Deferred, and event-loop timing would permit a snapshot before asynchronous command completion.

### D5. Separate action validation, dispatch, and deterministic mutation

`web/webclient/actions/registry.py` registers stable action IDs with exact payload validators and adapters. `dispatcher.py` performs global envelope validation, authentication, epoch/revision checks, duplicate and in-flight checks, action lookup, payload validation, adapter invocation, result serialization, and requested panel refresh. Adapters receive the actor resolved from `session.puppet`; actor identity is never client-controlled.

Every production adapter added by a later change must re-resolve referenced IDs and call a public API in the deterministic owner package. It may not assign `.db`, `AttributeProperty`, traits, map knowledge, quest records, wallets, or inventory directly. Presenters never call the dispatcher or enqueue an action. This change registers no production adapter; tests install a local proof adapter against an isolated registry and assert that it executes once.

Alternative considered: allow action descriptors to submit command strings. Command strings are ambiguous, expose a much larger parser surface, and cannot provide exact payload schemas or opaque identity binding.

### D6. Reject stale actions and serialize mutations per session

An action envelope contains exact fields: `protocol_version`, `presentation_epoch`, `request_id`, `base_revision`, `action_id`, and `payload`. Epoch and base revision must equal the newest values issued to the live session before payload-specific dispatch. A mismatch returns `stale`, invokes no adapter, and emits a fresh full snapshot.

The dispatcher holds a bounded insertion-ordered cache of completed `request_id` results per transport-and-puppet sequence. Repeating a completed ID returns the cached result without executing again. Only one mutation may be in flight per sequence; a second distinct mutation is rejected as busy, while `ui_sync` remains available. A puppet change atomically retires the old epoch and clears its request cache and in-flight marker. An old adapter Deferred may finish its already-started deterministic call for the captured old actor, but its completion token no longer matches the active sequence, so it cannot publish a result or panel state into the new puppet sequence. Cache entries and markers also disappear with the transport.

Every admitted non-duplicate action completes through one coordinator publication critical section. After the adapter Deferred settles, the server builds canonical presentation from committed state and allocates one next revision. Success and domain rejection use one affected-panel update when the adapter declares a nonempty safe panel set; stale, internal error, and completion without affected panels use a full snapshot. The server sends that presentation first, then sends `ui_action_result` with the same `presentation_revision`, and only then releases the server in-flight marker. Evennia WebSocket ordering makes these sends observable in that order. `ui_sync` may publish another serialized revision before or after this critical section but cannot interleave between the completion presentation and its result.

The browser records the result but releases its mutation lock only after it has both received the result and accepted presentation state at or above `presentation_revision`. If the completion presentation is malformed, its one recovery sync can advance beyond the target revision and unlock; otherwise the UI remains safely locked. A duplicate cached result can be replayed without a new presentation because the active store revision is already equal or newer. A busy pre-admission rejection uses the current revision and does not disturb the admitted request's lock.

An action result contains the request ID, epoch, exact outcome enum, stable code, safe Traditional Chinese message, and completion presentation revision. Internal errors are logged and include only a bounded correlation ID plus a generic message. The browser never automatically retries after disconnection; it resynchronizes and shows an uncertain-result notice.

Alternative considered: rely on browser-side button locking. A modified client or duplicated packet can bypass browser state, so the server must enforce both serialization and deduplication.

### D7. Derive compact status only from canonical read APIs

`world/rules/status_query.py` provides one frozen read model for presentation. It reads existing persistent trait, buff, sexual-state, creation, and combat-session records without constructing a lazy handler that could materialize defaults. An absent optional buff record means no active buffs; an unmaterialized but validated sexual baseline is interpreted in memory without writing it; missing or malformed required canonical data returns an unavailable query result. The status presenter serializes this read model and does not inspect raw persistent records itself.

The read model contains stored gauge `current` and `max` values for HP, MP, and SP, active rulebook buffs, sexual-state thresholds currently contributing combat modifiers, creation state, and `read_session()` data for combat mode and round. The clock module gains `read_world_clock()`, which returns the existing clock or `None` and never creates a Script, while deterministic startup explicitly ensures the singleton before accepting players. Presentation uses only `read_world_clock()` and current location for the header. If the clock is unexpectedly absent, synchronization returns a safe `ui_protocol_error` with code `presentation_unavailable`, leaves text play available, and creates no Script. Neither query nor presenter calls `get_display_value`; `disguise_active` only reports whether display-only overrides exist.

The deterministic combat-modifier module gains a read-only query returning each matched rule ID and its exact adjustment bundle. Existing `evaluate_combat_modifiers()` continues to merge those matches and remains the combat authority. The presenter maps stable rule/buff IDs to Traditional Chinese labels and severities through immutable display metadata; tests require metadata coverage for every currently displayable rule and buff. This avoids re-evaluating thresholds or reproducing modifier math in `web/`.

Required trait or rule data that is missing or malformed yields a status-unavailable payload. The presenter never fabricates zero resources. Reads do not advance the world clock, settle gauges, tick buffs, or mutate a combat session.

Alternative considered: expose `disguised_stats` or duplicate combat predicates in the presenter. Both violate the display-only disguise boundary and permit presentation to diverge from deterministic resolution.

### D8. Override the stock page with a local desktop shell

The project supplies a WebClient template that retains Evennia's core connection variables and `evennia.js` transport but loads a local, pinned GoldenLayout 1.x build and compatible local jQuery. Bootstrap, Popper, Favico, and other unused CDN scripts are omitted. Vendored assets include version/source metadata and license notices. No production or browser-test render requires a remote request.

The version-1 layout has required components for header, narrative, art placeholder, status, local-map placeholder, action dock, and command drawer. Narrative remains the largest surface. Required components and the action dock cannot be permanently closed. The project GoldenLayout plugin registers components and exposes only the minimal layout operations required by the shell rather than retaining the stock free-form pane editor.

Alternative considered: keep the stock remote template and intercept CDN requests in Playwright. That would make tests pass without making production offline-capable and would test a different asset path from users.

### D9. Persist only versioned presentation preferences

The browser stores a wrapper containing `layout_version`, bounded GoldenLayout dimensions/tab state, and harmless display preferences. It stores no epoch, revision, panel payload, request result, identity token, command text, or game state. A migration registry upgrades known layout versions. Missing, malformed, oversized, or unknown versions reset to the approved default before GoldenLayout initialization.

Because the project has no released users, version 1 does not import the stock `evenniaGoldenLayoutSavedState` keys. Those keys may be removed/reset. Future known project layout versions require an explicit migration.

Alternative considered: persist the complete client store for faster reload. Canonical state would become stale and could leak between puppets sharing a browser profile.

### D10. Keep state reduction and keyboard routing DOM-independent

`elosern/protocol.js` validates and reduces snapshots/updates. It performs atomic epoch adoption, strict schema/version checks, complete panel replacement, old-message rejection, and bounded error reporting. `keyboard_router.js` models one focus stack independently of rendering. Arrow keys move focus, Enter confirms, Escape pops one level, Space is reserved for later multi-select menus, and `/` opens the command drawer. Repeated Enter and every mutation while in flight are suppressed.

The action dock owns focus after initial sync and action completion/rejection. Disabled entries remain focusable for their explanation but cannot submit. The command drawer uses Evennia text submission and history, closes on send or Escape, and restores action-dock focus. Mouse activation calls the same control handlers. Labels and descriptions enter the DOM through text APIs, never HTML interpolation.

Alternative considered: place state and key handling inside GoldenLayout component callbacks. That makes ordering, focus, and reconnect behavior dependent on a browser DOM and difficult to test deterministically.

### D11. Degrade by surface while preserving text play

Before initial sync, graphical mutations are disabled. Transport loss preserves the last rendered view under a non-dismissible offline overlay and disables submissions. A malformed panel disables that renderer and triggers at most one full resync for the failure episode; repeated failure leaves the panel unavailable without a loop. A protocol mismatch disables all graphical mutations and offers reload while retaining text input.

OOB initialization failure leaves the narrative and stock text-send path usable. No OOB error includes a traceback, local path, raw exception, or unescaped player content. Server logs retain correlation IDs for diagnostics.

### D12. Make browser verification part of the existing quality gate

Playwright is added only to the uv development group with `uv add --dev playwright`; `pyproject.toml` and `uv.lock` remain synchronized. DOM-independent modules use Node 24's built-in test runner and add no npm runtime package or lockfile.

A Python `unittest` harness starts Evennia with a browser-test-only settings module whose SQLite database, logs, and runtime files live in one temporary directory. Each harness instance allocates its own dynamic loopback Telnet, HTTP, and WebSocket ports and verifies that it owns the launched process. It seeds a deterministic account and character, starts the server non-interactively, polls its allocated localhost WebClient URL with a bounded timeout, runs Chromium against localhost, and always stops only its managed process and removes temporary state. Tests block non-local requests and use no LLM, image generator, or developer database.

`web/tests/browser/` is intentionally discoverable by both the full `evennia test ... web` run and the explicit browser entry point required by the approved design. The harness is therefore repeatable and safe if collected twice: every run uses fresh dynamic ports and temporary roots, never assumes port 4001, and leaves no shared process or database. CI installs Chromium before either Python runner. Browser annotations write successful evidence in either run; repeated evidence records are harmless.

The quality gate installs Chromium, runs Node tests, and runs browser tests before requirement execution verification, using the same `OPENSPEC_TEST_EVIDENCE` path for annotated Python browser tests. Supported viewport checks run at 1440x900 and 1280x720. Existing Evennia, top-level, traceability, and aggregate 90% branch-coverage gates remain required.

Alternative considered: provide browser scripts only for local use. Focus, reconnect, layout migration, and offline degradation are release contracts and need mandatory CI evidence.

## Risks / Trade-offs

- [Project `text` wrapper can drift from Evennia input semantics] -> Keep the wrapper small, pin behavior with integration tests for idle input, nick replacement, command output, counters, Deferred completion, and Telnet/WebClient divergence; re-review it when upgrading Evennia.
- [Vendored browser libraries add repository weight and update responsibility] -> Vendor only the compatible jQuery and GoldenLayout runtime/CSS files, record exact versions and licenses, and prohibit remote runtime fallbacks.
- [A presenter may accidentally trigger lazy state mutation] -> Route status through the no-create frozen rules read model, prohibit presenter access to lazy handler properties, test unmaterialized baselines plus before/after canonical storage, and treat malformed required state as unavailable.
- [Snapshot-after-every-text-command is heavier than targeted updates] -> This foundation favors correctness; later UI adapters use affected-panel updates, and profiling may justify a separate optimization change without changing the protocol.
- [In-memory request deduplication cannot prove an outcome after transport loss] -> Never retry automatically; reconnect to canonical state and disclose uncertainty. Durable exactly-once semantics remain owned by each deterministic transaction where required.
- [GoldenLayout 1.x is legacy browser code] -> Keep it behind a small project plugin and DOM-independent state/router modules so a future layout-library replacement does not change server contracts.
- [Browser subprocess cleanup may be flaky on CI] -> Use bounded readiness and shutdown timeouts, `addCleanup`/`finally`, isolated process IDs and paths, and diagnostic log capture on failure.
- [Status display metadata can lag new rulebook entries] -> Test registry coverage against current buff definitions and matched modifier rule IDs; unknown entries fail the status panel closed instead of silently presenting misleading text.

## Migration Plan

1. Add the server protocol, coordinator, registries, status query/presenter, and pure/integration tests without enabling production adapters.
2. Add local browser assets, the project template, client modules, default layout, theme, and Node tests.
3. Add the isolated browser harness and Playwright dependency, then make Node/browser commands required in the quality gate.
4. Validate the complete change with strict OpenSpec validation, traceability evidence, the full Python suites, Node tests, Playwright viewports, and aggregate coverage.

No persisted game-data migration is required. Existing stock GoldenLayout localStorage is discarded because no project layout has shipped. Rollback removes the project template/static overrides and input functions; canonical game state is unaffected because all foundation state is ephemeral or presentational.

## Open Questions

None. Protocol version, delivery boundary, desktop viewports, keyboard model, failure behavior, and test entry points are fixed by the approved suite and focused designs.
