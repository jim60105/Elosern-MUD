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
`world/skills/sexual_acts/shame.py`'s `SHAME_ACTS` tuple SHALL contain, in addition to `sexual-act-seeds`'s one seed row, nine acts gated by `exposure_act_count` and/or `watched_count` thresholds declared as per-act `unlock` mappings (enumerated in the scenarios below). Every one of these nine acts SHALL declare `actor_part=None`.

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

#### Scenario: Tier 1 unlock declarations
- **WHEN** the Tier 1 shame act definitions are read
- **THEN** `shame_half_expose_chest`, `shame_half_expose_lower`, and `shame_loosen_collar` each declare `unlock={"exposure_act_count": <declared positive threshold>}`

#### Scenario: Tier 2 unlock declarations
- **WHEN** the Tier 2 shame act definitions are read
- **THEN** `shame_full_expose` declares the same counter-key topology as synthetic `unlock={"exposure_act_count": <declared positive threshold>}` and `shame_public_masturbation` declares the same counter-key topology as synthetic `unlock={"exposure_act_count": <declared positive threshold>, "masturbation_count": <declared positive threshold>}`

#### Scenario: Tier 3 unlock declarations
- **WHEN** the Tier 3 shame act definitions are read
- **THEN** `shame_provocative_gaze` declares the same counter-key topology as synthetic `unlock={"watched_count": <declared positive threshold>}` and `shame_public_performance` declares the same counter-key topology as synthetic `unlock={"watched_count": <declared positive threshold>, "exposure_act_count": <declared positive threshold>}`

#### Scenario: Tier 4 unlock declarations
- **WHEN** the Tier 4 shame act definitions are read
- **THEN** `shame_devoted_pose` declares the same counter-key topology as synthetic `unlock={"exposure_act_count": <declared positive threshold>}` and `shame_shameless_declaration` declares the same counter-key topology as synthetic `unlock={"exposure_act_count": <declared positive threshold>, "watched_count": <declared positive threshold>}`

#### Scenario: Declared thresholds are mutable and boundary examples are synthetic
- **WHEN** exact numerical boundary cases above are exercised
- **THEN** local fixed synthetic declarations use those boundary values; shipped acts retain the stated counter-key topology, membership and resistance policy with authored positive thresholds, and tests do not pin their literal unlock counts

### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event, actor-scoped; no new sexual.yaml row is added
Every shame act except `shame_provocative_gaze` SHALL declare both `"self_exposure"` and `"public_exposure"` in `sexual_events`, with `self_exposure` emitted through the actor-scoped channel (`sexual_event_actor:self_exposure`) so the event lands on the performing actor. `shame_provocative_gaze` SHALL declare `sexual_events=()`. `world/rules/rulebook/sexual.yaml` SHALL gain no rule row from this change.

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

#### Scenario: The declaring acts are enumerated
- **WHEN** the acts declaring `"self_exposure"` are listed
- **THEN** they are `shame_hem_lift`, `shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`, `shame_full_expose`, `shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`, and `shame_shameless_declaration`

### Requirement: shame_public_masturbation credits three counters and emits five events
shame_public_masturbation SHALL retain actor counters exposure_act_count, masturbation_count and watched_count and events self_exposure, public_exposure, public_sexual_activity, masturbation_climax and watched_during_activity. Watched counter/event SHALL remain observer-gated. Actors SHALL satisfy current declared eligibility before execution.

#### Scenario: Casting shame_public_masturbation in view of an observer increments all three counters by exactly one
- **WHEN** an eligible actor casts on itself with a co-located observer and pre-cast counters snapshotted
- **THEN** all three counters rise by 1 and the actor gains 露出, 自慰 and 被觀看 experiences

#### Scenario: Casting shame_public_masturbation alone skips only the watched credit
- **WHEN** an eligible actor casts alone in an empty room
- **THEN** exposure and masturbation counters each rise by 1, watched_count stays unchanged and 被觀看 experience is not granted

### Requirement: shame_public_performance credits both watched_count and exposure_act_count on the actor and emits the four public events
shame_public_performance SHALL retain actor counters watched_count/exposure_act_count, no participant counters and the self_exposure, public_exposure, public_sexual_activity and watched_during_activity events. Actors SHALL satisfy current declared eligibility instead of historical numerical unlock counts.

#### Scenario: Casting shame_public_performance increments both actor counters by exactly one
- **WHEN** an eligible actor casts on a hostile target with both entities' counters snapshotted
- **THEN** only the actor's watched/exposure counters rise by 1 and target counters stay unchanged

#### Scenario: Casting shame_public_performance grants all four public experiences to the performer
- **WHEN** the same eligible cast emits its public events
- **THEN** the actor gains 露出 and 被觀看 and shame rises via shame_up_on_public_sexual_activity; the target gains no experience from those events

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

### Requirement: shame_provocative_gaze credits hostile_act_count on both participants
shame_provocative_gaze SHALL retain hostile_act_count in both actor and participant counter declarations. Its actor SHALL satisfy current declared watched-count eligibility. Direction-bound exposure/watched counter credit SHALL remain actor-only for the four public-exposure acts.

#### Scenario: Casting shame_provocative_gaze credits both participants
- **WHEN** an eligible actor casts on a target with both hostile counters snapshotted
- **THEN** each hostile_act_count rises by exactly 1

#### Scenario: Public-exposure acts still credit direction-bound counters on the actor only
- **WHEN** an eligible actor casts shame_public_performance on a hostile target
- **THEN** actor watched/exposure counters each rise by 1 while both target counters stay unchanged

#### Scenario: Why both participants are credited
- **WHEN** shame_provocative_gaze provokes its target
- **THEN** hostile_act_count records hostile-act participation from either side of two bodies

#### Scenario: Direction-bound shame counters stay asymmetric
- **WHEN** any of the four public-exposure acts is declared
- **THEN** participant_counters stays empty because an audience member underwent neither its own exposure nor its own watched experience

### Requirement: The three AREA acts declare target_part as a BODY_PARTS member, never None
`shame_provocative_gaze`, `shame_public_performance`, and `shame_devoted_pose` SHALL each declare
`target_part="腰腹"`.

#### Scenario: An AREA shame act's target_part is a real body part
- **WHEN** each of the three AREA acts is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `target_part` equals `"腰腹"`, a member of `world.lore.sexual_vocab.BODY_PARTS`
