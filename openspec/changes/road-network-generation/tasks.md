# Tasks

Shared test command, with `<env>` a scratch file containing `MUD_TEST_SETTINGS=1`:
`uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb <label>`

Do not add `covers_requirement` in any task here; see D9.

## 1. Inputs

- [x] 1.1 Confirm `road-network-format` is merged: `uv run --locked python -c "from elosern_map_core.roads_codec import road_source_signature"` exits 0 and `content/maps/road_network.yaml` exists. If not, stop and report.
- [x] 1.2 Add `RoadGenerationError`, `RoadNode`, `RoadInput`, `Road` and `road_input` to new `packages/map-core/elosern_map_core/roads.py` per D2. Create `tests/test_road_network_generation.py` with the scenarios of "Road nodes are the gated settlements of the configured kinds", importing `authoring_fixtures` per D9. Register `tests.test_road_network_generation` in `top-level-4` of `.github/top-level-shards.json`. Verify with the shared command on that label and on `tests.test_evennia_test_optimization_contract`.

## 2. Algorithm

- [x] 2.1 Implement the D3 cost field and `compute_roads` per D4. Add tests for "The road cost field admits only legal walkable steps", "Road topology is a relative neighbourhood graph with detour repair" and "Roads are routed cheapest first and reuse earlier cells" on synthetic rasters of at most 64 cells a side. Use a `noise_amplitude` of 0 where a test compares costs. Assert legality, ends and cost, not exact cell sequences on uniform ground. Verify with the shared command.
- [x] 2.2 Implement `verify_roads` and `_check_input` per D5, feeding hand-built `Road` values to cover "Generation refuses an invalid network". Verify with the shared command.
- [x] 2.3 Implement `encode_roads` and `generate_road_network`. Add tests for "Generation is deterministic". Verify with the shared command, and from `packages/map-core` with `uv run --locked --extra generation python -m pytest tests -q`.

## 3. Game adapter and artifact

- [ ] 3.1 Implement `tools/road_network.py` per D7. Verify: `uv run --locked python -m tools.road_network --help` lists `--check`, `--output` and `--preview`.
- [ ] 3.2 Create `world/maps/tests/test_road_network_command.py`, a `unittest.TestCase` with `_bootstrap`, `build_input` and `artifact_text` patched, covering "The regeneration command reports stale artifacts" with temporary output paths and a tiny synthetic raster for the preview. Register `world.maps.tests.test_road_network_command` in shard `maps-33-1` of `.github/evennia-shards.json`. Verify with the shared command on that label and on `tests.test_evennia_test_optimization_contract`.
- [ ] 3.3 Run `uv run --locked python -m tools.road_network --preview <scratch>/roads.png`, with `<scratch>` outside the repository, and commit `world/maps/data/road_network.json`. Report the preview's absolute path in the hand-off. Verify: `uv run --locked python -m tools.road_network --check` exits 0 and `git status` shows no image. If a self-check problem names a shipped node or road, stop and report it; do not weaken the check.
- [ ] 3.4 Add the D8 step to `.github/workflows/quality-gate.yml`. Verify with the shared command on `tests.test_quality_gate_contract`.

## 4. Documentation and hand-off

- [ ] 4.1 Create `docs/development/road-network.md` covering the regeneration command, the regeneration order after a terrain change, and a "Human review record" section with a dated row saying the preview is pending review. Add the road commands after the partition and elevation lines in `.agents/skills/map-data-authoring/references/verification.md`. Verify: `uv run --locked python -m tools.road_network --check` runs as documented.
- [ ] 4.2 List each new test with the delta requirement and scenario it establishes in the change report. Verify: every requirement in `specs/road-network-generation/spec.md` has at least one test.
- [ ] 4.3 Run `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.test_data_lint check`. Verify: both exit 0.
- [ ] 4.4 After the last source edit, run `uv run --locked python -m tools.map_reference_context` and commit `content/map-reference-context.json`. Verify: the same command with `--check` exits 0.
- [ ] 4.5 Run `uv run --locked python -m tools.contract_gate --change road-network-generation` and `openspec validate road-network-generation --strict`. Verify: both exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests named in 4.2 with the tool-generated IDs from `uv run --locked python -m tools.spec_traceability list`.
- The human reviewer fills in the "Human review record" of `docs/development/road-network.md` from the preview. It does not block archive.
