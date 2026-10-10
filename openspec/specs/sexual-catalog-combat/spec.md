# sexual-catalog-combat Specification

## Purpose

Register the eight counter-gated 戰鬥線 acts across four tiers, filling the combat line from its
one seed act to nine. Tier 1 opens at `hostile_act_count >= 5`, Tier 2 at `hostile_act_count >= 20`,
Tier 3 at the compound `hostile_act_count >= 40` + `climax_count >= 30` gate, and Tier 5 at the
compound `hostile_act_count >= 80` + `climax_extension_count >= 30` gate with the sole AREA act
絕頂支配. Every act credits `hostile_act_count` symmetrically (`actor_counters` and
`participant_counters` — the counter records participation from either side) and declares no
`sexual_events` — 魅惑/束縛愛撫's accuracy/agility-debuff
flavour reuses the already-shipped `high_arousal_agility_accuracy_penalty` combat-modifier row
unchanged.

## Requirements

<!-- 搾取 (Tier 4, an SP-transfer act) is intentionally NOT covered by this capability — see
     design.md D-2: no cross-entity resource-transfer effect exists in the current schema. -->

### Requirement: Eight Tier 1/2/3/5 combat acts are registered, gated by hostile_act_count and/or climax_count and/or climax_extension_count thresholds
`world/skills/sexual_acts/combat.py`'s `COMBAT_ACTS` tuple SHALL contain, in addition to
`sexual-act-seeds`'s one seed row, the eight tier-gated acts named in the scenarios below.
Every one of these eight acts SHALL declare `resistible=True`,
`actor_counters=("hostile_act_count",)`, and
`participant_counters=("hostile_act_count",)`.

Numerical boundary examples below SHALL use scoped synthetic declarations. Shipped acts retain the named roster, counter-key topology and intent, but their positive thresholds SHALL be author-adjustable.

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

#### Scenario: The two Tier 1 acts share the hostile_act_count 5 gate
- **WHEN** the Tier 1 acts `combat_tease_whisper` and `combat_tease_touch` are read from `COMBAT_ACTS`
- **THEN** each declares the same counter-key topology as synthetic `unlock={"hostile_act_count": <declared positive threshold>}`

#### Scenario: The three Tier 2 acts share the hostile_act_count 20 gate
- **WHEN** the Tier 2 acts `combat_charm`, `combat_bind_caress`, and `combat_forced_pleasure` are read from `COMBAT_ACTS`
- **THEN** each declares the same counter-key topology as synthetic `unlock={"hostile_act_count": <declared positive threshold>}`

#### Scenario: The two Tier 3 acts share the hostile_act_count 40 + climax_count 30 gate
- **WHEN** the Tier 3 acts `combat_forced_climax` and `combat_relentless_torment` are read from `COMBAT_ACTS`
- **THEN** each declares the compound counter-key topology as synthetic `unlock={"hostile_act_count": <declared positive threshold>, "climax_count": <declared positive threshold>}`

#### Scenario: The single Tier 5 act carries the hostile_act_count 80 + climax_extension_count 30 gate
- **WHEN** the Tier 5 act `combat_climax_domination` is read from `COMBAT_ACTS`
- **THEN** it declares the compound counter-key topology as synthetic `unlock={"hostile_act_count": <declared positive threshold>, "climax_extension_count": <declared positive threshold>}`

#### Scenario: Counters credit both bodies of a hostile act
- **WHEN** the counter declarations of the eight acts are examined
- **THEN** `hostile_act_count` records participation from either side, because a hostile sexual act happens between two bodies

#### Scenario: Declared thresholds are mutable and boundary examples are synthetic
- **WHEN** exact numerical boundary cases above are exercised
- **THEN** local fixed synthetic declarations use those boundary values; shipped acts retain the stated counter-key topology, membership and resistance policy with authored positive thresholds, and tests do not pin their literal unlock counts

### Requirement: combat_forced_climax, combat_relentless_torment, and combat_climax_domination reliably clear the climax extension threshold
The three extension-oriented acts SHALL retain their existing guarantee of meeting the configured extension threshold at the established ordinary-sensitivity, strong-shame, two-participant control condition. Base pleasure and shared multipliers SHALL be author-adjustable; tests SHALL preserve the threshold relationship without pinning base pleasure 30 or gain 21. Formula correctness SHALL be covered separately by fixed synthetic mechanism fixtures.

#### Scenario: Worst-case target-side gain still clears the extension threshold
- **WHEN** a declared extension act resolves for a target already in 進行中 under that control condition
- **THEN** an extension is staged and consumed at settlement; changing balance data so that this established guarantee fails remains a meaningful content-quality failure

### Requirement: combat_forced_climax and combat_relentless_torment differ by actor_pleasure_ratio, not by dominance-freedom tuning
The two acts SHALL retain their existing distinct actor-side ratios, equal base pleasure, and respective target parts 私處 and 臀部. The relentless actor-side ratio SHALL exceed the forced ratio; exact magnitudes SHALL be authored data. Neither SHALL add dominance-freedom tuning.

#### Scenario: combat_relentless_torment always costs the actor more than combat_forced_climax at equal target-side gain
- **WHEN** the two acts execute against controlled participants with equal part sensitivity and unchanged target state
- **THEN** the relentless actor receives greater pleasure while the target-side base remains equal; no fixed ratio or resulting gain table is required

### Requirement: combat_climax_domination is the sole AREA act in this catalog line
`combat_climax_domination` SHALL declare `target_spec=TargetSpec.AREA` and
`actor_part="私處"`, `target_part="私處"` (an AREA restatement of 強制絕頂's exact part pair,
design.md D-1).
Every other act added by this change SHALL declare `target_spec=TargetSpec.SINGLE`.

#### Scenario: combat_climax_domination targets an area
- **WHEN** `combat_climax_domination` is read from `SEXUAL_ACT_REGISTRY`
- **THEN** its `SkillDef.target_spec` equals `TargetSpec.AREA`, its `actor_part` equals `"私處"`,
  and its `target_part` equals `"私處"`

### Requirement: No act added by this change declares a sexual_events entry
Every one of the eight acts added by this change SHALL declare `sexual_events=()`.

#### Scenario: 魅惑 and 束縛愛撫 declare no events
- **WHEN** `combat_charm` and `combat_bind_caress` are read from `SEXUAL_ACT_REGISTRY`
- **THEN** both declare `sexual_events == ()`, and their accuracy/agility-debuff flavour is delivered
  entirely by `world/rules/rulebook/combat_modifiers.yaml`'s existing
  `high_arousal_agility_accuracy_penalty` row, unchanged by this proposal
