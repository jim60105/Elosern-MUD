# art-source-fault-facts Specification

## Purpose
Preserve bounded startup artwork health facts attributable to the requested source so resolution can distinguish normal absence from actual failures.

## Requirements

### Requirement: Root absence retains configuration meaning
Artwork startup SHALL retain whether an optional default root was deliberately absent, explicitly configured unavailable, or unreadable. Missing optional configuration SHALL be normal; configured or I/O failures SHALL remain bounded fault facts without preventing unrelated sources or deterministic play.

#### Scenario: Default absence is normal
- **WHEN** the default optional root is absent with no explicit binding
- **THEN** no availability fault applies

#### Scenario: Configured root failure survives empty index
- **WHEN** an explicitly configured root is unavailable or a root is unreadable
- **THEN** the snapshot retains the matching availability fact even though it indexes no images

### Requirement: Faults are attributed to requested sources
The startup snapshot SHALL preserve bounded requested-default, rejected-identity and selected-source metadata faults. A broken declared default SHALL precede its deterministic substitute. Unselected rejected siblings SHALL remain diagnostics and SHALL NOT taint a healthy selected source.

#### Scenario: Default faults precede substitution
- **WHEN** a manifest default is missing or rejected and a valid sibling is selected deterministically
- **THEN** resolution can attribute a fault to the declared default before the substitute

#### Scenario: Selected metadata falls back safely
- **WHEN** selected-source geometry or applicable manifest metadata is invalid
- **THEN** a metadata fault accompanies safe geometry without blocking valid image bytes

#### Scenario: Unselected rejection remains isolated
- **WHEN** one unselected sibling is corrupt while the requested image is healthy
- **THEN** the healthy image has no presentation fault from that sibling
