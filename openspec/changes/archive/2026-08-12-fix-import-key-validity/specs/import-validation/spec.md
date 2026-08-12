## ADDED Requirements

### Requirement: Batch import rejects duplicate character keys

`validate_batch` SHALL reject a batch whose character records contain duplicate `key` values, mirroring the existing world-entry uniqueness check, before any record is instantiated.

#### Scenario: Duplicate character keys fail the whole batch

- **WHEN** a batch contains two valid character records with the same `key`
- **THEN** validation reports a structural issue and no record in the batch is instantiated

#### Scenario: Unique character keys pass

- **WHEN** a batch contains only distinct character keys
- **THEN** the batch passes the uniqueness check

### Requirement: Key charset is checked at import validation

The import validator SHALL apply the entity-key character-set and length rules as structural checks shared with the schema, so no key that could corrupt downstream `|`-delimited effect serialization reaches the loader.

#### Scenario: Separator key is a structural issue

- **WHEN** any record's key contains a structural separator
- **THEN** the record is flagged as a structural issue and excluded from instantiation
