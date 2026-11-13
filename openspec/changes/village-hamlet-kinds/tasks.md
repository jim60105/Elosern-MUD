# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused labels named below, one command per label. Never run a whole test suite for this change.

## 1. Vocabulary

- [ ] 1.1 Confirm `elven-village-id-cutover` is merged: `grep -c 'elven_village_ciaran' world/lore/anchors.py` prints 1. If it prints 0, stop and report.
- [ ] 1.2 Append `"village"` and `"hamlet"` to `LOCATION_KINDS` and add `VILLAGE` and `HAMLET` to `AnchorKind`, exactly as design D1. Verify: the test prefix on `world.lore.tests.test_anchors` passes, and `uv run --locked python -m unittest tests.test_road_network_generation` and `uv run --locked python -m unittest tests.test_road_network_format` pass unchanged.
- [ ] 1.3 Add the two members to `settlement_kinds` in `world/lore/tests/test_anchors.py` (design D6). Replace the `ANCHOR_LORE` comment sentence per design D5. Verify: the test prefix on `world.lore.tests.test_anchors` passes.

## 2. Consumers

- [ ] 2.1 Add the two kinds to `INHABITED_SETTLEMENT_KINDS` and the docstring per design D2, and add the population test of design D6. Verify: the test prefix on `world.maps.tests.test_population_geometry` passes.
- [ ] 2.2 Extend `SUPPORTED_SETTLEMENT_KINDS` and add the two rulebook rows exactly as design D3. Verify: the test prefix on `world.rules.tests.test_sight` passes.
- [ ] 2.3 Add the two rows to `expected` in `web/webclient/presentation/tests/test_world_map.py` (design D6). Verify: the test prefix on `web.webclient.presentation.tests.test_world_map` passes with no production change in `web/`.
- [ ] 2.4 Add the two dropdown rows of design D4. Verify: `pnpm --dir tools/map-editor/frontend test` passes.

## 3. Documentation and gates

- [ ] 3.1 Apply the three documentation edits of design D7. Verify: `grep -c 'hamlet' .agents/skills/map-data-authoring/references/locations-and-districts.md` is at least 3, and `grep -c 'expects every' .agents/skills/map-data-authoring/references/locations-and-districts.md` prints 0.
- [ ] 3.2 After the last source edit, run `uv run --locked python -m tools.map_reference_context`. Verify: the same command with `--check` exits 0 and `uv run --locked python -m unittest tests.test_map_geographic_sources` passes.
- [ ] 3.3 Run `uv run --locked python -m tools.road_network --check`. Verify: it exits 0 with no regeneration, because no map source changed.
- [ ] 3.4 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change village-hamlet-kinds` and `openspec validate village-hamlet-kinds --strict`. Verify: all exit 0. The hand-off lists each new or edited test with the delta scenario it establishes.
