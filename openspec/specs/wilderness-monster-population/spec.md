## Purpose

The deterministic, offline-computable monster population for the wilderness/Virtual layer: a pure
coordinate-to-monster model and an idempotent spawn/respawn service that places `Monster` objects at
wilderness coordinates via the wilderness script's `itemcoordinates`, guaranteeing huntable low-tier
monsters near `capital_altoria`'s entry point. No LLM, no RNG, no database reads in the population
decision.

## Requirements

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
- **THEN** it uses `name_index = (x * 92821 + y * 68917) % len(tier.example_monsters_zh)` — the same
  multiplier pair as the terrain spec, with the index expression explicit so the entry pin is
  formula-derived, not special-cased

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

### Requirement: ensure_population idempotently places and respawns monsters at a coordinate
`world/maps/wilderness_population.py` SHALL define `ensure_population(wilderness, coordinates) ->
None` that reconciles a wilderness coordinate against `population_for_coordinates`, leaving it
conforming to the model. Every monster it creates SHALL carry a persistent ownership marker
`monster.db.population_key == "wilderness:{x}:{y}"` for its coordinate; reconciliation SHALL act
only on monsters bearing a matching marker.

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

#### Scenario: Species-bearing ambient individuals reconcile inside their own domain
- **WHEN** ambient species rules cover a coordinate's region and a site-owned or quest-bound monster also stands there
- **THEN** the ambient pass creates/removes only its own marker-matching individuals up to authored quantity and capacity, and the foreign-owned monsters are untouched

#### Scenario: Ambient species selection is pure across restarts
- **WHEN** the ambient species selection for one coordinate is recomputed in a fresh process
- **THEN** it selects the same authored variant with no RNG, database, or wall-clock input

#### Scenario: Stale cleanup removes every marker-matching monster when the model returns None
- **WHEN** the model returns `None` for a coordinate holding marker-matching monsters
- **THEN** reconciliation deletes them and removes them from `wilderness.db.itemcoordinates`,
  leaving foreign monsters untouched

#### Scenario: A created monster is fully configured
- **WHEN** reconciliation creates a `Monster` for a populated coordinate
- **THEN** it has `threat_tier` set to the model's tier, `apply_monster_tier("floor")` applied, its
  `db.skills` left at the innate-only default, `db.population_key` set, is registered at
  `wilderness.db.itemcoordinates[monster] == coordinates`, and `.location` is set to the room
  currently active at that coordinate if one exists

#### Scenario: An already-matching monster is left untouched
- **WHEN** exactly one living marker-matching monster whose `threat_tier` and key still match the
  model already exists at a populated coordinate
- **THEN** reconciliation makes no change

#### Scenario: Foreign monsters are never deleted, moved, or modified
- **WHEN** reconciliation runs at a coordinate hosting monsters without a matching marker
- **THEN** it never deletes, moves, or modifies any other `Monster` at the coordinate

#### Scenario: Ambient individuals are built through the construction owner
- **WHEN** regional ambient placement rules cover the coordinate's region and species-bearing
  reconciliation creates ambient individuals
- **THEN** each is built through the individual construction owner from an authored variant key
  selected by the same pure coordinate-hash determinism, within the authored regional quantity and
  capacity, and each additionally carries its ambient ownership marker

#### Scenario: Uncovered coordinates keep the tier-example branch
- **WHEN** the ambient species rules do not cover a coordinate's region
- **THEN** the tier-example branch keeps its current behaviour for that coordinate

#### Scenario: Created monsters are immediately combat-ready
- **WHEN** a player engages a monster created by `ensure_population`
- **THEN** it is engageable and defeatable through the existing player combat-session path without
  further setup

### Requirement: A registered wilderness monster survives room recycling
A monster registered through `ensure_population` SHALL be tracked by the wilderness script's
`itemcoordinates` rather than by room contents, so that when a `TerrainRoom` is recycled and later a
room is activated again at the monster's coordinate, the contrib re-attaches the monster to that room.

#### Scenario: Re-activating a coordinate re-attaches the registered monster
- **WHEN** a coordinate has a registered monster, its room is vacated and recycled, and a character
  later enters the wilderness at that coordinate again
- **THEN** the registered `Monster` appears in the active room at that coordinate

### Requirement: Population reconciliation never destroys an active-session participant
Wilderness population reconciliation SHALL skip deleting or replacing any monster that a persisted
active combat session still references, until that session is restored and settled.

#### Scenario: Session-referenced monster is preserved during reconciliation
- **WHEN** `sync_wilderness` reconciliation runs while a persisted session references a wilderness
  monster (including one with zero HP after a committed terminal round)
- **THEN** the referenced monster is neither deleted nor respawned by the reconciliation; it is left
  for session restoration to settle

#### Scenario: Settled monsters are reconciled normally
- **WHEN** no persisted session references a wilderness monster
- **THEN** normal living-conformance reconciliation (delete defeated, respawn expected) proceeds
  unchanged
