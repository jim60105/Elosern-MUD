# Spec Delta

## MODIFIED Requirements

### Requirement: population_for_coordinates is a pure, deterministic function over the bounded map
`world/maps/wilderness_population.py` SHALL define a frozen `MonsterPopulation` dataclass carrying
`tier: str` and `name_zh: str`, and a pure function `population_for_coordinates(x: int, y: int) ->
MonsterPopulation | None` that reads no database state, no network state, and no random or
wall-clock input.

#### Scenario: Same input always returns the same output
- **WHEN** `population_for_coordinates(x, y)` is called twice with the same `(x, y)` in the same
  process
- **THEN** both calls return the identical `MonsterPopulation` (or `None`)

#### Scenario: Returned tiers and names are known
- **WHEN** `population_for_coordinates` is evaluated across the full valid coordinate range
- **THEN** every non-`None` result has `tier` in `MONSTER_TIER_REGISTRY` and `name_zh` inside that
  tier's `example_monsters_zh`

#### Scenario: The north-gate approach coordinate resolves to a literal, spec-pinned monster
- **WHEN** `population_for_coordinates(60, 103)` is called (`capital_altoria`'s north-gate
  approach cell, and the fixed `CAPITAL_ENTRY_XY` constant)
- **THEN** it returns `MonsterPopulation(tier="low", name_zh="哥布林")` ;  the closed-form result of
  `12,667,711 % 3 == 1` selecting index 1 of `("史萊姆", "哥布林", "巨鼠")`, pinning the formula and
  the tier registry together against silent drift

#### Scenario: Higher-tier regions actually produce their tier
- **WHEN** a representative coordinate in `northwest_highland_forest` is evaluated
- **THEN** the returned population (when present) has `tier == "mid"`, and a representative coordinate
  in `north_deep_forest` or `central_mountains` returns `tier == "high"` when present

#### Scenario: A low-density coordinate can be unpopulated
- **WHEN** a coordinate in a low-density region (e.g. a coast) falls outside the hunting band and the
  presence formula yields `>= _REGION_DENSITY`
- **THEN** `population_for_coordinates` returns `None`

#### Scenario: Returned values are drawn from the tier registry
- **WHEN** `population_for_coordinates` returns a non-`None` population
- **THEN** its `tier` names a key of `world.lore.monsters.MONSTER_TIER_REGISTRY` and its `name_zh`
  is drawn from that tier's `example_monsters_zh`

#### Scenario: Region mappings are immutable and cover every registry key
- **WHEN** the function's `_REGION_TIER` and `_REGION_DENSITY` mappings are inspected
- **THEN** they are immutable and cover every key of `WILDERNESS_REGION_REGISTRY`:
  `western_hills_valleys`, `southwest_coast`, `southeast_coast`, and `eastern_plains` at `low` tier;
  `northwest_highland_forest` at `mid`; `north_deep_forest` and `central_mountains` at `high`

#### Scenario: Presence outside the hunting band follows the density formula
- **WHEN** presence is decided for a coordinate outside the hunting band
- **THEN** it uses `(x * 92821 + y * 68917) % 10 < _REGION_DENSITY[region]` with the named densities
  (6 / 3 / 3 / 3 / 7 / 8 / 8 in registry order)

#### Scenario: Name selection is formula-derived on every branch
- **WHEN** the returned monster name is selected, on any branch including the hunting band
- **THEN** it uses `name_index = (x * 92821 + y * 68917) % len(tier.example_monsters_zh)` ;  the same
  multiplier pair as the terrain spec, with the index expression explicit so the entry pin is
  formula-derived, not special-cased

#### Scenario: Density tuning does not create an approval mirror
- **WHEN** valid authored regional density changes
- **THEN** production checks preserve determinism, references and hunting placement invariants without a second density table; fixed synthetic density fixtures prove deterministic placement boundaries

