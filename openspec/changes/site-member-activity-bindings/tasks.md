# Tasks

Future implementation only. Begin after `activity-group-formation` is merged. Follow design.md verbatim; synthetic catalogs only.

## 1. Schema, resolver and validation

- [x] 1.1 Apply design D1–D3 in `world/lore/monster_placement.py`. Extend `world/lore/tests/test_monster_placement.py` with: resolver precedence (override, row, composition) over synthetic rows; unknown row binding and unknown site binding rejected with `MonsterPlacementRegistryError`; `None` site override accepted; label accepted on a `(1, 1)` composition and rejected on a `(1, 2)` composition and when empty. The two requirements are added by this delta, so their tests carry no `covers_requirement` annotation before archive sync; the test → (requirement, scenario) table is handed off instead. Check: `world.lore.tests.test_monster_placement` passes and the shipped registry still publishes at import.

## 2. Writers, forecast and docs

- [x] 2.1 Apply design D4 to `regional_population.py` and `monster_sites.py`. Extend `world/maps/tests/test_monster_sites.py` with a synthetic no-override site holding a cohesive 2-member row and a solitary 1-member row (two groups, both site-owned, independent decisions) and a stationary-override site over the same composition (three groups); add a labelled one-member site whose individual's `key` equals the label and whose species/variant/site marker and group owner equal the unlabelled case. Extend `world/maps/tests/test_regional_population.py` with a row-bound zone birth. Check: the new classes pass under the focused command.
- [x] 2.2 Apply design D4 to `population_forecast.py`; extend `world/rules/tests/test_field_contact_boundaries.py` so a matured mixed-row site recovery and a row-bound zone birth project the committed group shapes. Apply design D5 and regenerate `content/map-reference-context.json`. Check: new tests pass and `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [x] 3.1 Run the touched focused labels, `uv run --locked python -m tools.observability_lint check`, `openspec validate site-member-activity-bindings --strict` and `uv run --locked python -m tools.contract_gate`; record commands and results in the developer section. Check: all exit 0, `.github/evennia-shards.json` is unchanged, and shipped site/composition declarations are unchanged.
