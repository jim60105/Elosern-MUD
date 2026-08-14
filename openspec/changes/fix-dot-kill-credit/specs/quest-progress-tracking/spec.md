## MODIFIED Requirements

### Requirement: DEFEAT progress is planned automatically from committed player action events
The quest event-effect planner SHALL inspect `target_defeated` entries produced by an `ActionResolver` request or by the combat upkeep settlement. It SHALL advance only active DEFEAT stages owned by the acting entity when that entity is a `PlayerCharacter`, and SHALL additionally advance the owner's matching stage when the acting entity is a bound companion of the owner (per the party binding) and is not knocked out; a companion's entries SHALL follow the same aggregation, cap, and one-transition rules as the owner's own. A bound-target objective SHALL match `data["target_id"]` against the record's `objective_target_ids`; an unbound objective SHALL match its declared `monster_tier`. Display keys SHALL NOT be used as entity identity. The resulting quest mutation SHALL commit in the same action or combat-round transaction as the lethal damage. The planner SHALL aggregate every matching defeat entry in one EventLog per quest, cap progress at the current objective quantity, perform at most one stage transition, and discard surplus kills rather than applying them to the next stage. Simulated defeats (guild examinations) and unattributed upkeep ticks SHALL advance no quest and SHALL not fail a protected entity.

#### Scenario: Player defeat advances a matching tier objective automatically
- **WHEN** a player action lethally damages a monster whose tier matches the player's active DEFEAT stage
- **THEN** `ActionResolver.resolve()` commits the damage and increments quest progress without any caller invoking a separate observer

#### Scenario: Bound objective matches exact dbref
- **WHEN** two monsters share a display key but only one dbref is in `objective_target_ids`
- **THEN** defeating the unbound monster does not advance the quest and defeating the bound monster does

#### Scenario: A bound companion's kill advances the owner's objective
- **WHEN** a bound, non-knocked-out companion defeats a monster matching the owner's active DEFEAT stage
- **THEN** the owner's quest progress advances in the same action transaction with the same cap and one-transition rules

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion defeats a matching-tier monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Another character's action grants no ordinary kill credit
- **WHEN** an NPC that is not a bound companion, a different `PlayerCharacter`, or a monster defeats a matching-tier monster
- **THEN** the quest owner's ordinary DEFEAT progress is unchanged

#### Scenario: Quest planner failure rejects the complete action
- **WHEN** the quest planner cannot stage a valid transition because the actor's active record is malformed
- **THEN** the action rejects before commit and target HP, resources, progression, quest log, and pins all remain unchanged

#### Scenario: AREA defeat entries aggregate without skipping stages
- **WHEN** one AREA action defeats three matching targets while the current objective needs two
- **THEN** progress reaches two, the current stage transitions exactly once, and the surplus kill is not applied to the next stage

#### Scenario: An attributed upkeep kill advances the matching objective
- **WHEN** the player's damaging rate tick causes the lethal HP crossing of a monster matching the player's active DEFEAT stage
- **THEN** the quest log advances in the same combat-round transaction with the same cap and one-transition rules

#### Scenario: A simulated or unattributed upkeep kill grants no quest progress
- **WHEN** a lethal rate tick fires inside a guild examination, or an upkeep tick has no resolvable source
- **THEN** no quest DEFEAT stage advances and no protected-entity failure occurs
