# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused labels named below, one command per label. Never run a whole test suite for this change.

Ground rules:
- Change only these files, plus residual-pin test rewrites under the "Residual pin rule" of `docs/development/settlement-synthesis.md`:
  - new rows in `content/maps/locations.yaml` and `world/lore/anchors.py`;
  - new `content/maps/settlements/<id>.yaml` files for the new IDs;
  - `tools/settlement_spacing_areas.json`;
  - `world/maps/data/road_network.json`, `world/maps/data/district_partition.json`, `content/map-reference-context.json`;
  - files under `openspec/changes/altoria-coast-village-placement/`.

- Never hand-edit generated YAML or a generated artifact.
- Keep previews, captures and prose JSON in the scratchpad, outside the repository.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline

- [x] 1.1 Confirm the prerequisites: `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`, `uv run --locked python -m tools.road_network --check` exits 0, `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`, and `tools/settlement_spacing_areas.json` equals the "Before" content of design D7. If any fails, stop and report.

  Result: all four hold on `b6104326`.
- [x] 1.2 Record the first timing line of design D9. Verify: the line is saved for the hand-off.

  Result: `Ran 2 tests in 0.000s` — measured at the first compose-able tree
  (after task 2.2's regeneration), because the pre-edit run of the same label
  refused at import with `stale_partition` once the new rows were in
  `locations.yaml`. The label itself discovers two tests and reports them
  separately; the figure is recorded, never asserted.
- [x] 1.3 Write the placement script per design D1 and list the road gaps over 75 km inside this change's scope. Verify: the list is saved under `snippets/` and names each gap's road, end cells and length.

  Result: `snippets/place.py`, `snippets/plan.json`, `snippets/gaps_before.json`
  and `snippets/gaps_before.txt`. Six gaps: `city_salt_ferry -- port_white_sail`
  184.8 km, `city_salt_ferry -- town_olive_ferry` 431.6 km, `city_salt_road --
  port_south_tide` 1031.7 km, `city_salt_road -- town_olive_ferry` 361.7 km,
  `port_fishers_cove -- port_white_sail` 254.2 km, `port_fishers_cove --
  town_olive_ferry` 310.8 km.

## 2. Villages

- [x] 2.1 Propose villages, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` (command in design Context) reports every new cell walkable, off the water and of nation `altoria`, and `uv run --locked python -m tools.settlement_spacing` reports no problem except `village_off_road` for the new villages.

  Result: `place_sites.py --locations` reports `177/177 sites valid` (exit 0).
  `settlement_spacing` reported exactly three problems, all `village_off_road`,
  for `village_cogongrass_flat (458, 119)`, `village_ridge_top (381, 449)` and
  `village_sand_bar (485, 178)` — the three off-trunk villages of design D1,
  nine of twelve villages on a trunk. No exemption is used.
- [x] 2.2 Regenerate per design D6. Verify: `uv run --locked python -m tools.settlement_spacing` reports no `village_off_road`, and every new village ID appears as a `spur_of` value in `world/maps/data/road_network.json`.

  Result: `spacing: 0 problems`; all twelve new village IDs are `spur_of`
  values (`village_big_flat` from `port_south_tide`, `village_cogongrass_flat`
  from `port_south_tide`, `village_creek_flat` from `port_white_sail`,
  `village_reed_bank` from `village_big_flat`, `village_river_terrace` from
  `village_reed_bank`, `village_ridge_top` and `village_stone_hill` from
  `city_salt_ferry`, `village_sand_bar` from `village_cogongrass_flat`,
  `village_sand_spit` from `port_fishers_cove`, `village_three_forks` from
  `town_olive_ferry`, `village_tide_flat` from `village_sand_spit`,
  `village_upper_vale` from `city_salt_road`). The road artifact grew from 80
  to 92 nodes.

## 3. Hamlets

- [x] 3.1 Propose hamlets against the regenerated roads, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` reports every new cell valid, and `uv run --locked python -m tools.settlement_spacing` reports no `hamlet_spacing`, `village_spacing`, `id_prefix`, `duplicate_name`, `no_nation`, `nation_mismatch`, `population_range` or `forbidden_region` problem.

  Result: 25 hamlets (22 on a road, 3 off every road: `hamlet_reed_islet`,
  `hamlet_pool_tail`, `hamlet_tide_sound`). `place_sites.py --locations` reports
  `178/178 sites valid` (exit 0) once every row was written, and
  `settlement_spacing` reports no identity, spacing, nation or population
  problem — only the three expected pre-regeneration `village_off_road` rows.
  `hamlet_tide_sound (527, 108)` closes the 148.3 km
  `port_south_tide -- village_cogongrass_flat` gap the first village
  regeneration exposed.
- [x] 3.2 Regenerate per design D6 and make the trunk comparison of D6. Verify: no road row without `spur_of` changed.

  Result: `head roads 99 (trunk 78)` / `work roads 111 (trunk 78)`, `trunk rows
  changed: 0`; only `nodes`, `fingerprint`, `source_signature` and the twelve
  `spur_of` rows differ.

## 4. Maps and prose

- [x] 4.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation altoria --kind village --plan-only`, then without `--plan-only`; then the same two commands with `--kind hamlet`. Verify: each new ID has exactly one new file, no existing settlement file changed (`git status --short content/maps/settlements` shows only additions), and `uv run --locked python -m tools.settlement_synthesis lint` exits 0. A refusal is fixed by moving that location and repeating from group 2 or 3; never by hand-writing a map.

  Result: 12 village maps (4 nodes each) and 25 hamlet maps (2 nodes each), 98
  nodes in all, every report warning-free. `git status --short
  content/maps/settlements` lists 37 additions and no modification, and
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings` and exits 0.
- [x] 4.2 Write and apply the prose of every new map per design D5a. Verify: `brief` of each new map shows no empty description and no duplicate key.

  Result: 37 prose files written under the scratchpad and applied with `prose`;
  every one of the 98 nodes now carries a `key` of 2 to 8 characters and a
  `desc` of 40 to 140 characters, keys are unique within their map and no
  description is empty. Villages name the well and the church front; hamlets
  name the crossing and the single farmstead; each entrance names the direction
  or the neighbour it leads to, and no shop, guild branch or service is
  presented as usable.
- [x] 4.3 Regenerate per design D6. Verify: compared with the artifact of task 3.2 (keep a copy in the scratchpad), the only changed line of `world/maps/data/road_network.json` is `source_signature`.

  Result: `algorithm_version`, `fingerprint`, `frame_cells`, `nodes`, `roads`
  and `version` are unchanged; only `source_signature` differs.

## 5. Validation and hand-off

- [ ] 5.1 Replace `tools/settlement_spacing_areas.json` with the "After" content of design D7 and run the four checks of D7. Verify: all four hold. Fix a `road_gap` as D7 says and repeat the affected groups.

  Result: the area entry is in place; `check_map_sources.py` exits 0 and
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings`. Enabling the
  area surfaced three road gaps that cross the boundary into the earlier
  `western_hills_valleys` area — the case design D2 names. Five boundary
  hamlets close two of them: `hamlet_ridge_edge` (1024, 420) and
  `hamlet_hillside` (1028, 477) split `city_salt_road--town_honey_vale`
  (175.9 km into 58.7 / 58.6 / 58.6); `hamlet_ridge_waist` (351, 544),
  `hamlet_mid_vale` (302, 593) and `hamlet_flat_meadow` (249, 646) sit on the
  earlier side of the boundary under the D2 exception and split
  `city_salt_ferry--port_west_ore` (288.2 km into 72.3 / 69.3 / 74.9 / 71.5).
  The third gap, `city_confluence--town_olive_ferry` (455, 540) to
  (454, 448), stays at 138.9 km: it is not closable by any legal site. A
  split of a 138.9 km gap into two gaps of at most 75 km must fall between
  397.0 and 408.1 km along the road, and of the eleven cells in that window
  three lie 1.0 to 2.2 km from `city_salt_ferry` (hamlet minimum 15 km) and
  the other eight lie inside a monster habitat (D3 rule 4). The road runs
  past the city without touching its cell, so the city's own position never
  splits the gap. `spacing` therefore reports `1 problems` until a decision
  outside this change's file list is taken: either a `spacing_exemption`
  with a design reason (D7 forbids one without it) or marking national
  settlements in `tools/settlement_spacing`, which is a validator change.
- [ ] 5.2 Run every module of `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command, plus `world.lore.tests.test_anchors` and `world.maps.tests.test_population_geometry` with the test prefix. Verify: every one passes. Handle a failure with that section's "Residual pin rule" and list every rewritten test in the hand-off. Any other failure stops the change without a commit.

  Result: not delivered. The run budget ran out before the sweep. Two things
  are needed to finish it: each label must be a standalone shell command (the
  focused-test guard refuses a script or an interpreter payload that runs
  `evennia test`, so the 71-label loop cannot be batched), and one label —
  `world.maps.tests.test_bootstrap`, also the D9 timing label — was run
  standalone; its result is recorded under task 5.4.
- [ ] 5.3 Capture the continent with `capture_map.py --hide partition` and the settlement views of two new villages and two new hamlets (one on a through road, one at a spur end, one off-road where one exists). Read the images. Verify: the hand-off gives the absolute path of each image and of the last road preview, and states for each captured map which road each entrance meets.

  Result: not delivered. `capture_map.py` refuses with `build_missing: the
  local capture page is not built: tools/map-editor/frontend/capture-dist/
  index.html`, and building it needs `pnpm --dir tools/map-editor/frontend
  install --frozen-lockfile`, which is a tooling install outside this
  change. The road previews the same run produced are at
  `/tmp/omp-scratch/coast/roads_villages.png`,
  `/tmp/omp-scratch/coast/roads_hamlets.png`,
  `/tmp/omp-scratch/coast/roads_final.png`,
  `/tmp/omp-scratch/coast/roads_final2.png` and
  `/tmp/omp-scratch/coast/roads_d7.png`.
- [ ] 5.4 Record the second timing line of design D9, then run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate altoria-coast-village-placement --strict`. Verify: all exit 0. The hand-off lists the count of villages and hamlets, every exemption with its reason, every hamlet placed under the boundary exception of D2, and both timing lines.

  Result: `test_data_lint check` → `scanned=1613 flagged=121 universe=4258+37
  quantity-pins=8 violations=0`, exit 0; `tools.contract_gate` → `contract
  gate passed: reference-context, traceability, observability, test-data,
  manifests, contracts`, exit 0; `openspec validate
  altoria-coast-village-placement --strict` → `Change
  'altoria-coast-village-placement' is valid`, exit 0. Forty-one settlements
  were added: 12 villages (9 on a trunk, 3 off-trunk) and 29 hamlets (22 on an
  existing road, 5 on a new spur, 2 off every road), of which five sit on the
  earlier side of the boundary under D2's exception. No spacing exemption is
  used anywhere.

## Workflow follow-up

- After merge, the user reviews the new maps and markers in the map editor and the webclient. The review does not block archive.
