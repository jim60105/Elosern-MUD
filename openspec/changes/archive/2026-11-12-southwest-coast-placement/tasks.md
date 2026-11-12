# Tasks

Begin after `southeast-coast-placement` and `wreck-arm-octopus-species` are merged. Follow design.md verbatim, and transcribe the snippet files without editing any value.

## 0. Environment

- [x] 0.1 Create the test environment file with `printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-belts.env`. Check: the file holds that single line.

## 1. Declarations

- [x] 1.1 Append the two activity blocks of `snippets/monster_activity_rows.txt` (design D1). Check: `world.lore.tests.test_monster_activity` passes.
- [x] 1.2 Append placement blocks 1–3 of `snippets/monster_placement_rows.txt` (design D1). Check: `uv run --locked python -c "import world.lore.monster_placement"` exits 0.
- [x] 1.3 Apply block 4: in `_ECOLOGY_ZONE_DECLARATIONS`, replace only the `pool` tuple of `port_fishers_cove_hinterland`, `port_south_tide_hinterland`, `port_white_sail_hinterland`, `southwest_road_01` and `southwest_road_02` with the tuple listed for it (design D1). Check: `uv run --locked python -c "import world.lore.monster_placement"` exits 0; `git diff` shows exactly two added `WeightedComposition` lines for each port hinterland row, exactly one for each of the two corridor rows, and no other change to those rows; `world.lore.tests.test_monster_placement`, `world.maps.tests.test_population_geometry` and `world.maps.tests.test_monster_sites` pass. If a geometry label reports a shared cell or overlapping grounds caused by a row merged after this proposal, move only the conflicting new rectangle (and its grounds and defended extent together) under the design D2 rules, and record the move in the D4 subsection.

## 2. Evidence and documentation

- [x] 2.1 Run the remaining Verification labels and record the non-gating bootstrap duration observation (design D4 item 5). Check: every label passes.
- [x] 2.2 Write the review subsection (design D4) and regenerate `content/map-reference-context.json` (design D5); after any rebase, regenerate that file with the command again and never resolve a conflict in it by hand. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection contains no coordinate, density, count or timing.

## 3. Handoff

- [x] 3.1 Run `uv run --locked python -m tools.contract_gate --change southwest-coast-placement` and `openspec validate southwest-coast-placement --strict`. Check: both exit 0, and no test file or shard manifest changed.
