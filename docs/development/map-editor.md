# Standalone Map Editor

The standalone map editor is an independent local tool. Its service lives in
`tools/map-editor/` (Python package `elosern_map_editor`, own `pyproject.toml`
and `uv.lock`) and its browser workspace in `tools/map-editor/frontend/` (Vue 3
and Vite, own pnpm workspace root and `pnpm-lock.yaml`). It reads the authored
map documents through `elosern_map_core` and never imports the game, Evennia or
Django, opens a database, or needs the game running.

The editor browses the complete authoring world: every domain, diagnostics,
source ownership, external-index and partition freshness, and static maps
drawn with `@elosern/map-view`. The first document commands rearrange interior
room layouts, with service-owned autosave, overwrite guards and undo/redo of
the manual segment (§3). Further domain commands, file following and the
full workbench arrive in later slices.

## 1. Launch

Build the frontend once. Node and pnpm are development-time tools only; the
running editor needs neither:

```console
pnpm --dir tools/map-editor/frontend install --frozen-lockfile
pnpm --dir tools/map-editor/frontend run build
```

Run the service from its own locked environment. `--workspace` defaults to the
repository checkout that contains `tools/map-editor`:

```console
uv run --locked --project tools/map-editor python -m elosern_map_editor
uv run --locked --project tools/map-editor python -m elosern_map_editor --workspace /path/to/repo --port 8765
```

Open `http://127.0.0.1:8765/`. The service serves `frontend/dist/` itself. If
the build is missing at startup, `/` answers 503 with the build command and the
API keeps working (restart the service after building). Only loopback
addresses are accepted for `--host`, and `--port` must be an explicit port: an
ephemeral `0` is refused because the Host/Origin allowlist names the port.

Checks:

```console
uv run --locked python -m pytest                                 # in tools/map-editor
pnpm --dir tools/map-editor/frontend test                        # pure frontend logic
pnpm --dir tools/map-editor/frontend run test:boundary           # game-tree import allowlist
uv run --locked python -m unittest tests.test_map_editor_service # real process, repo root
uv run --locked python -m unittest tests.test_map_editor_persistence
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_standalone
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_persistence
```

The two repository-level checks start the service as a child process from
`tools/map-editor/.venv` (synchronised with
`uv sync --locked --project tools/map-editor`) with a scrubbed environment and
an empty `PATH`, so neither the game's packages nor Node can be reached.

## 2. API

| Route | Purpose |
| --- | --- |
| `GET /api/workspace` | One complete replacement of the authoritative state: `session_generation`, `snapshot_revision`, `write_pause`, `preview_state` (`current`/`stale`/`unavailable`), `snapshot_read_at`, `checked_at`, `schema` (the core schema), `documents` (path, kind, id, fingerprint, values), `world` (the core-derived projection), `diagnostics`, `candidate_diagnostics` (the failing read while stale or unavailable), `external_context_status`, `partition_status`. |
| `GET /api/events` | Server-sent events: `status` on connect and `invalidate` after a published change, each carrying only `session_generation`, `snapshot_revision` and `preview_state`. A client refetches `/api/workspace` on every invalidation and on a reconnect status that names another session or revision. Nothing is patched or merged. |
| `POST /api/reload` | Authenticated reread of the current disk files. A loadable read publishes. A structural failure keeps the last preview, marks it `stale` and sets `write_pause`. An identical read publishes nothing. It never writes a file. |
| `POST /api/commands/<name>` | One named single-document command (`move_interior_layout`, `remove_interior_layout`) or `undo`/`redo` of the current segment (see §3). |
| `GET /api/session` | Same-origin launch-token bootstrap (see §4). |

`snapshot_revision` is an invalidation counter. It changes whenever the
observable state changes (a new world, or a new stale or unavailable status),
not only when the world changes, the write pause changes or the undo/redo
history moves. Commands must name the current `session_generation` and
`snapshot_revision` (§3). Startup is a fresh disk read with a new session identity, and
the editor is writable exactly when that read loads. There is no handoff,
resume or return route, and no generic patch, file-write, path, shell, Python
or account route.

## 3. Document Commands, Autosave and History

### 3.1 Envelope and admission

Every command is `POST /api/commands/<name>` with exactly this JSON body:

```json
{
  "session_generation": "<current session>",
  "snapshot_revision": 7,
  "segment": "<page-load id>",
  "document_id": "content/map-editor-layouts/<interior_id>.yaml",
  "expected_document_fingerprint": "<sha256 of the file> | absent",
  "arguments": {}
}
```

Admission runs in this order, inside the one service lock, so commands and
rereads are strictly serial:

1. the named command exists (`unknown_command`, 404) and the envelope is
   exactly these keys and types (`invalid_body`, 400);
2. `session_generation` and `snapshot_revision` equal the current values
   (`stale_session` / `stale_snapshot`, 409);
3. no write pause: a stale or unavailable preview, or an uncertain
   publication (`write_paused`, 423, with `reason`);
4. the handler validates its typed arguments (`invalid_command`, 400) and
   derives the one document it owns. A `document_id` that differs, or an
   object of another document, is `cross_document` (400, with `owner`);
5. the expected presence (content hash or the explicit `absent`) matches the
   current read and then the disk (`stale_document`, 409);
6. the complete candidate world passes its authoring gate
   (`validation_failed`, 422, with file/field/line diagnostics). An
   object-removing effect must also pass the execution-time external-reference
   guard of §8 (`deletion_refused`, 409, with the reasons);
7. publication (§3.3): `save_failed`, `save_uncertain` or `reread_failed`
   (500).

Clients never name a file operation. Each named handler returns exactly one
internal create, replace or remove effect for its owning document:

| Command | Arguments | Effect |
| --- | --- | --- |
| `move_interior_layout` | `interior_id`, `room_id`, integer `x`, `y` | Creates the absent layout of that interior (with only the moved room) or replaces it, keeping its comments. World coordinates, distances and the game snapshot are never touched. An unchanged position writes nothing (`changed: false`). |
| `remove_interior_layout` | `interior_id` | The explicit layout cleanup: removes that layout document. It never cascades from or into a world document. The service accepts it, but the browser has no control for it in this slice. |
| `undo`, `redo` | none | Applies the head of this segment's history. `document_id` and the expected fingerprint must equal `history.undo`/`history.redo` from the workspace state (`stale_history` or `history_empty`, 409). |

A success answers the new status, `changed`, `document_id` and the new
`fingerprint` (or `absent`) after the service has reread and published the
result. No shipped handler produces an object-removing world-document effect
yet. The reference guard is exercised through the real executor with
internally constructed effects, and the layout handlers remove no map object.

### 3.2 Drafts, completed operations and history

A manual operation completes on drag release, a confirmed inspector field
(Enter or blur with a complete integer), or one Shift+arrow press. Each
completed operation is one command and one history entry. Keystrokes stay
drafts: an incomplete value keeps the draft with an inline error and writes
nothing. Escape restores the saved value, and Escape during a drag cancels it.
Save (Ctrl/⌘+S) waits for accepted operations and never forces a draft.
A complete draft is confirmed whenever the field loses focus, so clicking
elsewhere saves it; an incomplete draft is never written by any path.
Leaving the page with a draft or a pending save asks for confirmation. Drafts
are never restored.

Undo and redo (Ctrl/⌘+Z, Shift+Ctrl/⌘+Z outside text fields) store both
round-trip baselines of each operation: presence or absence plus the exact
bytes. Undoing a creation removes the document, and redo recreates it only
while it is still absent. Undoing a removal recreates the retained bytes,
comments included, through the absence guard. Inverses use the same
validation, reference guard and writer. The stacks move only after the
inverse is confirmed on disk. A rejected or failed inverse leaves disk and
history unchanged.

History is service-owned and scoped to the **segment**, an id each page load
creates in memory. A command from another segment starts a new empty
segment, so a refreshed page, or a second tab, never inherits undo/redo, and
the second tab's first command ends the first tab's segment. The segment id
is not a security boundary. History is cleared whenever the service adopts a
source or layout change it did not write: it compares the fingerprint map of
every source and layout path after its own write with the map it expected.
Changes to the generated artifacts do not count. A service restart is a new
session with no history. Commands are never replayed after a reconnect.

Only one owning document is mutated per operation. The browser has no
multi-selection gesture in this slice. A selection that spans documents is
reported as unavailable, and the service refuses it as `cross_document`.

### 3.3 Durability

The writer is the only code that writes a source or layout file. It reaches
the parent directory through the same no-follow descriptor walk as reads.
Missing layout directories are created there, and a linked directory is
refused. Generated artifacts are never writable.

| Step | Outcome |
| --- | --- |
| Recheck the target's presence/hash immediately before publishing | mismatch: `stale_document`, nothing written |
| Write and flush a sibling `.<name>.<random>.tmp` | failure: `save_failed`, temporary removed, target untouched |
| Replace: atomic rename over the target. Create: hard-link the temporary to the target name (never overwrites), then drop the temporary. Remove: unlink | an errno that proves nothing happened (`EACCES`, `EPERM`, `EROFS`, `ENOSPC`, `EDQUOT`, `EXDEV`, `ENOENT`, `EEXIST`, `ENOTDIR`, `EISDIR`) is `save_failed`. The exceptions are an existing target on create and an already missing target on remove, which are `stale_document`. Any other errno is `save_uncertain` |
| Flush the parent directory | failure: `save_uncertain` |

A filesystem without hard links falls back to an exclusive create of the
target, and a failure after that has begun is uncertain (the partial file is
removed when possible). Directories created for a failed or rejected create
stay empty and are never discovered as documents. A temporary name is
never discovered as a document, because it does not end in `.yaml`.

`save_uncertain` pauses every command (`write_pause.reason` is
`uncertain_durability`). So does `reread_failed`: the publication succeeded
but the service's own reread afterwards raised, so it no longer knows what it
holds. A successful command changes `snapshot_revision` exactly once, with
its history move and new read applied together. The workspace state then carries `pending_intent`:
the command, document, baseline and intended fingerprints. Nothing is retried.
The banner's 重新讀取 action (`POST /api/reload`) clears the pause only when
the reread loads. That reread clears the history and records in
`uncertain_outcome` whether the intended content, the baseline or something
else is on disk. It never claims a save.

The pre-publication recheck and the publication are not atomic against
another process. That process might write the target or another document the
candidate world was validated with. The fingerprint guard detects accidental
overwrites under continuous file following. It is not a compare-and-swap or
merge guarantee: do not run two writers at once.

## 4. Security Model and Limitations

- **Loopback only.** The service binds a loopback address and answers only
  requests whose `Host` is exactly `127.0.0.1:<port>`, `localhost:<port>` or
  `[::1]:<port>`, which defeats DNS rebinding.
- **Same origin only.** A request that sends `Origin` must send this service's
  own origin. `null` and every other origin, including other localhost ports,
  are refused, and `Sec-Fetch-Site` must be `same-origin` or `none` when sent.
  No CORS header is ever emitted.
- **Mutations.** Every `POST` must carry the matching `Origin`, the launch
  token in `X-Map-Editor-Token`, `Content-Type: application/json` and a body of
  at most 64 KiB, checked from `Content-Length` before reading and counted for
  a body without one. These checks run before any route, lock or disk read.
  The body is parsed only after them, and unknown body keys are refused.
- **The token.** It is created per service start and invalidated by a restart.
  The page fetches it from `GET /api/session` and keeps it in memory only: never
  in a URL, the clipboard, browser storage or a log (the access log is off). It
  defends against pages on other browser origins (CSRF) and detects stale
  sessions. It does not authenticate local processes: anything that can open a
  loopback connection with the right `Host` can read it. Local malicious
  processes, remote access, accounts and multiple users are out of scope.
- **Confinement.** Document identities resolve only to the allowlisted
  sources (`content/maps/...`), layouts (`content/map-editor-layouts/...`) and
  the two generated artifacts. Files are opened by walking from a descriptor of
  the real workspace root with `O_NOFOLLOW`, so traversal and every symbolic
  link below the root are refused at the actual open, including links that
  would stay inside the workspace. A linked workspace root is resolved once at
  startup. External sources hashed for reference-context freshness are read
  the same way, and the index's discovery rules and manifest paths must be
  relative and free of `..`.
- **Bounds.** Documents (2 MiB), artifacts (8 MiB), the document count, the
  external-source count and their per-file and total bytes are bounded with
  `fstat` before reading or parsing.
- **Confinement limits.** The descriptor walk relies on POSIX `O_NOFOLLOW`,
  `O_DIRECTORY` and `dir_fd`, so the service supports Linux and macOS only.
  Hard links are not detected: a hard link inside the workspace to an outside
  file reads as an ordinary file. Its content is only parsed or hashed, never
  served raw. The reference index's discovery rules are expanded by the core's
  glob before the external-source count bound applies, so a very broad rule in
  a hand-edited index costs a full enumeration on each reread. The committed
  index is generated, so this is accepted rather than bounded here.
- **Document ids in commands.** A command's `document_id` must equal the
  canonical document its handler derives from validated identifiers, so a
  traversal or foreign path is refused before any file access
  (`tests/test_map_editor_persistence.py` proves this over HTTP against the
  real process). The writer still resolves the id through the allowlist and
  the no-follow walk.
- **Inert content.** Authored prose and scene identifiers are rendered as
  text, never markup, and are never turned into URLs. Every response carries a
  Content Security Policy (`default-src 'self'`, no inline script, no
  third-party image, font or connection), `nosniff`, `no-referrer` and frame
  denial.

## 5. Theme Boundary

The frontend uses the game's visual language, but from the game tree it
imports only `web/webclient-app/styles/tokens.css`, `styles/fonts.css`,
`styles/fonts-mono.css` and the pure `lib/ui_scale.js`, through the exact
aliases in `tools/map-editor/frontend/editor-aliases.mjs`.
`tools/map-editor/frontend/scripts/import-boundary.mjs` enforces that allowlist
with the GM portal's scanner (`scripts/gm-import-boundary.mjs`). The supported
viewports are 1451x790 and 2560x1440, with the game's `--ui-scale` factor and a
16 px text floor.

## 6. External Reference Context

The standalone map editor is an independent authoring tool that runs outside the Evennia/Django runtime and does not import game modules. To validate external dependencies (such as scene archetypes, quest definitions, service hosts, titles, and lore elements) and safely prevent deletion of referenced map objects, the game exports an authoritative static reference index:

- File: `content/map-reference-context.json`
- Generator: `tools/map_reference_context.py`
- Core Codec & Freshness Checker: `elosern_map_core.reference_context`

The reference context records:
- Supported `schema_version` (1) and `exporter_version` (1).
- External identifier sets (`scene_archetypes`, `quest_definitions`, `nations`, `wilderness_regions`, `titles`, `service_hosts`, `races`, `subraces`, `elements`, `magic_tiers`, `monster_tiers`, `monster_species`, `settlements`, `shops`, `assortments`).
- Incoming external static references to qualified map objects (such as `places` in `world/lore/settlements/` joining interior rooms, or `service_hosts` spawning in interior rooms).
- Workspace-relative source paths for diagnostic location reporting.
- A manifest of source file paths and SHA-256 digests covering the complete transitive external static source closure.
- Allowlisted discovery rules and an aggregate dependency fingerprint.

## 7. Exporter and Freshness Commands

### Regenerate committed index
When an external static declaration changes (e.g., adding an NPC place, altering a service host, or modifying a static registry):

```bash
uv run --locked python -m tools.map_reference_context
```

Commit `content/map-reference-context.json` together with the source changes that caused the regeneration.

### Verify freshness in CI
CI runs the check during preflight and as part of `tools.contract_gate`:

```bash
uv run --locked python -m tools.map_reference_context --check
```

If the committed file differs byte-for-byte or any source closure dependency has changed, the command exits with code 1 without rewriting the file.

## 8. Deletion Safety and Limitations

### Deletion Safety Requirements
An object-removing operation in the editor (including destructive delete commands and object-removing undo operations) requires all of the following:

1. **Current External Context**: The reference context must report `status="current"`. If the context is unavailable (due to changed sources, missing files, membership mismatch, or unsupported versions), deletion is refused immediately. Unknown or unavailable context can never prove absence of references.
2. **Zero External Incoming References**: No external static declaration (such as an authored place joining an interior room) may reference the target.
3. **Zero Map-Internal Incoming References**: No authoring document (e.g. another room's door or exit) may reference the target within the `AuthoringWorld`.

When external context is unavailable or an incoming reference exists:
- Destructive commands and object-removing undo operations refuse execution.
- No disk files or command history states are altered.
- Ordinary non-destructive editing (moving nodes, adjusting attributes, inspecting diagnostics) remains available.

### Live Database Safety
The editor operates on static authoring documents and does not connect to or query the live game database (`ObjectDB`). It cannot certify live save dependents (e.g., players currently occupying a room or dynamic exits). Live occupied room safety and persistent room preservation remain strictly game-side responsibilities enforced during runtime synchronization (`sync_map_world`).

### Geometry Exclusion
The reference index records stable authored identities (e.g. `settlement_node:capital_altoria:central_plaza`), not derived spatial coordinates or grid wire strings (`grid:capital_altoria:100:200`). Moving a node coordinate alone does not alter the external reference index or its dependency fingerprint.
