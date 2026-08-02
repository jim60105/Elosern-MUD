# WebClient OOB Foundation — Focused Design

**Date:** 2026-08-02
**Status:** Approved as part of the Browser-First MUD WebClient Suite
**Parent:** `2026-08-02-webclient-ui-design.md`
**Delivery unit:** `webclient-oob-foundation`

---

## 1. Intent

This is the load-bearing first delivery unit for every graphical panel. It establishes one versioned,
authenticated, server-authoritative presentation channel without implementing combat, map, service, or
art-specific behavior beyond the compact character status needed to prove the channel end to end.

The foundation must be useful by itself: after login, a desktop browser shows the approved GoldenLayout
shell, continues to display normal MUD text, receives HP/MP/SP and mode through OOB, supports keyboard
focus, and can recover from reload or reconnect. Telnet behavior remains unchanged.

---

## 2. Goals and Non-Goals

### Goals

- Define protocol and panel schema versioning.
- Add authenticated `ui_sync` and `ui_action` input functions.
- Build a snapshot coordinator with session revisions and presenter isolation.
- Build a bounded allowlisted dispatcher; exercise dispatch with a test-only registered adapter rather
  than shipping a fake production action.
- Add the browser state store, keyboard router, required GoldenLayout components, command drawer, and
  compact status renderer.
- Keep narrative text on Evennia's existing output path.
- Rebuild the full UI after login, puppet change, reload, and reconnect.
- Establish Node and Playwright test entry points used by later UI changes.
- Add Playwright as a locked dev dependency and wire Node/browser commands into the required quality gate.

### Non-Goals

- No combat action menu.
- No persistent map knowledge or minimap renderer.
- No scene or portrait queue/panel.
- No guild, quest, shop, inventory, exploration, or creation forms.
- No mobile layout.
- No generic REST API and no arbitrary command execution through `ui_action`.

---

## 3. Module Boundaries

```text
server/conf/inputfuncs.py
  ui_sync(session, ...)
  ui_action(session, ...)
  text(session, ...)              project wrapper; delegates normal command handling

web/webclient/presentation/
  protocol.py                     envelope types, schema constants, validation
  coordinator.py                  revisions, full snapshots, panel replacements
  registry.py                     presenter registration and stable panel names
  status.py                       compact status presenter

web/webclient/actions/
  dispatcher.py                   action allowlist, payload schemas, request cache
  registry.py                     adapter registration

web/static/webclient/js/
  plugins/elosern_state.js        validated state store and OOB receiver
  plugins/elosern_layout.js       GoldenLayout components and layout migration
  plugins/elosern_actions.js      action transport and in-flight state
  elosern/keyboard_router.js      DOM-independent focus/menu state machine
  elosern/protocol.js             DOM-independent envelope validation/reduction

web/static/webclient/css/
  elosern.css                     ink-night/vermilion desktop theme
```

The implementation uses the file boundaries above. The state reducer and keyboard router remain
independently testable without a DOM. Server presenters remain read-only. Action adapters remain separate
from presentation so imports cannot accidentally make a presenter mutate game state.

---

## 4. Protocol Contract

### 4.1 Message names

| Direction | Message | Purpose |
|---|---|---|
| Client → Server | `ui_sync` | Request a full snapshot after OOB initialization, reload, or recovery |
| Client → Server | `ui_action` | Submit one allowlisted action envelope |
| Server → Client | `ui_snapshot` | Replace complete UI state for the current puppet/mode |
| Server → Client | `ui_update` | Replace one or more named panel payloads at a newer revision |
| Server → Client | `ui_action_result` | Resolve one request ID as success, rejection, stale, or internal error |
| Server → Client | `ui_protocol_error` | Report envelope/protocol incompatibility without exposing internals |

Message names are transport identifiers. The payload's `protocol_version` is independently validated.

### 4.2 Full snapshot fields

| Field | Type | Rule |
|---|---|---|
| `protocol_version` | integer | Exactly `1` for this delivery unit |
| `presentation_epoch` | bounded opaque string | Server-generated identity for one transport/puppet presentation sequence |
| `revision` | non-negative integer | Strictly increases within one presentation epoch |
| `mode` | stable string enum | Initially `creation`, `exploration`, or `combat`; unknown values reject the snapshot |
| `panels` | object | Keys come from the registered panel allowlist; values contain their own schema version |
| `layout_version` | positive integer | Selects the approved GoldenLayout structure/migration |
| `server_time` | display object | Required derived world date/time; never browser-calculated authority |

Unknown top-level fields are rejected in development/tests. The production client reports a protocol
error and retains text access rather than guessing their meaning.

### 4.3 Panel replacement

`ui_update` is not JSON Patch. Every named value completely replaces that panel's prior payload. A
presenter owns its entire schema, so no renderer needs to merge unknown nested data. Within the active
epoch, a client receiving revision `N` discards every snapshot or update with revision `<= N`. Packets
from older epochs are always discarded.

### 4.4 Status schema version 1

The foundation status panel proves structured state without duplicating rules. It contains:

- actor display name and opaque server identity for display correlation only;
- HP/MP/SP current and maximum integer values;
- stable state entries with code, Traditional Chinese label, severity, optional duration, and exact
  rule-provided modifiers;
- an explicit `disguise_active` indicator without substituting disguised values for true resources;
- combat mode and round if an active persistent combat session exists.

All fields derive from canonical handlers and registries. Missing or malformed traits make this panel
unavailable; they do not fabricate zero values.

---

## 5. Session Revision and Request Semantics

### 5.1 Revision ownership

The snapshot coordinator owns a cryptographically unpredictable, bounded `presentation_epoch` plus an
in-memory revision counter associated with the connected transport and puppet. Reconnection starts a new
epoch and revision sequence. The first valid full snapshot received on the active transport atomically
clears the prior ClientStateStore, adopts the new epoch, and becomes the comparison baseline. A puppet
change also starts a new epoch. Revisions and epochs are presentation ordering, not world state, and are
never persisted to character attributes.

### 5.2 Request IDs

The browser creates a bounded opaque request ID unique within its live connection. The dispatcher keeps
a bounded recent-result cache per session. Repeating an ID returns the prior result. The cache has a
fixed maximum size and evicts oldest completed requests; no unbounded session memory is allowed.

### 5.3 Stale action

An action's `presentation_epoch` and `base_revision` must equal the newest values issued to that session.
A mismatch returns a stale result and a full snapshot without invoking an adapter. Domain validation
still runs after this check because equality does not prove that external state is unchanged.

### 5.4 In-flight action

Each session admits one mutation at a time. The browser disables submission while waiting. The server
also enforces the limit so a modified client cannot race two mutations. Read-only sync remains allowed
and does not cancel a mutation.

If the connection disappears after submit, the browser does not retry automatically. A new connection
syncs canonical state and shows the approved uncertain-result notice.

---

## 6. Input Functions and Dispatch

`ui_sync` requires an authenticated session and active puppet. It builds a full snapshot for that puppet
and never accepts an actor ID from the client.

`ui_action` validates, in order:

1. authenticated WebSocket session and active puppet;
2. payload is an object with exact known fields;
3. protocol version, request ID, revision, action ID, and global size limits;
4. duplicate request and in-flight state;
5. action allowlist membership and action-specific payload schema;
6. adapter invocation with actor obtained from the session;
7. result serialization and affected-panel refresh.

An adapter is responsible for re-resolving every referenced ID and calling a public deterministic API.
It may not set `.db`, `AttributeProperty`, trait values, or map/quest records directly.

The project `text` input function delegates to Evennia's normal text handling. For synchronous player
commands it requests a post-command snapshot for WebClient sessions. It does not alter Telnet output or
turn text commands into `ui_action` calls.

---

## 7. GoldenLayout Shell

The foundation defines required component names for header, narrative, art placeholder, status, local-map
placeholder, action dock, and command drawer. Art and map placeholders clearly say that their delivery
unit is unavailable; they are not fake images or fake map data.

The default layout is version 1. The browser stores only layout dimensions, open nonessential tabs, and
safe display preferences. A migration registry maps known prior layout versions to the current one. A
missing or invalid migration resets the layout while preserving no canonical game state because none is
stored locally.

The command drawer opens with `/`, preserves Evennia command history, and returns focus to the action dock
after send or Escape. Until later menu changes land, the action dock may display text guidance and
read-only mode information but must not imply unavailable graphical actions exist.

---

## 8. Failure and Recovery

- One presenter exception is logged with panel name and correlation ID. The coordinator returns an
  unavailable payload for that panel and continues other presenters.
- A malformed panel update disables only that renderer and requests one full sync. Repeated failure does
  not create a sync loop; the panel remains unavailable while text play continues.
- Protocol mismatch disables all graphical mutation controls and presents a reload action.
- Transport loss adds a non-dismissible offline overlay until reconnection; stale controls cannot submit.
- OOB initialization failure leaves the stock text input usable.
- No traceback, local file path, or unescaped player content enters an OOB error.

---

## 9. Security Limits

Global envelope limits cover object depth, total serialized size, field count, string length, and list
length. Limits are constants with tests. Session and puppet identity are resolved server-side. Action and
panel registries reject duplicate registration and unknown names. The browser treats all labels and
descriptions as text, not trusted HTML.

The foundation enables WebClient OOB through Evennia's existing WebSocket path. It does not enable
Telnet OOB; Telnet requires no graphical payload for fallback play.

---

## 10. Tests and Acceptance

### Pure tests

- Every valid and invalid envelope branch.
- Snapshot/update replacement, revision ordering within one epoch, atomic adoption of a new epoch, and
  rejection of late packets from an old epoch.
- Duplicate panel/action registration.
- Status payload true values under active disguise.
- Presenter exception isolation.
- Client reducer acceptance/rejection of revisions and schemas.
- Keyboard focus, Escape stack, `/` drawer transition, and repeated Enter suppression.

### Evennia integration

- Anonymous, logged-in without puppet, and properly puppeted session behavior.
- Full snapshot after sync; new epoch after reconnect and puppet change.
- Stale revision performs no adapter call.
- Duplicate live request executes once.
- Text command produces normal output and a refreshed snapshot for WebClient only.
- A malformed presenter does not block narrative or status.

### Browser acceptance

- At 1440x900 and 1280x720, every required panel and command-drawer control is visible.
- Keyboard-only drawer open/send/close restores action-dock focus.
- WebSocket interruption locks controls; reconnection accepts the lower-revision snapshot from its new
  epoch and rejects delayed packets from the prior epoch.
- Old layout version migrates; unknown version resets.
- Protocol mismatch leaves text input operational.

### Executable browser harness and CI

The foundation runs `uv add --dev playwright` and commits synchronized project/lock files. A shared
`unittest` harness uses an isolated SQLite path, deterministic seed helper, and managed Evennia subprocess.
It creates runtime directories, starts the server non-interactively, polls
`http://127.0.0.1:4001/webclient/` with a bounded timeout, runs Chromium against localhost, and calls
`evennia stop` in cleanup even after failure. Tests never share the developer database.

The quality-gate workflow adds these locked commands after environment sync and runtime preparation:

```text
uv run --locked playwright install --with-deps chromium
node --test web/static/webclient/js/tests/*.test.js
uv run --locked python -m unittest discover -s web/tests/browser -t .
```

Browser fixtures use deterministic placeholders and no remote network service. Later UI changes add their
panel journeys to the same required entry point rather than creating optional scripts.

The change is complete only after strict OpenSpec validation, traceability, the full relevant Evennia
suite, Node tests, and foundation Playwright tests pass.
