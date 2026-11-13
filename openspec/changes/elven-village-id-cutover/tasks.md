# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused labels named below, one command per label. Never run a whole test suite for this change. If the test guard refuses a package label because it discovers more than 100 tests, run that package's modules one by one.

Change only the 36 files of design D1, the bullet of D4 and the generated artifacts of D3.

## 1. Rename

- [ ] 1.1 Run `git mv content/maps/settlements/village_ciaran.yaml content/maps/settlements/elven_village_ciaran.yaml`. Verify: `git status --short` shows one rename and nothing else.
- [ ] 1.2 Save the 36-line file list of design D1 as `<scratchpad>/cutover-files.txt` and run `xargs perl -pi -e 's/(?<!elven_)(?<!test_)village_(fionnen|ciaran|eolas)(?!_hinterland)/elven_village_$1/g' < <scratchpad>/cutover-files.txt`. Verify: `git diff --stat` lists only those files, and a second run of the same command leaves `git diff --stat` unchanged.
- [ ] 1.3 Replace the bullet in `docs/lore/settlement-locations.md` with the text of design D4. Verify: `grep -c '〔提案〕精靈村落的地點 ID' docs/lore/settlement-locations.md` prints 0.

## 2. Leftovers and generated artifacts

- [ ] 2.1 Run `grep -rIlP --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.worktrees --exclude-dir=.var --exclude-dir=.codegraph --exclude-dir=dist --exclude-dir=.storybook-out --exclude-dir=openspec '(?<!elven_)(?<!test_)village_(fionnen|ciaran|eolas)(?!_hinterland)' .`. Verify: the output is exactly these 7 files: `content/map-reference-context.json`, `docs/design/world-map/prototype-data.js`, `docs/superpowers/specs/2026-09-20-settlement-shops-design.md`, `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md`, `docs/superpowers/specs/2026-10-21-world-map-scale-design.md`, `tests/test_map_settlement_contract.py` and `web/webclient-app/stories/fixtures/local_map.js`. If another file appears, apply the same substitution to it and name it in the hand-off.
- [ ] 2.2 Run the four commands of design D3 in order. Verify: `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` exits 0, `uv run --locked python -m tools.road_network --check` exits 0, `uv run --locked python -m tools.map_reference_context --check` exits 0, and the only changed lines of `git diff world/maps/data/road_network.json` are the two `source_signature` lines.

## 3. Focused verification

- [ ] 3.1 Run the test prefix on each of: `world.maps.tests.test_settlement_sources`, `world.maps.tests.test_village_ciaran`, `world.maps.tests.test_bootstrap_sync`, `world.maps.tests.test_bootstrap`, `world.maps.tests.test_settlement_reload`, `world.maps.tests.test_city_movement_cost`, `world.lore.tests.test_settlements`, `world.lore.tests.test_wilderness_entry`, `world.lore.tests.test_anchors`, `world.lore.tests.test_races`, `world.lore.tests.test_nations`, `world.quests.tests.test_definitions`, `world.rules.tests.test_guild_economy_sync.test_ciaran_village_commerce`. Verify: every label passes. A failure caused by a literal old ID is fixed by the same substitution in that file. Any other failure stops the change.
- [ ] 3.2 Run `uv run --locked python -m unittest tests.test_map_reference_context`, then `uv run --locked python -m unittest tests.test_map_core_contract`, then `uv run --locked python -m unittest tests.test_map_settlement_contract`. Verify: all three pass.
- [ ] 3.3 Run `pnpm run build` in `web/webclient-app`, then `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_scene_transitions` from the repository root. Verify: the module passes.
- [ ] 3.4 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate elven-village-id-cutover --strict`. Verify: all exit 0. The hand-off states that a development database needs the reset of `docs/development/database-reset.md`.
