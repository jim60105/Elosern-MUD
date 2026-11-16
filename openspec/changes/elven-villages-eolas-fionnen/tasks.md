# Tasks

Read `design.md` first. Every table, YAML block and code block named below is in it. Follow `.agents/skills/map-data-authoring/SKILL.md` for the authoring workflow.

Rules that hold for every task:

- IDs are permanent. Rename, move or delete nothing that exists.
- Do not edit `content/maps/locations.yaml`, any file under `openspec/specs/`, or any file under `content/map-editor-layouts/`.
- Add no test and no assertion that names a node, room, place, coordinate or count from this change.
- Keep the coordinates and bends in `design.md`. Do not straighten a road or align nodes into rows or columns.
- Prose guideline (design Decision 11): node and room descriptions follow the register of the existing 暗影谷村 nodes and interiors (`content/maps/settlements/elven_village_ciaran.yaml`, `content/maps/interiors/ciaran_*.yaml`): landscape, livelihood and daily life, each place a lived-in scene, not a service building. One to three sentences of Traditional Chinese each. No signboards, no shopkeeper wording, no building of worship.
- Run every Evennia test command alone, exactly as written, with nothing before or after it.
- Suggested commits: one per village's map sources, one for the courier rows with the test rewrites and the regenerated artifacts, one for the documents. Only the branch tip has to be game-ready; a village commit may carry a stale partition.

## 1. Baseline

- [ ] 1.1 Run `git status`, then `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` and `uv run --locked python -m tools.settlement_synthesis lint elven_village_ciaran`. Verify by noting the result line of each in the working notes; the expected baseline is `RESULT: game-ready as far as static checks can tell` (with advisory `footprint_location_offset` lines for other settlements) and `fit: 0 errors, 0 warnings`. If the baseline differs, record what it reports so later results can be compared against it.

## 2. 幽月谷村

- [ ] 2.1 Create `content/maps/settlements/elven_village_eolas.yaml` from design Decisions 2, 3 and 5: the header, 9 nodes, 18 road entries with the listed bends, the `wilderness_entry` block with `return_direction: s`, and the `city_gate` block. Write each node `desc` from its "What the description covers" cell under the prose guideline. Verify with `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py`: it reports no structure error and `game-adoption cross-file problems: 0` (a stale partition is expected here), and `uv run --locked python -m tools.settlement_synthesis lint elven_village_eolas` prints `fit: 0 errors`.
- [ ] 2.2 Create the four interiors `eolas_shelter`, `eolas_silverfeather`, `eolas_library` and `eolas_storehouse` under `content/maps/interiors/` from design Decision 6, with no `art_key` line. Before writing, confirm no room ID is taken: `grep -rn "^  eolas_" content/maps/interiors/` prints nothing. Verify by rerunning the check script: no structure error and `game-adoption cross-file problems: 0`.

## 3. 翠綠森林村

- [ ] 3.1 Create `content/maps/settlements/elven_village_fionnen.yaml` from design Decisions 2, 4 and 5: the header, 11 nodes, 22 road entries with the listed bends, the `wilderness_entry` block with `return_direction: w`, and the `city_gate` block. Write each node `desc` from its "What the description covers" cell under the prose guideline. Verify with the check script (no structure error, `game-adoption cross-file problems: 0`) and `uv run --locked python -m tools.settlement_synthesis lint elven_village_fionnen` printing `fit: 0 errors`.
- [ ] 3.2 Create the four interiors `fionnen_shelter`, `fionnen_silverfeather`, `fionnen_honey_house` and `fionnen_bow_shed` under `content/maps/interiors/` from design Decision 6, with no `art_key` line. Before writing, confirm `grep -rn "^  fionnen_" content/maps/interiors/` prints nothing. Verify by rerunning the check script: no structure error and `game-adoption cross-file problems: 0`.

## 4. 暗影谷村 bath node

- [ ] 4.1 In `content/maps/settlements/elven_village_ciaran.yaml`, add the `bathing_pool` node and its two road entries exactly as in design Decision 7; the road has no `bends`. Change no existing node, road, gate or comment. Write the `desc` as an open-air pool where the stream widens below the village; it must contain no ASCII word and none of `城牆`, `城門`, `衛兵`, `市集`, `市場`, `店`. Verify with the check script (no structure error, `game-adoption cross-file problems: 0`) and `uv run --locked python -m tools.settlement_synthesis lint elven_village_ciaran` printing `fit: 0 errors`.

## 5. Courier station rows and data-pin removal

- [ ] 5.1 Add the two `SETTLEMENT_REGISTRY` entries to `world/lore/settlements/settlements.py` and the two `PlaceDefinition` entries to `world/lore/settlements/places.py`, exactly as in design Decision 8. Verify with `uv run --locked python -c "from world.lore.settlements.places import PLACE_REGISTRY; print(PLACE_REGISTRY['eolas_silverfeather'].letter_service, PLACE_REGISTRY['fionnen_silverfeather'].letter_service)"` printing `True True`.
- [ ] 5.2 Rewrite the two methods in `world/lore/tests/test_settlements.py` as in design Decisions 9a and 9b, keeping each method's name and decorators and deleting the literal key list and the `expected` table. Append no key anywhere. Verification runs in task 7.1, after the partition is regenerated.
- [ ] 5.3 Rewrite the method in `world/rules/tests/test_guild_config/test_service_host_roster.py` as in design Decision 9c, keeping its name and decorator and deleting the literal key set. Verification runs in task 7.1.
- [ ] 5.4 Rewrite `test_lore_known_but_unplaced_anchor_is_rejected` in `world/quests/tests/test_definitions.py` as in design Decision 9d, and add the two import lines it names. Verification runs in task 7.2. The `anchors()` assertion was not run while planning; if it fails, read `world/lore/anchors.py` for the correct accessor and report the change.
- [ ] 5.5 Change the head of the final loop in `test_real_startup_converges_places_scene_art_and_quest_targets` in `world/maps/tests/test_bootstrap/test_bootstrap_selection.py` as in design Decision 9f. Change nothing else in the method. Verification runs in task 10.2.
- [ ] 5.6 Replace the comment above `_THIRD` in `world/maps/tests/test_settlement_sources.py` as in design Decision 9e. Change no assertion. Verify with `git diff world/maps/tests/test_settlement_sources.py` showing comment lines only.

## 6. Regenerate derived artifacts

Do this group only after groups 2 to 5 are finished. Any later edit to a settlement file repeats 6.1 and 6.2.

- [ ] 6.1 Run `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`. Verify with `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py --check` printing `district_partition.json is up to date`.
- [ ] 6.2 Run `uv run --locked python -m tools.road_network` (about 95 seconds, about 2.5 GiB of memory). Verify with `uv run --locked python -m tools.road_network --check` printing `road_network.json is up to date`, and with `git diff --stat world/maps/data/road_network.json` showing a change of one line (the `source_signature`). If more than the signature changed, stop and report.
- [ ] 6.3 Run `uv run --locked python -m tools.map_reference_context`. Verify with `uv run --locked python -m tools.map_reference_context --check` printing `is up to date`.
- [ ] 6.4 Run `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py`. Verify it ends with `RESULT: game-ready as far as static checks can tell`, with `district partition: current`, `wilderness elevation: current` and `reference context: current`.

## 7. Focused tests

- [ ] 7.1 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_settlements world.lore.tests.test_room_prose_language world.rules.tests.test_guild_config.test_service_host_roster world.narrative.tests.test_player_correspondence`. Verify it ends with `OK`. A failure in `test_room_prose_language` names the description to fix; fix the prose, then repeat group 6 if a settlement file changed.
- [ ] 7.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.quests.tests.test_definitions world.maps.tests.test_village_ciaran world.maps.tests.test_settlement_sources world.maps.tests.test_settlement_reload`. Verify it ends with `OK`. A failure in `test_village_ciaran` text tests names the forbidden word in the `bathing_pool` description; fix the prose, then repeat group 6.

## 8. Map images and review document

- [ ] 8.1 Prepare the capture runtime once: `uv sync --locked --project tools/map-editor --group capture`, `uv run --locked --project tools/map-editor --group capture playwright install chromium`, `pnpm --dir tools/map-editor/frontend install --frozen-lockfile`, `pnpm --dir tools/map-editor/frontend run build:capture`. Then capture each of the three maps into a directory outside the repository as PNG (create it first with `mkdir -p /tmp/elven-captures`), replacing `<map_id>` with `elven_village_eolas`, `elven_village_fionnen` and `elven_village_ciaran`: `uv run --locked --no-sync --project tools/map-editor --group capture python .agents/skills/map-data-authoring/scripts/capture_map.py --view settlement --map <map_id> --format png --output /tmp/elven-captures/<map_id>.png`. Verify that three image files exist. Do not commit them.
- [ ] 8.2 Open each of the three images with the image-reading tool and read it. For each map, compare what the image shows with the road table in design Decision 3, 4 or 7: every listed connection is drawn, no unlisted connection is drawn, the bends are visible, and no part of the map reads as a grid of rows and columns. If a map reads as a grid or a connection is wrong, fix the source, repeat group 6 and capture again. Verify by writing the reading of each image into the review document in task 8.3.
- [ ] 8.3 Create `docs/lore/elven-villages-map-review.md` in English with the five sections of design Decision 11: scope, map images (capture command and the reading from 8.2 for each of the three maps), prose review (one line per new node and room against the prose guideline), lore checks (no temple, no signboard, one magic practice spot per village, entrances that do not read as gates), and the paragraph for the reviewer's decision about the two new exits from 虛境. Verify the file lists all 21 new nodes and all 8 new rooms.

## 9. Lore document

- [ ] 9.1 Revise `docs/lore/settlement-locations.md` with the eight edits in the table of design Decision 12, in Traditional Chinese, using the `chinese-content-writing-guideline` and `writing-style-guideline` skills. Find each passage by its quoted text. Describe each bath as a daily-life water place: washing, laundry and talk. Verify with `grep -n "其中暗影谷村有地圖" docs/lore/settlement-locations.md` printing nothing, and `grep -n "溫泉浴場\|林泉浴場\|溪池浴場" docs/lore/settlement-locations.md` printing at least one line for each name.
- [ ] 9.2 Make the two one-sentence edits in `docs/development/evennia-testing-guide.md` and `docs/development/narrative-memory-and-recall.md` from the second table of design Decision 12. Verify with `grep -n "今日是兩個 gate map" docs/development/evennia-testing-guide.md` and `grep -n "兩個聚落各有一個無宿主" docs/development/narrative-memory-and-recall.md` both printing nothing.

## 10. Integration

- [ ] 10.1 Run `uv run --locked python -m tools.contract_gate`. Verify it ends with `contract gate passed`.
- [ ] 10.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap_sync world.maps.tests.test_bootstrap world.maps.tests.test_limbo_room` (88 tests, about fourteen minutes). Verify it ends with `OK`. If the test guard refuses the command for discovering more than 100 tests, run the three labels as three commands.
- [ ] 10.3 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.maps.tests.test_editor_final_yaml_adoption world.maps.tests.test_static_map_references world.maps.tests.test_service_interiors world.maps.tests.test_interior_sources world.lore.tests.test_wilderness_entry world.lore.tests.test_anchor_placement world.lore.tests.test_anchors world.maps.tests.test_room_art_metadata world.maps.tests.test_runtime_adoption world.maps.tests.test_city_movement_cost`. Verify it ends with `OK`.
- [ ] 10.4 Run the suites the map-authoring skill lists for locations, sight and the world map. They were not run while planning. Three commands, each alone. First: `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_map_district_content world.rules.tests.test_ground_reveal web.webclient.presentation.tests.test_world_map web.webclient.presentation.tests.test_map_panel_protocol`. Second: `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_sight`. Third: `uv run --locked python -m unittest tests.test_map_authoring_contract tests.test_map_geographic_sources tests.test_map_partition_independence tests.test_elevation_contract tests.test_map_editor_geography`. Verify each ends with `OK`. If the guard refuses the first command for size, run its labels separately.
- [ ] 10.5 Run `uv run --locked python -m tools.settlement_spacing`. Verify it prints `spacing: 0 problems`.
- [ ] 10.6 Check that the browser seed still derives its maps from the registry: `grep -n "CITY_GATE_REGISTRY" web/tests/browser/fixtures.py` prints the lines that build the map set from `CITY_GATE_REGISTRY.values()`, with no literal map list beside them. No browser test was run while planning. If the grep shows a literal map list, stop and report.
- [ ] 10.7 If any test in 10.2 to 10.4 fails: when the failing assertion compares against a literal roster, count or name of shipped places, nodes or maps, or walks a whole registry after starting only some of the maps, rewrite that assertion to the logic it stands for, as in design Decision 9, and append no new key; rerun the command. For any other failure, run the same label on `master`; if `master` passes, stop and report the failure with its output. Verify by recording in the working notes either "no failure" or each rewritten assertion with its file and method name.
- [ ] 10.8 Run `openspec validate elven-villages-eolas-fionnen --strict`. Verify it reports the change valid.

## Workflow follow-up

- In a running game, a person walks into each new village from the wilderness (stand on 幽月谷村's cell and step south; stand on 翠綠森林村's cell and step west), visits every node, enters every shared interior and sends a letter from each new courier station.
- A person reads `docs/lore/elven-villages-map-review.md` and the new prose before the change is archived.
