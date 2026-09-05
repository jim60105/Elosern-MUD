# import-schema Specification

## Purpose
TBD - created by archiving change import-contract. Update Purpose after archive.
## Requirements
### Requirement: Both schemas require an explicit record_type discriminator, not implicit field sniffing
`CHARACTER_SCHEMA_V1` SHALL require a `record_type` property constrained to the literal value
`"character"`, and `WORLD_SCHEMA_V1` SHALL require a `record_type` property constrained to the
literal value `"world_entry"`. Dispatch between the two schemas SHALL be performed by reading this
field, never by inferring the record's kind from which other fields happen to be present or absent.
A record whose `record_type` is missing, `null`, or any value other than the one its intended schema
requires SHALL be rejected, with the rejection message naming both valid values.

#### Scenario: A character record with the correct record_type passes the discriminator check
- **WHEN** a character record has `"record_type": "character"`
- **THEN** the record is dispatched to `CHARACTER_SCHEMA_V1` and this check does not reject it

#### Scenario: A world entry with the correct record_type passes the discriminator check
- **WHEN** a world-info record has `"record_type": "world_entry"`
- **THEN** the record is dispatched to `WORLD_SCHEMA_V1` and this check does not reject it

#### Scenario: A record with a mismatched record_type fails schema validation
- **WHEN** a record intended as a world entry has `"record_type": "character"` (or vice versa)
- **THEN** validation against the corresponding schema's `const` constraint fails

#### Scenario: A record with a missing record_type is rejected before any other check runs
- **WHEN** a character record — otherwise complete and valid, including `age`/`apparent_age` both
  18 or above — omits `record_type` entirely
- **THEN** the record is rejected specifically for the missing `record_type`, and this rejection
  does not depend on, or get confused with, any other field's presence or absence

#### Scenario: An incomplete character record is never silently misrouted to WORLD_SCHEMA_V1
- **WHEN** a record has `"record_type": "character"` but omits `age`
- **THEN** the record is validated against `CHARACTER_SCHEMA_V1` (never against `WORLD_SCHEMA_V1`
  on the reasoning that it lacks an age-like field) and fails specifically because `age` is a
  required `CHARACTER_SCHEMA_V1` property — the age gate is still the failure reported, not an
  unrelated `WORLD_SCHEMA_V1` complaint about a missing `content` field

#### Scenario: An unrecognized record_type value is rejected naming both valid values
- **WHEN** a record has `"record_type": "npc"` (neither `"character"` nor `"world_entry"`)
- **THEN** the record is rejected, and the rejection message names both `"character"` and
  `"world_entry"` as the only valid values

### Requirement: CHARACTER_SCHEMA_V1 rejects any record where age or apparent_age is below 18
`world/imports/schema.py` SHALL define `CHARACTER_SCHEMA_V1` as a JSON Schema (draft 2020-12)
document whose `age` and `apparent_age` properties are each `{"type": "integer", "minimum": 18}`,
enforced structurally by the schema itself, not only by a semantic-layer function. This constraint
SHALL NOT be downgradable to a warning by any code path.

#### Scenario: A record with age 17 fails schema validation
- **WHEN** a character record identical to the valid reference example except `"age": 17` is
  validated against `CHARACTER_SCHEMA_V1`
- **THEN** schema validation fails on the `age` property, and this failure is a hard rejection

#### Scenario: A record with apparent_age 17 fails schema validation even if age is 18 or above
- **WHEN** a character record has `"age": 22` and `"apparent_age": 17`
- **THEN** schema validation fails on the `apparent_age` property, independently of `age` passing

#### Scenario: A record with both age and apparent_age at exactly 18 passes the age gate
- **WHEN** a character record has `"age": 18` and `"apparent_age": 18`
- **THEN** schema validation does not fail on either property

#### Scenario: The age gate cannot be bypassed by omitting the fields
- **WHEN** a character record omits `age` or `apparent_age` entirely
- **THEN** schema validation fails, since both fields are required properties of
  `CHARACTER_SCHEMA_V1`

### Requirement: The age gate is documented in the schema's own description text
`CHARACTER_SCHEMA_V1`'s `age` and `apparent_age` property definitions SHALL each carry a
`description` stating that the minimum is a hard, code-level invariant that is never downgraded to
a warning, so a reader of `schema.py` alone — without design doc access — understands the
constraint's severity.

#### Scenario: Both age-related description strings name the invariant explicitly
- **WHEN** `CHARACTER_SCHEMA_V1["properties"]["age"]["description"]` and
  `CHARACTER_SCHEMA_V1["properties"]["apparent_age"]["description"]` are inspected
- **THEN** each contains language stating the check is a hard rejection, never a warning

### Requirement: stats values are documented as base, pre-skill-multiplier values
`CHARACTER_SCHEMA_V1`'s `stats` property SHALL carry a `description` stating explicitly that every
numeric value is a base value, that source-card notation such as `"88*1000"` means a base value of
88 with a separate skill multiplier applied at resolution time, and that a stored value already
reflecting that multiplier (e.g. `88000`) is incorrect — this description SHALL be readable without
consulting any other document.

#### Scenario: The stats description states the base-value convention without external reference
- **WHEN** `CHARACTER_SCHEMA_V1["properties"]["stats"]["description"]` is inspected
- **THEN** it explicitly states that values are base, pre-multiplier numbers and that skill
  multipliers (such as x1000) are never baked into a stored value

### Requirement: stats only accepts the eight documented trait keys
`CHARACTER_SCHEMA_V1`'s `stats` property SHALL restrict its keys to exactly `hp`, `mp`, `sp`,
`atk_phys`, `agility`, `defense`, `magic_power`, and `guild_merit`, each a non-negative integer
(`hp` strictly positive), with no additional properties permitted.

#### Scenario: An unknown stats key fails schema validation
- **WHEN** a character record's `stats` object includes a key not in the documented eight (e.g.
  `"luck": 10`)
- **THEN** schema validation fails due to `additionalProperties: false`

#### Scenario: A negative stat value fails schema validation
- **WHEN** a character record's `stats.atk_phys` is `-5`
- **THEN** schema validation fails

### Requirement: disguised_stats is typed as an integer-valued mapping with no key constraint at the schema layer
`CHARACTER_SCHEMA_V1`'s `disguised_stats` property SHALL be typed as an object whose values are all
integers, with no constraint at the schema layer on which keys may appear — the
subset-of-`stats`-keys relationship is validated separately by the semantic layer (see the
`import-validation` capability), since it is a cross-field relationship JSON Schema does not
express cleanly.

#### Scenario: disguised_stats with non-integer values fails schema validation
- **WHEN** a character record's `disguised_stats` object has `{"atk_phys": "sixty"}`
- **THEN** schema validation fails because the value is not an integer

#### Scenario: disguised_stats with any key set (schema layer only) passes structural validation
- **WHEN** a character record's `disguised_stats` object has an integer-valued key not present in
  `stats` (e.g. `disguised_stats = {"charisma": 5}` where `stats` has no `charisma` key)
- **THEN** `CHARACTER_SCHEMA_V1` structural validation alone does not reject this — the
  subset check is a semantic-layer concern, not a schema-layer one

### Requirement: persona is validated as an object and nothing more
`CHARACTER_SCHEMA_V1`'s `persona` property SHALL be typed only as `{"type": "object"}`, with no
required keys, no `additionalProperties: false`, and no nested type constraints of any kind. The
schema's `description` for this property SHALL state that `persona` is opaque and its contents are
never inspected beyond confirming it is an object.

#### Scenario: A persona with arbitrary nested structure passes validation
- **WHEN** a character record's `persona` field is any JSON object, regardless of what keys or
  nested shapes it contains
- **THEN** `CHARACTER_SCHEMA_V1` validation of the `persona` field passes, so long as it is an
  object

#### Scenario: A non-object persona fails validation
- **WHEN** a character record's `persona` field is a string, array, or number instead of an object
- **THEN** schema validation fails

#### Scenario: persona's schema description states its contents are never inspected
- **WHEN** `CHARACTER_SCHEMA_V1["properties"]["persona"]["description"]` is inspected
- **THEN** it states that persona is opaque and that its contents are never inspected, constrained,
  or enumerated

### Requirement: sexual_baseline requires arousal, virgin, and sensitivity, with level fields constrained to the sexual-vocabulary registry
`CHARACTER_SCHEMA_V1`'s `sexual_baseline` property SHALL require `arousal`, `virgin`, and
`sensitivity`, and SHALL constrain `arousal`, `wetness`, `shame`, `exposure`, and `climax_phase`
(where present) to the corresponding ordered tuple from the `sexual-vocabulary` capability, and
`sensitivity`'s values (where present) to the sensitivity vocabulary. `wetness`, `shame`,
`exposure`, and `climax_phase` are optional.

#### Scenario: A sexual_baseline with a value outside its vocabulary fails validation
- **WHEN** a character record's `sexual_baseline.arousal` is `"憤怒"` (not one of the five documented
  arousal levels)
- **THEN** schema validation fails

#### Scenario: A sexual_baseline missing a required field fails validation
- **WHEN** a character record's `sexual_baseline` object omits `virgin`
- **THEN** schema validation fails

#### Scenario: A sexual_baseline with only the required fields set passes validation
- **WHEN** a character record's `sexual_baseline` is `{"arousal": "微興奮", "virgin": true,
  "sensitivity": {}}`, matching design doc S5.3's own worked example
- **THEN** schema validation passes

#### Scenario: A sexual_baseline with an optional field set to a valid vocabulary value passes validation
- **WHEN** a character record's `sexual_baseline` additionally sets `"wetness": "微濕"`
- **THEN** schema validation passes

### Requirement: WORLD_SCHEMA_V1 validates a minimal, opaque world-info entry
`world/imports/schema.py` SHALL define `WORLD_SCHEMA_V1` as a JSON Schema requiring `record_type`
(constrained to `"world_entry"`), `schema_version`, `key`, and `content`, where `content` is a
non-empty string documented as opaque narrative flavor text never treated as mechanical world
truth.

#### Scenario: A world entry with only the required fields passes validation
- **WHEN** a record is `{"record_type": "world_entry", "schema_version": 1, "key":
  "tavern_flavor_01", "content": "..."}`
- **THEN** `WORLD_SCHEMA_V1` validation passes

#### Scenario: A world entry missing content fails validation
- **WHEN** a record has `record_type`, `schema_version`, and `key` but no `content` field
- **THEN** `WORLD_SCHEMA_V1` validation fails

#### Scenario: content's description states it is never a source of mechanical truth
- **WHEN** `WORLD_SCHEMA_V1["properties"]["content"]["description"]` is inspected
- **THEN** it states that this field is opaque narrative material for the generative layer only,
  never a source the deterministic rules engine reads

### Requirement: Imported entity keys use a safe character set

The import schema SHALL constrain every entity `key` to printable characters excluding the structural separators `|`, `/`, `:`, `{`, `}`, and control characters, with a maximum length of 64 characters. The schema SHALL additionally reject digit-only keys (ASCII digits only, e.g. `"42"`): the digit-only region of the character-portrait keyspace is reserved for player characters, whose stable keys are `str(pk)`, so no imported entity key may ever equal a player's pk string.

#### Scenario: Pipe key is rejected

- **WHEN** a character or world-entry record declares a `key` containing `|`
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Over-long key is rejected

- **WHEN** a record declares a `key` longer than 64 characters
- **THEN** the record fails structural validation and is not instantiated

#### Scenario: Valid printable keys pass

- **WHEN** a record declares a printable key without separators within the length bound
- **THEN** the record passes the key checks

#### Scenario: A digit-only key is rejected for both record kinds

- **WHEN** a character or world-entry record declares a `key` consisting only of ASCII digits
- **THEN** the record fails structural validation on the key pattern and is not instantiated

#### Scenario: A key with letters and digits passes

- **WHEN** a record declares a key that contains digits alongside non-digit characters (e.g. `"bandit_02"`)
- **THEN** the record passes the key checks, since only an entirely digit-only key is reserved

### Requirement: CHARACTER_SCHEMA_V1 accepts an optional affinity_elements array
`world/imports/schema.py` SHALL define `CHARACTER_SCHEMA_V1`'s `affinity_elements` as an optional
array of at most 8 unique strings, each a lowercase key from exactly the eight lore elements
(`fire`, `water`, `wind`, `earth`, `lightning`, `ice`, `light`, `dark`). Duplicate entries SHALL
fail structural validation via `uniqueItems: true`, an unknown element SHALL fail via an enum
constraint, and an over-long array SHALL fail via `maxItems: 8`. The property's `description` SHALL
state that an absent or empty array means neutral progression.

#### Scenario: A valid affinity_elements array passes schema validation
- **WHEN** a character record's `affinity_elements` is `["fire", "wind"]`
- **THEN** `CHARACTER_SCHEMA_V1` validation passes that property

#### Scenario: An unknown element fails schema validation
- **WHEN** a character record's `affinity_elements` includes `"luck"` (not one of the eight lore
  elements)
- **THEN** schema validation fails on the enum constraint

#### Scenario: A duplicate element fails schema validation
- **WHEN** a character record's `affinity_elements` is `["fire", "fire"]`
- **THEN** schema validation fails on the `uniqueItems` constraint

#### Scenario: An array larger than the maximum fails schema validation
- **WHEN** a character record's `affinity_elements` contains more than 8 entries
- **THEN** schema validation fails on the `maxItems` constraint

#### Scenario: An absent affinity_elements passes schema validation
- **WHEN** a character record omits `affinity_elements` entirely
- **THEN** schema validation passes and the record is neutral unless the semantic layer rules
  otherwise

### Requirement: CHARACTER_SCHEMA_V1 requires an explicit sex value constrained to the canonical vocabulary
`world/imports/schema.py` SHALL define `CHARACTER_SCHEMA_V1`'s `sex` as a required property
constrained by JSON Schema `enum` to `world.lore.sex.SEX_VALUES` exactly
(`"female"`, `"male"`, `"other"`). A record omitting `sex` SHALL fail structural validation on the
missing-required-property check; a record whose `sex` is not one of the three vocabulary values
SHALL fail on the enum constraint. `"other"` SHALL be accepted as a valid, deliberate declaration —
not merely as a fallback for an absent value, since the property is required.

#### Scenario: A valid sex value passes schema validation
- **WHEN** a character record's `sex` is `"female"`, `"male"`, or `"other"`
- **THEN** `CHARACTER_SCHEMA_V1` validation passes that property

#### Scenario: An omitted sex fails schema validation
- **WHEN** a character record omits `sex` entirely
- **THEN** schema validation fails on the missing-required-property check, naming `sex`

#### Scenario: An unrecognized sex value fails schema validation
- **WHEN** a character record's `sex` is `"nonbinary"` (not one of the three vocabulary values)
- **THEN** schema validation fails on the enum constraint

#### Scenario: An explicit other declaration is accepted, not merely tolerated
- **WHEN** a character record's `sex` is explicitly `"other"`
- **THEN** schema validation passes that property exactly as it does for `"female"` or `"male"`,
  with no separate code path distinguishing an explicit declaration from an absent one (there is no
  absent case, since the property is required)

### Requirement: The character record schema defines an optional profession field and an optional components field
`CHARACTER_SCHEMA_V1` SHALL define two new OPTIONAL fields: `profession` (a non-empty string or
`null`; the registry-membership check is semantic, not schema-level) and `components` (an array of
`{type, kwargs}` objects, `type` a non-empty string, `kwargs` an object with string keys). When
both fields are absent, a record SHALL be structurally identical to the pre-change schema;
`components` entries are valid only alongside a `profession` blueprint and never for a
`PlayerCharacter`-targeted import; `profession` SHALL reject unknown keys in the shared batch
validator (see import-loader), not by schema constants.

#### Scenario: An absent profession field leaves the record unchanged
- **WHEN** a pre-existing valid record omits both new fields
- **THEN** schema validation passes with the same report (identical `fields`, `keys`, warnings) as
  before this change

#### Scenario: Unknown profession keys name the record in the batch report
- **WHEN** a record declares `"profession": "paladin"`
- **THEN** validation rejects it with a field-path issue naming the record and the
  `profession` field; the key is checked against the profession registry, not a schema constant
  list

#### Scenario: Component entries are shape-checked at the schema level, vocabulary-checked semantically
- **WHEN** a record's `components` entry is `{"type": "merchant", "kwargs": {"shop_key": "silver"}}`
- **THEN** schema-level shape validation passes; a non-object `kwargs` or non-string key fails the
  shape check; vocabulary membership and the NPC-only rule (a profession/components pair on a
  `PlayerCharacter`-targeted record is rejected as a named batch issue) are enforced in
  `validate_character` against `profession_config.PROFESSION_COMPONENT_TYPES` and the load target

#### Scenario: A components list without a profession is rejected
- **WHEN** a record declares `components` but omits `profession`
- **THEN** validation rejects it naming the `components` field and the reason (the assembly plan
  exists only alongside a blueprint)

