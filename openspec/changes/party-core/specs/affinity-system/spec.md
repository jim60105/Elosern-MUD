## MODIFIED Requirements

### Requirement: The party auto-leave recheck hook runs after negative affinity deltas
The sole-writer API SHALL invoke the party auto-leave recheck after every negative delta. The hook
SHALL be the wired rule from `party-core`: when the NPC is a bound companion and its affinity
toward the player drops below the invite threshold (70), it SHALL call
`world/rules/party.py::leave_party(npc, player, reason="affinity_below_threshold")` as part of the
affinity write's transaction — a failed leave SHALL roll back the entire negative-delta operation
— and the caller SHALL notify the player only after the outer transaction commits; a drop that
stays at or above the threshold SHALL NOT end the party. The hook SHALL be deterministic and SHALL
be side-effect free for non-companions.

#### Scenario: The hook is invoked on negative deltas
- **WHEN** a negative delta is applied through the sole-writer API
- **THEN** the auto-leave recheck hook runs once with the affected NPC and player

#### Scenario: A below-threshold drop ends a companion party
- **WHEN** a bound companion's affinity drops from 70 to 69 through a negative delta
- **THEN** the binding is removed with the auto-leave reason and the player is notified after the
  write commits

#### Scenario: A failed auto-leave rolls back the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold
- **THEN** the affinity value and both party attributes return to their pre-delta values and no
  notification is sent

#### Scenario: A non-companion negative delta changes nothing
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** the hook runs, no party call occurs, and no notification is emitted
