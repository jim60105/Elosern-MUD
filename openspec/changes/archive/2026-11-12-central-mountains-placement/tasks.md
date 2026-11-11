# Tasks

Begin after `north-deep-forest-placement` and `rime-scale-serpent-species` are merged. Follow design.md verbatim, and transcribe the snippet files without editing any value.

## 0. Environment

- [x] 0.1 Create the test environment file with `printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-belts.env`. Check: the file holds that single line.

## 1. Declarations

- [x] 1.1 Append the two activity blocks of `snippets/monster_activity_rows.txt` (design D1). Check: `world.lore.tests.test_monster_activity` passes.
- [x] 1.2 Append the three placement blocks of `snippets/monster_placement_rows.txt` (design D1). Check: `world.lore.tests.test_monster_placement`, `world.maps.tests.test_population_geometry` and `world.maps.tests.test_monster_sites` pass.

## 2. Evidence and documentation

- [x] 2.1 Run the remaining Verification labels and record the non-gating bootstrap duration observation (design D4 item 4). Check: every label passes.
- [x] 2.2 Write the review subsection (design D4) and regenerate `content/map-reference-context.json` (design D5). Check: `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection contains no coordinate, density, count or timing.

## 3. Handoff

- [x] 3.1 Run `uv run --locked python -m tools.contract_gate --change central-mountains-placement` and `openspec validate central-mountains-placement --strict`. Check: both exit 0, and no test file or shard manifest changed.
