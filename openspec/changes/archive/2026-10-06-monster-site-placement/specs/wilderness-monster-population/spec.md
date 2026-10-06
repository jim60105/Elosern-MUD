## MODIFIED Requirements

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
- When the regional ambient placement rules cover the coordinate's region, the reconciliation SHALL
  additionally reconcile the species-bearing ambient individuals those rules author, within the
  authored regional quantity and capacity, building each through the individual construction owner from
  an authored variant key selected by the same pure coordinate-hash determinism (no RNG, no database
  state, no wall clock), each additionally carrying its ambient ownership marker. Species-bearing
  reconciliation SHALL stay inside this owner's marker domain and SHALL NOT act on site-, quest-,
  story-, or session-owned individuals, and the tier-example branch above SHALL keep its current
  behaviour for coordinates the ambient species rules do not cover.

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

#### Scenario: Species-bearing ambient individuals reconcile inside their own domain
- **WHEN** ambient species rules cover a coordinate's region and a site-owned or quest-bound monster also stands there
- **THEN** the ambient pass creates/removes only its own marker-matching individuals up to authored quantity and capacity, and the foreign-owned monsters are untouched

#### Scenario: Ambient species selection is pure across restarts
- **WHEN** the ambient species selection for one coordinate is recomputed in a fresh process
- **THEN** it selects the same authored variant with no RNG, database, or wall-clock input
