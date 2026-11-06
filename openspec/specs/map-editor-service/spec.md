# map-editor-service Specification

## Purpose
Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Editor runs without game services or dependencies
The editor SHALL install, load maps and serve its browser application in an independent environment without the game framework, database, frontend bundle, Node runtime or external network assets.

#### Scenario: Independent launch
- **WHEN** the editor is installed from its own locks with Evennia and Django absent and the game stopped
- **THEN** a real browser opens continental, settlement and interior snapshots with core-derived geometry and diagnostics

#### Scenario: Local build assets
- **WHEN** the built editor is served with Node unavailable and network access denied
- **THEN** essential UI and shared map drawing remain available without CDN or game dist requests

#### Scenario: Game theme without the game shell
- **WHEN** the editor build is scanned and rendered at 1451x790 and 2560x1440
- **THEN** it imports from the game tree only the allowlisted tokens, fonts and ui-scale modules, and its chrome scales with the game's ui-scale factor without loading the game shell stylesheet

### Requirement: Local API confines and authorizes workspace access
The service SHALL enforce expected Host/Origin, launch-session authorization for mutations, bounded data input and allowlisted confined document access.

#### Scenario: Rejected request
- **WHEN** a foreign origin/host, absent mutation token, traversal path or escaping symlink is submitted
- **THEN** the request is rejected without file changes or execution

#### Scenario: Untrusted content
- **WHEN** oversized data or authored executable-looking prose/scene URLs are supplied
- **THEN** data limits reject before expensive processing and displayed text causes no markup execution or arbitrary asset fetch

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
