## MODIFIED Requirements

### Requirement: Non-trait record fields are stored verbatim into the seam attributes without interpretation
`loader.py` SHALL store `persona`, `sexual_baseline`, `skills`/`passives`, `equipment`, and
`disguised_stats` into the corresponding `LivingEntity` attributes exactly as validated, without
adding, removing, or transforming any content (the sole derived write is the lineage auto-seed —
see `use-driven-skill-lineage`: prerequisite proficiency seeded to exactly the edge value, running
before schema range validation, always beaten by an explicit imported `skill_proficiency`), and SHALL store `inventory` into
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

#### Scenario: Lineage auto-seed lands inside the same transaction
- **WHEN** a valid record owns `firestorm` with no explicit `skill_proficiency` for its prerequisites
- **THEN** the loaded entity carries prerequisite proficiency seeded to exactly the edge values, and a record rejected by schema validation persists nothing, seed included

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
