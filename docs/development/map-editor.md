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
the manual segment (§3). The service follows the workspace files
continuously (§3.4) and the page recovers from stale previews, disconnects
and restarts without a handoff (§3.5). The workbench shell (§3.6) provides
navigation, search, selection, inspection, diagnostics, the copy-only OMP
context and the keyboard contract. Further domain commands arrive in later
slices (§3.7).

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
uv run --locked python -m unittest tests.test_map_editor_file_following
uv run --locked python -m unittest tests.test_map_editor_watching
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_standalone
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_persistence
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_file_following
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_map_editor_accessibility
```

The accessibility module runs its keyboard workflow in Chromium and Firefox
(`uv run --locked playwright install chromium firefox`).

The two repository-level checks start the service as a child process from
`tools/map-editor/.venv` (synchronised with
`uv sync --locked --project tools/map-editor`) with a scrubbed environment and
an empty `PATH`, so neither the game's packages nor Node can be reached.

## 2. API

| Route | Purpose |
| --- | --- |
| `GET /api/workspace` | One complete replacement of the authoritative state: `session_generation`, `snapshot_revision`, `write_pause`, `preview_state` (`current`/`stale`/`unavailable`), `snapshot_read_at`, `checked_at`, `schema` (the core schema), `documents` (path, kind, id, fingerprint, values), `world` (the core-derived projection), `diagnostics`, `candidate_diagnostics` (the failing read while stale or unavailable), `external_context_status`, `partition_status`, `history`, `pending_intent`, `uncertain_outcome`, `external_change` (`sequence`, `at` and the changed `documents` of the last adopted external change; §3.4) and `following` (`active`, reconciled `batches`, the last watcher `error`). `write_pause` is only the explicit pause of an uncertain publication; the stale or unavailable preview is the separate `preview_state`. |
| `GET /api/events` | Server-sent events: `status` on connect and `invalidate` after a published change, each carrying only `session_generation`, `snapshot_revision` and `preview_state`. A client refetches `/api/workspace` on every invalidation and on a reconnect status that names another session or revision. Nothing is patched or merged. |
| `POST /api/reload` | Authenticated explicit reread of the current disk files. A loadable read publishes and is the only way to resolve an uncertain publication. A structural failure keeps the last preview and marks it `stale`. An identical read publishes nothing. It never writes a file. |
| `POST /api/commands/<name>` | One named single-document command (`move_interior_layout`, `remove_interior_layout`) or `undo`/`redo` of the current segment (see §3). |
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
source or layout change it did not write, and when a read fails to load
(§3.4). Changes to the generated artifacts do not count. A service restart is a new
session with no history. Commands are never replayed after a reconnect.

Only one owning document is mutated per operation. A multi-selection (§3.6)
is inspect/copy only in this slice; a selection that spans documents states
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
  adopts it. Once no draft is left and no command is in flight, the held
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
  no delete command exists yet for that object. Map-internal incoming
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

This shell deliberately ships no domain command beyond interior layout moves.
The batch's later changes must deliver, through their own domain modules:

| Change | Delivers on this shell |
| --- | --- |
| `map-editor-continent-tools` | Continent tools (control points A, waterway, ridge, location, footprint grid), drawables for the ridge and footprint layers, location delete |
| `map-editor-settlement-tools` | Node N, road R (建立雙向), bends, node fields, multi-selection edits, node delete |
| `map-editor-interior-tools` | Room N, connection R, 自動排列, room fields, room delete |
| `map-editor-entrance-tools` | Entrance E, 前往另一端, 更換端點… with the qualified-object selector (`[data-object-selector]`) |
| `map-editor-partition-jobs` | Partition drawables, and 分區 chip regenerate/cancel |

Each registers its tools in `TOOLS` (`src/lib/workbench.js`), sends its own
named single-document command, and lets the service's refusal (for example
`deletion_refused`) replace the shell's explanatory delete block.
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
