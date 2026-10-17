# Spec Delta

## ADDED Requirements

### Requirement: Normal possession release preserves the companion's room presence

A release for `handback` or `party_change` SHALL preserve the companion's occupied pre-release room and party membership at the release boundary, with no off-grid stash or stale logout-location state. An initially co-located companion SHALL remain co-located with its owner and eligible for possession, following, and combat collection under their existing gates. Later membership removal SHALL retain its existing policy. Disconnect and link-dead recovery are outside this requirement.

#### Scenario: 歸位 leaves both party members in the room

- **WHEN** an owner possesses a bound companion in their shared room and performs 歸位 without either figure changing rooms
- **THEN** control returns to the owner, both figures remain in that room and its contents, the same companion remains in the owner's party, both possession bindings are clear, and the companion has no stale logout-location state

#### Scenario: Party-change handback preserves presence before membership removal

- **WHEN** a possession-carrying party change requests handback while the owner and companion share a room
- **THEN** handback returns control to the owner and leaves the companion in that room and still in the party at the release boundary, with both possession bindings clear and no stale logout-location state
- **AND** any subsequent actual membership removal is performed by its existing owning operation and does not stash the companion off-grid

#### Scenario: The released companion can be possessed again

- **WHEN** either normal release reason completes for a co-located pair with membership retained and all other possession gates still passing
- **THEN** a subsequent `possess` of that same companion succeeds without operator repair or an intervening login

#### Scenario: The released companion follows and participates in combat collection

- **WHEN** either normal release reason completes for a co-located pair with membership retained, then the owner moves through a valid exit and ordinary party following runs
- **THEN** the same companion follows into the destination room and is included by the existing combat-companion collection when its other eligibility conditions hold

#### Scenario: Release preserves an intentionally remote companion's position

- **WHEN** the controlled companion has moved to another room before a normal release
- **THEN** it remains in its occupied pre-release room, the owner's body stays in its own room, and release performs no reunion teleport or relaxation of co-location gates

#### Scenario: A failed handback restores the occupied room state

- **WHEN** the owner re-puppet is refused or a later release write fails after the companion unpuppets
- **THEN** the existing failure and recovery contract applies, the original possession remains recoverable, and both persisted and in-process companion location and logout-location state equal their pre-release values
- **AND** a subsequent successful retry leaves the companion in its occupied room with no stale logout-location state

#### Scenario: Repeated release does not move the companion

- **WHEN** a completed normal release is requested again with no active possession
- **THEN** it remains a no-op, with no movement, membership write, or duplicate successful-release event
