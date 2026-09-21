# altoria-crown-and-watch Specification

## Purpose
Give the capital its seats of government and violence: a palace, a noble
quarter's watch, a gate guardhouse and a drill yard. The palace lands host-less
on purpose — an empty throne approach is honest about being the edge of what is
built — and the change's two load-bearing refusals are written as rules: the
crown's rooms stand open until a story closes them (no gate, no rank check, no
quest prerequisite), and the city watch posts no work of its own, because the
guild board and `npc:` private commissions already exist and the source
document rules out a parallel bounty system.

## Requirements

### Requirement: The capital has a palace, a noble quarter, a guardhouse and a drill yard
The capital SHALL carry these four locations as permanent interiors. Three SHALL hold an
authored host who converses; the palace SHALL hold none, and SHALL still be a complete,
enterable, permanently tagged room reachable from and back to its exterior.

#### Scenario: Four locations exist, three of them staffed
- **WHEN** synchronization completes
- **THEN** all four interiors exist once and are reachable both ways, three hold one
  dialogue-carrying host each, and the palace holds no service host

#### Scenario: The empty palace survives a resynchronization
- **WHEN** synchronization runs twice
- **THEN** the palace interior exists exactly once and no host is created in it on either run

### Requirement: The crown's rooms stand open until a story closes them
Neither the palace nor the noble quarter SHALL carry an access lock, a rank check, a quest
prerequisite or any other gate. Their restriction is a narrative device the source document
reserves for a questline that has not been written, and a gate with nothing behind it makes a
room unreachable rather than mysterious. When such a story lands it SHALL introduce the gate
together with what lies beyond it.

#### Scenario: Any player may walk in
- **WHEN** a player with no rank, no quest and no prior visit enters the palace and the noble
  quarter
- **THEN** both are entered successfully and no lock or prerequisite is consulted

### Requirement: The watch posts no work of its own
The guardhouse SHALL NOT introduce a bounty board, a commission list, or any work-offering
surface parallel to the adventurers' guild. Work that a city watch would plausibly offer
SHALL reach players through the guild board or a private commission, which already exist.

#### Scenario: No parallel work surface appears
- **WHEN** the guardhouse and its host are inspected for quest-offering capability
- **THEN** the host carries no quest-issuer component, the room exposes no board, and no new
  work-listing command exists
