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

### Requirement Traceability Mapping

Nearest current canonical requirements in canonical spec tree:
- `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained`
  (Reason: covers deterministic generation of physical relief rasters, configuration bounds and offline extra separation)
- `map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world`
  (Reason: covers candidate validation, refusal on missing/stale/corrupt artifacts, and retention of prior published bundle)

Planned equivalent-tree remount for new delta requirements (after archive sync):

1. `wilderness-elevation-runtime::elevation-artifacts-are-bounded-and-source-identified`
   - **Requirement**: Generation SHALL atomically publish deterministic elevation tiles within 4MiB, with fingerprints covering geographic, configuration and algorithm inputs.
   - **Scenarios**: Budget and freshness; Partial edge tiles.
   - **Test evidence**:
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_round_trip_synthetic_frame_with_partial_edge_tiles`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_encode_elevation_artifact_produces_valid_structure`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_oversize_budget_rejection`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_freshness_reporting_and_named_changed_source`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_prior_bytes_survive_oversize_failure`
     - `packages/map-core/tests/test_elevation.py:test_default_config_matches_codec_mirror_and_digest`

2. `wilderness-elevation-runtime::runtime-elevation-rejects-stale-or-corrupt-artifacts`
   - **Requirement**: Map adoption SHALL reject missing, stale or integrity-invalid elevation artifacts and expose bounded cached tile lookup without offline numeric dependencies.
   - **Scenarios**: Admission and lookup.
   - **Test evidence**:
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_corrupt_base64_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_corrupt_zlib_stream_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_trailing_data_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_exceeded_ceiling_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_non_zero_reserved_bits_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_tile_non_zero_padding_cell_raises`
     - `packages/map-core/tests/test_elevation_codec.py:ElevationCodecTests.test_integrity_checks_detect_reordered_or_missing_tiles`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_unloaded_lookup_raises_without_zero_fallback`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_bounds_checks_reject_out_of_frame_and_non_integers`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_lru_cache_capacity_strictly_bounded_to_128_and_evicts`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_different_artifact_identity_does_not_hit_stale_cache`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_runtime_lookups_match_packed_bytes_on_partial_frame`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_admission_rejection_on_missing_or_corrupt_elevation_retains_prior_bundle`
     - `world/maps/tests/test_map_elevation.py:ElevationRuntimeLogicTests.test_clear_published_world_clears_elevation_pointer`
     - `tests/test_elevation_contract.py:RuntimeWithoutGenerationExtraTests.test_package_runtime_surface_imports_without_numpy_scipy_or_the_generator`

### Integration Verification Evidence and Benchmarks

Executed verification outcomes:
1. **Elevation Codec suite** (`uv run --locked --project packages/map-core python -m pytest packages/map-core/tests/test_elevation_codec.py`):
   - 13 passed in 0.07s. Covers packing, partial edge tiles, corrupt base64/zlib, trailing data, ceiling excess, reserved bits non-zero, padding cell non-zero, budget rejection, prior bytes survival, and freshness reporting.
2. **Elevation Generation suite** (`uv run --locked --project tools/map-editor python -m pytest packages/map-core/tests/test_elevation.py`):
   - 18 passed in 0.28s. Includes byte-for-byte verification that `asdict(DEFAULT_ELEVATION_CONFIG)` matches `DEFAULT_CONFIG_VALUES` and `DEFAULT_CONFIG_DIGEST`.
3. **Runtime Surface Probe** (`uv run --locked python -m unittest tests/test_elevation_contract.py`):
   - 2 passed in 0.26s. Subprocess probe proves `world.maps.elevation` and `elosern_map_core.elevation_codec` import without NumPy, SciPy or the offline generator.
4. **Server Runtime Adapter suite** (`uv run --locked evennia test --settings settings.py world.maps.tests.test_map_elevation`):
   - 7 passed in 2.8s. Verifies unloaded lookup error without zero-fallback, pointer clearance on uninstallation, bounds checks, strict LRU <= 128 eviction, fingerprint cache separation, packed byte matching, and candidate admission failure retaining prior bundle.
5. **Map Runtime Contract suite** (`uv run --locked evennia test tests.test_map_runtime_contract`):
   - 7 passed in 0.65s. Verifies single-writer authority and no retired symbols.
6. **Static Source Checker** (`uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py`):
   - Exit code 0, reports `wilderness elevation: current` with full integrity verification in < 1s without raster expansion.
7. **Artifact Benchmark**:
   - Committed `content/maps/wilderness_elevation.json`: 445,549 bytes (~435 KiB), representing 10.6% of the 4,194,304 bytes (4 MiB) budget ceiling.
8. **Gates & Lint**:
   - `tools.observability_lint check`: scanned=810, frozen=0, violations=0, exemptions=353.
   - `tools.spec_traceability check`: 2643 requirements, 11959 associations, 2643 covered, 0 uncovered, 0 errors.
   - `tools.contract_gate`: all 6 gates passed (reference-context, traceability, observability, test-data, manifests, contracts).
   - `openspec validate wilderness-elevation-runtime --strict`: valid.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
