## REMOVED Requirements

### Requirement: persona is validated as an object and nothing more
**Reason**: The NPC persona authoring design amends the "never inspected" rule for NPC targets: their persona must be a complete compact card, validated semantically after the schema layer.
**Migration**: The schema layer still checks only that `persona` is an object (see "persona is an object at the schema layer and NPC targets validate it semantically"); NPC-target card validation lives in `import-validation`, and player/non-NPC targets keep the opaque rule.

## ADDED Requirements

### Requirement: persona is an object at the schema layer and NPC targets validate it semantically
`CHARACTER_SCHEMA_V1`'s `persona` property SHALL be typed only as `{"type": "object"}`, with no
required keys, no `additionalProperties: false`, and no nested type constraints at the schema
layer. The property's `description` SHALL state that the schema checks only that `persona` is an
object, that an NPC-target import applies the compact NPC card contract during semantic validation,
and that a non-NPC target's persona is opaque and never inspected.

#### Scenario: A persona with arbitrary nested structure passes the schema layer
- **WHEN** a character record's `persona` field is any JSON object
- **THEN** `CHARACTER_SCHEMA_V1` validation of the `persona` field passes, so long as it is an object

#### Scenario: A non-object persona fails validation
- **WHEN** a character record's `persona` field is a string, array, or number instead of an object
- **THEN** schema validation fails

#### Scenario: persona's schema description names both rules
- **WHEN** `CHARACTER_SCHEMA_V1["properties"]["persona"]["description"]` is inspected
- **THEN** it states that the schema checks only for an object, that NPC-target imports apply the compact card contract semantically, and that non-NPC personas are opaque
