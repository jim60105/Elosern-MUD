# Tasks

Run only the focused commands named below. Never run a whole test suite for this change.
Do not add `covers_requirement` for the ADDED requirements (design D8).
Do not edit `content/maps/road_network.yaml` and do not regenerate `world/maps/data/road_network.json`.

## 1. Artifact format

- [ ] 1.1 Confirm `village-hamlet-kinds` is merged: `uv run --locked python -c "from elosern_map_core.schema import LOCATION_KINDS; assert 'village' in LOCATION_KINDS and 'hamlet' in LOCATION_KINDS"` exits 0. If not, stop and report.
- [ ] 1.2 Apply design D6 to `packages/map-core/elosern_map_core/roads_codec.py` and update the module docstring's artifact layout. Add the format tests of design D8 to `tests/test_road_network_format.py`. Verify: `uv run --locked python -m unittest tests.test_road_network_format` passes.

## 2. Generator

- [ ] 2.1 Add the constants of design D1, the `spur_nodes` field of D2 and the open-cell rule of D3 to `road_input`. Add the tests "Open cells", "Stage one is independent" and the `node_kinds` refusal. Verify: `uv run --locked python -m unittest tests.test_road_network_generation` passes.
- [ ] 2.2 Implement stage two per design D4 and `Road.spur_of`, and pass owners and nodes through `encode_roads` per D6. Add the tests "One spur per village", "The cheapest node is chosen", "A spur reuses a trunk", "Fixed order and village targets", "No settlement document needed" and "No village keeps the bytes". Verify: the same unittest command passes.
- [ ] 2.3 Apply design D5 to `_check_input` and `verify_roads`. Add the refusal tests and the hand-built invalid spur tests. Verify: the same unittest command passes, and from `packages/map-core`, `uv run --locked --extra generation python -m pytest tests -q` passes.

## 3. Adapter, documentation and gates

- [ ] 3.1 Apply design D7 to `tools/road_network.py`. Verify: `uv run --locked python -m tools.road_network --check` exits 0 on the committed artifact, `git status --short world/maps/data content/maps` prints nothing, and the test prefix `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_road_network_command` passes (`/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`). If `--check` reports the artifact as stale, stop and report; do not regenerate.
- [ ] 3.2 Apply the documentation edits of design D9. Verify: `grep -c 'Spur stage' docs/development/road-network.md` prints 1.
- [ ] 3.3 After the last source edit, run `uv run --locked python -m tools.map_reference_context`. Verify: the same command with `--check` exits 0.
- [ ] 3.4 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change road-spur-stage` and `openspec validate road-spur-stage --strict`. Verify: all exit 0. The hand-off lists each new test with the delta requirement and scenario it establishes.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
