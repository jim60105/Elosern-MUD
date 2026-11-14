# Spec Delta

## ADDED Requirements

### Requirement: The rite card opens on arrival and never on a session's first snapshot
The rite presentation state SHALL open the card when the committed `rite` panel becomes available for a district it has not seen available in the session, and SHALL stay closed on the first snapshot of a session.

#### Scenario: Arrival, repeat and return
- **WHEN** a later snapshot makes the panel available, the card is dismissed, the same district is committed again, and then the panel becomes unavailable and available again
- **THEN** the card opens, stays closed for the repeated snapshot, and opens again after the return

#### Scenario: First snapshot
- **WHEN** a session's first snapshot already carries an available panel
- **THEN** the state is closed

### Requirement: Rite transitions are local and performing dispatches once
Opening, approaching and leaving SHALL change only local state and send nothing. Performing SHALL send the rite action exactly once for a listed option while the stage is open, connected and unlocked, and SHALL send nothing otherwise.

#### Scenario: Local transitions
- **WHEN** the card is approached, left and reopened
- **THEN** the phase follows card, stage, closed, card with the revisit mark, and no action was sent

#### Scenario: Perform guards
- **WHEN** performing is requested twice in a row, for an unknown option, while disconnected, and while mutations are locked
- **THEN** exactly one action was sent, carrying the option and a null member identifier

### Requirement: The rite state adopts its own result and resets off the landmark
A success result for the pending request SHALL become the playing delivery; any other outcome SHALL clear the pending request and play nothing. The state SHALL reset to closed when the panel becomes unavailable, the mode leaves exploration or the session changes, and leaving SHALL be refused while a delivery plays.

#### Scenario: Result adoption
- **WHEN** the pending request succeeds with a delivery, another request's result arrives, and a second request is refused
- **THEN** the first delivery plays, the foreign result changes nothing, and the refusal leaves no delivery

#### Scenario: Reset
- **WHEN** the panel becomes unavailable while the stage is open
- **THEN** the phase is closed with no pending request and no delivery

### Requirement: An open rite card or stage is a centred card
While the rite card or stage is open the store's centred-card predicate SHALL be true, so walking and the compass stop as they do for every centred card.

#### Scenario: Predicate
- **WHEN** the phase is card, stage and closed in turn
- **THEN** the predicate is true, true and false
