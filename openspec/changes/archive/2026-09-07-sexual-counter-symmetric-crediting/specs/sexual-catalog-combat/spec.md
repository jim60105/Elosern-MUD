# sexual-catalog-combat delta

## MODIFIED Requirements

### Requirement: Eight Tier 1/2/3/5 combat acts are registered, gated by hostile_act_count and/or climax_count and/or climax_extension_count thresholds
`world/skills/sexual_acts/combat.py`'s `COMBAT_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s one seed row: two acts each declaring `unlock={"hostile_act_count": 5}`
(`combat_tease_whisper`, `combat_tease_touch`); three acts each declaring
`unlock={"hostile_act_count": 20}` (`combat_charm`, `combat_bind_caress`,
`combat_forced_pleasure`); two acts each declaring the compound gate
`unlock={"hostile_act_count": 40, "climax_count": 30}` (`combat_forced_climax`,
`combat_relentless_torment`); and one act declaring the compound gate
`unlock={"hostile_act_count": 80, "climax_extension_count": 30}` (`combat_climax_domination`).
Every one of these eight acts SHALL declare `resistible=True`,
`actor_counters=("hostile_act_count",)`, and
`participant_counters=("hostile_act_count",)`. A hostile sexual act happens
between two bodies, and `hostile_act_count` records participation from
either side.

#### Scenario: A Tier 1 act is locked below its threshold and unlocked at it
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 4`
- **THEN** `combat_tease_whisper` is absent from the returned set
- **WHEN** the same entity's `hostile_act_count` becomes `5`
- **THEN** `combat_tease_whisper` is present in the returned set

#### Scenario: A Tier 3 act requires both hostile_act_count and climax_count, not hostile_act_count alone
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 40` and
  `climax_count == 29`
- **THEN** `combat_forced_climax` is absent from the returned set
- **WHEN** the same entity's `climax_count` becomes `30`
- **THEN** `combat_forced_climax` is present in the returned set

#### Scenario: combat_climax_domination requires both hostile_act_count and climax_extension_count
- **WHEN** `SkillHandler.owned_keys()` is read for an entity with `hostile_act_count == 80` and
  `climax_extension_count == 29`
- **THEN** `combat_climax_domination` is absent from the returned set
- **WHEN** the same entity's `climax_extension_count` becomes `30`
- **THEN** `combat_climax_domination` is present in the returned set

#### Scenario: Casting any of the eight acts credits hostile_act_count on every participant
- **WHEN** entity A at the Tier 1 unlock threshold (`hostile_act_count == 5`) casts
  `combat_tease_whisper` targeting hostile entity B at `hostile_act_count == 0`
- **THEN** afterward `A.sexual.hostile_act_count` equals `6` and `B.sexual.hostile_act_count`
  equals `1`
