## MODIFIED Requirements

### Requirement: ActionResolver exposes side-effect-free preflight for player combat input
`ActionResolver.preflight(request)` SHALL validate skill ownership/kind, current resources, targets,
action capability, declared actor/target state and contact conditions, nonempty effect audiences, effect-handler availability, and time-cost metadata without randomness, effect
staging, EventLog emission, state mutation, or world-time advance. It SHALL return the same named
rejection categories as `resolve()` for those checks. A successful preflight SHALL not guarantee that
state remains valid after earlier initiative actions; final resolution SHALL still run all eight steps.

#### Scenario: Preflight rejection has no side effects
- **WHEN** preflight rejects an unknown skill, insufficient resource, invalid target, blocking buff,
  unmet state/contact condition, empty delivery audiences, unknown effect handler, or malformed time metadata
- **THEN** entity, battlefield, quest, session, random-generator, EventLog, and world-clock state are
  unchanged

#### Scenario: Successful preflight does not roll or stage
- **WHEN** a valid damage request passes preflight
- **THEN** no d100 roll occurs, no PendingEffect or EventLog is created, and later `resolve()` performs
  the ordinary complete pipeline once

#### Scenario: Final resolution may reject after initiative state changes
- **WHEN** preflight succeeds and an earlier combatant makes the target invalid before the actor's turn
- **THEN** final resolution returns its ordinary named rejection without claiming that the started round
  is rollback-safe
