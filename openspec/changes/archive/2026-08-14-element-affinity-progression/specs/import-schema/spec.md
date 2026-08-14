## ADDED Requirements

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
