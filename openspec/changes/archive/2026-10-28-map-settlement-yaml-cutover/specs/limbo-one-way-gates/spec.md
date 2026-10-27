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

#### Scenario: The registry pins the single capital row
- **WHEN** the capital's loaded starting-room relationship is resolved
- **THEN** its current qualified node and authored labels supply the immutable gate view; conversion preserves existing values without a second coordinate/copy approval table

#### Scenario: Every registry row yields exactly one forward exit
- **WHEN** every loaded entry has a materialized target and synchronization runs twice
- **THEN** each entry yields exactly one forward exit and colliding exit keys/aliases reject

#### Scenario: The registry cannot be mutated at runtime
- **WHEN** a consumer attempts to insert, replace or delete a loaded gate-view entry
- **THEN** mutation fails and the view remains unchanged

#### Scenario: Bootstrap carries no gate surface of its own
- **WHEN** a synthetic settlement entry's labels and target change
- **THEN** synchronization follows the loaded values without a competing bootstrap constant

#### Scenario: The registry carries exactly two rows today
- **WHEN** supported settlement files are added or removed
- **THEN** the derived entry set follows source membership rather than a fixed production count; no Python gate roster must be edited

#### Scenario: A row may name a concealed path, not a walled gate
- **WHEN** the loaded entry names a concealed path
- **THEN** that authored label is retained without assuming a walled gate

#### Scenario: Bootstrap duplicates no gate data
- **WHEN** gate views are rebuilt from modified source relationships
- **THEN** bootstrap uses those current labels and qualified targets rather than a duplicated declaration

### Requirement: Adding a city means adding a registry row, with no bootstrap code change
Adding a discovered settlement document with a starting-room entry SHALL extend gate synchronization without code registration and retain forward-only entry and reverse pruning.

#### Scenario: Additional source
- **WHEN** a supported settlement document with an entry is added
- **THEN** its forward gate appears after synchronization without Python roster changes and any reverse exit is pruned

#### Scenario: An injected second row gains its own forward exit
- **WHEN** a second synthetic settlement source supplies a distinct valid entry
- **THEN** it gains exactly its own forward exit without bootstrap registration

#### Scenario: Registry growth never reintroduces a reverse exit
- **WHEN** a reverse exit exists while multiple loaded settlement entries synchronize
- **THEN** the reverse exit is pruned and all remaining starting-room entries are forward-only

