## ADDED Requirements

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
