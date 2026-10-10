# Spec Delta

## MODIFIED Requirements

### Requirement: Eleven Tier 1-3 solo acts are registered, gated by masturbation_count and/or toy_use_count thresholds
`world/skills/sexual_acts/solo.py`'s `SOLO_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s three seed rows, the eleven tier-gated acts named in the scenarios below.
Every one of these eleven acts SHALL declare
`target_spec=TargetSpec.SELF`, `target_part=None`, `participant_counters=()`, and
`resistible=False`.

Numerical boundary examples below SHALL use scoped synthetic declarations. Shipped acts retain the named roster, counter-key topology and intent, but their positive thresholds SHALL be author-adjustable.

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

#### Scenario: The five Tier 1 acts share the masturbation_count 10 gate
- **WHEN** the Tier 1 acts `solo_deep_touch`, `solo_both_hands`, `solo_finger_lick`, `solo_rear_touch`, and `solo_nipple_play` are read from `SOLO_ACTS`
- **THEN** each declares the same counter-key topology as synthetic `unlock={"masturbation_count": <declared positive threshold>}`

#### Scenario: The three Tier 2 toy acts share the masturbation_count 25 gate
- **WHEN** the Tier 2 acts `solo_toy_vibrator`, `solo_toy_clamps`, and `solo_toy_plug` are read from `SOLO_ACTS`
- **THEN** each declares the same counter-key topology as synthetic `unlock={"masturbation_count": <declared positive threshold>}`

#### Scenario: The three Tier 3 advanced-toy acts share the compound gate
- **WHEN** the Tier 3 acts `solo_toy_advanced_link`, `solo_toy_advanced_full`, and `solo_bound_masturbation` are read from `SOLO_ACTS`
- **THEN** each declares the compound counter-key topology as synthetic `unlock={"masturbation_count": <declared positive threshold>, "toy_use_count": <declared positive threshold>}`

#### Scenario: Declared thresholds are mutable and boundary examples are synthetic
- **WHEN** exact numerical boundary cases above are exercised
- **THEN** local fixed synthetic declarations use those boundary values; shipped acts retain the stated counter-key topology, membership and resistance policy with authored positive thresholds, and tests do not pin their literal unlock counts

### Requirement: Tier 2 and Tier 3 acts credit both masturbation_count and toy_use_count on cast
Each of solo_toy_vibrator, solo_toy_clamps, solo_toy_plug, solo_toy_advanced_link, solo_toy_advanced_full and solo_bound_masturbation SHALL retain actor counters masturbation_count and toy_use_count. Real integration actors SHALL satisfy current declared eligibility, not historical unlock counts.

#### Scenario: Casting a toy act increments both counters by exactly one
- **WHEN** an eligible actor casts solo_toy_vibrator on itself and both counters are snapshotted before the cast
- **THEN** masturbation_count and toy_use_count each increase by exactly 1, regardless of valid authored threshold changes

