# Spec Delta

## MODIFIED Requirements

### Requirement: Nine Tier 1-4 shame acts are registered, gated by exposure_act_count and/or watched_count thresholds
`world/skills/sexual_acts/shame.py`'s `SHAME_ACTS` tuple SHALL contain, in addition to `sexual-act-seeds`'s one seed row, nine acts gated by `exposure_act_count` and/or `watched_count` thresholds declared as per-act `unlock` mappings (enumerated in the scenarios below). Every one of these nine acts SHALL declare `actor_part=None`.

Numerical boundary examples below SHALL use scoped synthetic declarations. Shipped acts retain the named roster, counter-key topology and intent, but their positive thresholds SHALL be author-adjustable.

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

