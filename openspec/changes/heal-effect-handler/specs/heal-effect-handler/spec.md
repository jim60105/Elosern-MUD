## ADDED Requirements

### Requirement: heal effect prefix restores HP capped at max
`world/rules/combat.py` SHALL register a `heal` effect handler via `register_effect_handler`, staging a
`PendingEffect` per target that increases `entity.traits.hp.value` by a caster-stat-derived amount,
clamped so the result never exceeds `entity.traits.hp.max` and never decreases HP.

#### Scenario: Healing a damaged target restores HP up to but not past max
- **WHEN** a `heal:single` effect resolves against a target at 40% of max HP
- **THEN** the target's HP increases by the computed amount and does not exceed `hp.max`

#### Scenario: Healing a full-HP target is a no-op that does not error
- **WHEN** a `heal:single` effect resolves against a target already at `hp.max`
- **THEN** the target's HP remains at `hp.max` and no exception is raised

### Requirement: heal:area targets every valid target in the action's target set
`heal:area` SHALL apply the same clamped restoration independently to every target the action
resolution pipeline already validated for an AREA-targeted skill, with no cross-target interaction
(one target's clamp does not affect another's).

#### Scenario: An area heal restores each target independently
- **WHEN** a `heal:area` effect resolves against three targets at different HP percentages
- **THEN** each target's HP increases by the same computed amount, independently clamped to that
  target's own `hp.max`

### Requirement: self_heal restores the acting entity's HP regardless of the skill's resolved targets
`world/rules/combat.py` SHALL register a `self_heal` effect handler via `register_effect_handler`,
staging a `PendingEffect` that increases the acting entity's `hp.value` by a caster-stat-derived amount
(clamped to `hp.max`), independent of and unaffected by the skill's own resolved target list — mirroring
how `self_buff_apply` binds to the actor rather than `targets`.

#### Scenario: self_heal restores the caster even when the skill's targets are enemies
- **WHEN** a skill with `effects=["damage:fire:magic", "self_heal"]` is cast at an enemy `SINGLE` target
- **THEN** the enemy target takes damage, and the caster's own HP increases (clamped to the caster's
  `hp.max`), not the enemy's

### Requirement: Neither heal nor self_heal can revive a knocked-out target
Both handlers SHALL rely on the existing action-resolution/targeting pipeline's own alive-only
validation (`target_dead` rejection for `hp <= 0` targets, and AREA shorthand's exclusion of
`knocked_out` entities) rather than implementing any bypass. Neither handler SHALL contain logic that
special-cases an `hp <= 0` target.

#### Scenario: A heal cannot be cast targeting a knocked-out ally
- **WHEN** a player attempts to cast a `heal:single` skill directly at a knocked-out (`hp <= 0`) ally
- **THEN** the cast is rejected by the existing targeting validation (`target_dead`), before the `heal`
  handler ever runs
