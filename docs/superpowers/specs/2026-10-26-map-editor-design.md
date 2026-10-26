# Standalone Developer Map Editor Design

**Date:** 2026-10-26
**Status:** Design decisions approved in conversation; written-spec review pending.
**Scope:** All authored static maps, a standalone graphical editor, shared map libraries, and file-based collaboration with an external AI executor.
**Implementation status:** Not implemented by this document.

The editor edits the same YAML sources that the game consumes. It runs from the same repository in an independent dependency environment, without Evennia, Django, a game server, or a game database. Developers alternate between graphical editing and an external OMP session; there is one writer at a time.

The companion [frontend requirements](2026-10-26-map-editor-frontend-requirements.md) defines the contract for a subsequent visual-design specialist. It does not prescribe a visual layout or theme.

## 1. Goals and exclusions

| Goal | Required outcome |
| --- | --- |
| Complete static-map coverage | Author continental geography, geographic locations, settlement graphs, permanent interiors, and their entrances. |
| Manual graphical editing | Construct and inspect maps with direct manipulation and equivalent explicit controls. |
| External AI collaboration | External OMP reads and writes the same workspace files; the visible preview follows those files. |
| Independent execution | Install and run the editor without the game framework, database, services, or frontend application shell. |
| Shared responsibility boundaries | One map model and one implementation of map rules; reusable frontend drawing foundations; consumer-specific behavior stays outside the libraries. |
| Simple ownership | Autosave completed manual operations, flush before handoff, and reread after an AI turn; no merge workflow. |

Excluded are embedded AI/chat/code editors, model configuration, AI-process management, concurrent collaborative authoring, automatic merging, diff-review UI, Git UI or automatic commits, gameplay simulation, database repair, and editing NPC dialogue, shops, inventory, quests, or other non-map content. Generated runtime instances and their promotion/TTL behavior remain game-owned.

Coverage includes geographic locations that currently have no authored settlement or interior map. Displaying such a location does not fabricate its rooms, dungeon floors, or procedural instance content.

## 2. Architectural amendment and alternatives

This design explicitly amends D9 of the [engine design](2026-07-29-ai-mud-engine-design.md) for authored static-map data only. Those declarations move from Python into YAML; their consumers receive validated immutable values. Other lore retains its existing ownership and source formats. The deterministic single-writer boundary is unchanged. Only the existing game subsystem owners apply persistent game state.

Approval authorizes the planned source-format cutover. It does not assert that the current Python declarations or game consumers have already changed.

Three alternatives were considered:

| Approach | Consequence | Decision |
| --- | --- | --- |
| Shared YAML plus pure map core | Direct common source, safe data parsing, reusable validation and algorithms; requires a complete source/caller cutover. | Selected. YAML supports readable multiline prose and authored comments. |
| Restricted Python declaration editing | Smaller source-format change, but a syntax-aware writer and restrictions on expressions become part of the editor contract. | Rejected. |
| YAML generating Python declarations | Retains more of the game's loading path but adds generated source and stale-output checks. | Rejected. No generated Python map files. |

The editor uses a local service and browser rather than a packaged desktop shell. The frontend uses Vue 3 and Vite to reuse the project's existing ecosystem without importing the game application.

## 3. Components and dependency direction

| Component | Responsibility | Forbidden dependencies |
| --- | --- | --- |
| `packages/map-core/`, Python package `elosern_map_core` | Authoring models, YAML codec, validation, coordinate transforms, sparse graphs/routes, deterministic terrain, and geography-generation inputs/algorithms. | Evennia, Django, game modules, HTTP, UI state, watchers, AI clients. |
| `packages/map-view/`, frontend package `@elosern/map-view` | Neutral coordinate projection, pan/zoom, geometry, and reusable glyph foundations. | Game stores, OOB actions, player knowledge, editor commands, application shells. |
| `tools/map-editor/` | Independent Python service, workspace file access, serialized saves, watching, handoff ownership, and editor-session history. | Game imports and database access. |
| `tools/map-editor/frontend/` | Separate Vue application, editing tools, navigation, inspection, diagnostics, and handoff UI. | Game client stores, command routing, or game shell styles. |
| Game-side adapters | Compose game-facing read-only registries, resolve game-only references, and call existing persistent map synchronization. | Editor service and editor-session state. |

These are planned ownership paths, not an instruction to create empty packages before their implementation work starts. Each package is introduced with its real consumers.

### 3.1 Python core

The core receives explicit documents or snapshots. Geometry and validation do not obtain their inputs through imported game registries or mutable module globals. Derived caches belong to an immutable input snapshot and cannot retain a prior world's values after a reload.

The core distinguishes a loadable `AuthoringWorld`, which may contain documented work-in-progress diagnostics, from a validated `RuntimeMapSnapshot`. Runtime snapshots cannot represent failed map or external-reference validation. A failed candidate leaves the previously published game registries unchanged.

The YAML codec retains source locations and round-trip document information alongside the typed authoring values. The editor's file-writing policy remains outside the core. Read-only source discovery follows the same documented file set for both consumers and has no import-time side effects.

Extract the existing sparse graph and terrain implementations rather than reimplement them. Game-specific `XYMap` adaptation, persistent objects, contrib providers, and object lookup remain in the game adapter. The core works with ordinary values and qualified authored references.

### 3.2 Frontend sharing

Extract neutral parts of `map_viewport.js`, geometry helpers, and glyph foundations. Share a shape's geometry where both consumers need it. Keep player-current, visibility, quest, travel-action, and editor-selection behavior in their respective hosts.

Do not import `AreaMapView` or `WorldMapView` wholesale into the editor, fake a current player node, or copy their algorithms into a second implementation. Existing game surfaces must be migrated to the extracted primitives in the same cutover. Application-specific styling uses host-provided theme hooks; the editor does not import the game's global shell CSS.

### 3.3 Independent installation

The editor has its own Python project metadata and locked dependency environment, with a local path dependency on `map-core`. Python commands use uv and the selected project's lockfile. The game also declares its dependency on that shared package. Installing the editor must not install the root game's dependency set transitively.

The service uses Starlette and Uvicorn, with `watchfiles` for workspace notifications. The core YAML codec uses `ruamel.yaml` for controlled comment-preserving round trips. These are explicit direct dependencies of their owning projects.

The frontend has an independent entry/build and locked pnpm dependencies. Its reusable map package is consumed locally by both applications. The service serves the editor build; it does not require the game frontend bundle, Node at runtime, or a game web route.

NumPy/SciPy are optional generation dependencies of the core. The editor installs that generation extra independently to support partition rebuilding. Ordinary runtime snapshot loading, geometry, routing, artifact decoding, and freshness checks do not import those heavy generation modules.

## 4. Sources, identity, and units

### 4.1 Source organization

| Source | Owned data |
| --- | --- |
| `content/maps/continent.yaml` | Wilderness frame, mainland boundary, terrain-region declarations and descriptions, classifier parameters, waterways, forest boundaries, ridge/pass/ford declarations, and reserved geographic sites. |
| `content/maps/locations.yaml` | Static geographic location identities, map-facing kinds/names/descriptions, and geographic cells. Local-map associations are derived from map-owned location references. |
| `content/maps/districts.yaml` | District identities/names, kinds, region membership, and stable landmark references. |
| `content/maps/settlements/<map_id>.yaml` | Settlement/map identity and location reference, local-frame binding, footprint and wilderness entrances, room nodes/prototypes, roads, map options, and map-owned scene references. |
| `content/maps/interiors/<interior_id>.yaml` | Permanent room identities, names/descriptions, internal connections, scene references, and exterior entrance relationships. |
| `content/map-editor-layouts/<interior_id>.yaml` | Editor-only room layout positions. Excluded from gameplay geometry and runtime snapshots. |
| `world/maps/data/district_partition.json` | Existing generated, read-only district partition artifact. Never an alternative editable map source. |
| `content/map-reference-context.json` | Generated, read-only index of external identifiers and incoming static references. Not a map source or game authority. |

Source discovery scans the supported paths in sorted order. Adding a local map does not require adding a Python import or changing a hard-coded map roster. Document kind, schema version, and file-stem identity must agree. Unknown document kinds and duplicate identities are errors.

Every world-data document has schema version `1`. A machine-readable schema is owned by the core and exposed to the editor; the frontend must not maintain a competing domain schema. All supported nested fields, including prototype fields, are explicitly described by that schema. Unknown fields and unsupported versions block writes rather than being silently discarded.

### 4.2 Qualified references

World objects use stable English-slug identifiers, independent of Chinese display names and coordinate bindings. New authored identifiers use lower-case ASCII letters, digits, and underscores, beginning with a letter. The qualified reference distinguishes its domain and map, such as a settlement plus node or an interior plus room.

A directed road retains its ordered endpoint identity; two-way streets contain two directed road entries in the same settlement document. Direction and optional bend points are authored fields. An entrance relationship owns both endpoints and both directional labels where applicable. It is stored once in its owning settlement or interior document, without a mirrored reverse record elsewhere.

A settlement owns its geographic location reference. Location-to-local-map navigation is derived from those references, with no reverse list authored in the location document. Creating a local map for an existing location therefore writes only the new settlement document.

Existing identities are retained during migration. Existing service-place keys that already identify permanent rooms remain the joins for those rooms; do not create replacement identities just because the data moves to YAML. Standalone interiors do not require a service/economy declaration.

The editor does not rename established IDs or cascade-delete external data. It supports creating new IDs, editing ordinary attributes, and deleting an object after its references are explicitly removed.

Coordinates remain spatial values. Coordinate-based game wire identities, map-knowledge IDs, and scene addresses are derived at their existing game boundaries from the current binding. They do not become the authored reference authority.

### 4.3 Coordinate contract

| Domain | Stored coordinate meaning |
| --- | --- |
| Wilderness | Integer one-kilometre cell indices within the declared frame. A cell is an area; its representative point is its centre. |
| Continental geometry | Explicitly named kilometre or metre fields; no unlabelled mixing with cell indices. |
| Settlement | Integer metres in the settlement's local east/north frame. Logical map/layer identity is not elevation. |
| Permanent interior | No physical coordinates. Editor-layout positions are presentation-only values. |

Preserve the current cell-centre offset and cross-layer transform. World metres equal wilderness anchor-cell centre plus local metres minus the local anchor binding. Settlement rendering uses uniform physical scale. Moving a node does not change its slug, infer a new compass exit, or move its interior-layout preferences into physical geometry.

### 4.4 Safe YAML and round trips

Use the YAML 1.2 core scalar rules with a restricted data-only policy. Reject duplicate keys before constructing mappings, custom tags, anchors/aliases, merge keys, timestamp values, unsupported scalar/object types, non-finite numbers, and unknown fields. Integer fields exclude booleans, numeric strings, and fractional values. Strings remain strings; a parser must not silently stringify a number into a name or ID.

Descriptions use readable multiline strings. Footprint masks are strings whose `#` and `.` values round-trip unchanged. The writer must not emit constructs that the loader rejects.

Preserve comments attached to retained stable-ID objects and unmodified document sections. Whitespace and collection formatting may be normalized. Removed-object comments may be removed with that object; exact byte-for-byte formatting preservation is not a requirement. Parsing an unsupported document never authorizes rewriting it into a smaller supported subset.

## 5. Migration ownership inventory

| Current declaration or responsibility | Planned owner and cutover |
| --- | --- |
| Settlement `PROTOTYPES`, `NODE_IDS`, `ROADS`, `XYMAP_DATA` | Settlement YAML and core assembly; remove the old authored Python tables and roster imports. Preserve prototype semantics and map options. |
| `SparseNode`, `SparseRoad`, sparse validation/routing | Core; keep game/contrib adaptation outside it. Migrate all callsites rather than retain re-export shims. |
| Wilderness geometry/constants and deterministic classification in `wilderness_regions.py` / `wilderness_provider.py` | Editable declarations in continent YAML; calculations in core; contrib room/provider integration remains game-side. |
| Anchor geographic cells and local-frame/placement bindings | Location/settlement YAML with qualified node references; remove competing Python placement tables. |
| Anchor map identity, map-facing name/kind/description | Location YAML. Game lore composition joins non-spatial records by the existing identity. |
| Political affiliation, population, floor-count lore, nation/economy/NPC metadata | Existing Python lore owners; not inferred from map geometry or migrated as map fields. |
| Wilderness footprint masks, entry gates, starting-room city entry | Settlement-owned YAML relationships; resolve current coordinates in game adapters. |
| Place room prose, exterior node, doorways, permanent room identity | Interior YAML; service/NPC/economy records retain a stable interior-room reference. Remove duplicate room/exterior/doorway fields from those records. |
| Special permanent interior-to-interior links | Explicit interior-owned relationships; remove equivalent hard-coded topology from bootstrap. |
| Scene/archetype associations for map nodes and rooms | YAML references by stable object identity; actual scene/art catalogs stay with their existing owners. |
| District declarations and landmarks | District YAML; settlement landmarks refer to stable nodes, not coordinate strings. |
| Offline partition input assembly and algorithm | Core generation extra; game-specific production-import assembly is replaced by snapshot inputs. |
| Partition artifact consumption | Lightweight core decoding plus game adapter; keep the existing artifact path. |
| Static game declarations that target map objects | Qualified authored references; adapters derive existing runtime locator/address forms. Include quests, service places, gates, districts, and art associations. |
| Player knowledge, live occupants, home/inbound object references | Existing game subsystem owners. Preserve their current safety and transactional synchronization behavior. |

`map_data.py`'s import-time global assembly must be replaced by explicit candidate loading and immutable publication. The game may continue exposing composed read-only lore registries where those are real consumers' domain contracts; they must contain loaded values rather than duplicate authored declarations.

Do not change authored geography, balance, names, prose, road topology, or population as an incidental result of conversion. Do not introduce compatibility aliases, release migrations, or generated Python source. Update all affected commands, presenters, source-contract tests, traceability claims, and developer documentation with the cutover.

## 6. Validation boundaries and external references

### 6.1 Acceptance gates

| Gate | Examples | Consequence |
| --- | --- | --- |
| Authoring load/save structure | Supported YAML/schema; required typed fields; unique IDs/coordinates; known map endpoints; no self-loop or duplicate ordered road; valid direction vocabulary; no duplicate outgoing direction. | Failure blocks structured editing/writes. External malformed candidates retain a stale prior preview until corrected externally. |
| Saveable map work-in-progress | Unreachable landmark, blocked approach, unfinished connectivity, terrain inconsistency, or stale required generated data. | Save and manual repair are allowed; show diagnostics and withhold game readiness. An empty newly authored graph is unfinished, not a valid playable map. |
| External static validation | Known scene/art/lore references and non-map incoming dependencies, checked with a current reference context. | Report valid/invalid/unavailable separately. Invalid or unavailable results cannot establish complete game readiness. |
| Game adoption | Complete map validation, authoritative game-side external checks, and required artifact freshness. | Publish the entire runtime snapshot or reject the candidate without registry or persistent-state changes. |

An explicit return from AI requires authoring-load success, not game readiness. A loadable world with a stale partition or inaccessible landmark can return to manual mode for repair. A YAML/schema/structural failure requires correction through the external file editor/OMP; this editor does not add a source-code editing surface.

The same core rules establish map diagnostics and game rejection. Consumers choose the relevant acceptance gate; they must not duplicate or weaken the rules. A geometric display can show saveable diagnostics, but runtime route/provider objects are created only from the inputs their invariants permit.

### 6.2 Read-only external reference context

A game-side development exporter reads authoritative static declarations and writes the reference index. It records external identifier sets, incoming references to qualified map objects, source paths for diagnostics, schema/exporter versions, and a dependency fingerprint. It must not query or serialize live database state.

The index includes relevant static quest, service, scene/art, and lore dependencies. Its fingerprint covers the external source closure and source-set membership, including exporter/schema changes and added/removed files. It excludes editable map geometry. Moving a stable node does not require regenerating an external index solely because its coordinates changed. Static consumers must declare stable targets before deriving coordinate-based runtime forms.

The editor checks freshness through file paths/hashes without importing game modules. Missing files, changed source membership, incompatible versions, or mismatched fingerprints make the context unavailable. The index is reproducible and committed with changes to its inputs; a game-side check rejects stale output in CI.

A current index allows the editor to identify incoming static references. Deletion requires no map-internal incoming reference and a current external context with no incoming external static reference. Without that context, deletion is conservatively disabled; adding, moving, inspecting, or editing other fields remains possible. Invalid external outgoing references can be saved as diagnosed work-in-progress.

The editor never claims to validate live save-game dependents. Existing game synchronization must continue refusing unsafe deletion of occupied or referenced persistent rooms. Game adoption uses the actual registries, not the exported index as an authority.

## 7. Workspace, commands, and autosave

### 7.1 One document per operation

Each completed manual command changes exactly one source document, or one editor-layout document. A bidirectional road command edits both directed entries in its settlement document. An entrance's endpoints and return labels live in one relationship record. Creating a location and subsequently creating its local map are separate complete authoring commands.

Multi-selection mutation is restricted to one owning document. Cross-document browsing and context copying are allowed; cross-document batch mutations, implicit cascading deletes, and workspace-wide transformations are excluded. Resolve cross-file references through IDs rather than coordinate rewrites.

This ownership avoids claiming multi-file filesystem atomicity. Each operation can be validated and atomically replaced as one file. A sequence of successful operations remains saved if a later operation fails; do not report the sequence as one atomic action or undo it implicitly.

### 7.2 Save semantics

A command commits after drag release, explicit field confirmation/blur, or completion of an add/connect/delete operation. A drag is one undoable operation. Text input does not write every keystroke; incomplete fields stay as uncommitted drafts. Save and undo/redo requests are serialized by the service.

For an admitted command, construct its complete candidate, apply the authoring gate, serialize to a sibling temporary file, flush it, and atomically replace the target. Acknowledge saved state only after the replacement succeeds. A failure before replacement leaves the prior target intact; uncertain durability after replacement pauses mutations and requires rereading rather than blind resubmission.

The service verifies the expected document fingerprint immediately before replacing it. It also checks the current service-session/turn generation. A mismatch rejects the stale command and pauses manual writing. This is an overwrite guard, not a concurrent-writer protocol; external writers must honor the turn-taking agreement.

The UI separates field drafts, accepted/in-flight commands, saved state, diagnosed game-readiness failures, and failed or uncertain writes. A visible geometric preview is not proof of persistence. Save failures retain the last saved baseline and pending intent for inspection/correction; they do not silently roll forward or launch automatic retries.

Undo/redo applies to the current uninterrupted manual segment. Each undo or redo is another validated, autosaved single-document operation. Clear the history on AI handoff or adoption of externally changed files. A browser refresh does not restore unsaved drafts or undo history.

## 8. Handoff, watching, and recovery

| State | Permitted behavior | Exit condition |
| --- | --- | --- |
| Startup/reconnect inspection | Browse a successfully loaded snapshot; no mutations. | Fresh disk load and explicit resume of manual control. |
| Manual | Edit and autosave using current session/turn/document state. | Handoff, unexpected external change, or a service/save failure. |
| Handoff pending | Resolve active drafts, close admission of new manual commands, drain admitted saves, then flush. | Successful flush grants the external turn; failure does not grant it. |
| External AI turn | Browse/select/inspect/copy context; external OMP writes workspace YAML. | User stops external writes and explicitly requests return. |
| Return pending | Reread current disk files and run the authoring gate; clear old history. | Loadable authoring world enables a new manual turn; malformed data remains read-only. |
| Paused/stale | Inspect last preview with persistent stale/error status. | Explicit reload/resume after the cause is resolved. |

The service owns mutation permission. Every mutation route, including undo, keyboard deletion, paste, layout edits, and regeneration output publication, obeys the state. A restored tab cannot restore write permission locally. A service restart creates a new session generation and begins read-only; it does not assume an external AI has stopped.

The user starts/stops OMP outside the editor. Handoff cannot establish or enforce a lock on an uncooperative external process. The UI explains this assumption and never labels OMP as running or finished based solely on a file notification.

Watch source directories for create, replace, rename, and delete, not only modifications to an already-open file. Coalesce notifications after a short settle interval and load a coherent candidate; do not promise that a debounce makes a multi-file AI edit transactional. Publish a new preview only after authoring-load success. Show map-semantic diagnostics for loadable work-in-progress.

When loading fails, retain the last previewable snapshot and its viewport, mark it stale persistently, and identify the offending file/field/line when available. With no prior preview, show an explicit unavailable-preview state. Never rewrite external files to match a retained snapshot.

Unexpected external changes during manual authoring stop further writes. Require explicit reload and explain that uncommitted drafts/history will be discarded. Do not merge, compare versions in a diff UI, or silently replay pending commands after reconnect.

After an AI turn, the user confirms the external writer has stopped. The service rereads current disk contents; it does not serialize its old state as a purported final save. Semantically unfinished but loadable data can resume manual repair. File updates preserve map/view/selection by stable identity where possible; deleted selections are cleared with an explanation.

## 9. Derived geography and preview

The editor previews author-visible static geography, terrain/passability, settlement topology, and interior connections. It has no player knowledge filter, live position, quest progression, combat state, or movement-time simulation. Route and length checks use the core, not screen-space measurements.

Preserve existing derived national boundaries and district semantics. Do not introduce editable border polylines that compete with the terrain/river/ridge rules. Expose editable inputs and distinguish their derived output.

Extract snapshot-to-`PartitionInput` assembly together with the existing partition algorithm. Do not leave `production_input()` importing game providers or map knowledge from inside a nominally independent generator.

Partition regeneration is explicit and runs outside the request/event loop. Only one regeneration runs at a time. During a generation, block manual world-data mutations and AI handoff while retaining browsing; cancellation/failure leaves the last artifact unchanged. If an external write occurs, its source fingerprint invalidates the result. Publish output only if the captured input signature still matches, with an atomic artifact replacement.

Store a source-dependency signature and algorithm version in the artifact so freshness can be checked without rebuilding rasters or importing NumPy/SciPy. Source changes conservatively mark dependent output stale. An old partition may remain visible only when labelled as belonging to an older input; it must not be presented as current or game-ready. Do not regenerate on every pointer movement or ordinary game action.

## 10. Local service and API boundaries

Bind to loopback by default. Serve frontend assets locally with no CDN/runtime network dependency. Do not add accounts, remote deployment, or multiuser permissions to this local tool.

Use HTTP for snapshots, commands, diagnostics, handoff/resume, and explicit generation requests. Use a server-sent event stream for invalidation/status notifications; clients fetch the latest authoritative snapshot after invalidation or reconnect. Send complete replacement state as needed, without a patch/merge protocol.

The API exposes domain commands and canonical workspace document identities. It does not expose arbitrary file writes, shell execution, Python evaluation, or generic object mutation. Resolve writes beneath the configured workspace and allowlisted source/layout/artifact paths; reject traversal and symlinks escaping those roots. Scene references are identifiers, not instructions to fetch arbitrary URLs or assets.

Validate the expected host/origin and protect mutating requests with a launch-session token. Loopback binding alone does not authorize requests from unrelated web origins. Bound document/body sizes and reject unsupported YAML before expensive processing. Render authored prose as text, never executable markup.

Game-side adoption and synchronization retain the repository's existing observability contracts. The map core has no operational logging dependency, and the editor does not collect external AI conversations or model payloads.

## 11. Verification and acceptance

These are required future implementation checks, not claims that the editor or tests have been run for this design-only change.

| Boundary | Required proof |
| --- | --- |
| Independent execution | Install/run the editor and import its core in its own environment with Evennia and Django absent. Open the actual editor in a browser without the game running or a game database. |
| Source cutover | Load the current authored world from YAML with unchanged topology/prose/units; remove old data authorities and migrate all consumers. Use conversion comparison as temporary evidence, not permanent balance-count approval tables. |
| Geometry and topology | Synthetic cases establish unit conversion, cell centres, physical road lengths, direction preservation, valid/invalid references, routing and failure bounds. |
| Identity movement | Move a node and verify its gate, interior exterior-link, district landmark, static consumer references and art association still resolve to that same ID at the new coordinates. Exercise the game's committed room/exit reload and existing knowledge/reference preservation. |
| Interior ownership | Load a standalone non-service interior and an existing service interior; preserve the existing place/room join and avoid duplicate spawning. |
| Safe YAML | Reject duplicate keys/tags/aliases/unknown fields/versions and invalid scalar types; round-trip multiline prose, footprint masks, retained comments, and road geometry without semantic changes. |
| File safety | Inject save failures before replacement and test an obsolete session/turn/revision request. A failed or stale save cannot overwrite AI files or be labelled saved. |
| Handoff | Failed flush blocks handoff; AI mode disables all mutation routes; return reads disk rather than writing old memory. Semantic errors permit manual repair, structural failures remain read-only. |
| Watching/recovery | Exercise real file replacement, addition/deletion, malformed-then-corrected YAML, browser reconnection, and service restart. Observe last-good/stale labels and explicit resume behavior. |
| External reference context | Fresh index blocks a referenced deletion; missing/stale index blocks deletion and withholds external validation. Verify deterministic export/freshness against the real static source closure. |
| Partition | Regenerate from a core snapshot without game imports; a changed input cannot publish a stale result as current. Runtime freshness/decode works without generation dependencies. |
| Shared rendering | Exercise the existing game map and the editor with common primitives. Preserve game player/knowledge/action behavior without leaking it into authoring. |
| Frontend | Cover the companion brief's concrete interactions and error states with focused component checks and real browser smoke paths. Include keyboard/non-drag access and compact desktop use. |

Follow repository test-location, synthetic-data, shard, traceability, and focused-run conventions. Keep existing consumer-visible tests; replace tests that pin incidental source layout or duplicate authored values. Do not change player commands incidentally; an intentional command-surface change requires both command documentation pages and their contracts.

Before an implementation handoff, run the repository contract gate and relevant focused checks. CI retains ownership of full managed browser and complete traceability-evidence runs.

## 12. Delivery decomposition

This is an umbrella architecture and product contract covering the complete editor. It is too broad for one implementation change. Prepare dependent, one-workday OpenSpec changes after written-spec approval, with these responsibility boundaries:

| Workstream | Deliverable and dependency |
| --- | --- |
| Core and data cutover | Shared models/algorithms, all static YAML sources, complete game adapters/caller migration, authoritative reference exporter, and preserved game behavior. Split coherent source domains into dependent changes where necessary; no half-switched authority. |
| Reusable frontend foundations | Extract neutral rendering primitives and migrate current game surfaces; independent of editor-specific tools once the model contract is fixed. |
| Editor workspace | Independent installation/build, service security, source discovery, safe one-document saving, history, file watching, external-index consumption, and handoff/recovery. Depends on the core contract. |
| Domain editing | Continental/locations/districts, settlement roads/nodes, interior graphs, and cross-layer entrances. These can be separate complete changes sharing workspace/interaction contracts. |
| Generation and end-to-end acceptance | Shared partition input/generation integration, current-output proofs, full manual/AI-turn browser smoke, and final designer acceptance. |

Every approved capability remains required for the completed editor. Decomposition does not authorize presenting a limited map viewer or one-domain editor as the finished product. Detailed frontend layout is a subsequent designer deliverable governed by the companion brief. No implementation begins before the user reviews these written documents and the next planning step completes.

### 12.1 Created OpenSpec proposals

The proposal batch is complete. This inventory records planning artifacts, not implementation progress or authorization to apply them. Each link opens its proposal; the same change directory contains its design, tasks, worker contract, and applicable delta specs.

| ID | Proposal | Deliverable | Direct prerequisites |
| --- | --- | --- | --- |
| P01 | [map-core-sparse-geometry](../../../openspec/changes/map-core-sparse-geometry/proposal.md) | Independent sparse graphs, coordinates, and deterministic terrain. | None |
| P02 | [map-core-authoring-documents](../../../openspec/changes/map-core-authoring-documents/proposal.md) | Complete authoring schema, safe round-trip YAML, discovery, and validation gates. | P01 |
| P03 | [map-qualified-static-references](../../../openspec/changes/map-qualified-static-references/proposal.md) | Stable qualified references and complete static-consumer migration. | P01; `npc-title-authoring-removal` and its prerequisites |
| P04 | [map-geography-yaml-cutover](../../../openspec/changes/map-geography-yaml-cutover/proposal.md) | Continental declarations and all geographic locations in YAML. | P02 |
| P05 | [map-settlement-yaml-cutover](../../../openspec/changes/map-settlement-yaml-cutover/proposal.md) | All settlement graphs, prototypes, bindings, footprints, and wilderness entries in YAML. | P03, P04 |
| P06 | [map-district-yaml-cutover](../../../openspec/changes/map-district-yaml-cutover/proposal.md) | District declarations and stable landmark references in YAML. | P05 |
| P07 | [map-partition-core-generation](../../../openspec/changes/map-partition-core-generation/proposal.md) | Shared partition algorithm, snapshot input assembly, and lightweight artifact freshness checks. | P06 |
| P08 | [map-interior-runtime-cutover](../../../openspec/changes/map-interior-runtime-cutover/proposal.md) | All permanent interiors and complete immutable game snapshot publication. | P06, P07 |
| P09 | [map-reference-context-export](../../../openspec/changes/map-reference-context-export/proposal.md) | Authoritative static-reference export and independent freshness checking. | P08 |
| P10 | [map-view-shared-foundations](../../../openspec/changes/map-view-shared-foundations/proposal.md) | Neutral frontend map primitives and existing game-surface migration. | None |
| P11 | [map-editor-standalone-service](../../../openspec/changes/map-editor-standalone-service/proposal.md) | Independent environment/build, secure local service, and browser workspace. | P08, P09, P10 |
| P12 | [map-editor-document-commands](../../../openspec/changes/map-editor-document-commands/proposal.md) | Guarded single-document persistence, autosave, and undo/redo. | P11 |
| P13 | [map-editor-turn-recovery](../../../openspec/changes/map-editor-turn-recovery/proposal.md) | External AI handoff, file watching, stale previews, and recovery. | P12 |
| P14 | [map-editor-interaction-shell](../../../openspec/changes/map-editor-interaction-shell/proposal.md) | Navigation, inspection, diagnostics, accessibility, and copy-only AI context. | P13 |
| P15 | [map-editor-continent-tools](../../../openspec/changes/map-editor-continent-tools/proposal.md) | Continental geometry, locations, districts, footprints, and bindings. | P14 |
| P16 | [map-editor-settlement-tools](../../../openspec/changes/map-editor-settlement-tools/proposal.md) | Nodes/prototypes, directed roads, bends, and physical route inspection. | P14 |
| P17 | [map-editor-interior-tools](../../../openspec/changes/map-editor-interior-tools/proposal.md) | Coordinate-free rooms/connections and separate editor layouts. | P14 |
| P18 | [map-editor-entrance-tools](../../../openspec/changes/map-editor-entrance-tools/proposal.md) | Cross-layer relationships, navigation, and reference-safe deletion. | P15, P16, P17 |
| P19 | [map-editor-partition-jobs](../../../openspec/changes/map-editor-partition-jobs/proposal.md) | Explicit background regeneration, cancellation, and guarded artifact publication. | P07, P18 |
| P20 | [map-editor-integrated-acceptance](../../../openspec/changes/map-editor-integrated-acceptance/proposal.md) | Complete independent browser/filesystem and committed game-consumer acceptance. | P19, transitively the whole batch |

P20 uses `skip_specs: true` because it supplies evidence for existing behavior rather than adding another product requirement. The [batch plan](../../../openspec/changes/map-core-sparse-geometry/batch-plan.md) contains the detailed dependency/conflict matrix, existing-proposal overlaps, source-authority timeline, and acceptance ownership. The [canonical worker contract](../../../openspec/changes/map-core-sparse-geometry/worker-contract.md) defines cross-slice interfaces and caller inventories.

### 12.2 Parallel implementation batches

This is a conservative schedule derived from the proposal dependencies and shared-file conflicts. A batch starts after its prerequisites have landed in the integration baseline. Parallel workers use separate feature branches/worktrees; independent tasks do not authorize simultaneous integration of conflicting files.

| Batch | Changes eligible to run together | Entry conditions and serialization |
| --- | --- | --- |
| B01 | P01 + P10 | No semantic dependency between Python core extraction and frontend primitives. Serialize shared metadata/documentation integration and overlapping game-view edits with `webclient-immutable-adoption`. |
| B02 | P02 | P01 complete. Keep core schema/model ownership serial with later source migrations. |
| B03 | P03 | P01 and `npc-title-authoring-removal` complete. P03 shares core and game-adapter surfaces with source migrations, so this schedule keeps it separate from P02/P04. |
| B04 | P04 | P02 complete; P03 already landed under this conservative schedule. |
| B05 | P05 | P03 + P04 complete. |
| B06 | P06 | P05 complete. |
| B07 | P07 | P06 complete; serialize partition input, decoder, and artifact edits. |
| B08 | P08 | P06 + P07 complete; preserve the final NPC service/identity contracts. |
| B09 | P09 | P08 complete; export against final authoritative static declarations. |
| B10 | P11 | P08 + P09 + P10 complete; approved frontend design and proposal reconciliation required before editor UI implementation. |
| B11 | P12 | P11 complete; one persistence/history owner. |
| B12 | P13 | P12 complete; one watcher and turn state machine. |
| B13 | P14 | P13 complete; implement the approved interaction design. |
| B14 | P15 + P16 + P17 | P14 complete and shared shell/schema/selector interfaces fixed. Separate domain modules; serialize shared files, dependency locks, manifests, and footprint/settlement integration. If work requires shared implementation changes, land those first or sequence the affected workers. |
| B15 | P18 | P15 + P16 + P17 complete; extends their relationship and selector modules. |
| B16 | P19 | P07 + P18 complete; extends the existing mutation state machine. |
| B17 | P20 | All preceding changes complete with their own focused evidence; integrated acceptance cannot replace it. |

The batches permit parallel implementation only where the listed boundaries remain independent. Shared shard manifests, traceability records, locks, and documentation always have one integration owner. Existing movement/publication/NPC proposals retain the serialization rules in the batch plan. Recheck current proposal phases before scheduling; a proposed external prerequisite must land first, while an archived prerequisite is consumed through its merged contract.

### 12.3 Frontend specialist coordination

Frontend visual design remains unassigned implementation work. The specialist receives the companion frontend requirements and this architecture, then produces annotated screens, interaction/state flows, component specifications, and keyboard/focus behavior for user review. The specialist does not need to create duplicate functional OpenSpec proposals.

Design work can proceed alongside B01-B09. Before B10 or any earlier editor-specific UI implementation, obtain user approval of the specialist's design and reconcile affected existing proposals, particularly P11-P19 and P20's acceptance evidence. Backend/API changes discovered during design must be reflected in their owning proposals before apply. P10 may proceed independently because it extracts neutral geometry and preserves existing game behavior without deciding the editor layout.

This coordination gate is recorded here as the intended scheduling constraint. The existing proposal batch describes specialist design as an apply-time deliverable; its affected artifacts must be updated to express the pre-implementation gate before those UI changes are applied. This document update does not claim that reconciliation has already occurred.
