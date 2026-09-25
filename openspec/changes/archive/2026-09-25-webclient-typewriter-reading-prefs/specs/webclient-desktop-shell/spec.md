## MODIFIED Requirements

### Requirement: Browser persistence is versioned and presentation-only
Local browser storage SHALL contain only a bounded wrapper with project layout version, safe dimensions/tab state, and harmless display preferences. It SHALL contain no transport generation, active or retired epoch, revision, panel payload, actor identifier, request result, command text, credential, or canonical game state. The current project layout version SHALL be 2, the version that adds the reading preferences (text speed and auto-advance). A project layout version SHALL migrate only through an explicitly registered migration, and the client SHALL register none: version 1 has no migration. Malformed, oversized, missing, stock, or unknown versions, version 1 among them, SHALL reset to the current version's default while preserving required components.

#### Scenario: Known layout version migrates
- **WHEN** a stored project layout uses a version with a registered migration, as supplied to the store by a caller
- **THEN** the migration produces the current layout and retains only supported display preferences

#### Scenario: Unknown layout version resets safely
- **WHEN** localStorage contains an unknown version or malformed configuration
- **THEN** the shell removes or ignores it and loads the approved default with every required component

#### Scenario: Stock layout state is not imported
- **WHEN** a browser profile contains Evennia's pre-project GoldenLayout storage keys
- **THEN** the current layout version does not treat those values as canonical project layout state

#### Scenario: A version-1 wrapper resets to the current default
- **WHEN** localStorage holds a well-formed version-1 wrapper with a stored prose scale
- **THEN** the client loads the version-2 default with every preference at its default, text speed `normal` and auto-advance off among them, and persists that version-2 wrapper
