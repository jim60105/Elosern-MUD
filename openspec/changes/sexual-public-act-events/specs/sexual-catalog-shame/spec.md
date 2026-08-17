# sexual-catalog-shame Delta Specification

## RENAMED Requirements

- FROM: `### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event; no new sexual.yaml row is added`
- TO: `### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event, actor-scoped; no new sexual.yaml row is added`
- FROM: `### Requirement: shame_public_masturbation credits three counters and emits two events`
- TO: `### Requirement: shame_public_masturbation credits three counters and emits five events`
- FROM: `### Requirement: shame_public_performance credits both watched_count and exposure_act_count on the actor`
- TO: `### Requirement: shame_public_performance credits both watched_count and exposure_act_count on the actor and emits the four public events`

## MODIFIED Requirements

### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event, actor-scoped; no new sexual.yaml row is added
`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`, `shame_full_expose`,
`shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`, and
`shame_shameless_declaration` SHALL each declare `"self_exposure"` in `sexual_events`, emitted
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

## ADDED Requirements

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
