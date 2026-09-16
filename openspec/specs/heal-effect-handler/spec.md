## Purpose

Defines the `heal:<shape>` and `self_heal` effect conventions and their cast-time
resolution: HP restoration capped at the target's maximum, staged through the
shared `PendingEffect` commit mechanism in `world/rules/combat.py`, with no
revival of knocked-out targets.

## Requirements

### Requirement: heal effect prefix restores HP capped at max
`world/rules/combat.py` SHALL register a `heal` effect handler via `register_effect_handler`, staging a
`PendingEffect` per target that increases `entity.traits.hp.value` by a caster-stat-derived amount,
clamped so the result never exceeds `entity.traits.hp.max` and never decreases HP. A `heal:<shape>`
effect SHALL be declared only on a skill whose `target_spec` matches the shape (`single` on `SINGLE`
or `SELF` skills, `area` on `AREA` skills); `SkillDef` construction SHALL reject a mismatched pairing
so the declared shape is never silently ignored at use time.

#### Scenario: Healing a damaged target restores HP up to but not past max
- **WHEN** a `heal:single` effect resolves against a target at 40% of max HP
- **THEN** the target's HP increases by the computed amount and does not exceed `hp.max`

#### Scenario: Healing a full-HP target is a no-op that does not error
- **WHEN** a `heal:single` effect resolves against a target already at `hp.max`
- **THEN** the target's HP remains at `hp.max` and no exception is raised

#### Scenario: A heal shape mismatching the skill's target spec fails at construction
- **WHEN** a `SkillDef` is constructed with `target_spec=AREA` and `effects=["heal:single"]`
- **THEN** construction raises `ValueError`

### Requirement: heal:area targets every valid target in the action's target set
`heal:area` SHALL apply the same clamped restoration independently to every target selected for that effect from the action
resolution pipeline's validated AREA candidates, with no cross-target interaction
(one target's clamp does not affect another's). Without an explicit per-effect audience this is the complete validated list, including enemies; an explicit audience SHALL only narrow delivery as declared.

#### Scenario: An area heal restores each target independently
- **WHEN** a `heal:area` effect resolves against three targets at different HP percentages
- **THEN** each target's HP increases by the same computed amount, independently clamped to that
  target's own `hp.max`

### Requirement: self_heal restores the acting entity's HP regardless of the skill's resolved targets
`world/rules/combat.py` SHALL register a `self_heal` effect handler via `register_effect_handler`,
staging a `PendingEffect` that increases the acting entity's `hp.value` by a caster-derived amount
(clamped to `hp.max`), independent of and unaffected by the skill's own resolved target list — mirroring
how `self_buff_apply` binds to the actor rather than `targets`. The magnitude basis SHALL follow the
parsed effect: the bare form keeps the caster-stat `_heal_magnitude` basis verbatim (coefficient,
`heal_gain` amplification, freeform scale), while the `self_heal:missing_fraction:<f>` form SHALL
compute `round(missing_hp × f)` from the ACTING entity's own HP gap (its maximum minus its current
stored HP) read at staging time — never the target's gap — multiplied by the freeform cast scale
through the same scaled-magnitude leg as the stat basis. The missing-fraction basis SHALL NOT apply
the stat-derived `heal_gain` amplification, and both bases SHALL share the identical
`_restored_amount`/`_apply_heal` clamping, staged-log amount, and commit-time guards.

#### Scenario: self_heal restores the caster even when the skill's targets are enemies
- **WHEN** a skill with `effects=["damage:fire:magic", "self_heal"]` is cast at an enemy `SINGLE` target
- **THEN** the enemy target takes damage, and the caster's own HP increases (clamped to the caster's
  `hp.max`), not the enemy's

#### Scenario: The missing-fraction basis reads the caster's own HP gap
- **WHEN** a synthetic damage-plus-`self_heal:missing_fraction:0.1` spell resolves from a caster
  whose maximum exceeds current HP by a known amount against an enemy at different HP
- **THEN** the caster recovers exactly one tenth of their own missing HP (rounded per the contracted
  rounding), clamped at their maximum, while the enemy's HP state never enters the amount

#### Scenario: Scale multiplies both bases identically and heal_gain amplifies only the stat basis
- **WHEN** a scaled cast resolves a stat-basis and a missing-fraction `self_heal` on casters carrying
  a nonzero merged `heal_gain`
- **THEN** each amount is the scaled value of its own basis, with `heal_gain` applied to the
  stat-derived amount only and never to the missing-fraction amount

#### Scenario: A full-HP caster recovers zero from a missing-fraction heal
- **WHEN** a `self_heal:missing_fraction:<f>` effect resolves with the caster already at `hp.max`
- **THEN** the staged amount is zero, HP stays at maximum, and no exception is raised

### Requirement: Neither heal nor self_heal can revive a knocked-out target
Both handlers SHALL rely on the existing action-resolution/targeting pipeline's own alive-only
validation (`target_dead` rejection for `hp <= 0` targets, and AREA shorthand's exclusion of
`knocked_out` entities) rather than implementing any bypass. A `heal`/`self_heal` commit SHALL be a
no-op when the affected entity is not alive at commit time, so no ordering of effects within one
action (and no `self_heal` on a knocked-out caster) can restore a knocked-out entity to positive HP.
This holds identically for every `self_heal` magnitude basis: a missing-fraction declaration on a
dead or mid-action-knocked-out caster stages zero or commits nothing.

#### Scenario: A heal cannot be cast targeting a knocked-out ally
- **WHEN** a player attempts to cast a `heal:single` skill directly at a knocked-out (`hp <= 0`) ally
- **THEN** the cast is rejected by the existing targeting validation (`target_dead`), before the `heal`
  handler ever runs

#### Scenario: A mid-action knockout is not reversed by a later heal
- **WHEN** a single action's effects first reduce a target's HP to 0 and then apply `heal:single` to
  that same target
- **THEN** the target remains knocked out at `hp = 0` and the heal restores no HP

#### Scenario: A knocked-out caster gains nothing from a missing-fraction self-heal
- **WHEN** a cast carrying `self_heal:missing_fraction:<f>` executes with the caster at `hp <= 0`
- **THEN** the caster's HP stays at zero or below — neither the staged amount nor the commit revives
  or credits them
