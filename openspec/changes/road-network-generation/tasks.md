# Tasks

Shared test command, with `<env>` a scratch file containing `MUD_TEST_SETTINGS=1`:
`uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb <label>`

## 1. Road parameter document

- [ ] 1.1 Implement D1 in `packages/map-core/elosern_map_core/sources.py`, `schema.py`, `documents.py` and `authoring.py`. Add `road_network` to the kind sets pinned in `packages/map-core/tests/test_yaml_codec.py` and `tests/test_map_authoring_contract.py`. Verify from `packages/map-core`: `uv run --locked --extra generation python -m pytest tests -q` passes.
- [ ] 1.2 Create `tests/test_road_network_generation.py` with the "Invalid content is rejected" and "Unknown forbidden region is rejected" scenarios, using `covers_requirement` and `make_source_document` on synthetic text. Register `tests.test_road_network_generation` in `top-level-4` of `.github/top-level-shards.json`. Verify with the shared command on label `tests.test_road_network_generation`.
- [ ] 1.3 Create `content/maps/road_network.yaml` with the D1 values. In `docs/development/map-authoring-documents.md`, add the row to the document table and name the optional singleton exception. Verify: `uv run --locked --project packages/map-core python -m elosern_map_core inspect .` reports no blocking diagnostic, and `uv run --locked python -m tools.map_reference_context --check` passes.

## 2. Pure generator

- [ ] 2.1 Add `RoadGenerationError`, `RoadNode`, `RoadInput`, `Road` and `road_input` to new `packages/map-core/elosern_map_core/roads.py` per D2. Add tests for "Road nodes are the gated settlements of the configured kinds" and "An absent document stops generation only", with synthetic document text inline in the test file, reusing the helpers of `packages/map-core/tests/authoring_fixtures.py` only by copying what the test needs. Verify with the shared command.
- [ ] 2.2 Implement the D3 cost field and `compute_roads` per D4. Add tests for "The road cost field admits only legal walkable steps", "Road topology is a relative neighbourhood graph with detour repair" and "Roads are routed cheapest first and reuse earlier cells" on synthetic rasters of at most 64 cells a side. Use a `noise_amplitude` of 0 where a test needs exact geometry. Verify with the shared command.
- [ ] 2.3 Implement `verify_roads` and `_check_input` per D5, feeding hand-built `Road` values to cover "Generation refuses an invalid network". Verify with the shared command.

## 3. Artifact codec

- [ ] 3.1 Implement new `packages/map-core/elosern_map_core/roads_codec.py` per D6, and `encode_roads` and `generate_road_network` in `roads.py`. Add tests for "The road artifact reproduces deterministically and reports freshness". Copy the subprocess import-blocking pattern from `tests/test_map_partition_independence.py` for "Independent decoding". Verify with the shared command, and from `packages/map-core` with `uv run --locked --extra generation python -m pytest tests -q`.
- [ ] 3.2 Add "Tuning leaves other artifacts current": `partition_source_signature_from_fingerprints` and `elevation_source_signature` give equal results with and without a changed `content/maps/road_network.yaml` row. Verify with the shared command.

## 4. Game adapter and artifact

- [ ] 4.1 Add `region_speeds_m_per_hour` to `world/rules/travel_cost.py` and its `__all__`. Implement `tools/road_network.py` per D7. Verify: `uv run --locked python -m tools.road_network --help` lists `--check`, `--output` and `--preview`.
- [ ] 4.2 Create `world/maps/tests/test_road_network_command.py`, a `unittest.TestCase` with `_bootstrap`, `build_input` and `artifact_text` patched, covering "The regeneration command reports stale artifacts" with temporary output paths and a tiny synthetic raster for the preview. Register `world.maps.tests.test_road_network_command` in shard `maps-33-1` of `.github/evennia-shards.json`. Verify with the shared command on that label and on `tests.test_evennia_test_optimization_contract`.
- [ ] 4.3 Run `uv run --locked python -m tools.road_network --preview <scratch>/roads.png`, with `<scratch>` outside the repository, and commit `world/maps/data/road_network.json`. Report the preview's absolute path in the hand-off. Verify: `uv run --locked python -m tools.road_network --check` exits 0 and `git status` shows no image. If a self-check problem names a shipped node or road, stop and report it; do not weaken the check.
- [ ] 4.4 Add the D8 step to `.github/workflows/quality-gate.yml`. Verify with the shared command on `tests.test_quality_gate_contract`.

## 5. Documentation and hand-off

- [ ] 5.1 Create `docs/development/road-network.md` covering the regeneration command, the regeneration order after a terrain change, and a "Human review record" section with a dated row saying the preview is pending review. Add the road commands after the partition and elevation lines in `.agents/skills/map-data-authoring/references/verification.md`. Verify: `uv run --locked python -m tools.road_network --check` runs as documented.
- [ ] 5.2 Run `uv run --locked python -m tools.contract_gate --change road-network-generation` and `openspec validate road-network-generation --strict`. Verify: both exit 0.
