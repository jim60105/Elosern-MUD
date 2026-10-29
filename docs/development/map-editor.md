# Standalone Map Editor

The standalone map editor is an independent local tool. Its service lives in
`tools/map-editor/` (Python package `elosern_map_editor`, own `pyproject.toml`
and `uv.lock`) and its browser workspace in `tools/map-editor/frontend/` (Vue 3
and Vite, own pnpm workspace root and `pnpm-lock.yaml`). It reads the authored
map documents through `elosern_map_core` and never imports the game, Evennia or
Django, opens a database, or needs the game running.

The editor browses the complete authoring world: every domain, diagnostics,
source ownership, external-index and partition freshness, and static maps
drawn with `@elosern/map-view`. The document commands edit interior room
layouts, with service-owned autosave, overwrite guards and undo/redo of
the manual segment (§3). The service follows the workspace files
continuously (§3.4) and the page recovers from stale previews, disconnects
and restarts without a handoff (§3.5). The workbench shell (§3.6) provides
navigation, search, selection, inspection, diagnostics, the copy-only OMP
context and the keyboard contract. Further domain commands arrive in later
slices (§3.7). Partition regeneration is an explicit background job (§3.12).
The integrated acceptance evidence and its focused commands are in §9.

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

### 1.1 Container launch (Podman)

`scripts/podman-map-editor.sh` builds `tools/map-editor/Containerfile` and runs
the editor in a container, mirroring `scripts/podman-build-run.sh` for the game.
Node and pnpm stay inside the build stage, so the host needs only Podman:

```console
./scripts/podman-map-editor.sh                 # build, then serve on 127.0.0.1:8765
./scripts/podman-map-editor.sh --no-build      # reuse the existing local image
./scripts/podman-map-editor.sh --port 9000     # another port
./scripts/podman-map-editor.sh --workspace /path/to/repo
```

The image carries the service environment and the built workspace; the checkout
itself is mounted read-write at `/workspace`, so autosaved YAML lands in the
working tree. The container shares the host network namespace because the
service binds loopback only and its Host/Origin allowlist names
`127.0.0.1:<port>`; a published port could never reach it. It runs with
`--userns=keep-id` so saved files stay owned by the invoking user, and it is
independent of the game container. Logs: `podman logs -f elosern-map-editor`;
stop: `podman stop elosern-map-editor`.

Checks:

```console
uv run --locked python -m pytest                                 # in tools/map-editor
pnpm --dir tools/map-editor/frontend test                        # pure frontend logic
pnpm --dir tools/map-editor/frontend run test:boundary           # game-tree import allowlist
uv run --locked python -m unittest tests.test_map_editor_service # real process, repo root
uv run --locked python -m unittest tests.test_map_editor_persistence
uv run --locked python -m unittest tests.test_map_editor_file_following
uv run --locked python -m unittest tests.test_map_editor_watching
uv run --locked python -m unittest tests.test_map_editor_geography
uv run --locked python -m unittest tests.test_map_editor_settlements
uv run --locked python -m unittest tests.test_map_editor_interiors
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_standalone
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_persistence
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_file_following
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_accessibility
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_geography
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_settlements
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_interiors
```

The accessibility module runs its keyboard workflow in Chromium and Firefox
(`uv run --locked playwright install chromium firefox`).
Settlement and interior creation forms submit on Enter only from text inputs
and selects. Enter on Create or a checkbox does not post a command. Ordinary
buttons retain native activation, so Enter on Cancel closes a valid form
without posting a command; pointer activation of Create still submits.

The two repository-level checks start the service as a child process from
`tools/map-editor/.venv` (synchronised with
`uv sync --locked --project tools/map-editor`) with a scrubbed environment and
an empty `PATH`, so neither the game's packages nor Node can be reached.

### 1.2 Offline capture build

The offline map capture page is a second build of the same frontend sources.
It needs no service, dev server, Node runtime or network once built:

```console
pnpm --dir tools/map-editor/frontend run build:capture
```

That writes `tools/map-editor/frontend/capture-dist/index.html`: the map host
and one classic (IIFE) script, a relative stylesheet and the same locally
emitted font files as the editor, all addressed with relative paths so the page
opens from a `file://` URL. `vite.capture.config.js` reuses the editor's
aliases and the import boundary of §5; the normal `build` and `dist/` output
are unchanged, and both build directories stay untracked. The generated page
contains no authored payload — the runner calls
`window.renderMapCapture(payload)` (§10).

## 2. API

| Route | Purpose |
| --- | --- |
| `GET /api/workspace` | One complete replacement of the authoritative state: `session_generation`, `snapshot_revision`, `write_pause`, `preview_state` (`current`/`stale`/`unavailable`), `snapshot_read_at`, `checked_at`, `schema` (the core schema), `documents` (path, kind, id, fingerprint, values), `world` (the core-derived projection), `diagnostics`, `candidate_diagnostics` (the failing read while stale or unavailable), `external_context_status`, `partition_status` (artifact freshness, its `artifact_fingerprint`, input and expected signatures, and `game_ready`), `partition_job` (§3.12), `history`, `pending_intent`, `uncertain_outcome`, `external_change` (`sequence`, `at` and the changed `documents` of the last adopted external change; §3.4) and `following` (`active`, reconciled `batches`, the last watcher `error`). `write_pause` is only the explicit pause of an uncertain publication; the stale or unavailable preview is the separate `preview_state`. |
| `GET /api/events` | Server-sent events: `status` on connect and `invalidate` after a published change, each carrying only `session_generation`, `snapshot_revision` and `preview_state`. A client refetches `/api/workspace` on every invalidation and on a reconnect status that names another session or revision. Nothing is patched or merged. |
| `POST /api/reload` | Authenticated explicit reread of the current disk files. A loadable read publishes and is the only way to resolve an uncertain publication. A structural failure keeps the last preview and marks it `stale`. An identical read publishes nothing. It never writes a file. |
| `POST /api/commands/<name>` | One named single-document command (the layout commands of §3.1, the geography commands of §3.8, the settlement commands of §3.9, the interior commands of §3.10, the entrance commands of §3.11) or `undo`/`redo` of the current segment (see §3). |
| `POST /api/partition/generate` | Admits one explicit partition job (§3.12). Body: exactly `session_generation` and `snapshot_revision`. |
| `POST /api/partition/cancel` | Cancels the generating partition job (§3.12). Body: exactly `session_generation`. |
| `GET /api/partition/outlines` | The current partition artifact's `artifact_fingerprint`, `input_signature` and district `outlines` (rings of `[x0, y0, x1, y1, ...]` metres); 404 `partition_unavailable` for a missing or malformed artifact. Read-only. |
| `GET /api/session` | Same-origin launch-token bootstrap (see §4). |

`external_incoming_references` maps the `qualified_ref` of every projected
location, settlement node and interior room that the reference index names to
its incoming external references (looked up with the core's
`incoming_references_for`, so the payload stays bounded to projected objects).
It is present whenever the index decoded, current or not; only a current index
can support a deletion, and the execution-time guard of §8 stays the authority.

`snapshot_revision` is an invalidation counter. It changes whenever the
observable state changes (a new world, or a new stale or unavailable status),
not only when the world changes, the write pause changes or the undo/redo
history moves. Commands must name the current `session_generation` and
`snapshot_revision` (§3). Startup is a fresh disk read with a new session identity, and
the editor is writable exactly when that read loads. There is no handoff,
resume or return route, and no generic patch, file-write, path, shell, Python
or account route. The partition routes take no path or file content: the job
writes only the partition artifact (§3.12).

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
3. no write pause, then a current preview. Both are `write_paused` (423)
   with a `reason`: `uncertain_durability` for an uncertain publication, or
   `stale_preview` / `unavailable_preview` while the last read did not load.
   The two conditions are orthogonal: a stale preview recovers by itself,
   the pause only through the explicit reread;
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
result. `delete_location` (§3.8) and the undo of `create_location` are the
object-removing world-document effects. Every removal first passes the
map-internal reference guard on the fresh disk baseline (a settlement
`location_ref`, a node `anchor_key` or a district landmark still naming the
removed object refuses it as `deletion_refused` with `guard: internal` and
the `internal_references`), then the authoring gate and the execution-time
external-reference guard of §8. Nothing cascades.

### 3.2 Drafts, completed operations and history

A manual operation completes on drag release, a confirmed inspector field
(Enter or blur with a complete integer), or one Shift+arrow press. Each
completed operation is one command and one history entry. Keystrokes stay
drafts: an incomplete value keeps the draft with an inline error and writes
nothing. Escape restores the saved value, and Escape during a drag cancels it.
Save (Ctrl/⌘+S) waits for accepted operations and never forces a draft.
A complete draft is confirmed whenever the field loses focus, so clicking
elsewhere saves it; an incomplete draft is never written by any path.
Navigation that would remove an unresolved field returns focus to that field,
including selection changes, layer hiding and another object's drag. Resolve
the draft with a valid confirmation or Escape before leaving it.
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
source or layout change it did not write, and when a read fails to load
(§3.4). Changes to the generated artifacts do not count. A service restart is a new
session with no history. Commands are never replayed after a reconnect.

Only one owning document is mutated per operation. A multi-selection (§3.6)
is inspect/copy only; a selection that spans documents states
so, and the service refuses it as `cross_document`.

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

### 3.4 Continuous file following

There is no handoff, turn, ownership or return state, and no route for one.
Manual and AI (OMP) editing alternate freely. The editor never starts OMP
and never claims whether OMP is running or finished.

**Watching.** `elosern_map_editor.watching` runs one watch coordinator
(watchfiles) in the service lifespan. It watches:

- `content/` recursively: world sources, layouts (also a layout directory
  created later) and the reference context;
- the partition artifact's directory, filtered to that file;
- the external context source closure where available: the literal
  directory prefix of each glob discovery rule recursively, and each literal
  rule file through its parent directory, filtered to the file.

A root that does not exist is watched through its nearest existing ancestor.
After every reconciliation the plan is recomputed, and a changed plan
restarts the watchers. Each (re)start reconciles once as soon as the watcher
is established, which covers changes made while it was starting.
Notifications are coalesced until the directories stay quiet for the settle
interval (`settle_seconds`, 0.15 s; at most 1.6 s per batch). A debounce is
not a multi-file transaction: an AI edit that spans files may be seen
half-way and simply loads (or fails) as it is. A watcher failure is reported
in `following.error` and retried with a backoff of 2 s up to 30 s.

**Reconciliation.** Each batch is one complete fresh read under the service
lock, compared with the *committed fingerprint ledger*: the source/layout
presence map the service last committed to. That is its last adopted loaded
read, or that map plus its own write's result (absence included). A write
that published counts as committed even when the service's own reread after
it failed or did not load. While a publication is uncertain, either its
intended or its baseline presence is own output. No path or event is ever
suppressed because it was recently saved.

| Fresh read | Effect |
| --- | --- |
| Loads and equals the ledger | The service's own output, however delayed or coalesced the notification was: history kept, nothing published (unless an artifact status changed) |
| Loads and differs | An external change, adopted automatically as the new snapshot: history cleared, and `external_change` records the differing documents |
| Does not load | Read once more after the settle interval, in case a write was caught half-way. If it still fails, the last preview is kept and marked `stale` (or `unavailable` with no prior preview), and `candidate_diagnostics` gives file, field and line. The history is cleared, the ledger is not moved by the failed read, and commands are rejected (`stale_preview`). The next loadable change recovers automatically. Nothing is ever rewritten from memory. |

Restoring the exact committed bytes after a failure is not an external
change, but the failure already ended the segment. The same fingerprint
limit applies the other way: an external writer that writes exactly the
bytes the editor committed cannot be told apart from the editor's own write.
If another document changes while a command is published, the segment ends
and that guarded operation starts the next one. If the command's own
document is overwritten before the service's reread, the operation is not
recorded.

**Remaining race.** If OMP and the editor write the same document within
one settle interval, the editor's save is rejected with the external content
intact: `stale_snapshot`, or `stale_document` at the disk recheck. The page
then shows the reloaded content. Nothing is merged or retried. The operator
is responsible for not editing the same documents in OMP and the editor at
the same time.

### 3.5 Recovery states on the page

The page keeps one displayed snapshot, and every command is built against
it. Each complete workspace the service returns is either adopted at once or
held:

- **External change with an open field draft.** It is held behind the
  banner 檔案已被外部修改（有草稿）, which names the changed documents and the
  drafts and history that will be discarded. 載入新版 discards the drafts and
  adopts it. Tab or Shift+Tab from a held draft focuses 載入新版 without
  confirming the draft; an open inspector drawer closes so the action is
  outside any modal focus trap. Enter on that button explicitly discards the
  draft. Other blur confirmations retain their usual behavior. Once no draft
  is left and no command is in flight, the held
  snapshot is adopted silently. A draft confirmed meanwhile is still sent
  against the snapshot it was typed on, and it is rejected without changing
  disk. Snapshots after that command (its own result included) stay held
  until the drafts are resolved. Without drafts, adoption is silent apart
  from the 檔案同步 chip.
- **Selection.** Domain, open maps, canvas view and selection are preserved
  by qualified identity. A selection removed by the external change is
  cleared, and the inspector names it.
- **Stale or unavailable preview.** The canvas is desaturated with the stale
  badge, and the banner shows the first failing `path:line`. There is no
  action, because recovery is automatic. With no prior snapshot, the canvas
  shows no preview, never an empty world. Controls are not pre-disabled. A
  rejected command is shown in the banner until a newer snapshot or the next
  successful command.
- **Disconnected.** The last snapshot stays on screen, inspectable and
  marked stale. Every queued command is abandoned, so nothing is replayed. A
  command already sent when the connection dropped is reported as failed;
  whether it landed is shown by the next read, and the fingerprint guard
  protects any later write. A reconnect to the same session refetches
  automatically.
- **Restarted service.** A new session (new generation and token) is held.
  The old snapshot stays stale, and the old tab's writes are rejected
  (`unauthorized` for the old token, `stale_session` for the old
  generation). 重新連線並讀取 rereads and discards drafts, and only then are
  writes allowed. Write permission, drafts and commands are never restored
  from browser storage.

Banner priority, highest first: disconnected or restarted, failed or
uncertain save, external change with drafts, rejected command, stale or
unavailable preview.

### 3.6 Workbench interaction

The page is the three-column workbench of the frontend design §2: header
(domain tabs on 1/2/3, breadcrumb, return button, status chips), one priority
banner, navigation, canvas, inspector and the diagnostics strip. When the
viewport cannot hold both side columns beside a 480 px canvas (all widths
times `--ui-scale`), as at 200 % zoom of the 1451x790 reference, the columns
become drawers opened from the header (導覽, 檢查器). An open drawer traps Tab,
Escape closes it and returns focus to its toggle, and selecting an object opens
the inspector drawer.

- **Navigation.** Continent layer visibility (a view preference that never
  writes), the world tree with 無本地圖 tags, search by name, ID or qualified
  reference (each result shows its parent map and source document, and equal
  names are marked), and the object list, the keyboard/text alternative to the
  canvas. Click selects one object; Ctrl/⌘ toggles one in or out and Shift
  extends over the object list (also with Enter). Ctrl/⌘ on a search result
  adds it across maps and documents.
- **Return context.** Following a search result, a diagnostic or a
  relationship pushes the previous map and selection on a stack (capped at
  20, no consecutive duplicates). The 「← 返回」 button and Alt+← pop it. Focus
  lands on the destination's inspector heading, or the canvas for a map-level
  target.
- **Inspection.** One object shows its copyable qualified ID and source path,
  fields with unit and frame, and directed relationships read from authored
  fields (roads, connections, entrances, interior links, gates, landmarks,
  local maps, anchors) plus the indexed external references. Nothing is
  derived: no reachability, length or geometry is computed in the browser. A
  multi-selection lists every object and owning document; a selection that
  spans documents is inspect/copy only, with 跨文件的選取只能檢視與複製 in
  place of mutation actions.
- **Delete.** The Delete key and the inspector action show an inline
  explanation and never write or ask for confirmation. Order: a cross-document
  selection; an index that is not current (external references unknown, so
  deletion is refused while inspection and editing continue); external
  references of a current index (what the service guard enforces); otherwise
  the object's delete command is sent, or the block states that its kind
  has no delete command yet. For locations, settlement nodes and interior
  rooms the map-internal references refuse first (§3.8 to §3.10), each
  linked to its declaration (an entrance to its relationship, §3.11). A
  selected relationship, road or connection is removed directly. Map-internal incoming
  references are listed alongside as references a deletion would leave
  dangling; nothing cascades.
- **Diagnostics.** Rows grouped as structure, external index and references,
  service and save, unfinished (semantic) and partition. Each names its
  object, file, field and line. A row of the loaded snapshot whose target
  resolves offers 前往, or 顯示圖層並前往 when the target sits on a hidden
  continent layer. Rows of a read that did not load, or with a reference that
  does not resolve, keep file:line without navigation (there is no source
  editor). The 檔案同步, 索引 and 分區 chips expand the strip; 存檔 focuses the
  banner action while a save failed or is uncertain.
- **OMP context.** Ctrl/⌘+C outside text fields (and with no text selected on
  the page) or the inspector's 複製 OMP 脈絡 action writes plain text to the
  clipboard: every selected qualified ID with its domain, map, relative source
  path and coordinates with frame and unit (or the layout grid, stated as
  editor-only), and whether it came from the current files or a stale preview
  (naming the first failing file and line). It is built from an allowlist of
  snapshot fields, so the launch token, session, segment, fingerprints and
  absolute paths never appear. It states no ownership and starts nothing.
- **Keyboard.** F6/Shift+F6 cycle header, navigation, canvas, inspector and
  diagnostics. On the canvas, Tab walks the marks in object-list order, an
  arrow moves focus to the nearest mark in that direction, and Enter selects
  and focuses the first inspector field. Shift+arrow nudges a single selected
  room when focus is on the canvas or the object list. Ctrl/⌘+Z and
  Shift+Ctrl/⌘+Z (⌘ on macOS, Ctrl elsewhere) undo and redo; Delete; `/` or
  Ctrl/⌘+K focus search; Escape closes an open drawer, then cancels a tool,
  then the delete explanation, then the selection (a field draft and a drag
  consume their own Escape first). Single-key shortcuts never act in a text
  input, select or `[data-object-selector]`, during IME composition or with a
  modifier; inside a field its own undo, delete and copy apply.

### 3.7 Mandatory domain dependencies

The shell's domain commands arrive with their changes. Delivered:
`map-editor-continent-tools` (§3.8), `map-editor-settlement-tools` (§3.9),
`map-editor-interior-tools` (§3.10) and `map-editor-entrance-tools`
(§3.11). The batch's remaining change must deliver, through its own domain
modules:

| Change | Delivers on this shell |
| --- | --- |
| `map-editor-partition-jobs` | Partition district drawables, 分區 chip and inspector regenerate/cancel, and rejection of every command route (geography included) while a generation runs |

Each registers its tools in `TOOLS` (`src/lib/workbench.js`), sends its own
named single-document command, and lets the service's refusal (for example
`deletion_refused`) replace the shell's explanatory delete block.

### 3.8 Continent geography tools

Service handlers live in `elosern_map_editor/geography.py` on the shared
`DocumentCommand` base (`commands.py`): typed arguments, the owner check, a
mutation of the thawed document data, comment-preserving serialization
validated by the core schema, then the authoring gate and the writer. Field
values are validated by the core schema; the service and the browser keep no
second schema or classifier. Frames: mainland vertices are kilometre geometry
(`km 地理`); forest-edge, waterway-route, ford, site, location, ridge and pass
values are one-kilometre wilderness cell indices (`1 km 格`); the settlement
local anchor is metres (`m 地方`).

| Command | Document | Arguments |
| --- | --- | --- |
| `move_control_point`, `insert_control_point`, `remove_control_point` | continent | `feature` (`{kind: mainland}`, `{kind: forest_edge}`, or `{kind: waterway_route}` / `{kind: waterway_ford}` with `waterway_id`), `index`, `point` `[a, b]` (move/insert) |
| `set_terrain_parameter` | continent | `field` (`ridge.base_x`, `ridge.period`, `ridge.step`, `ridge.min_x`, `ridge.max_x`, `ridge.north_limit_y`, `ridge.mountain_corridor_half_width`, `coastal_y_max`, `border_river_key`), `value` |
| `add_ridge_pass`, `set_ridge_pass`, `remove_ridge_pass` | continent | `y_min`, `y_max`, `index` |
| `add_waterway`, `remove_waterway` | continent | `waterway_id` (new), `route` cells; the border river is never removed |
| `set_region_field` | continent | `region_id` (the core's fixed regions), `field` (`display_name_zh`, `nation_key`, `terrain_flavor_zh`, `nominal_nation_keys`, `scene_archetype`), `value` |
| `add_site`, `set_site_field`, `remove_site` | continent | reserved (harbour) sites: `site_id`, `display_name`, `role`, `cell` |
| `create_location`, `set_location_field`, `delete_location` | locations | a new `location_id` plus `kind`, `display_name_zh`, `description`, `geographic_constraint`, `scene_archetype`, `cell`; established IDs are never renamed |
| `create_district`, `set_district_field` | districts | names, `membership` `{kind, region_key}` (set together) and a stable qualified `landmark` `{domain, map_id, object_id, cell}` |
| `set_footprint_cell` | settlement | `settlement_id`, absolute `cell`, `filled`; a filled cell outside the mask grows it with `.` (at most 64x64). The saved value is the mask's offset from the settlement's location cell, so existing `#` cells keep their absolute positions and a later location move carries the whole mask |

Creating a location never creates a local map, room or settlement document;
a local map is a separate settlement command. Locations derive their local
maps from settlement `location_ref` values, so 開啟本地圖 appears only when one
exists and 無本地圖 otherwise.

There is no editable binding and no `set_binding` command: a settlement's world
frame is derived from its location cell and its unique `anchor_room` node. A
location drag on the continent is therefore one `set_location_field` command
and one undo entry writing only `locations.yaml`; the reloaded core translates
every node's world metres, the mask and every gate approach by the drag delta,
and the partition becomes stale without being rewritten.

The projection adds the core's `terrain_preview` (`terrain_preview()` over
`terrain_definition()` of the current inputs, sampled on at most 90x90 cells
with region and surface codes, the closed ridge walls between passes, pass
centres and the derived national borders), the ridge, coastal and
border-river fields, full region fields, ford centres and each settlement's
`footprint` (`shape`, the authored `offset`, and the derived absolute `origin`
and `cells`), plus each settlement's derived `world_frame`
(`anchor_cell`, `local_anchor_m`) and node `world_m` — `null` while the frame is
unavailable (no anchor room yet). Inconsistent terrain inputs save as
diagnosed work in progress with `terrain_preview.status: unavailable`.

Derived output is never written and never handled: a committed change to a
partition source only makes `partition_status` stale (its `input_signature`
no longer equals `expected_signature`); nothing regenerates per pointer
movement or per command. A stale partition is not a stale preview, so
commands stay admitted. Commands are rejected (423) while writes are paused
or the preview is stale or unavailable, and every world-data command is
rejected while a partition job runs (§3.12).

On the page the continent tools are 選取 V, 加控制點 A (insert at the nearest
segment, or after the selected point), 水系 (two clicks, then a creation
form), 山脊 (a pass creation form at the clicked row), 地點 (a location or
reserved-site creation form at the clicked cell) and 佔地 (toggle cells of the
selected footprint). Selecting a feature (by click or in the object list)
shows its control-point diamonds; a drag is one command on release and Escape
cancels it. The inspector gives every essential edit a non-drag path:
frame-labelled numeric fields, 前方插入/後方插入/移除控制點, the footprint
`#`/`.` grid (arrow keys and Space), the structured landmark selector, and a
衍生結果 section with the terrain preview state, the partition's input
signature against the current one and the explicit 重新產生分區 / 取消產生
control (§3.12). Geometry deletions send their
command directly; a location delete first shows the inline refusal while a
map or external reference remains.

### 3.9 Settlement tools

Service handlers live in `elosern_map_editor/settlements.py`; each writes
exactly one document, `content/maps/settlements/<settlement_id>.yaml`.
Positions and bends are integer metres in the settlement's local east/north
frame (`m 地方`). Directions are authored values: no command, and nothing in
the browser, infers or recomputes a compass direction from positions.

| Command | Arguments |
| --- | --- |
| `create_settlement` | `settlement_id` (new), `location_id` (existing), `options` (`{map_visual_range, map_mode}` or `null`); expected presence `absent`. The document starts with no binding, no nodes and no roads, so it is diagnosed unfinished rather than playable; the first `create_node` becomes the `anchor_room` of that location (`anchor_key` equal to `location_ref`) and supplies the local frame |
| `set_settlement_field` | `field` `options` or `exit_prototype`, `value` (`null` removes it) |
| `create_node` | `node_id` (new) and `fields` with every node field (`x_m`, `y_m`, `prototype_parent`, `key`, `desc`, `anchor_key`, `typeclass`, `scene_archetype`) |
| `duplicate_node` | `node_id`, `new_node_id`, `x_m`, `y_m` |
| `set_node_fields` | `node_id`, `fields` (any node field except the position; `prototype_parent` and `anchor_key` together) |
| `move_nodes` | `moves` `[{node_id, x_m, y_m}, ...]`: one or several nodes in one operation |
| `delete_nodes` | `node_ids` |
| `create_road` | `source`, `destination`, `direction`, `bends`, `return` (`{direction, bends}` adds the reverse entry in the same operation, or `null`) |
| `set_road` | `source`, `destination` of an existing road and `value` `{source, destination, direction}`; bends are kept |
| `delete_road` | `source`, `destination` |
| `insert_bend`, `move_bend`, `remove_bend` | `source`, `destination`, `index`, `point` `[x_m, y_m]` (insert/move) |

Every command carries `settlement_id` and is refused as `cross_document` when
its `document_id` names another document. Lists (moves, deleted nodes, bends)
hold at most 1,000 entries. Field values are validated by the core schema and
the candidate world by the authoring gate: a duplicate node ID, a duplicate
coordinate, a duplicate ordered road, a second road leaving a node in the same
direction, a self-loop or an unknown endpoint is refused with nothing written.
Unfinished connectivity (an unconnected node, an unreachable landmark) is
saved work in progress with its diagnostic.

- **A new local map** writes only its settlement document: no location data,
  since a location's local maps derive from `location_ref`. It has no nodes
  or roads and the core diagnoses it `empty_graph` (semantic), so it is never
  presented as playable. Its first created node becomes the `anchor_room` of
  that location (the entered ID, position and other fields are kept) and is
  what places the graph on the continent. Undo removes the file.
- **The anchor node owns the local frame.** Moving `anchor_room` alone changes
  one settlement command and one undo entry: the anchor stays on the location
  cell's centre, the location and the footprint stay fixed, and every
  untouched node's world position shifts by the negative local delta. A group
  move that includes the anchor shifts each moved node and the anchor
  together, so the selected nodes keep their world positions. Deleting the
  anchor from a non-empty graph promotes nothing: the map reports
  `missing_anchor_room` until the user supplies one through the existing
  prototype fields, and the core rejects a second `anchor_room`.
- **Identity.** Established IDs are read-only; new nodes need new IDs.
  `duplicate_node` copies the ordinary values (name, description, scene,
  typeclass, prototype) under a new ID and copies no relationship: no road,
  gate, city gate, interior exterior or landmark. An `anchor_room` copy
  becomes a `grid_room` without an anchor key, because the anchor binds the
  one room of its location.
- **Moves** keep the node ID, every authored road direction and every
  dependent selector (gates, interior exteriors, district landmarks, external
  references by qualified ID); the core recomputes the road lengths. Authored
  metres are the map's non-negative grid coordinates, so a move that would
  leave a node west or south of the frame origin re-origins the whole document
  in the same write: every node and road bend translates by the same delta,
  which changes no world position (the transform subtracts the anchor node)
  and no road length.
- **Deletion never cascades.** `delete_nodes` is refused (409
  `deletion_refused`, guard `internal`) while a road in either direction, a
  wilderness gate, the city gate, an interior exterior or a district
  landmark names one of the nodes, also for a road between two deleted
  nodes; remove those first. The shared internal guard on the fresh disk
  baseline also reports interior exteriors for any object-removing effect,
  including an undo. Then the execution-time external reference check
  applies (§8). Roads and bends are owned by their settlement document only
  and are removed directly.

The projection adds each node's `typeclass` and `scene_status` (`none`,
`valid`, `invalid` against the current index's `scene_archetypes`, or
`unavailable` when the index is not current), each settlement's `options`
and `exit_prototype`, and road `length_m` from the core's `road_lengths`
(present also for maps whose graph cannot be built, such as an empty one).
`GET /api/workspace` carries `external_identifiers.scene_archetypes` only
while the index is current. `GET /api/settlements/<id>/route?source=&destination=`
is a read-only preview of the core planner (`settlement_route`) over the
published snapshot: `status` (`route`, `no_route`, `unknown_node`,
`unavailable`), each step's authored direction and length, the total, and
the `snapshot_revision` it was computed for; the inspector marks a result
that belongs to an older revision.

On the page the tools are 選取 V, 節點 N (a creation form at the clicked
point, rounded to whole metres) and 道路 R (choose the source node, then the
destination, on the canvas or in the object list; the form requires the
direction and, with 建立雙向, the return direction), and 入口 E (§3.11). Dragging a node or a bend diamond is one
command on release (Escape cancels); a node dragged inside a one-document
multi-selection moves the group by one integer delta, and a refused move
returns to the saved position. Every edit has a non-drag path: the node
inspector's schema-typed fields (name, prototype with its anchor location,
scene from the current index, typeclass, description) and `m 地方` position
fields, 複製為新節點, ⟶ 新道路, the directed road rows (`北 → 北門 · 65 m`,
`← 北 來自 鐘樓廣場`) and the core route preview; the road inspector's
endpoint and direction selectors, length, bend rows with 前方插入/後方插入/
移除彎點 and 建立反向道路; the multi-selection's mixed values (`—`), group
delta and Shift+arrow (10 m per press). A selection spanning documents is
inspect/copy only. The location inspector's 建立本地圖 creates a local map
and opens it. Rejection of commands while a partition generation runs is
added by `map-editor-partition-jobs`.

### 3.10 Interior tools

Service handlers live in `elosern_map_editor/interiors.py`. Each source
command writes exactly one document, `content/maps/interiors/<interior_id>.yaml`,
and carries `interior_id`; a `document_id` naming another document is
`cross_document`. Interiors are coordinate-free: no command, projection
field or browser control gives a room a position in metres, a distance or a
route length.

| Command | Arguments |
| --- | --- |
| `create_interior` | `interior_id` (new), `room_id` (new) and `fields` with every room field (`name_zh`, `desc_zh`, `scene_archetype`, `art_key`); expected presence `absent` |
| `delete_interior` | `interior_id` only: removes the document |
| `create_room` | `room_id` (new), `fields` with every room field |
| `duplicate_room` | `room_id`, `new_room_id` |
| `set_room_fields` | `room_id`, `fields` (any room field; the ID is never renamed) |
| `delete_room` | `room_id` |
| `create_connection` | `source`, `destination`, `label`, `return_label` (a name adds the reverse connection in the same operation, or `null`) |
| `set_connection` | `source`, `destination`, `label` of an existing connection and `value` `{source, destination, label}` |
| `delete_connection` | `source`, `destination`, `label` |
| `arrange_interior_layout` | `positions` `[{room_id, x, y}, ...]` (at most 1,000, integers within ±100,000): writes only `content/map-editor-layouts/<interior_id>.yaml`, merging into its other positions |

- **Standalone interiors.** A new interior has its first room, no
  connections, no interior links and no exterior. No service, NPC, economy
  or layout record is written or required. Creating a room never writes a
  layout: it is drawn at the deterministic list position
  (`[index % 3, ⌊index / 3⌋]`) until a later, distinct layout command places
  it.
- **Identity.** Room and interior IDs are read-only once created. The game
  gives a permanent room one identity across every interior, and the shared
  core authoring gate rejects such a candidate (`duplicate_interior_room`)
  for every interior effect, undo and redo included. A duplicate already on
  disk makes the world structure-invalid, so the editor keeps no current
  preview and refuses writes until the documents are fixed. `duplicate_room`
  copies the ordinary values (name, description, scene, art key) and no
  relationship: no connection, exterior, interior link or landmark, and no
  incoming reference is retargeted.
- **Service rooms.** Existing service-place keys stay the room IDs that
  service and host records join. The inspector lists the joining `places` and
  `service_hosts` records from the reference index read-only; editing a
  joined room's prose keeps its ID and creates no second interior. Host and
  goods authoring is not part of the editor.
- **Connections** are directed and named; the name is the exit's name.
  Endpoints must be rooms of the document and differ (`self_loop`), and the
  ordered triple is unique (`duplicate_connection`); a two-way creation
  checks both triples before writing either. Names are non-blank with no
  surrounding whitespace. Two exits of one room with the same name are not
  refused (the core has no such rule); the inspector marks them.
- **Deletion never cascades.** `delete_room` is refused (409
  `deletion_refused`, guard `internal`) while a connection in either
  direction, the exterior, an interior link of the document, another
  interior's link or a district landmark names the room. Then the
  execution-time external reference check applies (§8): a room joined by a
  service place or host is refused, and nothing is removed while the index is
  not current. `delete_interior` passes the same guards for every room it
  declares. Undoing a room or interior creation removes objects, so it also
  needs a current index. Layout positions of a deleted room or interior are
  left in place for the explicit `remove_interior_layout` cleanup; a later
  room or interior with the same ID shows them again.

The projection adds each room's `scene_status`, as for settlement nodes
(§3.9).

On the page the tools are 選取 V, 房間 N (opens the room creation form at
once, or the new-interior form when no interior is open), 連接 R (choose the
source room, then the destination, on the canvas or in the object list; the
form requires the name and, with 建立雙向, the return name) and 自動排列 (one
`arrange_interior_layout` command: columns by connection distance from the
entrance room, rows in authored order, unreached rooms after them; it
overwrites the arranged positions and is undoable), and 外部入口 E (§3.11). Rooms are cards and connections curved arrows,
each with one direction chevron; a two-way pair reads `去 ⇄ 回` once.
Selecting a connection selects its editor-local reference
`connection:<interior>:<source>><destination>/<percent-encoded name>`, which
no other document can name. Every edit has a non-drag path: the room
inspector's name, description, scene (from the current index) and art key
fields, the directed connection rows with ⟶ 新連接 and ⧉ 複製為新房間, the
connection inspector's endpoint selectors and name field with 建立反向連接,
the editor-only 版面 X/Y fields, Shift+arrow, and the open interior's ＋ 新房間,
自動排列, ＋ 新室內 and 刪除室內文件. After a layout save the diagnostics strip
names the layout document.

### 3.11 Entrance tools

Service handlers live in `elosern_map_editor/relationships.py`. Every
entrance relationship is stored once, in its owning document, with both of
its endpoints and every directional label it has. No command writes a
mirrored reverse record, and a two-way meaning is never a second file
operation. Editing one relationship writes only its owner.

| Command | Owner | Arguments |
| --- | --- | --- |
| `create_wilderness_gate` | settlement | `settlement_id`, `return_direction`, `node`. Without a wilderness entry, a one-cell point entry is created at offset `(0, 0)` — its hash cell is the location cell — and the continent 佔地 tool can then grow it |
| `set_wilderness_gate` | settlement | `settlement_id`, `return_direction` of an existing gate, `value` `{return_direction, node}` |
| `delete_wilderness_gate` | settlement | `settlement_id`, `return_direction`. The last gate is refused (`last_gate`): an entry keeps at least one gate |
| `remove_wilderness_entry` | settlement | `settlement_id`: the explicit removal of the whole entry, its footprint mask included (undoable) |
| `set_city_gate` | settlement | `settlement_id`, `value` `{node, exit_key, exit_aliases}` or `null` |
| `set_exterior` | interior | `interior_id`, `value` `{room, node, doorway_key, doorway_aliases}` or `null` |
| `create_interior_link` | interior | `interior_id`, `source`, `target`, `label`, `return_label` (a name makes the link two-way in the same record, `null` one-way) |
| `set_interior_link` | interior | `interior_id`, `source`, `target`, `label` of an existing link and `value` `{source, target, label, return_label}` |
| `delete_interior_link` | interior | `interior_id`, `source`, `target`, `label` |

- **Endpoints are qualified IDs** (`settlement_node:<map>:<node>`,
  `interior_room:<map>:<room>`), never a display name or an unlabelled
  coordinate. Gates and the start entry land on a node of their own
  settlement. An exterior joins a room of its own interior to any settlement
  node. A link joins a room of its own interior to any interior's room, never
  the same room. Each of the following answers 422 with nothing written: a
  refused endpoint (`invalid_endpoint`, `wrong_domain`, `wrong_map`,
  `unknown_target`, `self_loop`), a duplicate gate direction or link, and the
  last gate. The diagnostic names the `relationship` (`wilderness_gate`,
  `city_gate`, `exterior`, `interior_link`), its `owner` document and the
  argument `field_path`. An authoring-gate failure on an entrance field gets
  the same attribution, for example a target that disappeared from disk
  after the page loaded.
- **The start entry is one-way.** The starting room is not a map object, so
  its entry has no return field. A value that names one (`return_label`,
  `return`, ...) is refused with 400, naming the key. The inspector states
  that the entry cannot become two-way.
- **Doorway names.** The game refuses two interiors that open onto the same
  settlement node under one doorway name (aliases are not compared) and the
  shared core authoring gate reports `duplicate_doorway` for such a candidate
  on every world-source effect, undo and redo included.
- **No index is needed.** A relationship is not a qualified object that any
  other document can name, so removing one needs no reference index, just
  like removing a road or a connection. Deleting an endpoint object is still
  the existing guarded command (§3.8 to §3.10, §8). While a relationship
  still names the object, the deletion is refused, and the inline refusal
  links that relationship. Removing the relationship and later deleting the
  object are two separate, complete operations. Nothing cascades.

The projection gives each wilderness gate an `approach_cell`: the wilderness
cell that the core's `gate_approach_cell` computes from the mask and the
return direction. It is read-only, and the browser derives no geometry.

On the page, relationships use editor-local references:

- `gate:<settlement>:<return_direction>`
- `city_gate:<settlement>`
- `exterior:<interior>`
- `interior_link:<interior>:<source>><target_interior>:<target_room>/<percent-encoded label>`

They are catalogued on their owner's map. Search, the object list,
selection preservation by identity and the OMP context therefore include
them. Search matches a relationship by ID; searching a node or room name
finds the object itself. The interior draws its exterior as a fixed, dashed
card one layout column left of its room. The settlement lists its gates and
start entry in the object list.

- **Tools.** 入口 E (settlement) and 外部入口 E (interior) wait for a node or a
  room on the canvas or in the object list. Picking one selects it and opens
  the entrance form.
  - On a settlement, the form offers a wilderness gate or the one-way start
    entry. The gate's return direction is chosen, never inferred. The start
    entry takes an exit name and aliases.
  - In an interior, the form offers the exterior doorway or an interior
    link. The doorway takes a node chosen with the qualified-object selector,
    a doorway name and aliases. The link takes a target chosen with the
    selector, a name, and, with 建立雙向, a return name.
  - The node and room inspectors open the same form through ⌂ 新入口.
- **Relationship inspector.** The heading names both ends. The record rows
  give the owner document as the one record and the direction: 雙向, 單向,
  or a fixed 單向 for the start entry. Each endpoint shows:
  - its domain;
  - its qualified ID as a link;
  - the end's name and directional label;
  - its current coordinates where the projection has them: a node's local
    metres, or a gate's approach cell, which links to the settlement's
    continental footprint.

  The inspector's actions:
  - 前往另一端 navigates to the endpoint that is off the map on display
    (otherwise the target), keeping the return context of §3.6.
  - 更換端點… opens the qualified-object selector.
  - Fields edit the labels, aliases, gate direction and link return name.
  - 移除這個關係, the generic ✕ 刪除 and the Delete key each remove the
    relationship with one command. A gate also offers the explicit
    whole-entry removal.
- **Qualified-object selector** (`[data-object-selector]`). Search the
  allowed objects by name, ID or qualified ID. Each result shows its parent
  map and qualified ID, and equal names are marked. ArrowUp and ArrowDown
  move, Enter chooses, and Escape closes the selector and returns focus to
  the trigger. The page's single-key shortcuts never act inside it.
- **Relations and refusals.** The node and room relation rows list each
  entrance from either side and link to the relationship: an interior's
  exterior appears on its node, and a link on both of its rooms. A refused
  node or room deletion links each entrance that must go first. Core
  diagnostics on `city_gate` and `exterior` fields locate the relationship.

### 3.12 Partition jobs

Partition generation is explicit and runs outside request handling
(`elosern_map_editor/partition_job.py`, `partition_worker.py`). The editor
project installs the core `generation` extra (NumPy/SciPy) in its own lock,
without any game dependency. Nothing regenerates per pointer movement, drag,
command or file change: only `POST /api/partition/generate`, reached from the
分區 chip or the inspector's 重新產生分區, starts a job.

**Admission** (inside the service lock): the current `session_generation` and
`snapshot_revision` (`stale_session` / `stale_snapshot`, 409); no write pause
and a current preview (`write_paused`, 423); no running job (`job_running`,
409). A fresh confined read of the world sources must carry the published
world's partition source signature (`stale_snapshot`, 409, until the reread),
and the artifact's presence must be readable (`artifact_unreadable`, 409).
That read is the captured input; its signature is the job's
`input_signature`.

**Execution.** A dedicated thread runs `python -I -m
elosern_map_editor.partition_worker` as a child process on exactly the
captured sources. The child loads them with the core authoring loader, binds
them with `elosern_map_core.partition.world_snapshot` and generates the
artifact text; it reads and writes no workspace file. The service's event
loop and interpreter never run the raster work, so browsing, inspection,
rereads, file following, status and cancellation stay responsive. A job that
exceeds `partition_timeout_seconds` (900 s by default) fails with `timeout`.
The editor's `world_snapshot` binding and the game's
`tools.map_district_partition` registry binding are two bindings of one seed
rule; `tests/test_map_partition_independence.py` proves the editor binding
regenerates the committed artifact byte for byte.

**Exclusion.** While a job is `generating` or `publishing`, every command
whose document is a world source, including undo and redo of one, is
rejected (`write_paused`, 423, `reason: partition_generating`) at admission
and again at the single effect publication point. Editor layout commands
stay admitted: a layout cannot change a generation input. There is no
handoff state to block.

**Invalidation and publication.** Any adopted loaded read (file following, an
explicit reread or the service's own write) whose partition signature differs
from the captured one ends the job at once (`failed`, `inputs_changed`) and
ends its child process. When the child answers, publication runs inside the
same lock as commands: the job must still be the generating one, then no
write pause, a current preview, a fresh disk read whose partition signature
(the signature over the partition-kind sources, the "full current source
signature" of the design; interiors and layouts cannot change ownership)
equals the captured one, and an unchanged artifact presence
(`write_paused`, `stale_preview`, `inputs_changed`, `artifact_changed`).
Only then does the writer replace `world/maps/data/district_partition.json`
with the same guarded atomic replacement as a source document (temporary
file, flush, rename, directory flush), reached through the one confined
opener reserved for this artifact; no command or route can name it. The
service rereads and publishes the new snapshot. The artifact is not a
source, so it never enters the committed fingerprint ledger and its own
change is no external change (history stays).

**States** (`partition_job.state`): `idle`, `generating`, `publishing`,
`succeeded`, `cancelled`, `failed` with a `reason` (`generation_failed`,
`inputs_invalid`, `inputs_changed`, `write_paused`, `stale_preview`,
`artifact_changed`, `publish_failed`, `publish_uncertain`, `reread_failed`,
`timeout`, `worker_failed`, `output_too_large`, `internal_error`) and bounded
`problems`. Any unexpected error in the job thread or the publication ends
the job as `internal_error`, so no failure leaves world-data writes refused. A
cancel, a failure or a timeout never touches the last artifact.
`POST /api/partition/cancel` ends a generating job; while or after
publication it answers `job_not_running` (409) with the job's own state, so
a completed publication is reported as completed and nothing promises a
rollback. A `publish_uncertain` outcome leaves whatever the reread finds on
disk and withholds `game_ready` until a later job succeeds; it does not
pause source writes, because the artifact's freshness is always read from
disk.

**Freshness on the page.** `partition_status.game_ready` is true only for an
artifact that describes the current inputs (and not after an uncertain
publication); the core's `stale_partition` diagnostic withholds game
readiness otherwise. Source saved state is separate from output freshness: a
saved relevant edit leaves the old artifact in place and marks it stale. The
分區 chip reads 分區 現行, ▲ 分區過期 · 重新產生, ⟳ 分區產生中 · 取消,
分區已取消 · 保留舊版 or ✕ 分區產生失敗 · 保留舊版; activating it regenerates when
the output is not current and cancels while generating. The canvas draws the
current artifact's district outlines (fetched once per
`artifact_fingerprint`) as derived, non-selectable rings on the 分區 layer.
Outlines of an artifact for older inputs stay inspectable but fade and carry
a persistent canvas label and an inspector note; they are never shown as
current. A command refused during generation appears in the banner slot
with its own reason.

**Limitations.** One job at a time per service; a service restart ends a
running job (its child is killed) and the next session starts idle. The
publication recheck and the replacement are not atomic against another
process writing the same files, exactly like source writes; an external
writer must not regenerate the artifact concurrently. A source change that
lands after the publication recheck but before the reread leaves the job
`succeeded` with an artifact for the captured inputs; the reread then
reports it stale (`game_ready` false, the chip offers 重新產生), so it is
never labelled current. The withheld readiness after `publish_uncertain` is
session state: after a restart the artifact's freshness is again read from
disk alone. The child has a wall-clock bound but no memory bound, and its
answer is buffered before the size check; this is a developer-only tool.

### 3.13 Capture snapshot loader

`elosern_map_editor/snapshot.py` owns the one confined read of the workspace
and the projection of it: `load_sources()` discovers the world sources and the
editor layouts once, reads each discovered document once through
`ConfinedWorkspace`, loads them with `elosern_map_core`, parses the layouts and
projects the world (`_project`). `read_workspace()` builds the editor's read
model from that operation and keeps the interactive editor's policy: a layout
document that fails to parse produces diagnostics and a partial layout
projection, a refused or unloadable source set produces an unloaded read.

`elosern_map_editor/capture_snapshot.py` is the one-shot read-only consumer for
offline map capture. `load_capture_snapshot(root, *, view, map_id,
hidden_layers)` returns JSON-ready `{world, partition, diagnostics}`, or raises
`CaptureSnapshotError` with a stable `code`; it never returns partial data, and
it never starts the service, the writer, the watcher, a partition job or the
game. `world` is the same projection the editor reads (interior layouts,
`layout_position` absent for a room the layout does not place, continental
terrain preview). `diagnostics` are the sorted structured diagnostics;
an external-reference index that is missing or not current is reported as one
advisory (`warning`) diagnostic and never gates the capture.

Two policies are capture-specific:

- **Structure blocks, semantics stay visible.** Any source or layout
  structure diagnostic — a refused path, an unloadable document, a malformed
  or duplicate-key layout, an out-of-range coordinate — refuses the capture
  with the diagnostics instead of falling back to deterministic positions.
  Loadable semantic work in progress (unresolved references, unreachable
  nodes) still captures, with its diagnostics. Nothing is persisted, so a
  fallback position stays a renderer input only.
- **Partition output is admitted only where it is drawn.** Only
  `view == "continent"` without the `partition` layer hidden reads
  `world/maps/data/district_partition.json`. It is decoded through the shared
  core codec with the loaded mainland land rule, so valid metadata over a
  corrupt body is refused too, and its freshness is compared against the
  partition signature of the world this invocation loaded — the freshness of
  one snapshot, never a second read of the files. A missing, malformed or
  stale artifact raises `partition_unavailable` with the reason and the
  recovery guidance: regenerate it with
  `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`
  or hide the layer with `--hide partition`. Hidden partition and the
  settlement/interior views never open the artifact, and their terrain
  preview still derives from the loaded source.

Argument shape is the caller's: this loader validates the view name, that a
settlement/interior request names an authored document of that view (an absent
id is `unknown_map`, an id of the other view is `wrong_view`) and that a
continent request names none. The capture command above it owns the layer
vocabulary, bounds, sizes and output format.

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
  the two generated artifacts; only the partition job publishes the
  partition artifact (§3.12), and no command can name either artifact. Files are opened by walking from a descriptor of
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
The editor operates on static authoring documents and does not connect to or query the live game database (`ObjectDB`). It cannot certify live save dependents (e.g., players currently occupying a room or dynamic exits). Live occupied room safety and persistent room preservation remain strictly game-side responsibilities enforced during runtime adoption and synchronization (`world.maps.runtime.adopt` and `world.maps.runtime.synchronize`). The editor's static checks are authoring diagnostics, not an authoritative live-save validation, and its status chips never claim game readiness.

### Geometry Exclusion
The reference index records stable authored identities (e.g. `settlement_node:capital_altoria:central_plaza`), not derived spatial coordinates or grid wire strings (`grid:capital_altoria:100:200`). Moving a node coordinate alone does not alter the external reference index or its dependency fingerprint.

## 9. Integrated Acceptance

The integrated acceptance evidence (map-editor-integrated-acceptance) chains the
focused slice checks into whole sessions. It adds no behaviour of its own:
every test drives the independently installed service (its own locked
environment, scrubbed environment, empty `PATH`, real watcher; no game server,
Evennia, Django or database) or the game's existing map owners, and asserts the
effect on disk, in the core reload or in the committed persistent world.

| Evidence | Owner | Scenarios |
| --- | --- | --- |
| Manual authoring workflows | `web/tests/browser/test_map_editor_workflows.py`, `MapEditorWorkflows{Chromium,Firefox}Test` | Location, control point, footprint cell and district landmark in one session; node, two-way road, room, two-way connection, exterior endpoint (keyboard selector) and layout drag in another. After each operation exactly the owning document changed and the map core, run in the editor's interpreter, reloads the files with the new value; the final continental files load in a freshly started service. Chromium also copies the OMP context with a user gesture (Playwright grants no clipboard permission in Firefox, a deliberate gap). |
| Continuous file following | same module, `MapEditorFollowing{ReferenceChromium,LargeChromium,ReferenceFirefox}Test` (1451x790 and 2560x1440) | Automatic adoption with the selection kept; a change held behind an open draft, resolved by 載入新版 (pointer) or Esc (keyboard) with no write; the fingerprint-guard race (an external replacement lands after the page built its command and before the service checks the disk: `stale_document`, external bytes kept, no merge or retry); malformed to corrected YAML with semantic work in progress; an old tab after a restart; an externally removed selection. |
| Reflow and keyboard | `web/tests/browser/test_map_editor_accessibility.py` | The keyboard-only workflow and the viewport reflow (dense diagnostics, long Chinese names, a multiline description, 200 % zoom emulated as 725x395 at scale 2) in Chromium and Firefox. |
| Independent jobs and deletion | `tests/test_map_editor_independent_environment.py` | Cancel and input change keep the prior artifact byte-identical until a current run publishes the core's own output; a current index refuses an externally referenced room, a missing index refuses every deletion while edits save; nothing else appears in the workspace and the editor interpreter has no game framework. |
| Game adoption of final YAML | `world/maps/tests/test_editor_final_yaml_adoption.py` | A moved, occupied and observed node with an interior entrance and further gate, landmark or art dependents keeps its room, exits, occupant, home, inbound exits and knowledge ticks; static declarations resolve to the new position; a repeated synchronization changes nothing. A stale partition, a structural error and an invalid external reference leave the registry and the persistent baseline unchanged; removing a node whose room is still live (occupied and the destination of persisted exits) is refused by the prune guard and rolled back. |

The game test stands in for the editor's partition regeneration by signing the
committed artifact metadata for the candidate inputs, because the game reads
the committed repository artifact and every settlement edit makes it stale.
`partition_freshness` itself still runs (it compares the format, algorithm and
source signature), and the stale case uses the committed artifact unchanged.

Reproducible focused runs, from the repository root (build the frontend first,
see §1):

```console
uv run --locked playwright install chromium firefox
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_workflows
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_accessibility
uv run --locked python -m unittest tests.test_map_editor_independent_environment
uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb world.maps.tests.test_editor_final_yaml_adoption
uv run --locked python -m tools.contract_gate
```

`<file>` contains `MUD_TEST_SETTINGS=1`. CI runs the same evidence without a
separate entry point: the editor package tests in the preflight job
(`tools/map-editor`, its own lock), the repository wrappers in the top-level
job (`CI` turns an unavailable editor environment into a failure instead of a
skip), the browser methods in the shards listed in
`.github/browser-shards.json` (Chromium and Firefox are installed there and the
editor frontend is built in both workspaces), and `world.maps` in its evennia
shard. The full managed browser suite and `tools.spec_traceability verify
--evidence` remain CI-owned.

## 10. Offline Render Surface

The capture page (§1.2) draws one authoring view from an in-memory payload. It
reuses the editor's own drawing and theme and adds no second renderer, no
service access and no mutation behaviour.

### 10.1 Shared surface, separate hosts

`src/components/MapSurface.vue` owns every painted map element: the dot-field
background, the terrain preview raster, authored and derived shapes, links
(bent roads, curved interior connections, the dashed exterior link) and marks
(nodes, gate glyphs, locations, sites, fords, passes, control-point handles and
the room/exterior cards), with every label drawn through text interpolation.
It owns no camera, no selection and no chrome.

`src/components/MapCanvas.vue` stays the interactive host: it measures the
frame, fits the camera, pans and zooms, runs pointer and keyboard interaction,
draws drag drafts, and renders the tool pill, zoom pill, north arrow, scale bar
and coordinate frame. `src/capture.js` with
`src/components/CaptureApp.vue` is the offline host: an exact pixel frame, an
empty selection, no mutation handlers, no chrome and no workbench state.

### 10.2 Capture request and coordinate frames

`window.renderMapCapture({world, partition, view, map_id, width, height,
bounds, hidden_layers})` resolves `{bounds, units, axes}` after the local font
faces, the terrain raster and the laid-out paint are complete, and rejects with
the underlying error otherwise (also left on `window.__mapCaptureState`). A
partial render is never reported as ready.

| `view` | Scene coordinates | `units` | `axes` | Boundary conversion |
| --- | --- | --- | --- | --- |
| `continent` | metres | `km` | `{x: "east", y: "north"}` | CLI kilometres ×1000; reported bounds ÷1000 |
| `settlement` | metres | `m` | `{x: "east", y: "north"}` | none |
| `interior` | north-positive layout units | `layout` | `{x: "right", y: "down"}` | CLI `[minX,minY,maxX,maxY]` → scene `[minX,-maxY,maxX,-minY]`; reported back in the same reverse order |

`bounds` selects an explicit region in the CLI's frame; `null` fits the whole
map. The scene boundary conversions and the camera arithmetic live in
`src/lib/capture.js` and are pure, so the same rules can be checked without a
browser.

**Explicit region.** The requested rectangle keeps its centre and is grown on
its narrower axis to the output aspect ratio, then mapped to the image edge
with one uniform scale. Nothing is clamped, recentred or margin-padded:
`[0,0,10,20]` kilometres at 200×100 pixels reports `[-15,0,25,20]`, and
interior `[1,2,5,8]` at 100×100 reports `[0,2,6,8]`. A region with no objects,
or one that reaches beyond the map, behaves identically, and content outside
the region clips at the image edge.

**Full-map fit.** The reference extent comes from the complete unfiltered
scene: every authored point, every link vertex (authored road bends included),
every mark anchor and the terrain raster corners. Because cards, glyphs and
labels are pixel-sized, the fit then converges on what is actually painted —
measured from the browser after the local fonts load — growing the extent
monotonically for a bounded number of iterations (at most eight, settling
below 0.5 % growth). The result keeps every painted card and label inside the
image at a 1280×960 output; positive but tiny output sizes are still accepted,
scaled uniformly, without an undocumented minimum size and without promising
readable detail.

The measured painted box at the final camera decides success, not the
convergence flag alone: a size too small to hold the cards and labels the map
must show is refused with an explicit error instead of resolving a clipped
image, and the caller can ask for explicit bounds (which clip by design) or a
larger size. One page renders one image at a time; an overlapping call is
refused rather than sharing the surface with a render in flight.

Readiness re-reads `document.fonts.ready` after forcing style and layout for
the newly inserted text — the promise is already resolved until a layout
starts the face loads — repeats that (bounded) while any face is still
loading, then rejects if any local face ended in the error state. A capture
that introduces a family, weight or unicode-range subset the previous one did
not use therefore still waits for it.

Layer hiding never enters the camera: the fit is computed on the unfiltered
scene, so the camera, the reported bounds and the background are identical
whatever the caller hides.

### 10.3 Layer ownership

Every layer defaults to on for a capture, independently of the editor's stored
preferences and without writing or reading them.

| `view` | Geometry layers | Labels |
| --- | --- | --- |
| `continent` | `terrain` (mainland, terrain/passability raster, forest edge), `water` (waterways), `ridge` (ridge walls, passes, fords), `locations` (locations and reserved harbour sites), `footprint` (settlement footprints), `partition` (derived national borders and district outlines) | `labels` |
| `settlement` | `nodes` (node marks including gate glyphs), `roads` (authored directed bent links) | `labels` |
| `interior` | `rooms` (room cards), `connections` (within-interior links and their direction chevrons), `exterior` (the doorway card and its dashed link) | `labels` |

Hiding a geometry layer removes that layer's drawables together with their own
labels; `labels` removes text only, so cards, glyphs and direction indicators
stay. `nodes`/`rooms` and `roads`/`connections` are independent in both
directions. Hiding every applicable layer leaves the normal background (the
dot field for the metric views, the page gradient for an interior) at the same
camera.

### 10.4 Verification

Focused runs, from the repository root (build both outputs first, §1 and
§1.2):

```console
cd tools/map-editor/frontend
node --test tests/capture.test.mjs          # frames, aspect expansion, layers
node scripts/import-boundary.mjs            # the §5 allowlist, capture output excluded
pnpm run build && pnpm run build:capture     # editor and capture bundles
cd ../../..
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_capture_surface
```

`web/tests/browser/test_map_capture_surface.py` opens the built page from
`file://` with every HTTP and HTTPS request aborted. It renders the synthetic
workspace's three views, asserts the exact reported bounds and the projected
mark positions for a requested region, checks that measured labels and cards
lie inside the image, walks every view's layers (geometry alone, labels alone,
everything hidden at an unchanged camera), confirms authored hostile text and
URL-shaped names stay inert, proves a missing script never reports readiness,
holds readiness behind a deliberately delayed font file, waits for a face a
later capture introduces, and refuses an automatic fit that cannot hold the
surface. `MapSurfaceEditorSmokeBrowserTest` in the same module drives the
extracted surface through the interactive host: a click selects one mark, a
pointer drag pans by exactly the pointer travel without writing anything, the
wheel scales the surface by one uniform factor about one anchor and the
opposite wheel restores it, and one node drag is exactly one `move_nodes`
command that changes only the settlement document.

### 10.5 Human review record

Reviewed 2026-10-29 against the synthetic workspace (its place names, one
river with a ford, one ridge pass, two settlement nodes with two directed
roads, two interior rooms with a two-way connection and an exterior card),
rendered by the commands above and captured per view at 1280×960:

- **Continent**: map-only composition with no header, navigation, inspector,
  tools, zoom controls, frame text, badge, selection ring or handle; the
  mainland boundary, forest edge, river, ford, ridge walls and terrain preview
  raster read in the editor's own colours; 合成城, 合成荒野, 隘口 1（4–5）and
  `synthetic_river · 渡口 1` are legible at the 16 px floor with no clipped or
  substituted glyphs.
- **Settlement**: dot-field background with the gate glyph, the yard node and
  both bent roads; `Gate` and `Yard` sit fully inside the image with visible
  margin, and no direction chevron appears without a selection (unchanged from
  the editor).
- **Interior**: three cards (the dashed exterior card naming the other map and
  node, 前廳/front, 後室/back), two curved arrows with one chevron each and the
  `in ⇄ out` connection text; 前廳 and 後室 render from the local Traditional
  Chinese faces without clipping.
- **Explicit region** `[0,0,10,20]` kilometres at 200×100: the image is exactly
  the requested extent (reported `[-15,0,25,20]`) and content beyond it clips
  at the edge, as intended for a regional capture.
