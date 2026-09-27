## ADDED Requirements

### Requirement: Client help and finite display vocabularies are localized
Client-owned help, combat target types, party guidance, condition modifiers and server-owned codex race titles SHALL use Traditional Chinese display vocabulary instead of raw English keys. Protocol identifiers, command syntax and user-authored content SHALL remain unchanged.

#### Scenario: Unknown modifier retains information
- **WHEN** a condition contains known and unknown modifier keys
- **THEN** known keys are localized, unknown keys receive a neutral localized descriptor, and every original numeric sign/unit/value remains in the accessible description

#### Scenario: Help describes real keys
- **WHEN** the help overlay opens after combat navigation has changed
- **THEN** it names only implemented bindings in localized prose and preserves literal key/command syntax

### Requirement: Condition chips expose readable names as well as severity
Each visible condition chip SHALL pair its non-colour severity indicator with a readable bounded condition label and supplied duration, while preserving the full accessible description and existing overflow path.

#### Scenario: Labels are long
- **WHEN** six conditions have long names and another condition overflows
- **THEN** visible names remain bounded without covering vitals, full descriptions remain accessible, and the overflow control reaches the remainder

### Requirement: Gallery dates use structured timestamps and local presentation
Gallery card timestamps SHALL be presented as localized relative time with the exact localized instant available, using structured created_at values rather than parsing label text. Generated card labels SHALL NOT repeat a UTC timestamp; status information SHALL remain truthful.

#### Scenario: Cards share a generated label
- **WHEN** two gallery cards have different creation times
- **THEN** their relative/exact dates distinguish them without a duplicate UTC name or any record mutation
