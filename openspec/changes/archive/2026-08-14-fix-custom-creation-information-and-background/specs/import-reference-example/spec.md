## MODIFIED Requirements

### Requirement: The reference example exercises the persona block with a background
`world/imports/examples/example_character.json` SHALL be a single character record that satisfies
`CHARACTER_SCHEMA_V1` (including its required, registered, race-compatible `subrace`) and produces
zero validation rejections and zero warnings, and its `persona`
object SHALL include a `background` key with a non-empty text value alongside the existing
identity/prose keys — demonstrating the opaque-persona shape (including the player- and NPC-facing
`background` flavor text) that both the administrator-import path and the look appearance path
consume.

#### Scenario: The reference example sets the required record_type discriminator
- **WHEN** `examples/example_character.json`'s `record_type` field is inspected
- **THEN** it equals `"character"`, so the record routes to `CHARACTER_SCHEMA_V1` rather than being
  guessed as a world entry

#### Scenario: The reference example produces zero rejections
- **WHEN** `examples/example_character.json` is validated with `world.imports.validate`
- **THEN** validation reports zero rejections

#### Scenario: The reference example produces zero warnings
- **WHEN** `examples/example_character.json` is validated with `world.imports.validate`
- **THEN** validation reports zero warnings

#### Scenario: The reference persona demonstrates the background key
- **WHEN** `examples/example_character.json`'s `persona` object is inspected
- **THEN** it is an object containing a non-empty `background` key in addition to its identity and
  prose fields, showing the opaque shape the import and look paths consume
