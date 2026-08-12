## ADDED Requirements

### Requirement: Subject producer validation rejects unrepresentable keys

`_validate_subject_key` SHALL reject keys containing `|`, `/`, `:`, `{`, `}`, or control characters, and keys longer than the shared 64-character maximum, so no subject can pass producer validation and then fail the media route or the wire bounds.

#### Scenario: Slash key is rejected with a named error and no queue record

- **WHEN** a portrait subject is derived from a key containing `/`
- **THEN** the subject resolution is rejected with a named error and no queue record is created
