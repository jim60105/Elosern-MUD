# Tasks

Shared test command, with `<env>` a scratch file containing `MUD_TEST_SETTINGS=1`:
`uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb <label>`

Do not add `covers_requirement` in any task here; see D4.

## 1. Road parameter document

- [ ] 1.1 Implement D1 in `packages/map-core/elosern_map_core/sources.py`, `schema.py`, `documents.py` and `authoring.py`. Add `road_network` to the kind sets pinned in `packages/map-core/tests/test_yaml_codec.py` and `tests/test_map_authoring_contract.py`. Verify from `packages/map-core`: `uv run --locked --extra generation python -m pytest tests -q` passes, and the shared command on `tests.test_map_authoring_contract` passes.
- [ ] 1.2 Create `tests/test_road_network_format.py` covering the scenarios of "Road parameters are a validated authored document", importing `authoring_fixtures` per D4. Register `tests.test_road_network_format` in `top-level-4` of `.github/top-level-shards.json`. Verify with the shared command on `tests.test_road_network_format` and `tests.test_evennia_test_optimization_contract`.
- [ ] 1.3 Create `content/maps/road_network.yaml` with the D1 values. In `docs/development/map-authoring-documents.md`, add the row to the document table and name the optional singleton exception. Verify: `uv run --locked --project packages/map-core python -m elosern_map_core inspect .` reports no blocking diagnostic.

## 2. Artifact codec

- [ ] 2.1 Implement `packages/map-core/elosern_map_core/roads_codec.py` per D2. Add tests for "The road artifact decodes and reports freshness without generation dependencies", with a helper named `run_with_numpy_blocked(source)` copied from the subprocess pattern in `tests/test_map_partition_independence.py`. Verify with the shared command on `tests.test_road_network_format`.

## 3. Region speeds

- [ ] 3.1 Implement D3 in `world/rules/travel_cost.py`. Verify: `uv run --locked python -c "from world.rules.travel_cost import region_speeds_m_per_hour; print(all(isinstance(v, int) for v in region_speeds_m_per_hour().values()))"` prints `True`.

## 4. Hand-off

- [ ] 4.1 After the last source edit, run `uv run --locked python -m tools.map_reference_context` and commit `content/map-reference-context.json`. Verify: the same command with `--check` exits 0.
- [ ] 4.2 List each new test with the delta requirement and scenario it establishes in the change report. Verify: every requirement in `specs/road-network-artifact/spec.md` has at least one test.
- [ ] 4.3 Run `uv run --locked python -m tools.contract_gate --change road-network-format` and `openspec validate road-network-format --strict`. Verify: both exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests named in 4.2 with the tool-generated IDs from `uv run --locked python -m tools.spec_traceability list`.
