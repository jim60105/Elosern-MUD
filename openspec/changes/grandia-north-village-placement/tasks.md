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
  - files under `openspec/changes/grandia-north-village-placement/`.

- Never hand-edit generated YAML or a generated artifact.
- Keep previews, captures and prose JSON in the scratchpad, outside the repository.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline

- [x] 1.1 Confirm the prerequisites: `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`, `uv run --locked python -m tools.road_network --check` exits 0, `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`, and `tools/settlement_spacing_areas.json` equals the "Before" content of design D7. If any fails, stop and report.

  Result: all four hold on `c082d80c`. `spacing: 0 problems`; the road
  artifact reports `is up to date`; `generate --help` lists
  `--kind {capital,city,town,port,village,hamlet}`; the area file is exactly
  the Before content.
- [x] 1.2 Record the first timing line of design D9. Verify: the line is saved for the hand-off.

  Result: `Ran 46 tests in 334.189s` (one error: `invalid map world: road
  network artifact is not current`, because the run started before the first
  village rows and finished after they were written, so its adoption step saw
  the stale artifact). The cost line is valid; the error is the racing edit,
  not a test finding. The end-of-change run is recorded in task 5.4.
- [x] 1.3 Write the placement script per design D1 and list the road gaps over 75 km inside this change's scope. Verify: the list is saved under `snippets/` and names each gap's road, end cells and length.

  Result: `snippets/place.py`, `snippets/gaps_before.json` and
  `snippets/gaps_before.txt`. Fifteen gaps over 75 km in scope, from
  `capital_grandia -- city_imperial_ferry` 147.3 km to `city_imperial_ferry --
  town_east_pasture` 422.7 km. The `cover --foreign` command found a 51-cell
  on-road set that cuts every gap to 75 km or less with zero over-length left;
  fourteen of those cells lie on the southern side of the y 1100 boundary and
  are the boundary hamlets of design D2.

## 2. Villages

- [x] 2.1 Propose villages, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` (command in design Context) reports every new cell walkable, off the water and of nation `grandia`, and `uv run --locked python -m tools.settlement_spacing` reports no problem except `village_off_road` for the new villages.

  Result: 14 villages, 10 on an inner trunk cell and 4 off-trunk
  (`village_bulrush_bend`, `village_channel_mouth`, `village_tide_meadow`,
  `village_reed_shore`, at 24 to 41 km from the nearest trunk on the imperial
  west tributary and the east coast river). `place_sites.py --locations`
  reports `249/249 sites valid` (exit 0); `settlement_spacing` reports exactly
  four problems, all `village_off_road`, for those four sites. No exemption.
- [x] 2.2 Regenerate per design D6. Verify: `uv run --locked python -m tools.settlement_spacing` reports no `village_off_road`, and every new village ID appears as a `spur_of` value in `world/maps/data/road_network.json`.

  Result: `spacing: 0 problems`; all 14 new village IDs are `spur_of` values
  and the road artifact grew from 109 nodes and 128 road rows to 123 nodes and
  142 road rows. Three new spur rows are longer than 75 km:
  `village_birch_hollow` 146.6 km and `village_grain_hollow` 129.0 km copy a
  prefix of their trunk cell for cell, where the trunk gaps are already 72 to
  74 km, so only `village_channel_mouth` at 91.8 km needs an internal hamlet;
  task 3.1 adds one on it.

## 3. Hamlets

- [x] 3.1 Propose hamlets against the regenerated roads, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` reports every new cell valid, and `uv run --locked python -m tools.settlement_spacing` reports no `hamlet_spacing`, `village_spacing`, `id_prefix`, `duplicate_name`, `no_nation`, `nation_mismatch`, `population_range` or `forbidden_region` problem.

  Result: 48 hamlets. 42 stand on a road cell — 41 of the cover set and
  `hamlet_saddle_hollow` on the 91.8 km channel-mouth spur — and 6 stand off
  every road (`hamlet_shore_farm`, `hamlet_willow_dike`,
  `hamlet_bulrush_dike`, `hamlet_lotus_pond`, `hamlet_caltrop_shore`,
  `hamlet_reed_pond`). Fourteen of the on-road hamlets lie south of the
  y 1100 boundary under design D2: `hamlet_channel_plain`, `hamlet_bean_plain`,
  `hamlet_caltrop_pond`, `hamlet_fallow_field`, `hamlet_locust_plain`,
  `hamlet_bulrush_shoal`, `hamlet_bean_knoll`, `hamlet_alfalfa_plain`,
  `hamlet_reed_bar`, `hamlet_river_beach`, `hamlet_alfalfa_knoll`,
  `hamlet_buckwheat_slope`, `hamlet_parasol_knoll`, `hamlet_channel_beach`.
  `place_sites.py --locations` reports `297/297 sites valid` (exit 0);
  `settlement_spacing` reports `spacing: 0 problems`, and no identity,
  population or region problem.

  Boundary evidence: `place.py context` on the 14 southern cells reports
  `"region": "eastern_plains", "scope": "boundary"` for each, and every one
  carries a road of the artifact: `city_imperial_ferry -- town_east_pasture`
  (6), `port_tide_wind -- town_east_pasture` (4),
  `town_maple_foot -- town_steed_plain` (3),
  `city_imperial_ferry -- city_starglow` (1). None lies in
  `southeast_coast`.
- [x] 3.2 Regenerate per design D6 and make the trunk comparison of D6. Verify: no road row without `spur_of` changed.

  Result: the artifact is 123 nodes and 142 road rows before and after; the
  only changed top-level field is `source_signature`, `nodes` and `roads` are
  byte-identical, so zero road rows changed and every trunk row is unchanged.
  The real checker now reads the D7 "After" area list early (see task 5.1) and
  prints `spacing: 0 problems`; `snippets/gaps_after.txt` records the empty
  gap report and `snippets/plan_after.txt` the 48 valid hamlet candidates with
  no remaining over-length gap.

## 4. Maps and prose

- [x] 4.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation grandia --kind village --plan-only`, then without `--plan-only`; then the same two commands with `--kind hamlet`. Verify: each new ID has exactly one new file, no existing settlement file changed (`git status --short content/maps/settlements` shows only additions), and `uv run --locked python -m tools.settlement_synthesis lint` exits 0. A refusal is fixed by moving that location and repeating from group 2 or 3; never by hand-writing a map.

  Result: 14 village maps (4 nodes each) and 48 hamlet maps (2 nodes each),
  152 nodes in all, every generation report warning-free. `git status --short
  content/maps/settlements` lists 62 additions and no modification, and
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings` and exits 0.
- [x] 4.2 Write and apply the prose of every new map per design D5a. Verify: `brief` of each new map shows no empty description and no duplicate key.

  Result: 62 prose files written under `/tmp/grandia-north/` and applied with
  `prose`; every one of the 152 nodes now carries a key of 2 to 8 characters
  and a description of 40 to 140 characters, keys are unique within their map
  and no description is empty. Villages name the green, its well and the church
  front; hamlets name the crossing and the single farmstead; each entrance
  names the direction or the neighbour it leads to; no shop, guild branch or
  service is presented as usable.
- [x] 4.3 Regenerate per design D6. Verify: compared with the artifact of task 3.2 (keep a copy in the scratchpad), the only changed line of `world/maps/data/road_network.json` is `source_signature`.

  Result: `algorithm_version`, `fingerprint`, `frame_cells`, `nodes`, `roads`
  and `version` are unchanged; only `source_signature` differs, and `nodes`
  and `roads` compare equal, so zero road rows changed. The partition and the
  reference context were refreshed after the last prose edit.

## 5. Validation and hand-off

- [x] 5.1 Replace `tools/settlement_spacing_areas.json` with the "After" content of design D7 and run the four checks of D7. Verify: all four hold. Fix a `road_gap` as D7 says and repeat the affected groups.

  Result: all four hold. The "After" area list (full `eastern_plains`, no
  bounds) was enabled after task 3.2, before any map was written, so the real
  checker could speak early; `snippets/spacing_after.txt` and
  `snippets/plan_after.txt` record that run. Final state:
  `tools.settlement_spacing` prints `spacing: 0 problems`;
  `check_map_sources.py` reports `cross-file problems: 0`, `district
  partition: current`, `wilderness elevation: current`, `reference context:
  current` and `RESULT: game-ready as far as static checks can tell`, exit 0;
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings`;
  `road_network --check` and `map_reference_context --check` both report `is
  up to date`, exit 0. Enabling the full region surfaced no remaining road
  gap.
- [ ] 5.2 Run every module of `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command, plus `world.lore.tests.test_anchors` and `world.maps.tests.test_population_geometry` with the test prefix. Verify: every one passes. Handle a failure with that section's "Residual pin rule" and list every rewritten test in the hand-off. Any other failure stops the change without a commit.
- [x] 5.3 Capture the continent with `capture_map.py --hide partition` and the settlement views of two new villages and two new hamlets (one on a through road, one at a spur end, one off-road where one exists). Read the images. Verify: the hand-off gives the absolute path of each image and of the last road preview, and states for each captured map which road each entrance meets.

  Result: six images rendered and read. Continent:
  `/tmp/grandia-north/continent.webp` (`--hide partition`) and the
  north-eastern region `/tmp/grandia-north/continent_north.png`
  (`--bounds 1578 1056 2627 1930`). Settlements:
  `/tmp/grandia-north/village_wheat_slope.png`,
  `/tmp/grandia-north/village_bulrush_bend.png`,
  `/tmp/grandia-north/hamlet_duckweed_bend.png`,
  `/tmp/grandia-north/hamlet_lotus_pond.png`. Entrances:
  `village_wheat_slope` has a north-east and a south-west entrance on the
  capital to wheat wave highway — north-east toward the wheat wave city,
  south-west toward the capital. `village_bulrush_bend` has one north entrance
  at the end of its spur `town_maple_foot--village_bulrush_bend`, facing the
  maple foot town; its south lane is the river-side village end.
  `hamlet_duckweed_bend` has a south and a north-west entrance on the capital
  to imperial ferry trunk, south toward the imperial ferry city and north-west
  toward the capital. `hamlet_lotus_pond` touches no road; its one south
  entrance faces the wilderness toward the hemp plain village. The last road
  preview is `/tmp/grandia-north/roads_final2.png`; earlier runs left
  `roads_villages.png`, `roads_hamlets.png` and `roads_final.png`. The capture
  reported one advisory diagnostic about `city_imperial_ferry`'s footprint
  offset, which belongs to an earlier change.
- [ ] 5.4 Record the second timing line of design D9, then run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate grandia-north-village-placement --strict`. Verify: all exit 0. The hand-off lists the count of villages and hamlets, every exemption with its reason, every hamlet placed under the boundary exception of D2, and both timing lines.

## Workflow follow-up

- After merge, the user reviews the new maps and markers in the map editor and the webclient. The review does not block archive.
