# Tasks

Future implementation only. Begin after `reservoir-warden-variant`, `ember-bristle-boar-species`, `abandoned-transfer-station-encounter` and `site-member-activity-bindings` are merged. Follow design.md verbatim.

## 1. Declarations

- [x] 1.1 Append the areas, activities, compositions and sites (design D1, D2). Check: both lore modules import; `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity` and `world.maps.tests.test_population_geometry` pass; `tide_mouth_boss_site` is unchanged.

## 2. Evidence and documentation

- [x] 2.1 Add `HighTierBossSiteTests` (design D3). Check: it and `TransferStationEncounterTests` pass under the focused command.
- [x] 2.2 Extend the review subsection (design D4); regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [x] 3.1 Run the design.md Verification labels, `openspec validate high-tier-boss-sites --strict` and `uv run --locked python -m tools.contract_gate`. Check: all exit 0; `.github/evennia-shards.json` is unchanged.
