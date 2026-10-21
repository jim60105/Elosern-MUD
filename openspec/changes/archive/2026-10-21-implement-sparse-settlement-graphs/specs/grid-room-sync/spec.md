# Spec Delta

## ADDED Requirements

### Requirement: Sparse authored graphs synchronize without identity loss
Settlement graph synchronization SHALL support sparse integer-coordinate nodes and explicit roads with stable authored identity. Coordinate replacement SHALL converge in place before missing-node deletion, preserving rooms, occupants and references; conflicting bindings SHALL fail before mutation.

#### Scenario: Identity replacement and repeat startup
- **WHEN** an occupied synthetic node changes from (1,1) to (5000,200) and synchronization runs twice
- **THEN** room dbid, occupant location, homes, inbound references and authored exit identities persist; the second run changes nothing and creates no duplicates.

#### Scenario: Sparse route costs
- **WHEN** nodes span millions of coordinate units with only three roads
- **THEN** pathfinding uses those roads with unequal physical lengths and allocates proportional to graph size, never a meter lattice.

#### Scenario: Collision rejection
- **WHEN** two authored identities bind the same destination or an old room binds ambiguously
- **THEN** validation refuses before any room, tag, reference or cached coordinate changes.

## MODIFIED Requirements

### Requirement: sync_grid() is distinct from sync_all() and instantiates real rooms and exits
`world/maps/bootstrap.py` SHALL provide a `sync_grid()` function, distinct in name and module from
`world/lore/sync.py::sync_all()`. `sync_grid()` SHALL synchronize every declared sparse node and explicit road into corresponding `XYZRoom`/`XYZExit` objects, without dense ASCII parsing.
`sync_all()` SHALL NOT be renamed, merged with, or repurposed to perform this work.

#### Scenario: sync_grid produces real, puppetable-adjacent room objects
- **WHEN** `sync_grid()` runs against an empty database
- **THEN** twenty-one `GridRoom`/`AnchorRoom` instances and fifty-two `XYZExit` instances exist in
  the database for the `capital_altoria` map, each queryable via ordinary Evennia object search —
  not `LoreRecord` Scripts. The fifty-two directed exits reflect the twenty-six map links spawning
  one exit per travel direction.

#### Scenario: sync_all's own behavior is unaffected
- **WHEN** `sync_all()` runs
- **THEN** it creates or updates only `LoreRecord` Script objects, exactly as before this change; it
  creates no `GridRoom`, `AnchorRoom`, or `XYZExit`
