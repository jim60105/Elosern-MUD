## MODIFIED Requirements

### Requirement: Stable keys share one producer contract
All portrait/scene stable-key producers SHALL reject forbidden separators/control characters and keys exceeding 64 characters or 200 UTF-8 bytes. The common limits SHALL bound gallery path components, per-image job keys and serialized subjects. Removing fixed-output identities SHALL NOT relax producer validation.

#### Scenario: Slash key is rejected at import
- **WHEN** a character import record declares a `key` containing `/`
- **THEN** the import is rejected with a structural issue and no entity is created

#### Scenario: Pipe key is rejected at import
- **WHEN** a character import record declares a `key` containing `|`
- **THEN** the import is rejected with a structural issue and no entity is created

#### Scenario: Over-length key is rejected at import
- **WHEN** a character import record declares a `key` longer than 64 characters
- **THEN** the import is rejected with a structural issue and no entity is created

#### Scenario: Quest characterization key follows the same rules
- **WHEN** a quest blueprint assigns a portrait stable key
- **THEN** the same character set and length rules apply before any record is created

#### Scenario: Full wire subject keys always fit the wire bound
- **WHEN** every `ArtSubjectKind` prefix is combined with a 64-character producer key
- **THEN** the resulting full subject key is at or below the wire `MAX_SUBJECT_KEY`
