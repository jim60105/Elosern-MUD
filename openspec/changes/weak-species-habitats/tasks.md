# Tasks

Future implementation only. Begin after `activity-group-formation`, `mudfilm-slime-species`, `wax-pouch-rat-species` and `sticky-palm-goblin-species` are merged. Follow design.md verbatim.

## 1. Declarations

- [ ] 1.1 Append the activity areas and activities (design D1, D2). Check: importing `world.lore.monster_activity` raises nothing and `world.lore.tests.test_monster_activity` passes, including `test_every_shipped_reference_resolves`.
- [ ] 1.2 Append the compositions and zones (design D3, D4). Check: importing `world.lore.monster_placement` raises nothing; `world.lore.tests.test_monster_placement` (all shipped-row classes) and `world.maps.tests.test_population_geometry` pass.

## 2. Evidence and documentation

- [ ] 2.1 Run `world.maps.tests.test_bootstrap` and `world.maps.tests.test_regional_population` focused labels; write the review subsection (design D5) with those results; regenerate `content/map-reference-context.json`. Check: tests pass, `uv run --locked python -m tools.map_reference_context --check` exits 0, and the subsection contains no coordinate, density or count and records the slime damp-cell deviation.

## 3. Handoff

- [ ] 3.1 Run `openspec validate weak-species-habitats --strict` and `uv run --locked python -m tools.contract_gate`. Check: both exit 0; no test file or shard manifest changed.
