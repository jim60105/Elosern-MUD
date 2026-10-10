# Spec Delta

## MODIFIED Requirements

### Requirement: Seven Tier 1-4 interspecies acts are registered, gated by hostile_act_count and/or climax_count and/or interspecies_act_count thresholds
`world/skills/sexual_acts/interspecies.py`'s `INTERSPECIES_ACTS` tuple SHALL contain the seven acts
`interspecies_touch`, `interspecies_caress`, `interspecies_entangle`, `interspecies_receive`,
`interspecies_mating`, `interspecies_domination`, and `interspecies_resonance`, each gated by the
unlock thresholds below.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 9`
- **THEN** `interspecies_touch` is absent from the returned set
- **WHEN** the same entity's `hostile_act_count` becomes `10`
- **THEN** `interspecies_touch` is present in the returned set

#### Scenario: interspecies_mating requires both hostile_act_count and climax_count, not hostile_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 30` and
  `climax_count == 19`
- **THEN** `interspecies_mating` is absent from the returned set
- **WHEN** the same entity's `climax_count` becomes `20`
- **THEN** `interspecies_mating` is present in the returned set

#### Scenario: A Tier 4 act is gated by interspecies_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `interspecies_act_count == 20` and
  `hostile_act_count == 0`
- **THEN** `interspecies_domination` is present in the returned set

#### Scenario: Casting any of the seven acts credits interspecies_act_count on every participant, including the Monster target
- **WHEN** entity A casts `interspecies_touch` targeting a `Monster` B, both starting at
  `interspecies_act_count == 0`
- **THEN** afterward `A.sexual.interspecies_act_count` equals `1` and `B.sexual.interspecies_act_count`
  equals `1`

#### Scenario: A same-species target keeps the shipped crediting behavior
- **WHEN** entity A casts `interspecies_touch` at a non-Monster target under the shipped target contract
- **THEN** crediting matches exactly the shipped pre-change behavior for that path (pin: the species gate is untouched)

#### Scenario: All seven acts share the line's fixed field set
- **WHEN** each of the seven acts' fields are inspected
- **THEN** every one SHALL declare `target_spec=TargetSpec.SINGLE`, `target_part=None`,
  `resistible=True`, `actor_counters=("interspecies_act_count",)`, and
  `participant_counters=("interspecies_act_count",)`

#### Scenario: The unlock mappings are tiered by counter thresholds
- **WHEN** the seven acts' `unlock` mappings are inspected
- **THEN** `interspecies_touch` and `interspecies_caress` each declare
  `unlock={"hostile_act_count": <declared positive threshold>}`; `interspecies_entangle` and `interspecies_receive` each
  declare `unlock={"hostile_act_count": <declared positive threshold>}`; `interspecies_mating` declares the compound gate
  `unlock={"hostile_act_count": <declared positive threshold>, "climax_count": <declared positive threshold>}`; and `interspecies_domination` and
  `interspecies_resonance` each declare `unlock={"interspecies_act_count": <declared positive threshold>}`

#### Scenario: The counter records participation from either side
- **WHEN** an interspecies act happens between two bodies of different species
- **THEN** `interspecies_act_count` records the experience from either side

#### Scenario: The species gate stays exactly as shipped
- **WHEN** this delta lands
- **THEN** the acts are authored against Monster targets, and target validation is NOT changed by
  this delta

#### Scenario: Mirroring and same-species crediting follow the shipped handler
- **WHEN** an act resolves, including a same-species cast (a target that is not a `Monster`)
- **THEN** mirroring applies whenever the act resolves; a same-species cast keeps the shipped
  actor-credit behavior and credits the participant only if the shipped handler's own rules already
  do ;  this delta adds no species condition to the counter handler

#### Scenario: Declared thresholds are mutable and boundary examples are synthetic
- **WHEN** exact numerical boundary cases above are exercised
- **THEN** local fixed synthetic declarations use those boundary values; shipped acts retain the stated counter-key topology, membership and resistance policy with authored positive thresholds, and tests do not pin their literal unlock counts


### Requirement: interspecies_receive declares the highest actor_pleasure_ratio among this change's seven acts
`interspecies_receive` SHALL retain the greatest actor-side ratio among the seven existing acts, with the exact ratio authored as adjustable data.

#### Scenario: interspecies_receive's ratio exceeds every sibling act's ratio
- **WHEN** shipped declarations are validated
- **THEN** the receive ratio exceeds each sibling's ratio without an expected literal ratio table

### Requirement: interspecies_mating grants the actor strictly more pleasure than interspecies_receive despite the lower ratio
`interspecies_mating` SHALL retain its established greater actor pleasure than `interspecies_receive` despite its smaller ratio, including the existing ordinary-sensitivity, strong-shame, two-participant control condition. Exact base pleasure and ratio magnitudes SHALL remain authored data.

#### Scenario: Worst-case actor-side gain still orders interspecies_mating above interspecies_receive
- **WHEN** both acts resolve from separately reset controlled participant states
- **THEN** observed actor pleasure increase is greater for mating, without pinning 13/12 gains or computing the expected result with the same production gain function
