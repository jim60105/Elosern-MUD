# wilderness-monster-population Specification

## Purpose

The deterministic, offline-computable monster population for the wilderness/Virtual layer: a pure
coordinate-to-monster model and an idempotent spawn/respawn service that places `Monster` objects at
wilderness coordinates via the wilderness script's `itemcoordinates`, guaranteeing huntable low-tier
monsters near `capital_altoria`'s entry point. No LLM, no RNG, no database reads in the population
decision.

## ADDED Requirements

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

#### Scenario: The entry coordinate resolves to a literal, spec-pinned monster
- **WHEN** `population_for_coordinates(60, 100)` is called (`capital_altoria`'s registered wilderness
  entry point, and the fixed `CAPITAL_ENTRY_XY` constant)
- **THEN** it returns `MonsterPopulation(tier="low", name_zh="哥布林")` — the closed-form result of
  `12,460,960 % 3 == 1` selecting index 1 of `("史萊姆", "哥布林", "巨鼠")`, pinning the formula and
  the tier registry together against silent drift

#### Scenario: Higher-tier regions actually produce their tier
- **WHEN** a representative coordinate in `northwest_highland_forest` is evaluated
- **THEN** the returned population (when present) has `tier == "mid"`, and a representative coordinate
  in `north_deep_forest` or `central_mountains` returns `tier == "high"` when present

#### Scenario: A low-density coordinate can be unpopulated
- **WHEN** a coordinate in a low-density region (e.g. a coast) falls outside the hunting band and the
  presence formula yields `>= _REGION_DENSITY`
- **THEN** `population_for_coordinates` returns `None`

### Requirement: A hunting band around the capital entry always hosts a low-tier monster
Every coordinate within Chebyshev distance 3 of `capital_altoria`'s registered wilderness entry point
`(60, 100)` SHALL be present in the population at `low` tier, independent of the density formula, so
the introductory hunt (討伐低階魔物) is reliably completable immediately after leaving the North Gate.

#### Scenario: The entry coordinate is always populated at low tier
- **WHEN** `population_for_coordinates(60, 100)` is called
- **THEN** it returns a `MonsterPopulation` with `tier == "low"`

#### Scenario: The hunting band is contiguous around the entry point
- **WHEN** `population_for_coordinates` is called for every coordinate within Chebyshev distance 3 of
  `(60, 100)`
- **THEN** every result is a `MonsterPopulation` with `tier == "low"`, never `None`

### Requirement: ensure_population idempotently places and respawns monsters at a coordinate
`world/maps/wilderness_population.py` SHALL define `ensure_population(wilderness, coordinates) ->
None` that reconciles a wilderness coordinate against `population_for_coordinates`. Every monster it
creates SHALL carry a persistent ownership marker `monster.db.population_key ==
"wilderness:{x}:{y}"` for its coordinate; reconciliation SHALL act only on monsters bearing a matching
marker and SHALL never delete, move, or modify any other `Monster` at the coordinate:
- When the model returns `None`, SHALL delete and remove from `wilderness.db.itemcoordinates` every
  marker-matching `Monster` at the coordinate (stale-cleanup), leaving foreign monsters untouched.
- When the model returns a population, SHALL reconcile the coordinate to exactly one living
  marker-matching `Monster`: delete/pop dead or surplus marker-matching monsters, then create one
  `Monster` with `threat_tier` set to the model's tier, `apply_monster_tier("floor")` applied, its
  `db.skills` left at the innate-only default, `db.population_key` set, registered at
  `wilderness.db.itemcoordinates[monster] == coordinates`, and `.location` set to the room currently
  active at that coordinate if one exists. When exactly one living marker-matching monster whose
  `threat_tier` and key still match the model already exists, SHALL make no change; a marker-matching
  monster that has drifted from the model (wrong tier or name), a dead marker-matching monster, or any
  surplus marker-matching monsters SHALL be deleted and replaced by one fresh `Monster` matching the
  model.

The created monster SHALL be engageable and defeatable through the existing player combat-session
path without further setup.

#### Scenario: An empty coordinate is populated once
- **WHEN** `ensure_population` is called for a coordinate whose model returns a population and which
  has no marker-matching monster
- **THEN** exactly one `Monster` is created, registered in `itemcoordinates` at that coordinate, with
  matching `threat_tier`, matching `population_key`, and innate combat readiness

#### Scenario: Repeated calls create no duplicates
- **WHEN** `ensure_population` is called twice in succession for the same populated coordinate
- **THEN** exactly one `Monster` remains registered at that coordinate after the second call

#### Scenario: A dead monster is replaced on the next call
- **WHEN** the marker-matching `Monster` registered at a populated coordinate has non-positive stored
  HP and `ensure_population` is called again
- **THEN** the dead monster is removed and replaced by a fresh living `Monster` of the same model tier
  and the same `population_key`

#### Scenario: Dead or surplus matching monsters are cleaned to exactly one living monster
- **WHEN** a populated coordinate holds one living marker-matching `Monster` plus any additional
  dead or surplus marker-matching `Monster`s and `ensure_population` is called
- **THEN** exactly one living marker-matching `Monster` remains at the coordinate after the call

#### Scenario: A matching monster that drifted from the model is reconciled
- **WHEN** a living marker-matching `Monster` at a populated coordinate has a `threat_tier` (or key)
  that no longer matches the current model and `ensure_population` is called
- **THEN** the drifted monster is deleted and replaced by one fresh `Monster` whose `threat_tier` and
  key match the model

#### Scenario: A coordinate the model no longer populates is cleaned up
- **WHEN** a marker-matching `Monster` is registered at a coordinate and `ensure_population` is called
  for that coordinate while the model returns `None`
- **THEN** the lingering `Monster` is deleted and no longer appears in `itemcoordinates`

#### Scenario: Foreign monsters at the coordinate are never reconciled
- **WHEN** a `Monster` without a matching `population_key` is present at a coordinate and
  `ensure_population` runs for that coordinate
- **THEN** the foreign monster is neither deleted, nor moved, nor modified by the reconciliation

### Requirement: A registered wilderness monster survives room recycling
A monster registered through `ensure_population` SHALL be tracked by the wilderness script's
`itemcoordinates` rather than by room contents, so that when a `TerrainRoom` is recycled and later a
room is activated again at the monster's coordinate, the contrib re-attaches the monster to that room.

#### Scenario: Re-activating a coordinate re-attaches the registered monster
- **WHEN** a coordinate has a registered monster, its room is vacated and recycled, and a character
  later enters the wilderness at that coordinate again
- **THEN** the registered `Monster` appears in the active room at that coordinate
