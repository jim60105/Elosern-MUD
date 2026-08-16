## ADDED Requirements

<!-- 交合 and 深度交合 (vaginal intercourse, the sole source-catalog acts that break `virgin`) are
     intentionally NOT covered by this capability — see design.md D-2: no mechanism exists to select
     a sexual_events entry from the participants' sex field at cast time. -->

### Requirement: Fourteen Tier 1-4 partner acts are registered, gated by duo_act_count and/or group_act_count and/or climax_count thresholds
`world/skills/sexual_acts/partner.py`'s `PARTNER_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s two seed rows: four acts each declaring `unlock={"duo_act_count": 5}`
(`partner_kiss`, `partner_neck_caress`, `partner_breast_play`, `partner_ear_whisper`); five acts each
declaring `unlock={"duo_act_count": 15}` (`partner_deep_caress`, `partner_oral_service`,
`partner_breast_sex`, `partner_thigh_rub`, `partner_foot_service`); two acts each declaring the
compound gate `unlock={"duo_act_count": 30, "climax_count": 10}` (`partner_anal_sex`,
`partner_mutual_masturbation`); one act declaring `unlock={"duo_act_count": 30}`
(`partner_group_caress`); one act declaring `unlock={"group_act_count": 15}`
(`partner_group_orgy`); and one act declaring `unlock={"group_act_count": 30}`
(`partner_group_service`). Every one of these fourteen acts SHALL declare `resistible=True`.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `duo_act_count == 4`
- **THEN** `partner_kiss` is absent from the returned set
- **WHEN** the same entity's `duo_act_count` becomes `5`
- **THEN** `partner_kiss` is present in the returned set

#### Scenario: A Tier 3 act requires both duo_act_count and climax_count, not duo_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `duo_act_count == 30` and
  `climax_count == 9`
- **THEN** `partner_anal_sex` is absent from the returned set
- **WHEN** the same entity's `climax_count` becomes `10`
- **THEN** `partner_anal_sex` is present in the returned set

#### Scenario: partner_group_orgy is gated by group_act_count, not duo_act_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `group_act_count == 15` and
  `duo_act_count == 0`
- **THEN** `partner_group_orgy` is present in the returned set

### Requirement: Every Tier 1-3 act credits duo_act_count on both the actor and the target; every Tier 4 act credits group_act_count on both
Each of `partner_kiss`, `partner_neck_caress`, `partner_breast_play`, `partner_ear_whisper`,
`partner_deep_caress`, `partner_oral_service`, `partner_breast_sex`, `partner_thigh_rub`,
`partner_foot_service`, `partner_anal_sex`, and `partner_mutual_masturbation` SHALL declare
`actor_counters=("duo_act_count",)` and `participant_counters=("duo_act_count",)`. Each of
`partner_group_caress`, `partner_group_orgy`, and `partner_group_service` SHALL declare
`actor_counters=("group_act_count",)` and `participant_counters=("group_act_count",)`.

#### Scenario: Casting a Tier 1 act increments duo_act_count on both participants
- **WHEN** entity A casts `partner_kiss` targeting entity B, both starting at `duo_act_count == 0`
- **THEN** afterward both `A.sexual.duo_act_count` and `B.sexual.duo_act_count` equal `1`

#### Scenario: Casting a Tier 4 act increments group_act_count, not duo_act_count, on every participant
- **WHEN** entity A casts `partner_group_caress` targeting entities B and C, all three starting at
  `group_act_count == 0` and `duo_act_count == 0`
- **THEN** afterward `A.sexual.group_act_count`, `B.sexual.group_act_count`, and
  `C.sexual.group_act_count` each equal `1`, and all three entities' `duo_act_count` remains `0`

### Requirement: partner_breast_sex is the sole emitter of breast_sex_performed
`partner_breast_sex` SHALL declare `sexual_events=("breast_sex_performed",)`. Every other act added
by this change SHALL declare `sexual_events=()`.

#### Scenario: Casting partner_breast_sex emits breast_sex_performed
- **WHEN** entity A casts `partner_breast_sex` targeting entity B
- **THEN** `apply_event` is invoked with event name `"breast_sex_performed"` for the resolved
  recipient, and no other act added by this change ever names that event

### Requirement: partner_anal_sex and partner_mutual_masturbation are the two Tier 3 acts, trading off at baseline sensitivity
`partner_anal_sex` SHALL declare `base_pleasure=26` and `actor_pleasure_ratio=0.6`.
`partner_mutual_masturbation` SHALL declare `base_pleasure=18` and `actor_pleasure_ratio=1.0`. This
baseline trade-off is not a claim that either act dominates the other for every character: per
design.md D-4, `sensitivity_mult` is a per-body-part trait (後庭 vs 私處) that can diverge with play
history and is not pinned by this requirement.

#### Scenario: partner_anal_sex grants the target strictly more than partner_mutual_masturbation does at baseline
- **WHEN** `compute_pleasure_gain` is evaluated for a target entity at baseline (`普通` sensitivity,
  `無` shame) for both acts, with `participant_count == 2` for both (the only value either
  `TargetSpec.SINGLE` act can reach)
- **THEN** `partner_anal_sex`'s target-side gain exceeds `partner_mutual_masturbation`'s target-side
  gain

#### Scenario: partner_mutual_masturbation grants the actor strictly more than partner_anal_sex does at baseline
- **WHEN** `compute_pleasure_gain` is evaluated for the actor at baseline (`普通` sensitivity, `無`
  shame) for both acts, with `participant_count == 2` for both
- **THEN** `partner_mutual_masturbation`'s actor-side gain exceeds `partner_anal_sex`'s actor-side gain

### Requirement: All fourteen acts declare resistible=True
Every one of the fourteen acts this change adds SHALL declare `resistible=True`.

#### Scenario: Every new act is resistible
- **WHEN** each of the fourteen acts this change adds is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `resistible` field is `True`

### Requirement: None of this change's fourteen keys collide with any previously-registered act key
Every `key` this change adds to `PARTNER_ACTS` SHALL be distinct from every key already present in
`SEXUAL_ACT_REGISTRY` before this change (the two `PARTNER_ACTS` seeds plus every `sexual-act-seeds`,
`sexual-catalog-solo`, and `sexual-catalog-shame` key).

#### Scenario: No key collision with the pre-existing registry
- **WHEN** `SEXUAL_ACT_REGISTRY`'s key set before this change is compared against this change's
  fourteen new keys
- **THEN** the two sets are disjoint

### Requirement: The three Tier 4 acts declare target_part as a BODY_PARTS member, never None
`partner_group_caress`, `partner_group_orgy`, and `partner_group_service` SHALL each declare
`target_part="腰腹"` and `target_spec=TargetSpec.AREA`.

#### Scenario: A Tier 4 act's target_part is a real body part
- **WHEN** each of the three Tier 4 acts is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `target_part` equals `"腰腹"`, a member of `world.lore.sexual_vocab.BODY_PARTS`,
  and each one's `SkillDef.target_spec` equals `TargetSpec.AREA`
