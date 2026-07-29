## ADDED Requirements

### Requirement: loader.py instantiates entities only after batch validation reports zero rejections
`world/imports/loader.py` SHALL run full batch validation (reusing `world.imports.validate`'s
functions, not a separate re-implementation) before constructing any entity, and SHALL raise
without constructing anything if the batch contains any rejection anywhere.

#### Scenario: A batch with one rejecting record constructs nothing, not even the valid records
- **WHEN** `load_batch()` is called with three files, one of which fails a reject-level check
- **THEN** no `PlayerCharacter` or `NPC` instance is constructed for any of the three files, and an
  error is raised carrying the full validation report

#### Scenario: A fully valid batch constructs one entity per character record
- **WHEN** `load_batch()` is called with files that all pass every reject-level check
- **THEN** one entity is constructed per character record, and world-info records (if any are in
  the same batch) do not produce entities

### Requirement: Loaded trait values are the literal imported stats, merged onto the race floor for omitted keys, never re-derived or multiplied
`loader.py` SHALL populate a constructed entity's `entity.traits` by starting from
`world.rules.traits.race_floor()` for the record's race, then overwriting every key present in the
record's `stats` object with that literal value. No stored trait value SHALL be computed by scaling,
multiplying, or otherwise deriving it from another field.

#### Scenario: An explicitly imported stat value is used verbatim
- **WHEN** a character record's `stats.atk_phys` is `88` and the record's `race` is `elf`
- **THEN** the constructed entity's `entity.traits.atk_phys` base value equals exactly `88`, not a
  value derived from `vital_baseline` or scaled by any multiplier

#### Scenario: An omitted stat falls back to the race floor
- **WHEN** a character record's `stats` object has no `guild_merit` key
- **THEN** the constructed entity's `entity.traits.guild_merit` value equals
  `race_floor(RACE_REGISTRY[record_race])["guild_merit"]`

#### Scenario: No loaded trait value falls in a range only reachable via a skill multiplier
- **WHEN** any valid character record is loaded
- **THEN** every one of `entity.traits.atk_phys`, `agility`, `defense`'s resulting values falls
  within the race's or subrace-adjusted documented range for that stat, never a value three orders
  of magnitude larger that would only be reachable by baking in a x1000 skill multiplier

### Requirement: Non-trait record fields are stored verbatim into the seam attributes without interpretation
`loader.py` SHALL store `persona`, `sexual_baseline`, `skills`/`passives`, `equipment`, and
`disguised_stats` into the corresponding `LivingEntity` attributes exactly as validated, without
adding, removing, or transforming any content, and SHALL store `inventory` into
`entity.db.inventory` using Evennia's attribute store directly (no seam attribute declaration
required from any other change).

#### Scenario: persona is stored without inspection
- **WHEN** a valid character record's `persona` object contains arbitrary nested structure
- **THEN** the constructed entity's `entity.db.persona` equals that object exactly, unmodified,
  leaving the bare `entity.persona` name free for the `PersonaStore` handler to mount on

#### Scenario: sexual_baseline is stored as a raw dict, not converted into a state-machine object
- **WHEN** a valid character record's `sexual_baseline` is `{"arousal": "微興奮", "virgin": true,
  "sensitivity": {}}`
- **THEN** the constructed entity's `entity.db.sexual` equals that dict exactly, and no
  `SexualState`-like object is constructed (that class does not exist yet), leaving the bare
  `entity.sexual` name free for change 7's `SexualState` to mount on

#### Scenario: skills and passives are stored together as a raw structure
- **WHEN** a valid character record has `"skills": ["fire_mastery"]` and `"passives":
  ["defense_instinct"]`
- **THEN** the constructed entity's `entity.db.skills` contains both lists, unmodified, with no
  resolution against any skill registry performed by the loader itself, and the bare `entity.skills`
  name is left free for change 5's `SkillHandler` to mount on

#### Scenario: disguised_stats is stored using the storage convention entity-traits already declared
- **WHEN** a valid character record has a non-empty `disguised_stats`
- **THEN** the constructed entity's `entity.db.disguised_stats` equals that object exactly

#### Scenario: inventory is stored without requiring any change to LivingEntity's declared attributes
- **WHEN** a valid character record has a non-empty `inventory` array
- **THEN** the constructed entity's `entity.db.inventory` equals that array exactly, and no
  modification to `typeclasses/entities.py` is required for this to work

### Requirement: The loader can target either PlayerCharacter or NPC
`loader.py`'s entity-construction function SHALL accept a `typeclass` parameter defaulting to `NPC`,
allowing a caller to construct a `PlayerCharacter` instead, without this change performing any
Account/session binding.

#### Scenario: The default construction produces an NPC
- **WHEN** `instantiate_character()` is called without a `typeclass` argument
- **THEN** the constructed entity is an `NPC` instance

#### Scenario: An explicit typeclass argument produces a PlayerCharacter
- **WHEN** `instantiate_character()` is called with `typeclass=PlayerCharacter`
- **THEN** the constructed entity is a `PlayerCharacter` instance, and no Account or session is
  created or bound as part of this call
