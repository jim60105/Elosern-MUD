## MODIFIED Requirements

### Requirement: Nonlethal policy transforms lethal projection before EventLog planners
A validated BattlefieldActionContext MAY carry a deterministic `nonlethal` policy as a
session-wide flag and/or per-entity `nonlethal_keys` (entity keys protected by the policy; in a
hostile session these are the allied companions). During damage
projection, a positive-to-non-positive crossing under the policy SHALL stage HP at 1 and mark the exact
target knocked out; the per-entity key set SHALL apply to the damaged target's key and the
session-wide flag SHALL apply to every target, with the flag unchanged in its existing exam
semantics. Step 7 SHALL emit `target_knocked_out` and SHALL NOT emit `target_defeated`. This
transformation SHALL occur before event-effect planners, so ordinary kill XP, DEFEAT progress,
protected-entity failure, and loot consumers receive no defeat entry. Contexts without the policy
SHALL retain existing lethal behavior.

#### Scenario: Nonlethal projection emits knockout only
- **WHEN** exam damage would cross a target from positive HP to zero or lower
- **THEN** projected and committed HP is 1, knockout identity is staged, `target_knocked_out` is emitted,
  and no `target_defeated` entry exists

#### Scenario: A companion key under the per-entity policy is knocked out
- **WHEN** hostile-session damage would cross a companion from positive HP to zero or lower
- **THEN** the companion's projected and committed HP is 1, `target_knocked_out` is emitted, and no
  `target_defeated` entry exists for the companion

#### Scenario: Hostile targets outside the key set stay lethal
- **WHEN** identical damage in the same hostile session would cross a monster from positive HP to
  zero or lower
- **THEN** the ordinary lethal crossing and `target_defeated` behavior apply to the monster

#### Scenario: Quest and XP planners cannot observe exam defeat
- **WHEN** event-effect planners inspect the completed nonlethal EventLog
- **THEN** none can match ordinary defeat because the log contains only knockout identity

#### Scenario: Ordinary hostile damage is unchanged
- **WHEN** identical damage resolves without a nonlethal policy
- **THEN** the existing lethal HP crossing and target-defeated planner behavior apply
