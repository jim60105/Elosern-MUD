## ADDED Requirements

### Requirement: ActionResolver exposes side-effect-free preflight for player combat input
`ActionResolver.preflight(request)` SHALL validate skill ownership/kind, current resources, targets,
action capability, effect-handler availability, and time-cost metadata without randomness, effect
staging, EventLog emission, state mutation, or world-time advance. It SHALL return the same named
rejection categories as `resolve()` for those checks. A successful preflight SHALL not guarantee that
state remains valid after earlier initiative actions; final resolution SHALL still run all eight steps.

#### Scenario: Preflight rejection has no side effects
- **WHEN** preflight rejects an unknown skill, insufficient resource, invalid target, blocking buff,
  unknown effect handler, or malformed time metadata
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

### Requirement: Nonlethal policy transforms lethal projection before EventLog planners
A validated BattlefieldActionContext MAY carry a deterministic `nonlethal` policy. During damage
projection, a positive-to-non-positive crossing under that policy SHALL stage HP at 1 and mark the exact
target knocked out. Step 7 SHALL emit `target_knocked_out` and SHALL NOT emit `target_defeated`. This
transformation SHALL occur before event-effect planners, so ordinary kill XP, DEFEAT progress,
protected-entity failure, and loot consumers receive no defeat entry. Contexts without the policy SHALL
retain existing lethal behavior.

#### Scenario: Nonlethal projection emits knockout only
- **WHEN** exam damage would cross a target from positive HP to zero or lower
- **THEN** projected and committed HP is 1, knockout identity is staged, `target_knocked_out` is emitted,
  and no `target_defeated` entry exists

#### Scenario: Quest and XP planners cannot observe exam defeat
- **WHEN** event-effect planners inspect the completed nonlethal EventLog
- **THEN** none can match ordinary defeat because the log contains only knockout identity

#### Scenario: Ordinary hostile damage is unchanged
- **WHEN** identical damage resolves without a nonlethal policy
- **THEN** the existing lethal HP crossing and target-defeated planner behavior apply
