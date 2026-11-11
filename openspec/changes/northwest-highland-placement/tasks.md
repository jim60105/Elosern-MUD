# Tasks

Begin after `central-mountains-placement` and `ore-nest-griffin-species` are merged. Follow design.md verbatim, and transcribe the snippet files without editing any value.

## 0. Environment

- [ ] 0.1 Create the test environment file with `printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-belts.env`. Check: the file holds that single line.

## 1. Declarations

- [ ] 1.1 Append the two activity blocks of `snippets/monster_activity_rows.txt` (design D1). Check: `world.lore.tests.test_monster_activity` passes.
- [ ] 1.2 Append placement blocks 1–3 of `snippets/monster_placement_rows.txt` (design D1). Check: `uv run --locked python -c "import world.lore.monster_placement"` exits 0.
- [ ] 1.3 Apply block 4: in `_ECOLOGY_ZONE_DECLARATIONS`, replace only the `pool` tuple of each `highland_road_01` … `highland_road_08` row with the tuple listed for it (design D1). Check: `git diff` shows, for each of those eight rows, exactly two added `WeightedComposition` lines and no other change to the row; `world.lore.tests.test_monster_placement`, `world.maps.tests.test_population_geometry` and `world.maps.tests.test_monster_sites` pass.

## 2. Evidence and documentation

- [ ] 2.1 Run the remaining Verification labels and record the non-gating bootstrap duration observation (design D4 item 5). Check: every label passes.
- [ ] 2.2 Write the review subsection (design D4) and regenerate `content/map-reference-context.json` (design D5). Check: `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection contains no coordinate, density, count or timing.

## 3. Handoff

- [ ] 3.1 Run `uv run --locked python -m tools.contract_gate --change northwest-highland-placement` and `openspec validate northwest-highland-placement --strict`. Check: both exit 0, and no test file or shard manifest changed.
