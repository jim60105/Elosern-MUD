## MODIFIED Requirements

### Requirement: Browser persistence is versioned and presentation-only
Local browser storage SHALL contain only a bounded wrapper with project layout version, safe dimensions/tab state, and harmless display preferences. It SHALL contain no transport generation, active or retired epoch, revision, panel payload, actor identifier, request result, command text, credential, or canonical game state. The current project layout version SHALL be 3, the version that replaces the reduced-motion override with the optional motion level (`full`, `reduced`, or `off`; absent while the player has chosen none). A project layout version SHALL migrate only through an explicitly registered migration, and the client SHALL register none: versions 1 and 2 have no migration. Malformed, oversized, missing, stock, or unknown versions, versions 1 and 2 among them, SHALL reset to the current version's default while preserving required components. A stored preference value outside its defined values SHALL be dropped while the wrapper's other valid preferences are kept.

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
- **WHEN** localStorage holds a well-formed version-1 or version-2 wrapper with a stored prose scale
- **THEN** the client loads the version-3 default with every preference at its default, text speed `normal`, auto-advance off, and no stored motion level among them, and persists that version-3 wrapper

#### Scenario: An invalid motion level is dropped
- **WHEN** localStorage holds a version-3 wrapper whose `motionLevel` is not `full`, `reduced`, or `off`, beside a valid prose scale
- **THEN** the wrapper loads with no stored motion level and keeps the prose scale
