## ADDED Requirements

<!-- Three source-document secondary effects (挑釁凝視's dedicated accuracy debuff, 獻身姿態's
     self-defense penalty, 無恥宣言's temporary shame-multiplier buff) are intentionally not covered
     by this capability as dedicated effects — see design.md D-2 (a reuse, not a gap) and D-3 (two
     genuine drops) for why. -->

### Requirement: Nine Tier 1-4 shame acts are registered, gated by exposure_act_count and/or watched_count thresholds
`world/skills/sexual_acts/shame.py`'s `SHAME_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s one seed row: three acts each declaring `unlock={"exposure_act_count": 5}`
(`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`); one act declaring
`unlock={"exposure_act_count": 20}` (`shame_full_expose`); one act declaring
`unlock={"exposure_act_count": 20, "masturbation_count": 25}` (`shame_public_masturbation`); one act
declaring `unlock={"watched_count": 10}` (`shame_provocative_gaze`); one act declaring
`unlock={"watched_count": 10, "exposure_act_count": 20}` (`shame_public_performance`); one act
declaring `unlock={"exposure_act_count": 50}` (`shame_devoted_pose`); and one act declaring
`unlock={"exposure_act_count": 50, "watched_count": 30}` (`shame_shameless_declaration`). Every one
of these nine acts SHALL declare `actor_part=None`.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `exposure_act_count == 4`
- **THEN** `shame_half_expose_chest` is absent from the returned set
- **WHEN** the same entity's `exposure_act_count` becomes `5`
- **THEN** `shame_half_expose_chest` is present in the returned set

#### Scenario: shame_public_masturbation requires both exposure_act_count and masturbation_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `exposure_act_count == 20` and
  `masturbation_count == 24`
- **THEN** `shame_public_masturbation` is absent from the returned set
- **WHEN** the same entity's `masturbation_count` becomes `25`
- **THEN** `shame_public_masturbation` is present in the returned set

#### Scenario: shame_provocative_gaze is gated by watched_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `watched_count == 10` and
  `exposure_act_count == 0`
- **THEN** `shame_provocative_gaze` is present in the returned set

#### Scenario: shame_shameless_declaration requires both exposure_act_count and watched_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `exposure_act_count == 50` and
  `watched_count == 29`
- **THEN** `shame_shameless_declaration` is absent from the returned set
- **WHEN** the same entity's `watched_count` becomes `30`
- **THEN** `shame_shameless_declaration` is present in the returned set

### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event; no new sexual.yaml row is added
`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`, `shame_full_expose`,
`shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`, and
`shame_shameless_declaration` SHALL each declare `"self_exposure"` in `sexual_events`.
`shame_provocative_gaze` SHALL declare `sexual_events=()`. `world/rules/rulebook/sexual.yaml` SHALL
gain no rule row from this change.

#### Scenario: Casting a Tier 1 act raises the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_half_expose_chest` on
  itself
- **THEN** `entity.sexual.exposure`'s ordinal increases by exactly `1`

#### Scenario: shame_provocative_gaze does not raise the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_provocative_gaze`
- **THEN** the actor's `exposure` ordinal is unchanged afterward

#### Scenario: An AREA shame act's self_exposure lands on its targets, not the actor
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_public_performance`
  targeting one other entity
- **THEN** the target's `exposure` ordinal increases by exactly `1` and the actor's `exposure`
  ordinal is unchanged afterward

### Requirement: shame_public_masturbation credits three counters and emits two events
`shame_public_masturbation` SHALL declare `actor_counters=("exposure_act_count",
"masturbation_count", "watched_count")` and `sexual_events=("self_exposure", "masturbation_climax")`.

#### Scenario: Casting shame_public_masturbation increments all three counters by exactly one
- **WHEN** an entity at `exposure_act_count=20, masturbation_count=25, watched_count=0` casts
  `shame_public_masturbation` on itself
- **THEN** afterward `exposure_act_count=21`, `masturbation_count=26`, and `watched_count=1`

### Requirement: shame_public_performance credits both watched_count and exposure_act_count on the actor
`shame_public_performance` SHALL declare `actor_counters=("watched_count", "exposure_act_count")`
and `participant_counters=()`.

#### Scenario: Casting shame_public_performance increments both actor counters by exactly one
- **WHEN** an entity at `watched_count=10, exposure_act_count=20` casts `shame_public_performance`
  targeting one hostile entity, both starting at those exact values
- **THEN** afterward the actor's `watched_count` equals `11` and `exposure_act_count` equals `21`,
  and the target's counters are unchanged

### Requirement: shame_provocative_gaze credits hostile_act_count on the actor only, never on a target
`shame_provocative_gaze` SHALL declare `actor_counters=("hostile_act_count",)` and
`participant_counters=()`.

#### Scenario: Casting shame_provocative_gaze credits only the actor
- **WHEN** entity A casts `shame_provocative_gaze` targeting entity B, both starting at
  `hostile_act_count == 0`
- **THEN** `A.sexual.hostile_act_count` equals `1` and `B.sexual.hostile_act_count` remains `0`
  afterward

### Requirement: The three AREA acts declare target_part as a BODY_PARTS member, never None
`shame_provocative_gaze`, `shame_public_performance`, and `shame_devoted_pose` SHALL each declare
`target_part="腰腹"`.

#### Scenario: An AREA shame act's target_part is a real body part
- **WHEN** each of the three AREA acts is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `target_part` equals `"腰腹"`, a member of `world.lore.sexual_vocab.BODY_PARTS`
