# Delta: wilderness-monster-population (wilderness-anchor-footprint)

## MODIFIED Requirements

### Requirement: population_for_coordinates is a pure, deterministic function over the bounded map
`world/maps/wilderness_population.py` SHALL define a frozen `MonsterPopulation` dataclass carrying
`tier: str` and `name_zh: str`, and a pure function `population_for_coordinates(x: int, y: int) ->
MonsterPopulation | None`. For every valid `(x, y)`, the function SHALL read no database state, no
network state, no random or wall-clock input, and SHALL return the same value for the same input on
every call. A returned `tier` SHALL name a key of `world.lore.monsters.MONSTER_TIER_REGISTRY`, and a
returned `name_zh` SHALL be drawn from that tier's `example_monsters_zh`.

The function SHALL define immutable `_REGION_TIER` and `_REGION_DENSITY` mappings covering every key
of `WILDERNESS_REGION_REGISTRY`: `western_hills_valleys`, `southwest_coast`, `southeast_coast`, and
`eastern_plains` at `low` tier; `northwest_highland_forest` at `mid`; `north_deep_forest` and
`central_mountains` at `high`. Presence outside the hunting band SHALL use
`(x * 92821 + y * 68917) % 10 < _REGION_DENSITY[region]` with the named densities (6 / 3 / 3 / 3 / 7 /
8 / 8 in registry order). The returned monster name SHALL be selected by
`name_index = (x * 92821 + y * 68917) % len(tier.example_monsters_zh)` on every branch, hunting band
included — the same multiplier pair as the terrain spec, with the index expression explicit so the
entry pin is formula-derived, not special-cased.

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
- **THEN** it returns `MonsterPopulation(tier="low", name_zh="哥布林")` — the closed-form result of
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

### Requirement: A hunting band around the capital's north gate always hosts a low-tier monster
Every provider-valid coordinate within Chebyshev distance 3 of the `capital_altoria` entry's
north-gate `approach_cell` `(60, 103)` — the cell a traveler lands on leaving the 北門 toward the
open wilderness — SHALL be present in the population at `low` tier, independent of the density
formula, so the introductory hunt (討伐低階魔物) is reliably completable immediately after leaving
the North Gate. Cells inside any anchor footprint are outside the provider's valid set and are not
band members.

#### Scenario: The north-gate approach coordinate is always populated at low tier
- **WHEN** `population_for_coordinates(60, 103)` is called
- **THEN** it returns a `MonsterPopulation` with `tier == "low"`

#### Scenario: The hunting band is contiguous over valid ground around the north gate
- **WHEN** `population_for_coordinates` is called for every provider-valid coordinate within
  Chebyshev distance 3 of `(60, 103)`
- **THEN** every result is a `MonsterPopulation` with `tier == "low"`, never `None`, and the
  footprint cells of `capital_altoria` inside the band's square are skipped rather than populated
