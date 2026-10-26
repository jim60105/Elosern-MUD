# Spec Delta

## MODIFIED Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
Immutable game gate views SHALL derive solely from settlement-owned starting-room entry relationships with qualified targets and authored labels, without reverse entry declarations.

#### Scenario: Forward gates and immutability
- **WHEN** two synthetic settlement entries are loaded and synchronized twice
- **THEN** each yields one forward exit with its authored labels, the view rejects mutation, and no reverse entry is created

#### Scenario: Concealed path
- **WHEN** an entry targets a settlement without a walled gate
- **THEN** its authored concealed-path naming is preserved without a bootstrap naming constant

### Requirement: Adding a city means adding a registry row, with no bootstrap code change
Adding a discovered settlement document with a starting-room entry SHALL extend gate synchronization without code registration and retain forward-only entry and reverse pruning.

#### Scenario: Additional source
- **WHEN** a supported settlement document with an entry is added
- **THEN** its forward gate appears after synchronization without Python roster changes and any reverse exit is pruned

