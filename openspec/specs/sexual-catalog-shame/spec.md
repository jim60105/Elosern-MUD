# sexual-catalog-shame Specification

## Purpose

Register the nine counter-gated 羞恥線 acts across four tiers, filling the shame line from its one
seed act to ten. Tier 1 opens at `exposure_act_count >= 5`, Tier 2 at `exposure_act_count >= 20`
(公開自慰 compound-gated on `masturbation_count`), Tier 3 at `watched_count >= 10` (公開表演
compound-gated on `exposure_act_count`), and Tier 4 at `exposure_act_count >= 50` (無恥宣言
compound-gated on `watched_count`). Every act except the battlefield taunt 挑釁凝視 reuses the
actor-scoped `self_exposure` event shipped with the seed and adds the actor-scoped
`public_exposure` event; the four public acts additionally declare the observer-gated
`watched_during_activity` event, and the three implicitly sexual public acts declare
`public_sexual_activity`. This change adds no rulebook row.

## Requirements

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

### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event, actor-scoped; no new sexual.yaml row is added
`shame_hem_lift`, `shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`,
`shame_full_expose`, `shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`,
and `shame_shameless_declaration` SHALL each declare `"self_exposure"` in `sexual_events`, emitted
through the actor-scoped channel (`sexual_event_actor:self_exposure`) so the event lands on the
performing actor. `shame_provocative_gaze` SHALL declare `sexual_events=()`. Every act except
`shame_provocative_gaze` SHALL also declare `"public_exposure"` in `sexual_events`.
`world/rules/rulebook/sexual.yaml` SHALL gain no rule row from this change.

#### Scenario: Casting a Tier 1 act raises the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_half_expose_chest` on
  itself
- **THEN** `entity.sexual.exposure`'s ordinal increases by exactly `1`

#### Scenario: shame_provocative_gaze does not raise the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_provocative_gaze`
- **THEN** the actor's `exposure` ordinal is unchanged afterward

#### Scenario: An AREA shame act's self_exposure lands on the performing actor, not the audience
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_public_performance`
  targeting one other entity
- **THEN** the actor's `exposure` ordinal increases by exactly `1` and the target's `exposure`
  ordinal is unchanged afterward

#### Scenario: Casting a shame act grants the exposure experience type
- **WHEN** an entity casts `shame_half_expose_chest` on itself
- **THEN** the actor's `experience_types` contains `露出` afterward

### Requirement: shame_public_masturbation credits three counters and emits five events
`shame_public_masturbation` SHALL declare `actor_counters=("exposure_act_count",
"masturbation_count", "watched_count")` and `sexual_events=("self_exposure", "public_exposure",
"public_sexual_activity", "masturbation_climax", "watched_during_activity")`. The `watched_count`
counter and the `watched_during_activity` event SHALL be observer-gated (see
`sexual-act-effects`).

#### Scenario: Casting shame_public_masturbation in view of an observer increments all three counters by exactly one
- **WHEN** an entity at `exposure_act_count=20, masturbation_count=25, watched_count=0` casts
  `shame_public_masturbation` on itself while a co-located entity is present
- **THEN** afterward `exposure_act_count=21`, `masturbation_count=26`, and `watched_count=1`, and
  the actor's `experience_types` contain `露出`, `自慰`, and `被觀看`

#### Scenario: Casting shame_public_masturbation alone skips only the watched credit
- **WHEN** the same entity casts `shame_public_masturbation` in an empty room
- **THEN** afterward `exposure_act_count=21` and `masturbation_count=26`, `watched_count` remains
  `0`, and the actor's `experience_types` do not contain `被觀看`

### Requirement: shame_public_performance credits both watched_count and exposure_act_count on the actor and emits the four public events
`shame_public_performance` SHALL declare `actor_counters=("watched_count", "exposure_act_count")`,
`participant_counters=()`, and `sexual_events=("self_exposure", "public_exposure",
"public_sexual_activity", "watched_during_activity")`.

#### Scenario: Casting shame_public_performance increments both actor counters by exactly one
- **WHEN** an entity at `watched_count=10, exposure_act_count=20` casts `shame_public_performance`
  targeting one hostile entity, both starting at those exact values
- **THEN** afterward the actor's `watched_count` equals `11` and `exposure_act_count` equals `21`,
  and the target's counters are unchanged

#### Scenario: Casting shame_public_performance grants all four public experiences to the performer
- **WHEN** the same entity casts `shame_public_performance` targeting one hostile entity
- **THEN** the actor's `experience_types` contain `露出` and `被觀看`, and the actor's `shame`
  increases through `shame_up_on_public_sexual_activity`; the target gains no experience type from
  these events

### Requirement: The four public acts declare the public-event vocabulary
`shame_public_masturbation`, `shame_public_performance`, and `shame_shameless_declaration` SHALL
each declare `"public_sexual_activity"` in `sexual_events`; `shame_devoted_pose` SHALL NOT.
`shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`, and
`shame_shameless_declaration` SHALL declare `"watched_during_activity"` in `sexual_events`
(always observed for an AREA cast; observer-gated for a SELF cast). `shame_provocative_gaze`
SHALL keep `sexual_events=()`.

#### Scenario: 無恥宣言's public-event set includes the sexual-activity event
- **WHEN** `shame_shameless_declaration`'s `sexual_events` is read
- **THEN** it contains `"public_sexual_activity"` and `"watched_during_activity"`

#### Scenario: 獻身姿態 is a public exposure act, not a public sexual act
- **WHEN** `shame_devoted_pose`'s `sexual_events` is read
- **THEN** it contains `"public_exposure"` and `"watched_during_activity"` and does not contain
  `"public_sexual_activity"`

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
