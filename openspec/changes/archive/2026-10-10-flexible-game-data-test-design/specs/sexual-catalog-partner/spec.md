# Spec Delta

## MODIFIED Requirements

### Requirement: Sixteen Tier 1-4 partner acts are registered, gated by duo_act_count and/or group_act_count and/or climax_count thresholds
`world/skills/sexual_acts/partner.py`'s `PARTNER_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s two seed rows, sixteen counter-gated acts across four tiers, each declaring
the unlock gate enumerated for its tier group in the scenarios below. Every one of these sixteen
acts SHALL declare `resistible=True`.

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

#### Scenario: The four Tier 1 acts declare the duo_act_count 5 gate
- **WHEN** the unlock gates of `partner_kiss`, `partner_neck_caress`, `partner_breast_play`, and
  `partner_ear_whisper` are read
- **THEN** each declares the same counter-key topology as synthetic `unlock={"duo_act_count": <declared positive threshold>}`

#### Scenario: The five Tier 2 acts declare the duo_act_count 15 gate
- **WHEN** the unlock gates of `partner_deep_caress`, `partner_oral_service`, `partner_breast_sex`,
  `partner_thigh_rub`, and `partner_foot_service` are read
- **THEN** each declares the same counter-key topology as synthetic `unlock={"duo_act_count": <declared positive threshold>}`

#### Scenario: The four Tier 3 acts declare the compound duo and climax gate
- **WHEN** the unlock gates of `partner_anal_sex`, `partner_mutual_masturbation`,
  `partner_vaginal_sex`, and `partner_deep_vaginal_sex` are read
- **THEN** each declares the compound counter-key topology as synthetic `unlock={"duo_act_count": <declared positive threshold>, "climax_count": <declared positive threshold>}`

#### Scenario: The three Tier 4 acts declare their group-tier gates
- **WHEN** the unlock gates of the three Tier 4 AREA acts are read
- **THEN** `partner_group_caress` declares the same counter-key topology as synthetic `unlock={"duo_act_count": <declared positive threshold>}`, `partner_group_orgy`
  declares the same counter-key topology as synthetic `unlock={"group_act_count": <declared positive threshold>}`, and `partner_group_service` declares
  `unlock={"group_act_count": <declared positive threshold>}`

#### Scenario: Declared thresholds are mutable and boundary examples are synthetic
- **WHEN** exact numerical boundary cases above are exercised
- **THEN** local fixed synthetic declarations use those boundary values; shipped acts retain the stated counter-key topology, membership and resistance policy with authored positive thresholds, and tests do not pin their literal unlock counts


### Requirement: The four Tier 3 acts trade off at baseline sensitivity
The four existing Tier 3 acts SHALL retain the established baseline trade-offs while base pleasure and actor-side ratios remain authored data. At equal ordinary sensitivity, no shame and two participants, anal intercourse SHALL give the target more pleasure than mutual masturbation while mutual masturbation gives the actor more. Deep vaginal intercourse SHALL exceed ordinary vaginal intercourse for both participants and retain the larger actor-side gap.

#### Scenario: partner_anal_sex grants the target strictly more than partner_mutual_masturbation does at baseline
- **WHEN** the four acts resolve in separately reset controlled participant states
- **THEN** observed actor and target pleasure deltas satisfy those relationships without numerical gain pins or expected values derived from the same production calculation
#### Scenario: partner_mutual_masturbation grants the actor strictly more than partner_anal_sex does at baseline
- **WHEN** separately reset ordinary-sensitivity/no-shame participants execute both acts with equal two-participant and resistance-control conditions
- **THEN** observed actor pleasure gain is greater for mutual masturbation

#### Scenario: 深度交合 escalates the stakes over 交合 on both sides
- **WHEN** separately reset baseline participants execute ordinary and deep intercourse
- **THEN** deep target gain exceeds ordinary target gain and the actor-side gap exceeds the target-side gap

#### Scenario: Baseline trade-offs do not claim per-character dominance
- **WHEN** the baseline comparison is interpreted
- **THEN** it is not universal dominance: per-body-part sensitivity can diverge with play history
