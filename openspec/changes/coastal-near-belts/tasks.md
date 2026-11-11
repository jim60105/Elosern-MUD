# Tasks

Begin after `western-hills-near-belts` is merged. Follow design.md verbatim, and transcribe the snippet files without editing any value.

## 1. Declarations

- [ ] 1.1 Append the two activity blocks of `snippets/monster_activity_rows.txt` (design D1). Check: `world.lore.tests.test_monster_activity` passes.
- [ ] 1.2 Append the two placement blocks of `snippets/monster_placement_rows.txt` (design D1). Check: `world.lore.tests.test_monster_placement` and `world.maps.tests.test_population_geometry` pass, and `git diff --stat` shows only the two lore modules changed so far.

## 2. Evidence and documentation

- [ ] 2.1 Run the remaining Verification labels and record the non-gating bootstrap duration observation (design Risks). Check: every label passes.
- [ ] 2.2 Write the review subsection (design D4) and regenerate `content/map-reference-context.json` (design D5). Check: `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection holds no coordinate, density, count or timing.

## 3. Handoff

- [ ] 3.1 Run `uv run --locked python -m tools.contract_gate --change coastal-near-belts` and `openspec validate coastal-near-belts --strict`. Check: both exit 0, and no test file or shard manifest changed.
