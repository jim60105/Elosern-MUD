# Spec Delta

## MODIFIED Requirements

### Requirement: advance() settles exactly the entities its caller supplies, never a global registry
Clock per-entity stages SHALL settle only the supplied scope without global actor discovery; registered owner sources SHALL settle their own declared durable activity/journey intervals globally through their snapshot contract, excluding duplicate settlement of any supplied body for that same interval.

#### Scenario: Only the supplied entities are settled
- **WHEN** `advance()` is called with `entities=[actor]`, and a different `LivingEntity` exists
  elsewhere in the database with an active buff
- **THEN** that other entity's buff state is unchanged after the call , only `actor`'s state reflects
  settlement

#### Scenario: The registered call sites pass their documented scopes
- **WHEN** `CmdCast`'s integration, out-of-combat item use, and the skip commands call `advance()`
- **THEN** each passes the acting character's present party scope, `charge_movement()` passes the
  travelling party, and `settle_combat_result()` passes `entities=battlefield.roster.values()`

#### Scenario: Explicit activity-owned interval
- **WHEN** a registered monster activity source settles an unobserved actual group and one group member is also supplied to the advance
- **THEN** its declared physiology interval settles once under its owner, unrelated entities stay untouched and later source failure restores every owner surface
