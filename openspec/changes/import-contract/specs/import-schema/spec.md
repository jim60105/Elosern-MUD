## ADDED Requirements

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
`atk_phys`, `agility`, `defense`, `magic_level`, and `guild_merit`, each a non-negative integer
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
`world/imports/schema.py` SHALL define `WORLD_SCHEMA_V1` as a JSON Schema requiring
`schema_version`, `key`, and `content`, where `content` is a non-empty string documented as opaque
narrative flavor text never treated as mechanical world truth.

#### Scenario: A world entry with only the required fields passes validation
- **WHEN** a record is `{"schema_version": 1, "key": "tavern_flavor_01", "content": "..."}`
- **THEN** `WORLD_SCHEMA_V1` validation passes

#### Scenario: A world entry missing content fails validation
- **WHEN** a record has `schema_version` and `key` but no `content` field
- **THEN** `WORLD_SCHEMA_V1` validation fails

#### Scenario: content's description states it is never a source of mechanical truth
- **WHEN** `WORLD_SCHEMA_V1["properties"]["content"]["description"]` is inspected
- **THEN** it states that this field is opaque narrative material for the generative layer only,
  never a source the deterministic rules engine reads
