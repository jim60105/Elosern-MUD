## ADDED Requirements

### Requirement: Workspace state publishes the monster spawn section
The workspace state SHALL carry the decoded monster spawn section beside the external context status, drawn from the same read, and SHALL carry an empty section when the reference context cannot be read or decoded.

#### Scenario: Current artifact
- **WHEN** the workspace holds a current reference context with a synthetic section
- **THEN** the state's `monster_spawns` equals the encoded section and the external context status is current

#### Scenario: Stale artifact
- **WHEN** an external source changes so the decoded reference context is no longer current
- **THEN** the state still carries the decoded section and the external context status is not current

#### Scenario: Missing or undecodable artifact
- **WHEN** the reference context is absent or declares schema version 1
- **THEN** the state's `monster_spawns` holds empty zones and sites, the status is not current, and the map documents still load

#### Scenario: Section-only change
- **WHEN** only the section's bytes change while the context fingerprint stays the same
- **THEN** the next workspace read publishes a new snapshot revision carrying the new section
