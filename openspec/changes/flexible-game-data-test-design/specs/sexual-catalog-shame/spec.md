# Spec Delta

## MODIFIED Requirements

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

