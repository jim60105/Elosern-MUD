# Spec Delta

## ADDED Requirements

### Requirement: sync_limbo removes every exit that touches 虛境
On every call that finds the starting room, `sync_limbo()` SHALL delete every persisted exit located in the starting room or leading into it, whatever its key, aliases or subclass. It SHALL log each deletion as the event `bootstrap_limbo_exit_pruned`, with context naming the exit and the side it touched. Objects that have a destination but are not exits SHALL be left alone.

#### Scenario: A leftover forward exit is removed
- **WHEN** a database holds an exit from the starting room to a settlement room and `sync_limbo()` runs
- **THEN** that exit no longer exists, and one `bootstrap_limbo_exit_pruned` event names it

#### Scenario: A reverse exit is removed
- **WHEN** a database holds an exit from any room into the starting room and `sync_limbo()` runs
- **THEN** that exit no longer exists, and one `bootstrap_limbo_exit_pruned` event names it

#### Scenario: A converged room is left alone
- **WHEN** `sync_limbo()` runs twice in a row
- **THEN** the second run deletes nothing and logs no prune event

#### Scenario: A non-exit object with a destination survives
- **WHEN** a non-exit object whose destination is the starting room exists and `sync_limbo()` runs
- **THEN** that object still exists

#### Scenario: Grid synchronization creates no exit touching 虛境
- **WHEN** `sync_grid()` runs over synthetic settlements while a starting room exists
- **THEN** no exit located in or leading into the starting room exists afterwards

## REMOVED Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
**Reason**: Characters start in their subrace's settlement (`subrace-start-settlements`),
and the owner decided that 虛境 only holds creation-pending shells. No gate view is consumed.
**Migration**: None. The game no longer reads the document `city_gate` block.
`drop-settlement-city-gate-field` removes it from the schema and the documents.

### Requirement: sync_grid creates exactly one forward gate exit per registry row and converges it idempotently
**Reason**: 虛境 has no exits any more.
**Migration**: `sync_limbo()` removes leftover forward exits (see "sync_limbo removes
every exit that touches 虛境").

### Requirement: Every sync prunes every exit whose destination is the starting room
**Reason**: Replaced by `sync_limbo()`'s removal of every exit touching 虛境, which
covers reverse exits too.
**Migration**: None. The replacement runs on every server start.

### Requirement: A registry row whose gate room is missing warns and is skipped without blocking other rows
**Reason**: There are no gate rows left.
**Migration**: None.

### Requirement: Adding a city means adding a registry row, with no bootstrap code change
**Reason**: There are no gate rows left. A settlement becomes a start location through
the start-location registry (`character-start-location`).
**Migration**: None.

### Requirement: The first city-gate traversal re-anchors a 虛境 home to the arrival gate room
**Reason**: Activation now sets `home` to the start room, so no player character has a
虛境 home to re-anchor.
**Migration**: None. Development databases with characters whose `home` is 虛境 are
recreated; the project has no released users.
