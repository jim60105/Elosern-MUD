# import-loader Specification

## Purpose
Requires loader.py to construct entities only after full batch validation reports zero rejections, within a single database transaction, and to preserve imported data faithfully: literal trait values merged onto the race floor, non-trait fields stored verbatim, and sex assigned from the validated record. Covers targeting PlayerCharacter or NPC and assembling blueprint components for profession-bearing NPC records with explicit precedence.
## Requirements

### Requirement: loader.py instantiates entities only after batch validation reports zero rejections
`world/imports/loader.py` SHALL run full batch validation (reusing `world.imports.validate`'s
functions, not a separate re-implementation) before constructing any entity, and SHALL raise
without constructing anything if the batch contains any rejection anywhere. Construction SHALL
run in one database transaction so a later runtime failure rolls back earlier objects. The public
`instantiate_character()` SHALL validate its single input before constructing it.

#### Scenario: A batch with one rejecting record constructs nothing, not even the valid records
- **WHEN** `load_batch()` is called with three files, one of which fails a reject-level check
- **THEN** no `PlayerCharacter` or `NPC` instance is constructed for any of the three files, and an
  error is raised carrying the full validation report

#### Scenario: A fully valid batch constructs one entity per character record
- **WHEN** `load_batch()` is called with files that all pass every reject-level check
- **THEN** one entity is constructed per character record, and world-info records (if any are in
  the same batch) do not produce entities

#### Scenario: A construction failure rolls back earlier entities
- **WHEN** validation passes but construction of a later character raises
- **THEN** every entity already created for that batch is rolled back

#### Scenario: Direct construction cannot bypass validation
- **WHEN** `instantiate_character()` receives an age-17 record
- **THEN** it raises `ImportRejected` before creating an entity

### Requirement: Loaded trait values are the literal imported stats, merged onto the race floor for omitted keys, never re-derived or multiplied
Loaded traits SHALL equal literal imported stats merged onto the race floor for omitted keys. Capability configuration SHALL apply no skill/profession multipliers or tier defaults. Explicit independently owned tier creation paths SHALL remain unchanged.

#### Scenario: An explicitly imported stat value is used verbatim
- **WHEN** an elf record supplies stats.atk_phys 88
- **THEN** its loaded base is exactly 88 with no derivation or multiplier

#### Scenario: An omitted stat falls back to the race floor
- **WHEN** a record omits guild_merit from stats
- **THEN** the loaded value equals that race's ordinary floor

#### Scenario: The loader never applies a skill multiplier
- **WHEN** a warning-only out-of-band static value is loaded
- **THEN** that literal value persists without scaling and the validation warning remains

#### Scenario: Literal stats beat any profession tier
- **WHEN** a direct-capability record supplies literal stats
- **THEN** they merge onto the race floor without capability-derived tier defaults

#### Scenario: Empty stats with a tiered profession use the tiered baseline
- **WHEN** a direct-capability NPC supplies empty stats
- **THEN** it uses the ordinary race floor; legacy profession input rejects

#### Scenario: No profession means no behavior change
- **WHEN** a valid record omits capabilities and profession
- **THEN** its literal-stats construction remains unchanged

#### Scenario: A null-tier profession row is a no-op
- **WHEN** an input includes a removed profession field
- **THEN** the closed schema rejects it instead of consulting a default tier

### Requirement: Non-trait record fields are stored verbatim into the seam attributes without interpretation
`loader.py` SHALL store `persona`, `sexual_baseline`, `skills`/`passives`, `equipment`, and
`disguised_stats` into the corresponding `LivingEntity` attributes exactly as validated, without
adding, removing, or transforming any content; the sole derived write is the lineage auto-seed
(see `use-driven-skill-lineage`). The loader SHALL store `inventory` into `entity.db.inventory`
using Evennia's attribute store directly.

#### Scenario: persona is stored without inspection
- **WHEN** a valid character record loaded against `PlayerCharacter` carries a `persona` object with arbitrary nested structure
- **THEN** the constructed entity's `entity.db.persona` equals that object exactly, unmodified,
  leaving the bare `entity.persona` name free for the `PersonaStore` handler to mount on

#### Scenario: An NPC import persists its validated card with metadata
- **WHEN** a valid NPC-target record is loaded
- **THEN** the NPC's persona equals the validated normalized card, its persona metadata is at version 1 with `import` provenance naming the record key, and a later failure in the same batch rolls back both

#### Scenario: sexual_baseline is stored as a raw dict, not converted into a state-machine object
- **WHEN** a valid character record's `sexual_baseline` is `{"arousal": "微興奮", "virgin": true,
  "sensitivity": {}}`
- **THEN** the constructed entity's `entity.db.sexual` equals that dict exactly, and no
  `SexualState`-like object is constructed (that class does not exist yet), leaving the bare
  `entity.sexual` name free for change 7's `SexualState` to mount on

#### Scenario: Lineage auto-seed lands inside the same transaction
- **WHEN** a valid record owns `firestorm` (prereq `scorching_wave >= 3`) with no explicit
  `skill_proficiency` for its prerequisites
- **THEN** the loaded entity OWNS the closed prerequisite chain, carries `scorching_wave` proficiency
  seeded to exactly the edge value, and `can_use_skill` passes for `firestorm`; a record rejected by
  schema validation persists nothing, seed and closure included

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

#### Scenario: No other change must declare a seam attribute for inventory
- **WHEN** the loader writes `inventory` through Evennia's attribute store
- **THEN** no seam attribute declaration is required from any other change

#### Scenario: Lineage normalization runs before schema range validation
- **WHEN** the lineage auto-seed expands a record's `skills`/`passives`
- **THEN** the whole normalization runs before schema range validation

#### Scenario: An explicit imported proficiency entry beats the seed
- **WHEN** a record declares an explicit `skill_proficiency` entry for a prerequisite the seed would
  also add
- **THEN** the explicit imported entry always wins over the seeded value

#### Scenario: An NPC persona is the normalized card written with import provenance
- **WHEN** an NPC-target record is loaded
- **THEN** the validated persona is the normalized compact card, written through the deterministic
  NPC persona initializer with `import` provenance naming the record key, inside the batch
  transaction, so the NPC also carries persona metadata at version 1, and the stored card equals
  the validated card exactly

#### Scenario: A non-NPC persona is stored verbatim
- **WHEN** a record is loaded against a non-NPC target
- **THEN** the persona is stored verbatim

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

### Requirement: The loader assigns sex from the validated record, mirroring race and subrace
`loader.py` SHALL assign `entity.sex = record["sex"]` during instantiation, using the same direct
`AttributeProperty`-assignment shape as `entity.race = record["race"]` and
`entity.subrace = record.get("subrace")` — not the `entity.db.*` seam-attribute shape used for
opaque payloads. `sex` is a required schema property (see `import-schema`), so this assignment
SHALL always read a value present in the validated record, never a missing key.

#### Scenario: A validated record's sex value is assigned verbatim
- **WHEN** a valid character record's `sex` is `"male"`
- **THEN** the constructed entity's `entity.sex` equals `"male"` exactly

#### Scenario: Assignment uses direct attribute assignment, not the db seam
- **WHEN** `loader.py`'s instantiation code is inspected
- **THEN** the `sex` assignment reads `entity.sex = record["sex"]`, with no corresponding
  `entity.db.sex` assignment anywhere in the loader

#### Scenario: Opaque payload fields keep the db seam shape
- **WHEN** the loader stores `persona`, `sexual_baseline`, `skills`/`passives`, `equipment`, or
  `disguised_stats`
- **THEN** those use the `entity.db.*` seam-attribute shape, unlike `sex`

### Requirement: A profession-bearing NPC record assembles blueprint components with explicit precedence
The loader SHALL assemble exactly the validated direct NPC component plan inside the complete import transaction. All required configuration and binding/room references SHALL validate before persistence; assembly failure SHALL restore storage and handler caches.

#### Scenario: Blueprint minus explicit components
- **WHEN** a record declares two direct components
- **THEN** exactly those components and kwargs are installed without expansion or override precedence

#### Scenario: Missing identity kwargs reject the batch instead of guessing
- **WHEN** a merchant entry omits service_id or shop_key
- **THEN** the entire batch rejects naming the field and no entity persists

#### Scenario: No profession means byte-identical construction
- **WHEN** a record declares no components
- **THEN** construction preserves unrelated import semantics

#### Scenario: Each assembled NPC emits one assembly info event
- **WHEN** a direct capability installation commits
- **THEN** one import_capabilities_assembled event names the record and declared types with no profession field; a rollback emits none

#### Scenario: Assembly rides the import transaction
- **WHEN** component attachment fails midway
- **THEN** the complete batch and handler caches roll back

#### Scenario: Explicit entries the blueprint omits keep record order
- **WHEN** a direct component list is accepted
- **THEN** exactly its unique entries retain record order without blueprint expansion

#### Scenario: Identity resolution is fail-closed at two gates
- **WHEN** authored component identity/configuration is incomplete
- **THEN** validation rejects before construction and assembly revalidates the complete plan before writes

#### Scenario: The loader never invents an identity value
- **WHEN** a required service_id, shop_key, branch_key or dialogue_key is absent
- **THEN** validation rejects without inventing or defaulting that identifier

#### Scenario: Assembly reuses the guild economy attach path
- **WHEN** imports and roster hosts attach components
- **THEN** both use the same deterministic validated-plan assembly owner
