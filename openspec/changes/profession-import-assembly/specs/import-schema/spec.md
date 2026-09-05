# Delta spec: import-schema (profession-import-assembly)

Adds the two blueprint fields to `CHARACTER_SCHEMA_V1`. The profession key must name a registry
row; component types are constrained to the profession vocabulary; identity kwargs stay authored
in the record.

## ADDED Requirements

### Requirement: CHARACTER_SCHEMA_V1 accepts optional profession and components fields
`CHARACTER_SCHEMA_V1` SHALL accept an optional `profession` (a non-empty string that must name a
key of the loaded profession registry — an unknown key rejects the record in the shared batch
validator) and an optional `components` (a list of `{"type": <vocabulary key>, "kwargs":
<mapping of strings to authored values>}` entries whose `type` values are constrained to the
profession loader's component-type vocabulary). Both fields absent SHALL leave validation and
construction byte-identical to the pre-change schema. `profession` SHALL be rejected with a named
issue on a record whose target typeclass is `PlayerCharacter`.

#### Scenario: An unknown profession key rejects the batch
- **WHEN** a record declares `"profession": "blacksmith"` and no such registry key exists
- **THEN** the record carries a named validation issue and `load_batch` persists nothing

#### Scenario: A component type outside the vocabulary is rejected
- **WHEN** a record's `components` entry declares `type: tinker`
- **THEN** validation names the record and the unknown type, and no entity is constructed

#### Scenario: A PlayerCharacter record cannot declare a profession
- **WHEN** a `PlayerCharacter`-targeted record declares `profession`
- **THEN** validation rejects the record with a named issue

#### Scenario: Records without the new fields are untouched
- **WHEN** every existing example and fixture record validates after the schema change
- **THEN** validation results and constructed attribute state equal the pre-change behavior
