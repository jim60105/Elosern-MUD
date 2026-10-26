# Worker contract

## Fixed cross-slice interfaces

Use these proposed names as the integration contract. Implementations may choose private helpers; do not create a second public seam.

| Owner | Export / contract | Consumers |
| --- | --- | --- |
| map-core authoring | load_authoring_world(source_documents) -> AuthoringWorld; source documents carry canonical relative path, fingerprint, text and provenance; schema() returns the machine-readable version-1 domain schema | Game explicit loader and editor service |
| map-core validation | diagnose_world(world) -> typed diagnostics; compile_runtime(world, authoritative_external_result, partition_freshness) -> RuntimeMapSnapshot or rejection | Game adapter; editor never supplies authoritative game approval |
| map-core identity | resolve_reference(world, qualified_ref); qualified_ref is a tagged value with domain, map_id when scoped, and object_id or explicitly typed wilderness cell | All static adapters and selectors |
| map-core codec | parse_document(relative_path, text) -> typed values plus round-trip tree/source locations; serialize_document(candidate, retained_tree) -> supported YAML | Game reads; editor writer owns file policy |
| map-core partition | partition_input(map_input_snapshot); generate_partition(input); decode_partition(document); partition_freshness(metadata, input_signature, algorithm_version) | Game CLI and editor job runner; lightweight calls import no generation modules |
| map-view | Explicit view/frame/point values and host theme/glyph inputs; no host store/actions or fake player | Migrated game maps and standalone editor |
| editor read model | GET /api/workspace returns one complete replacement containing session_generation, snapshot_revision, write_pause, preview_state, world/schema, per-document fingerprints, diagnostics, external_context_status and partition_status | Browser; never game/OOB transport |
| editor invalidation | GET /api/events is SSE invalidation/status notification; on any invalidation/reconnect GET /api/workspace again | Browser, no patch/merge state |
| editor commands | POST /api/commands/<named-domain-command>, launch token in a request header; payload carries session_generation, snapshot_revision, document_id, expected_document_fingerprint (content hash or explicit `absent`) and typed command arguments | All source/layout mutations and undo/redo |
| editor reread | POST /api/reload, authenticated; rereads disk and clears a write pause after uncertain durability; never sends an old-world payload. There is no resume, handoff or return route (frontend design D3) | Explicit user action from the priority banner only |
| editor generation | POST /api/partition/jobs and POST /api/partition/jobs/<id>/cancel, authenticated; result publication uses existing writer/state guard | Explicit user action only |

These route names are proposed implementation details, not new product scope. Error responses distinguish structure/field validation, semantic WIP, external invalid/unavailable, stale session/document, write pause, stale preview, save failure/uncertainty and unauthorized request. Return named diagnostic code plus relative file, qualified object, field path and line when available. Frontend may localize explanations but must not implement a competing map schema or substitute unavailable for valid.

A mutating command is admitted only after token/session/write-pause/stale-preview checks. A named handler returns one internal create, replace or remove effect for its owner, never an arbitrary file operation. Validate the complete resulting authoring world before publication, recheck expected absence/hash, use no-overwrite atomic create or guarded atomic replace/unlink, and acknowledge only after the durability boundary. History retains presence/absence and round-trip baselines; undo creation removes its file and redo requires absence. Failed/rejected effects leave disk/history unchanged, while uncertain publication pauses for reread. Layout cleanup is always a separate operation.

Every object-removing effect, including undo or a replacement that drops objects, rechecks current external-context dependency membership/hashes at execution. Prior browser status or unchanged index bytes cannot authorize deletion after external source changes. Watcher reconciliation compares freshly read presence/content with committed writer fingerprints; expected self-notifications preserve history, while a mismatched external replacement that loads is adopted automatically (history cleared; held behind a banner while the client has a draft) and one that does not load keeps the stale preview and rejects writes, without path-only event suppression.

UI fields have draft/accepted/in-flight/saved/failed/uncertain states and server status is authoritative. A generation result has input_signature and algorithm_version and is publishable only after current signature/write-pause recheck. Fingerprints detect accidental overwrites under continuous file following; no multi-process compare-and-merge guarantee is claimed.

## Caller cutover checklist

This table is an implementation checklist, not a second registry. Follow the full caller closure of the named owners; no obsolete import is permitted after its owning cutover. Resolve newly changed callsites through CodeGraph in the assigned worktree at apply time, then edit them immediately in the same task. Do not replace this checklist with a generic exploration task.

| Existing owner / caller family | Destination and exact responsibility | Owning slice |
| --- | --- | --- |
| world/maps/sparse_graph.py, build_sparse_graph, route planners, bootstrap graph types | pure algorithms/types in elosern_map_core; graph_from_xymap/contrib lookup only in game adapter | core-sparse-geometry |
| world/lore/wilderness_regions.py; wilderness_provider constants/classifier, wilderness_reachability, monster_provisioning/population, map geometry presenters | continent YAML data, explicit-snapshot core rules and game provider wrappers; snapshot-scoped caches | geography cutover |
| anchors Anchor/GeographicAnchor/LocalFrameAnchor, lore __init__/sync, map quest destinations | locations YAML map fields; Python political/population/floors; settlement binding YAML; composed read-only views | geography then settlement |
| city_gates, wilderness_entry, anchor_placement, map_districts, places exterior, room_art coordinates and static quest/service declarations | qualified refs first, runtime coordinate/wire forms derived only at existing consumer boundary | qualified-static-references |
| altoria_capital/village_ciaran PROTOTYPES/NODE_IDS/ROADS/XYMAP_DATA; map_data fixed imports | all settlement YAML fields, explicit immutable load and no hard-coded roster | settlement cutover |
| typeclasses/exits gate/return/home re-anchor, movement length/route callers, bootstrap grid/wilderness/start sync | preserve gameplay and transaction/knowledge owners while reading current resolved map values | settlement plus runtime |
| map_districts and map_district_lighting; partition seed input; world/area presenters | district YAML and qualified landmarks; existing canonical visited-node lighting at game boundary | district cutover |
| places_altoria_*, places_ciaran, courier records, places.py fields; _hosts, guild_economy, service_gate; resolve_residence_route; special bootstrap links | interior YAML prose/topology; retain place key as permanent room ID and non-map service room_ref; no duplicate spawning or host reset | interior/runtime |
| room_art REGION/GRID/PLACE tables; bootstrap _apply_room_art; scene identity/quest locators | references in continent/settlement/interior sources; actual scene/art catalogs and wire scene forms remain game-owned | geography/settlement/interior respectively |
| static quests/services/scenes/art/lore and authored-registry reference model; GM source/registry readers | qualified target validation, final source paths and snapshot-scoped cache rebuilding | qualified refs then runtime/export |
| server/conf/at_server_startstop; lore sync; all commands, GM readers and map presenters | explicit validated complete bundle before persistent synchronization/publication; no import-time partial authority | runtime cutover |
| tools/map_district_partition production_input and world/maps/district_partition | core explicit snapshot input/algorithm extra; lightweight signed artifact decode/freshness; game CLI thin adapter | partition-core-generation |
| map_viewport/area_map_view/minimap_projection neutral geometry and glyph consumers; AreaMapView/WorldMapView | @elosern/map-view; host-owned knowledge/actions/selection/theme | shared-foundations |
| world/tests/synthetic_data, source-contract tests, shard/traceability annotations, developer docs | new authoritative sources and same behavioral claims; retire only incidental source/data pins, not consumer evidence | every owning slice |

If a player-command surface intentionally changes, update docs/game/commands.md and docs/game/command-reference.md together and preserve tests/test_command_docs.py. This batch intends no command syntax or availability changes.
