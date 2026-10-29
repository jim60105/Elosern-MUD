# Design

## Context

See `proposal.md` for motivation and `specs/map-capture-snapshots/spec.md` for behavior. The approved capture design and engine architecture are `docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md` and `2026-07-29-ai-mud-engine-design.md` in the same directory. The loader remains developer tooling over the bounded static-map YAML source, with no game lifecycle or persistent-state authority.

Observed implementation anchors:

- `elosern_map_editor.snapshot.read_sources()` uses `ConfinedWorkspace` discovery/read limits and records raw-byte fingerprints. `_read_layout_sources()` and `_parse_layouts()` use the core restricted YAML parser.
- `read_workspace()` loads world/layouts, external context and partition statuses, diagnoses the world and calls `_project()`. It does not instantiate the service. However it sets `loaded=True` after layout parse diagnostics and obtains partition metadata unconditionally; directly trusting `loaded` would let malformed layouts become fallback placement in capture.
- `_project()` supplies the existing JSON-ready domain projection and terrain preview. `WorkspaceRead.authoring` retains the core world with `partition_signature`.
- `packages/map-core/elosern_map_core/partition_codec.py` owns metadata, freshness and full artifact decoding; `world/maps/district_partition.py` binds a game-world land predicate and must not be imported here.
- Existing fixtures in `tools/map-editor/tests/synthetic_workspace.py` provide isolated world sources, bent-road/interior builders, generated artifact helpers and tree digests. Top-level `tests/test_map_editor_service.py` demonstrates locked independent-environment subprocess evidence and discoverable traceability tests.

## Goals / Non-Goals

**Goals:** A completed reusable one-shot loader for capture, testable with no frontend or service. Reuse existing read/projection behavior and treat layout structure failures more strictly for this consumer.

**Non-Goals:** Browser/CLI/encoding, watcher retries, stale-preview retention, automatic generation, game startup, a map-list API, writes, arrange/persisted fallback, compatibility layers or migrations. Keep interactive editor policy unchanged.

## Decisions

### Reuse a pure read boundary with explicit capture policy

Add proposed `elosern_map_editor/capture_snapshot.py` with `load_capture_snapshot(root, *, view, map_id, hidden_layers)`; it returns JSON-ready `{world, partition, diagnostics}` or a typed capture-loading failure. View/map argument grammar belongs to the final CLI, but this callable resolves IDs against the loaded world and rejects absent/wrong-view identity rather than silently rendering another map.

Extract the minimal common source/layout/core load and projection operation from `snapshot.py` into a pure function within that existing owner. Both editor `read_workspace()` and the capture adapter consume it. Keep editor status construction and reference-editing policies above the shared operation; do not add a `capture` switch throughout EditorService. A second YAML parser/projection or a service instantiation is rejected.

Discover current world/layout sources once and read each discovered source once per invocation with existing limits, confinement and UTF-8/restricted-YAML checks. Use that in-memory authoring world for projection, diagnostics and partition freshness. This is a one-shot read, not a filesystem transaction or watcher-resynchronized view. Do not rescan to compute the partition signature.

### Structure blocks, semantics remain visible

Reject any source or discovered layout structure diagnostic before handing data to the renderer, even if the interactive editor would retain a partial layout projection. Missing layout files and absent positions for individual rooms remain valid; preserve the existing projected `layout_position` absence for deterministic `storedPosition()` fallback. Never persist a fallback or invoke arrange.

Return sorted loadable semantic diagnostics as JSON data. An unavailable/stale external-reference index is informative and never a viewing gate. Reuse current external context loading/status if needed for diagnostics, but do not write/refresh it or treat its absence as authorization to edit/delete. Missing or stale partition diagnostics must not block the views that do not require boundaries. A successful snapshot does not claim game adoption validation.

### Conditional partition decoding from the same snapshot

Only `view == 'continent'` with `partition` absent from normalized hides requires partition content. Read it through the confined workspace and existing artifact limit, decode through the shared core codec using the loaded mainland land predicate, and compare shared freshness metadata against `authoring.partition_signature` (including format/algorithm freshness rules). Capture gets outlines in scene metres; no game adapter import is permitted.

Missing, malformed or stale content raises an error naming explicit regeneration (`uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`) or `--hide partition`. Do not attempt either action for the caller. Full decoding is necessary because valid metadata alone does not establish usable outlines.

Hidden partition and settlement/interior requests do not read or require a partition artifact. Terrain preview continues to derive from current loaded source independently, including when all terrain is later hidden. No artifact/index writes, generator imports or game startup occur.

### Cross-change payload contract

Return `{world, partition, diagnostics}`. `world` is the existing complete JSON-ready projection, including interior layouts and continental terrain preview. `partition` is null when not requested or `{outlines}` after successful admission; outlines preserve shared codec metre coordinates. Diagnostics are structured sorted objects. No editor sessions, revisions, transport token or mutation API enters the payload.

`map-offline-render-surface` consumes world/partition with request `{view,map_id,width,height,bounds,hidden_layers}`. It owns scene selection and frame conversion; this adapter does not invent interior geographic positions or pre-filter geometry for hides. `map-agent-image-capture` calls this loader once, passes the payload as structured browser data and owns reporting.

## Risks / Trade-offs

- Reusing `WorkspaceRead.loaded` alone would admit malformed layouts. Capture admission tests inject malformed layout YAML and independently assert failure, alongside missing-position success.
- Pure-seam extraction may affect editor statuses. Preserve existing `read_workspace()` policy and run focused snapshot/confinement regressions.
- Metadata may be fresh while partition bodies are malformed. Use full shared decode and test corrupted outline/run content in addition to signature mismatch.
- Source changes during invocation cannot be atomically prevented without expanding scope. Keep one loaded snapshot, derive freshness from it and never claim to capture a later reread.

## Verification and requirement evidence

Add adjacent `tools/map-editor/tests/test_capture_snapshot.py` using synthetic fixtures for one-read loading, confined paths, structure-versus-semantic admission, absent/partial layouts and the complete partition matrix. Add `tests/test_map_capture_snapshot.py` with discoverable `unittest.TestCase` methods that execute the actual adapter in the independent editor environment and assert real payload/error/disk outcomes. These top-level methods own requirement coverage, not assertions that a helper was forwarded to another helper. Existing package-adjacent pytest tests alone do not establish root-runner evidence.

Cover partition missing/malformed/stale/fresh for visible continent, hidden continent, settlement and interior. Hash world YAML, layouts, partition and reference context before/after successes and failures, with expected bytes obtained from synthetic fixture setup. Test missing/stale reference context with loadable semantics. Instrument source reads narrowly for the single-read invariant while separately asserting captured positions and snapshot freshness after later source mutation.

Obtain canonical IDs with `tools.spec_traceability list` on the equivalent merged spec tree before archive and attach them to matching discoverable assertions. While active, use only substantively nearest existing canonical associations and record provisional mapping/reason; never invent identifiers or weak coverage tests. Run the focused package tests, top-level adapter module and repository contract gate. Full evidence remains CI-owned.

Update existing `docs/development/map-editor.md` with loader ownership, structure policy and conditional partition behavior; prose quality remains human review, not a new requirement.

## Migration Plan

Cut both pure-loading callers over in one implementation change with existing editor behavior intact. No source/data migration or alias. The final image command depends on this completed adapter; it must not ship a placeholder loader while this change is pending.
