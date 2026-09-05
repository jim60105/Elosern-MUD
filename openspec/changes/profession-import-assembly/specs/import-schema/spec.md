# Delta spec: import-schema (profession-import-assembly)

Adds the two blueprint fields to `CHARACTER_SCHEMA_V1`. The profession key must name a registry
row; component types and kwargs are constrained semantically; identity kwargs stay authored.

## ADDED Requirements

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
- **WHEN** a record declares `components` — presence, not content, is the declaration, so an
  explicit empty array counts — but carries no `profession` (absent or explicit `null`)
- **THEN** validation rejects it naming the `components` field and the reason (the assembly plan
  exists only alongside a blueprint)
