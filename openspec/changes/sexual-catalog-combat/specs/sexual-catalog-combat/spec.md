## ADDED Requirements

<!-- 搾取 (Tier 4, an SP-transfer act) is intentionally NOT covered by this capability — see
     design.md D-2: no cross-entity resource-transfer effect exists in the current schema. -->

### Requirement: Eight Tier 1/2/3/5 combat acts are registered, gated by hostile_act_count and/or climax_count and/or climax_extension_count thresholds
`world/skills/sexual_acts/combat.py`'s `COMBAT_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s one seed row: two acts each declaring `unlock={"hostile_act_count": 5}`
(`combat_tease_whisper`, `combat_tease_touch`); three acts each declaring
`unlock={"hostile_act_count": 20}` (`combat_charm`, `combat_bind_caress`,
`combat_forced_pleasure`); two acts each declaring the compound gate
`unlock={"hostile_act_count": 40, "climax_count": 30}` (`combat_forced_climax`,
`combat_relentless_torment`); and one act declaring the compound gate
`unlock={"hostile_act_count": 80, "climax_extension_count": 30}` (`combat_climax_domination`).
Every one of these eight acts SHALL declare `resistible=True`, `actor_counters=("hostile_act_count",)`,
and `participant_counters=()`.

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

#### Scenario: Casting any of the eight acts credits hostile_act_count on the actor only
- **WHEN** entity A casts `combat_tease_whisper` targeting hostile entity B, both starting at
  `hostile_act_count == 0`
- **THEN** afterward `A.sexual.hostile_act_count` equals `1` and `B.sexual.hostile_act_count`
  remains `0`

### Requirement: combat_forced_climax, combat_relentless_torment, and combat_climax_domination reliably clear the climax extension threshold
`combat_forced_climax`, `combat_relentless_torment`, and `combat_climax_domination` SHALL each
declare `base_pleasure=30`.

#### Scenario: Worst-case target-side gain still clears the extension threshold
- **WHEN** `compute_pleasure_gain` is evaluated for a target at `普通` sensitivity (multiplier `1.0`),
  `強烈` shame (multiplier `0.65`), and `participant_count == 2` for `combat_forced_climax`
- **THEN** the resulting gain is greater than or equal to `climax_extension_threshold` (`20`)

### Requirement: combat_forced_climax and combat_relentless_torment differ by actor_pleasure_ratio, not by dominance-freedom tuning
`combat_forced_climax` SHALL declare `actor_pleasure_ratio=0.4` and `target_part="私處"`.
`combat_relentless_torment` SHALL declare `actor_pleasure_ratio=0.6` and `target_part="臀部"`, with
`base_pleasure=30` matching `combat_forced_climax` exactly.

#### Scenario: combat_relentless_torment always costs the actor more than combat_forced_climax at equal target-side gain
- **WHEN** `compute_pleasure_gain` is evaluated for the actor for both acts at identical sensitivity,
  shame, and participant count
- **THEN** `combat_relentless_torment`'s actor-side gain exceeds `combat_forced_climax`'s actor-side
  gain

### Requirement: combat_climax_domination is the sole AREA act in this catalog line
`combat_climax_domination` SHALL declare `target_spec=TargetSpec.AREA` and `target_part="私處"`.
Every other act added by this change SHALL declare `target_spec=TargetSpec.SINGLE`.

#### Scenario: combat_climax_domination targets an area
- **WHEN** `combat_climax_domination` is read from `SEXUAL_ACT_REGISTRY`
- **THEN** its `SkillDef.target_spec` equals `TargetSpec.AREA` and its `target_part` equals `"私處"`

### Requirement: No act added by this change declares a sexual_events entry
Every one of the eight acts added by this change SHALL declare `sexual_events=()`.

#### Scenario: 魅惑 and 束縛愛撫 declare no events
- **WHEN** `combat_charm` and `combat_bind_caress` are read from `SEXUAL_ACT_REGISTRY`
- **THEN** both declare `sexual_events == ()`, and their accuracy/agility-debuff flavour is delivered
  entirely by `world/rules/rulebook/combat_modifiers.yaml`'s existing
  `high_arousal_agility_accuracy_penalty` row, unchanged by this proposal
