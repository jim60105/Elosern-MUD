# Design

## Context

Observed owners and nearby test targets: world/rules/map_knowledge.py SCHEMA_VERSION/NodeVisit/parse_knowledge/record_arrival/prune/remap; full-projection callers in lighting/discovery/local/area/world/party; test_map_knowledge_integration.py and existing pruning/discovery/presentation fixtures.

## Goals / Non-Goals

Replace schema1 with bounded chunk-addressed wilderness observations. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Exact schema2 record is {schema_version:2,visited:{...},wilderness:{...}}. visited contains only grid:/room: canonical IDs with first_seen_tick/last_seen_tick pairs. wilderness maps registered wilderness name to chunk map keyed canonical decimal chunk_x:chunk_y. Chunk entries are canonical decimal local offsets0..4095 -> {first_seen_tick,last_seen_tick,sight}. offset=(y%64)*64+x%64, chunk=(x//64,y//64). Validate nonnegative integer ticks, first<=last, sight integer0..8, registered in-frame identity, no booleans/extra keys. Edge padding invalid. Bound to ceil(frame/64)² chunks and frame² visits per wilderness and4096 entries per chunk; never silently prune history.

Retain parse_knowledge as the needed full deterministic NodeVisit projection, extending wilderness observations with sight. Add visits_in_bounds(character,bounds,padding=0) and has_visited(character,node_id) for bounded/direct access. Bounded reads validate envelope and selected chunks only; distant corrupt chunks diagnose on their access/full parse. Missing history follows existing empty/unavailable caller semantics. Schema1 rejects as unknown with existing corrupt-record diagnostics and is never converted/overwritten. In this storage-only slice record_arrival stores sight0 for new wilderness visits, preserving maximum previous sight; dependent ground-reveal replaces the radius input. It remains a complete real visit writer, not a stub.

Adapt every record-shape consumer/fixture, including full world trail, local map, lighting, discovery, reclamation pruning and coordinate-remap. Prune only room entries and preserve all chunks; remap retains ticks/sight. No NPC/companion record. Existing movement snapshot compensation remains valid. No automated reset, migration, alias, schema1 parser or dual write. Explain development reset in existing knowledge documentation. Preserve all original MODIFIED requirement scenarios except the explicitly changed record/no-geometry assertion, which now permits chunk addresses and sight. Pure reads still never write.

## Dependency contracts

Independent root slice.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

### Temporary spec traceability mapping
- MODIFIED `map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record`: Covered by `test_map_knowledge.py`, `test_map_knowledge_integration.py`.
- MODIFIED `map-knowledge::parse-knowledge-isolates-corrupt-records-without-resetting-them`: Covered by `test_map_knowledge.py`.
- ADDED `wilderness-observations-are-chunk-addressed`: Associated with nearest canonical requirement `map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record` before sync. Planned equivalent-tree remount: `wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed`.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
