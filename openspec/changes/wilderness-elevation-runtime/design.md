# Design

## Context

Observed owners and nearby test targets: new elosern_map_core/elevation_codec.py, world/maps/elevation.py; world/maps/runtime.py compose/adopt; authoring skill check_map_sources.py and regenerate_partition.py precedent; runtime/codec tests.

## Goals / Non-Goals

Publish bounded fingerprinted elevation tiles and runtime lookup. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Existing district partition actually lives in world/maps/data/district_partition.json. Do not relocate it. New generated artifact is content/maps/wilderness_elevation.json, excluded from authored YAML discovery. Exact root fields: version1, algorithm_version, source_signature, fingerprint, frame_cells, tile_cells64, data_sha256, tiles. source_signature lists sorted input identities/digests for continent geometry (coast/ridge/waterways/regions/shapes), canonical generator config and algorithm version; fingerprint is SHA256 of canonical signature JSON. Conservative whole-continent fingerprinting is allowed, documented. data_sha256 hashes ordered tile coordinates, lengths and compressed bytes, permitting startup integrity checking without raster expansion.

Tiles are row-major exact {x,y,data} objects, tile indices and canonical base64 zlib. Each decodes to4096 bytes, packed (band<<4)|tier, reserved bits2/3 zero. Frame2700 is not divisible by64: ceil(frame/64)^2 tiles, padded east/north bytes zero, lookups only0..frame-1. Canonical UTF8 JSON must be<=4MiB; reject before atomic replacement and retain prior output on failure.

Add regenerate_elevation.py beside regenerate_partition.py, using locked uv offline generation extra. Generate the full real artifact without changing authored geography. Extend check_map_sources.py freshness and existing runtime candidate composition/adoption admission before any published bundle changes. Missing/stale source, version, tile structure or compressed digest refuses startup with named diagnostic and retains the prior bundle. No implicit import-time loader or zero-elevation fallback.

Runtime band(x,y)/prominence_tier(x,y) share a fingerprint-keyed128-tile LRU. Pure Python codec imports no numpy/scipy. Decode one tile on demand with4096-byte output ceiling, complete-stream/no-trailing-data validation and nibble checks. Startup verifies compressed structure/hash without decoding the full frame. Tile corruption discovered during lookup raises a named error. Artifact identity changes invalidate cache identity. Update existing map authoring references with artifact ownership/regeneration/check commands.

## Dependency contracts

- [wilderness-elevation-generation](../wilderness-elevation-generation/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
