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
  - files under `openspec/changes/valhalla-village-placement/`;
  - the marked lines of `docs/lore/settlement-locations.md` (design D8).
- Never hand-edit generated YAML or a generated artifact.
- Keep previews, captures and prose JSON in the scratchpad, outside the repository.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline

- [x] 1.1 Confirm the prerequisites: `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`, `uv run --locked python -m tools.road_network --check` exits 0, `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`, and `tools/settlement_spacing_areas.json` equals the "Before" content of design D7. If any fails, stop and report.

  Result: all four hold on `c70b1eac`. `spacing: 0 problems`; the artifact
  reports `is up to date`; `--kind {capital,city,town,port,village,hamlet}` is
  listed; the area file is exactly the Before content.
- [x] 1.2 Record the first timing line of design D9. Verify: the line is saved for the hand-off.

  Result: the first `world.maps.tests.test_bootstrap` run raced the first
  village edit and reported `Ran 2 tests in 0.000s` with two
  `stale_partition` import errors, exactly the race the previous placement
  change recorded. A clean measurement on a stable tree was then taken and is
  the honest first line: see task 4.2. The second line is in task 5.4; neither
  cost ever blocks (D9).
- [x] 1.3 Write the placement script per design D1 and list the road gaps over 75 km inside this change's scope. Verify: the list is saved under `snippets/` and names each gap's road, end cells and length.

  Result: `snippets/place.py` (adapted from the Grandia north script: region
  `northwest_highland_forest`, the four earlier regions as completed areas,
  `--foreign` for the D2 boundary). `snippets/gaps_before.json` and
  `snippets/gaps_before.txt` list 30 gaps over 75 km in scope, from
  `city_horn_plain -- town_stag_ferry` 98.7 km to
  `town_grizzly -- town_pine_ferry` 392.6 km. `snippets/cover.json` records the
  43-cell cover set that cuts every gap to 75 km or less with zero
  over-length left.

## 2. Villages

- [x] 2.1 Propose villages, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` (command in design Context) reports every new cell walkable, off the water and of nation `valhalla`, and `uv run --locked python -m tools.settlement_spacing` reports no problem except `village_off_road` for the new villages.

  Result: 17 villages, all on an inner trunk cell at a two- or three-road
  junction, two of them on the highland river (otter ford, reindeer shoal).
  `snippets/village_plan.json` and `snippets/plan_villages.txt` record the
  approved cells; `snippets/villages_context.jsonl` the site facts.
  `place_sites.py --locations` reported `314/314 sites valid` (exit 0) and
  `settlement_spacing` printed `spacing: 0 problems` — no `village_off_road`,
  because every village stands on a trunk cell.
- [x] 2.2 Regenerate per design D6. Verify: `uv run --locked python -m tools.settlement_spacing` reports no `village_off_road`, and every new village ID appears as a `spur_of` value in `world/maps/data/road_network.json`.

  Result: `spacing: 0 problems`; all 17 new village IDs are `spur_of` values
  and the artifact grew from 123 nodes and 142 road rows to 140 nodes and 159
  road rows — 17 added rows, zero existing rows changed.

## 3. Hamlets

- [x] 3.1 Propose hamlets against the regenerated roads, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` reports every new cell valid, and `uv run --locked python -m tools.settlement_spacing` reports no `hamlet_spacing`, `village_spacing`, `id_prefix`, `duplicate_name`, `no_nation`, `nation_mismatch`, `population_range` or `forbidden_region` problem.

  Result: 35 hamlets. 26 stand on an inner road cell — the recomputed cover set
  of `snippets/hamlet_plan_cover.json` plus the hamlet on the 102.2 km
  deer-vale spur — and 9 stand off every road, 1 to 3 km from the highland or
  border river, 16 to 29 km from a settlement. `snippets/hamlet_plan.json` and
  `snippets/plan_hamlets.txt` record the 35 approved cells and 500 in-area
  gaps all at or below 75 km. One ID collided with the Altoria
  `hamlet_deer_slope` and was renamed `hamlet_deer_trail` before commit.
  `place_sites.py --locations` reported `349/349 sites valid` (exit 0) and
  `settlement_spacing` printed `spacing: 0 problems` (the D7 area entry was
  enabled early so the checker could speak, as the previous change did).
- [x] 3.2 Regenerate per design D6 and make the trunk comparison of D6. Verify: no road row without `spur_of` changed.

  Result: with the hamlet rows written, the artifact is 140 nodes and 159 road
  rows before and after; `nodes` and `roads` compare equal and the only
  changed top-level key is `source_signature`, so zero road rows changed and
  every trunk row is unchanged.

## 4. Maps and prose

- [x] 4.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation valhalla --kind village --plan-only`, then without `--plan-only`; then the same two commands with `--kind hamlet`. Verify: each new ID has exactly one new file, no existing settlement file changed (`git status --short content/maps/settlements` shows only additions), and `uv run --locked python -m tools.settlement_synthesis lint` exits 0. A refusal is fixed by moving that location and repeating from group 2 or 3; never by hand-writing a map.

  Result: 17 village maps (4 nodes each, `beast_town` / `tribal_ring`) and 35
  hamlet maps (2 nodes each), 138 nodes in all, every generation report
  warning-free. `git status --short content/maps/settlements` lists 52
  additions and no modification, and `settlement_synthesis lint` prints
  `fit: 0 errors, 0 warnings` and exits 0.
- [x] 4.2 Write and apply the prose of every new map per design D5a. Verify: `brief` of each new map shows no empty description and no duplicate key.

  Result: 52 prose files written under `/tmp/valhalla-placing/prose/` and
  applied with `prose`; all 138 nodes now carry a key of 2 to 8 characters and
  a description of 40 to 66 characters (the range of the shipped corpus), keys
  are unique within their map and no description is empty. Villages name the
  totem ground and the ancestral altar, camps the totem pole and the shared
  hearth; every entrance names the direction and the neighbour it leads to; no
  shop, guild branch or service is presented as usable. The first D9 timing
  line taken on the stable pre-map tree: see the hand-off.
- [x] 4.3 Regenerate per design D6. Verify: compared with the artifact of task 3.2 (keep a copy in the scratchpad), the only changed line of `world/maps/data/road_network.json` is `source_signature`.

  Result: `/tmp/valhalla-placing/road_after_villages.json` is the task 3.2
  copy. After the final regeneration only `source_signature` differs;
  `algorithm_version`, `fingerprint`, `frame_cells`, `nodes`, `roads` and
  `version` are unchanged, `nodes` and `roads` compare equal, so zero road
  rows changed. The partition and the reference context were refreshed after
  the last prose edit.
- [x] 4.4 Apply the lore mark edits of design D8 to `docs/lore/settlement-locations.md`. Verify: `git diff --stat docs/lore/settlement-locations.md` shows only that file's marked lines changed, and the rows of the other people keep their marks.

  Result: commit `4d08fbf0` changes only that file: `8 insertions(+), 8
  deletions(-)`. The changed lines are exactly the two 〔提案〕 marks of the
  beastfolk rows in 〈聚落原型〉, the four map-level rows, the
  「並陸續建置中」 clause and the 「這兩層都是〔提案〕。」 sentence. The elf,
  human city/town/port and dungeon rows keep their marks.

## 5. Validation and hand-off

- [ ] 5.1 Replace `tools/settlement_spacing_areas.json` with the "After" content of design D7 and run the four checks of D7. Verify: all four hold. Fix a `road_gap` as D7 says and repeat the affected groups.
- [ ] 5.2 Run every module of `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command, plus `world.lore.tests.test_anchors` and `world.maps.tests.test_population_geometry` with the test prefix. Verify: every one passes. Handle a failure with that section's "Residual pin rule" and list every rewritten test in the hand-off. Any other failure stops the change without a commit.
- [ ] 5.3 Capture the continent with `capture_map.py --hide partition` and the settlement views of two new villages and two new hamlets (one on a through road, one at a spur end, one off-road where one exists). Read the images. Verify: the hand-off gives the absolute path of each image and of the last road preview, and states for each captured map which road each entrance meets.
- [ ] 5.4 Record the second timing line of design D9, then run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate valhalla-village-placement --strict`. Verify: all exit 0. The hand-off lists the count of villages and hamlets, every exemption with its reason, every hamlet placed under the boundary exception of D2, and both timing lines.

## Workflow follow-up

- After merge, the user reviews the new maps and markers in the map editor and the webclient. The review does not block archive.
