# sexual-catalog-partner Specification

## Purpose

Register the sixteen counter-gated 關係線 acts across four tiers, filling the partner line from
its two seed acts to eighteen. Tier 1 opens at `duo_act_count >= 5`, Tier 2 at
`duo_act_count >= 15`, Tier 3 at the compound `duo_act_count >= 30` + `climax_count >= 10` gate, and
Tier 4's AREA acts at `duo_act_count >= 30` / `group_act_count >= 15` / `group_act_count >= 30`.
交合 and 深度交合 (vaginal intercourse) implement the D-12 opposite-sex `virgin`-breaking branch
through their `pair_events` tables, selected from the participants' `sex` fields at cast time.

## Requirements

### Requirement: Sixteen Tier 1-4 partner acts are registered, gated by duo_act_count and/or group_act_count and/or climax_count thresholds
`world/skills/sexual_acts/partner.py`'s `PARTNER_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s two seed rows: four acts each declaring `unlock={"duo_act_count": 5}`
(`partner_kiss`, `partner_neck_caress`, `partner_breast_play`, `partner_ear_whisper`); five acts each
declaring `unlock={"duo_act_count": 15}` (`partner_deep_caress`, `partner_oral_service`,
`partner_breast_sex`, `partner_thigh_rub`, `partner_foot_service`); four acts each declaring the
compound gate `unlock={"duo_act_count": 30, "climax_count": 10}` (`partner_anal_sex`,
`partner_mutual_masturbation`, `partner_vaginal_sex`, `partner_deep_vaginal_sex`); one act declaring
`unlock={"duo_act_count": 30}` (`partner_group_caress`); one act declaring
`unlock={"group_act_count": 15}` (`partner_group_orgy`); and one act declaring
`unlock={"group_act_count": 30}` (`partner_group_service`). Every one of these sixteen acts SHALL
declare `resistible=True`.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `duo_act_count == 4`
- **THEN** `partner_kiss` is absent from the returned set
- **WHEN** the same entity's `duo_act_count` becomes `5`
- **THEN** `partner_kiss` is present in the returned set

#### Scenario: A Tier 3 act requires both duo_act_count and climax_count, not duo_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `duo_act_count == 30` and
  `climax_count == 9`
- **THEN** `partner_anal_sex` and `partner_vaginal_sex` are absent from the returned set
- **WHEN** the same entity's `climax_count` becomes `10`
- **THEN** `partner_anal_sex` and `partner_vaginal_sex` are present in the returned set

#### Scenario: partner_group_orgy is gated by group_act_count, not duo_act_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `group_act_count == 15` and
  `duo_act_count == 0`
- **THEN** `partner_group_orgy` is present in the returned set

### Requirement: Every Tier 1-3 act credits duo_act_count on both the actor and the target; every Tier 4 act credits group_act_count on both
Each of `partner_kiss`, `partner_neck_caress`, `partner_breast_play`, `partner_ear_whisper`,
`partner_deep_caress`, `partner_oral_service`, `partner_breast_sex`, `partner_thigh_rub`,
`partner_foot_service`, `partner_anal_sex`, `partner_mutual_masturbation`, `partner_vaginal_sex`,
and `partner_deep_vaginal_sex` SHALL declare
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

#### Scenario: Casting 交合 increments duo_act_count on both participants
- **WHEN** entity A casts `partner_vaginal_sex` targeting entity B, both starting at
  `duo_act_count == 0`
- **THEN** afterward both `A.sexual.duo_act_count` and `B.sexual.duo_act_count` equal `1`

### Requirement: partner_breast_sex is the sole emitter of breast_sex_performed
`partner_breast_sex` SHALL declare `sexual_events=("breast_sex_performed",)`. Every other act added
by this change SHALL declare `sexual_events=()`, with the two intercourse acts declaring
`pair_events` instead (see the sex-dependent-event requirement).

#### Scenario: Casting partner_breast_sex emits breast_sex_performed
- **WHEN** entity A casts `partner_breast_sex` targeting entity B
- **THEN** `apply_event` is invoked with event name `"breast_sex_performed"` for the resolved
  recipient, and no other act added by this change ever names that event

### Requirement: The four Tier 3 acts trade off at baseline sensitivity
`partner_anal_sex` SHALL declare `base_pleasure=26` and `actor_pleasure_ratio=0.6`.
`partner_mutual_masturbation` SHALL declare `base_pleasure=18` and `actor_pleasure_ratio=1.0`.
`partner_vaginal_sex` SHALL declare `base_pleasure=28` and `actor_pleasure_ratio=0.6`.
`partner_deep_vaginal_sex` SHALL declare `base_pleasure=34` and `actor_pleasure_ratio=0.9`.
These baseline trade-offs are not a claim that any act dominates another for every character: per
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

#### Scenario: 深度交合 escalates the stakes over 交合 on both sides
- **WHEN** `compute_pleasure_gain` is evaluated at baseline for the actor and a target for both
  intercourse acts, with `participant_count == 2`
- **THEN** `partner_deep_vaginal_sex`'s target-side gain exceeds `partner_vaginal_sex`'s, and the
  actor-side gain gap between the two acts is strictly larger than the target-side gain gap (the
  deeper act costs the actor disproportionately more)

### Requirement: All sixteen acts declare resistible=True
Every one of the sixteen acts this change adds SHALL declare `resistible=True`.

#### Scenario: Every new act is resistible
- **WHEN** each of the sixteen acts this change adds is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `resistible` field is `True`

### Requirement: None of this change's sixteen keys collide with any previously-registered act key
Every `key` this change adds to `PARTNER_ACTS` SHALL be distinct from every key already present in
`SEXUAL_ACT_REGISTRY` before this change (the two `PARTNER_ACTS` seeds plus every `sexual-act-seeds`,
`sexual-catalog-solo`, `sexual-catalog-shame`, and `sexual-catalog-partner` key).

#### Scenario: No key collision with the pre-existing registry
- **WHEN** `SEXUAL_ACT_REGISTRY`'s key set before this change is compared against this change's
  sixteen new keys
- **THEN** the two sets are disjoint

### Requirement: The three Tier 4 acts declare target_part as a BODY_PARTS member, never None
`partner_group_caress`, `partner_group_orgy`, and `partner_group_service` SHALL each declare
`target_part="腰腹"` and `target_spec=TargetSpec.AREA`.

#### Scenario: A Tier 4 act's target_part is a real body part
- **WHEN** each of the three Tier 4 acts is read from `SEXUAL_ACT_REGISTRY`
- **THEN** each one's `target_part` equals `"腰腹"`, a member of `world.lore.sexual_vocab.BODY_PARTS`,
  and each one's `SkillDef.target_spec` equals `TargetSpec.AREA`

### Requirement: 交合 and 深度交合 emit exactly one sex-dependent penetration event per cast, breaking virgin symmetrically and only for opposite-sex parties
`partner_vaginal_sex` and `partner_deep_vaginal_sex` SHALL each declare the canonical
`pair_events` table: `(("female", "male"), "first_vaginal_penetration")`,
`(("female", "female"), "penetrative_sex_with_female")`, and
`(("male", "male"), "penetrative_sex_with_male")`. A cast whose participants are opposite-sex SHALL
emit `first_vaginal_penetration` for **both** participants, breaking each one's `virgin` flag
through the shipped one-way setter and adding the `陰道性交` experience type to both. A cast whose
participants are both female SHALL emit `penetrative_sex_with_female` (adding `女女性愛`, never
touching `virgin`); both male SHALL emit `penetrative_sex_with_male` (adding `男男性愛`, never
touching `virgin`). A cast in which either participant's sex is `"other"` or unknown — including
every `Monster` target, which defaults to `"other"` — SHALL emit no penetration event and SHALL
never break `virgin`.

#### Scenario: An opposite-sex cast breaks virgin on both parties
- **WHEN** entity A (`sex="female"`, `virgin=True`) casts `partner_vaginal_sex` targeting entity B
  (`sex="male"`, `virgin=True`)
- **THEN** afterward both `A.sexual.virgin` and `B.sexual.virgin` are `False`, and both entities'
  `experience_types` contain `陰道性交`

#### Scenario: A same-sex cast never breaks virgin and adds the matching experience type
- **WHEN** entity A (`sex="female"`) casts `partner_vaginal_sex` targeting entity B (`sex="female"`,
  `virgin=True`)
- **THEN** `B.sexual.virgin` remains `True`, and both entities' `experience_types` contain
  `女女性愛` and do not contain `陰道性交`

#### Scenario: A cast involving an other/unknown party emits no event
- **WHEN** entity A (`sex="male"`) casts `partner_vaginal_sex` targeting entity B (`sex="other"`,
  `virgin=True`)
- **THEN** neither participant's `virgin` changes and neither participant gains any penetration
  experience type

#### Scenario: A cast against a Monster never breaks virgin
- **WHEN** entity A (`sex="female"`) casts `partner_vaginal_sex` targeting a `Monster` (which reads
  `sex` as the default `"other"`)
- **THEN** `A.sexual.virgin` remains `True` and the monster's `virgin` remains `True`
