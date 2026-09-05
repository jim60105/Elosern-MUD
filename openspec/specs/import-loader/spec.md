# import-loader Specification

## Purpose
TBD - created by archiving change import-contract. Update Purpose after archive.
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
`loader.py` SHALL construct traits from `race_floor(RACE_REGISTRY[race])` updated by the record's
literal `stats`, with no skill multipliers, no profession multipliers, and no re-derivation. The
sole tier influence allowed: when the record declares `profession` whose registry row carries a
non-null `default_tier` AND the record's own `stats` is empty, trait construction SHALL route
through the race-baseline tiered construction (`initial_trait_config(race, subrace, tier)`)
instead of the plain race floor. A record declaring any literal stat keeps those literal values
unchanged, and a record without `profession` (or with a null-tier row) SHALL construct traits
byte-identically to the pre-change loader.

#### Scenario: An explicitly imported stat value is used verbatim
- **WHEN** a character record's `stats.atk_phys` is `88` and the record's `race` is `elf`
- **THEN** the constructed entity's `entity.traits.atk_phys` base value equals exactly `88`, not a
  value derived from `vital_baseline` or scaled by any multiplier

#### Scenario: An omitted stat falls back to the race floor
- **WHEN** a character record's `stats` object has no `guild_merit` key
- **THEN** the constructed entity's `entity.traits.guild_merit` value equals
  `race_floor(RACE_REGISTRY[record_race])["guild_merit"]`

#### Scenario: The loader never applies a skill multiplier
- **WHEN** a warning-only out-of-band static value is loaded
- **THEN** the resulting trait equals that literal imported value; the loader never multiplies or
  scales it, while the validation warning remains visible

#### Scenario: Literal stats beat any profession tier
- **WHEN** a record with `"profession": "merchant"` (row tier non-null) also declares literal
  `stats` values
- **THEN** the constructed entity's traits equal the literal values merged onto the race floor,
  exactly as before the profession field existed

#### Scenario: Empty stats with a tiered profession use the tiered baseline
- **WHEN** a record declares `profession` naming a row whose `default_tier` is a real tier key and
  declares `"stats": {}`
- **THEN** the constructed traits equal `initial_trait_config(race, subrace, tier)` for that tier

#### Scenario: No profession means no behavior change
- **WHEN** a record omits `profession`
- **THEN** trait construction is byte-identical to the pre-change loader for the same record

### Requirement: Non-trait record fields are stored verbatim into the seam attributes without interpretation
`loader.py` SHALL store `persona`, `sexual_baseline`, `skills`/`passives`, `equipment`, and
`disguised_stats` into the corresponding `LivingEntity` attributes exactly as validated, without
adding, removing, or transforming any content (the sole derived write is the lineage auto-seed —
see `use-driven-skill-lineage`: `skills`/`passives` are extended with the transitive
prerequisite-ownership closure of what the record declared, prerequisite proficiency is seeded to
exactly the edge value, the whole normalization runs before schema range validation, and an explicit
imported `skill_proficiency` entry always beats the seed), and SHALL store `inventory` into
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
opaque payloads (`persona`, `sexual_baseline`, `skills`/`passives`, `equipment`,
`disguised_stats`). `sex` is a required schema property (see `import-schema`), so this assignment
SHALL always read a value present in the validated record, never a missing key.

#### Scenario: A validated record's sex value is assigned verbatim
- **WHEN** a valid character record's `sex` is `"male"`
- **THEN** the constructed entity's `entity.sex` equals `"male"` exactly

#### Scenario: Assignment uses direct attribute assignment, not the db seam
- **WHEN** `loader.py`'s instantiation code is inspected
- **THEN** the `sex` assignment reads `entity.sex = record["sex"]`, with no corresponding
  `entity.db.sex` assignment anywhere in the loader

### Requirement: A profession-bearing NPC record assembles blueprint components with explicit precedence
When a validated NPC record declares `profession`, `loader.py` SHALL attach, inside the record's
construction transaction, every component of the profession blueprint that the record does NOT
list explicitly in its own `components` (blueprint minus explicit types — an explicit entry of the
same type replaces the blueprint entry entirely, design D5). Explicit vocabulary entries the
blueprint omits SHALL be appended in record order. Component kwargs SHALL come only from authored
sources: the record's explicit `components` entry kwargs. When a blueprint component's identity
kwargs (any of `service_id`, `shop_key`, `branch_key`, `dialogue_key`) cannot be fully supplied
from authored record data, the WHOLE batch SHALL be rejected with a named issue BEFORE any entity
is constructed (the shared batch validator owns the rejection; the loader re-runs the same
resolution fail-closed as its second gate); the loader SHALL NEVER invent or default an identity
value. Assembly SHALL attach through the same component-attach path
`world/rules/guild_economy.py`'s sync uses, and an absent-`profession` record SHALL construct
byte-identically to the pre-change loader. Each assembled NPC SHALL emit one
`import_profession_assembled` info event (`char` = the record key, `profession` = the row key).

#### Scenario: Blueprint minus explicit components
- **WHEN** a record declares a profession whose blueprint carries `guild_staff` and
  `scripted_dialogue`, and its own `components` lists a `guild_staff` entry with full kwargs
- **THEN** the constructed NPC carries the record's `guild_staff` kwargs, plus the blueprint's
  `scripted_dialogue` component (kwargs from the record's same-type entry if present), and no
  second `guild_staff`

#### Scenario: Missing identity kwargs reject the batch instead of guessing
- **WHEN** a record declares `"profession": "merchant"` with no `components` entry supplying the
  `merchant` component's `service_id` and `shop_key`
- **THEN** the batch is rejected naming the record, the component, and the missing kwargs, and no
  entity persists

#### Scenario: Assembly rides the import transaction
- **WHEN** component attachment fails midway (e.g. a duplicate component slot)
- **THEN** `load_batch` persists nothing for the whole batch, matching the existing
  all-or-nothing contract

### Requirement: A blueprint schedule template is applied to assembled NPCs only
When the profession row's `schedule_template` is non-null and the constructed entity is an `NPC`,
the loader SHALL store the template-reference schedule (`{"schema_version": 1, "template": <key>}`)
through `world/rules/npc_schedules.py::set_npc_schedule` inside the same transaction; a null
template applies no schedule; the shipped professions (all null templates) therefore change
nothing for shipped records.

#### Scenario: A tiered-and-scheduled profession schedules the NPC
- **WHEN** a test profession row carries `schedule_template: guard` and a record uses it
- **THEN** the constructed NPC carries the validated template-reference schedule for `guard`

#### Scenario: Null template stores nothing
- **WHEN** a record uses a shipped profession (null template)
- **THEN** the NPC carries no schedule attribute and settlement skips it exactly as today
