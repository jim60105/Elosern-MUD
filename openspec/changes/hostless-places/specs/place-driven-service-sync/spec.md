## MODIFIED Requirements

### Requirement: One place record yields a complete working location
Adding a place record and running synchronization SHALL produce the whole
location with no other file edited: its interior room tagged and described,
its doorways connecting it to its exterior in both directions, its host
standing in it with the declared profession's components attached, and its
goods purchasable.

A place record that authors no host SHALL still yield its whole location —
the tagged, described interior and both doorways — with no NPC created for
it and no roster row derived from it. The room is the deliverable; the host
is an optional part of it, not its precondition.

#### Scenario: One record yields a working location
- **WHEN** a place record is added and synchronization runs
- **THEN** its interior, both doorways, its host and its purchasable goods
  all exist, and no module constant was added for it

#### Scenario: A host-less record yields a room and no NPC
- **WHEN** a place record authoring no host is added and synchronization
  runs
- **THEN** its interior exists once, tagged and described, reachable from
  and back to its exterior, and no service host stands in it

#### Scenario: A repeated run leaves a host-less room alone
- **WHEN** synchronization runs twice over a host-less place record
- **THEN** the room exists exactly once and no NPC is created on either run
