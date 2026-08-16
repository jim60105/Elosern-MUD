# sexual-catalog-solo Specification

## Purpose

Register the eleven counter-gated 獨處線 acts across three tiers, filling the solo line from its
three seed acts to fourteen. Tier 1 opens at `masturbation_count >= 10`, Tier 2's toy acts at
`masturbation_count >= 25`, and Tier 3's advanced-toy acts at the compound
`masturbation_count >= 25` + `toy_use_count >= 15` gate. The three source-document pleasure-reduction
acts (快感控制, 寸止, 極限忍耐) are deferred pending an engine capability this change does not build.

## Requirements

<!-- Three source-document 獨處線 acts (快感控制, 寸止, 極限忍耐) and one flavour detail
     (拘束自慰's self-defense penalty) are intentionally NOT covered by this capability — see
     design.md D-2/D-3/D-4 for why each is deferred pending an engine capability this proposal does
     not build. -->

### Requirement: Eleven Tier 1-3 solo acts are registered, gated by masturbation_count and/or toy_use_count thresholds
`world/skills/sexual_acts/solo.py`'s `SOLO_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s three seed rows: five acts each declaring `unlock={"masturbation_count": 10}`
(`solo_deep_touch`, `solo_both_hands`, `solo_finger_lick`, `solo_rear_touch`, `solo_nipple_play`);
three acts each declaring `unlock={"masturbation_count": 25}` (`solo_toy_vibrator`,
`solo_toy_clamps`, `solo_toy_plug`); and three acts each declaring the compound gate
`unlock={"masturbation_count": 25, "toy_use_count": 15}` (`solo_toy_advanced_link`,
`solo_toy_advanced_full`, `solo_bound_masturbation`). Every one of these eleven acts SHALL declare
`target_spec=TargetSpec.SELF`, `target_part=None`, `participant_counters=()`, and
`resistible=False`.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `masturbation_count == 9`
- **THEN** `solo_deep_touch` is absent from the returned set
- **WHEN** the same entity's `masturbation_count` becomes `10`
- **THEN** `solo_deep_touch` is present in the returned set

#### Scenario: A Tier 2 act requires masturbation_count, not toy_use_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `masturbation_count == 25` and
  `toy_use_count == 0`
- **THEN** `solo_toy_vibrator` is present in the returned set

#### Scenario: A Tier 3 act requires both masturbation_count and toy_use_count, not toy_use_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `toy_use_count == 15` and
  `masturbation_count == 24`
- **THEN** `solo_toy_advanced_link` is absent from the returned set
- **WHEN** the same entity's `masturbation_count` becomes `25`
- **THEN** `solo_toy_advanced_link` is present in the returned set

### Requirement: Tier 2 and Tier 3 acts credit both masturbation_count and toy_use_count on cast
Each of `solo_toy_vibrator`, `solo_toy_clamps`, `solo_toy_plug`, `solo_toy_advanced_link`,
`solo_toy_advanced_full`, and `solo_bound_masturbation` SHALL declare
`actor_counters=("masturbation_count", "toy_use_count")`.

#### Scenario: Casting a toy act increments both counters by exactly one
- **WHEN** an entity whose `masturbation_count` is `25` and `toy_use_count` is `0` casts
  `solo_toy_vibrator` on itself
- **THEN** afterward `entity.sexual.masturbation_count` equals `26` and
  `entity.sexual.toy_use_count` equals `1`

### Requirement: Only the two deepest Tier 1 acts add the masturbation experience type
`solo_deep_touch` and `solo_both_hands` SHALL each declare `sexual_events=("masturbation_climax",)`.
Every other act added by this change SHALL declare `sexual_events=()`.

#### Scenario: solo_deep_touch adds the masturbation experience type
- **WHEN** an entity with an empty `experience_types` set casts `solo_deep_touch` on itself
- **THEN** `"自慰"` is present in `entity.sexual.experience_types` afterward

#### Scenario: A Tier 1 act outside the deepest two adds no experience type
- **WHEN** an entity with an empty `experience_types` set casts `solo_finger_lick` on itself
- **THEN** `entity.sexual.experience_types` remains empty afterward
