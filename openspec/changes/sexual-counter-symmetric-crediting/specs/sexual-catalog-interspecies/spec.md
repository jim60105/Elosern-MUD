# sexual-catalog-interspecies delta

## MODIFIED Requirements

### Requirement: Seven Tier 1-4 interspecies acts are registered, gated by hostile_act_count and/or climax_count and/or interspecies_act_count thresholds
`world/skills/sexual_acts/interspecies.py`'s `INTERSPECIES_ACTS` tuple SHALL contain: two acts each
declaring `unlock={"hostile_act_count": 10}` (`interspecies_touch`, `interspecies_caress`); two acts
each declaring `unlock={"hostile_act_count": 30}` (`interspecies_entangle`,
`interspecies_receive`); one act declaring the compound gate `unlock={"hostile_act_count": 30,
"climax_count": 20}` (`interspecies_mating`); and two acts each declaring
`unlock={"interspecies_act_count": 20}` (`interspecies_domination`, `interspecies_resonance`). Every
one of these seven acts SHALL declare `target_spec=TargetSpec.SINGLE`, `target_part=None`,
`resistible=True`, `actor_counters=("interspecies_act_count",)`, and
`participant_counters=("interspecies_act_count",)`. An interspecies act
happens between two bodies of different species, and `interspecies_act_count`
records the experience from either side.
The line's species gate stays exactly as shipped: the acts are authored
against Monster targets, and target validation is NOT changed by this
delta. Mirroring applies whenever the act resolves; a same-species cast
(a target that is not a `Monster`) keeps the shipped actor-credit behavior
and credits the participant only if the shipped handler's own rules already
do — this delta adds no species condition to the counter handler.

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
