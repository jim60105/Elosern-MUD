# Tasks

Begin after `eastern-plains-deep-placement` and `breakwater-seal-species` are merged. Follow design.md verbatim, and transcribe the snippet files without editing any value.

## 0. Environment

- [x] 0.1 Create the test environment file with `printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-belts.env`. Check: the file holds that single line.

## 1. Declarations

- [x] 1.1 Append the two activity blocks of `snippets/monster_activity_rows.txt` (design D1). Check: `world.lore.tests.test_monster_activity` passes.
- [x] 1.2 Append placement blocks 1–3 of `snippets/monster_placement_rows.txt` (design D1). Check: `uv run --locked python -c "import world.lore.monster_placement"` exits 0.
- [x] 1.3 Apply block 4: in `_ECOLOGY_ZONE_DECLARATIONS`, replace only the `pool` tuple of `port_east_bay_hinterland`, `port_golden_sheaf_hinterland`, `port_south_cape_hinterland` and `southeast_road_01` with the tuple listed for it (design D1). Check: `uv run --locked python -c "import world.lore.monster_placement"` exits 0; `git diff` shows exactly two added `WeightedComposition` lines for each port hinterland row, exactly one for `southeast_road_01`, and no other change to those rows; `world.lore.tests.test_monster_placement`, `world.maps.tests.test_population_geometry` and `world.maps.tests.test_monster_sites` pass.

## 2. Evidence and documentation

- [x] 2.1 Run the remaining Verification labels and record the non-gating bootstrap duration observation (design D4 item 5). Check: every label passes.
  - Note: `world.maps.tests.test_bootstrap.test_bootstrap_grid` is the one label not run — design D4 makes it a non-gating observation and the local command-duration budget forbids the label — so no before or after duration was collected and D4 item 5's duration is explicitly unfulfilled (recorded in the review subsection). Every other Verification label passed.
- [x] 2.2 Write the review subsection (design D4) and regenerate `content/map-reference-context.json` (design D5). Check: `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection contains no coordinate, density, count or timing.

## 3. Handoff

- [x] 3.1 Run `uv run --locked python -m tools.contract_gate --change southeast-coast-placement` and `openspec validate southeast-coast-placement --strict`. Check: both exit 0, and no test file or shard manifest changed.
