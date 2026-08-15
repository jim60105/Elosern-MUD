## ADDED Requirements

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
