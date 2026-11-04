# Tasks

Future implementation only. Begin after `site-member-activity-bindings`, `weak-species-habitats`, `wax-pouch-rat-species` and `sticky-palm-goblin-species` are merged. Follow design.md verbatim.

## 1. Declarations

- [ ] 1.1 Append the areas, activities, composition and site (design D1, D2). Check: both lore modules import; `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity` and `world.maps.tests.test_population_geometry` pass.

## 2. Evidence and documentation

- [ ] 2.1 Add `world/maps/tests/test_content_expansion_sites.py` with `TransferStationEncounterTests`, its shard entry and freeze-ledger entry (design D3). Check: the class passes under the focused command and `world.maps.tests.test_monster_sites` still passes.
- [ ] 2.2 Write the review subsection (design D4) with the smoke results; regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [ ] 3.1 Run the design.md Verification labels, `openspec validate abandoned-transfer-station-encounter --strict` and `uv run --locked python -m tools.contract_gate`. Check: all exit 0 and the new module has exactly one shard owner.
