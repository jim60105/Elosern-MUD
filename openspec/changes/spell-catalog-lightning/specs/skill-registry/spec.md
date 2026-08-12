## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 雷-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 雷-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["lightning"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `spark_shock` | 電擊術 | 學徒 | `TargetSpec.SINGLE` | `mp=13` | `damage:lightning:magic` |
| `static_ward` | 靜電護體 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:lightning_static_ward` |
| `chain_lightning` | 雷鎖術 | 術師 | `TargetSpec.AREA` | `mp=27` | `damage:lightning:magic` |
| `paralyzing_bolt` | 麻痺電擊 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `damage:lightning:magic`, `buff_apply:paralysis` |
| `thunder_combo` | 雷霆連擊 | 大師 | `TargetSpec.SINGLE` | `mp=46` | `damage:lightning:magic` |
| `lightning_strike` | 落雷術 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:lightning:magic` |
| `heavens_thunder` | 天雷降臨 | 賢者 | `TargetSpec.AREA` | `mp=92` | `damage:lightning:magic` |
| `thunder_gods_haste` | 雷神之速 | 賢者 | `TargetSpec.SELF` | `mp=68` | `self_buff_apply:lightning_extra_action` |
| `judgement_thunder` | 審判雷霆 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:lightning:magic` |
| `divine_lightning_slaughter` | 神雷滅殺 | 主宰 | `TargetSpec.AREA` | `mp=155` | `damage:lightning:magic` |

#### Scenario: All ten 雷 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 雷 keys (`spark_shock`, `static_ward`, `chain_lightning`, `paralyzing_bolt`, `thunder_combo`, `lightning_strike`, `heavens_thunder`, `thunder_gods_haste`, `judgement_thunder`, `divine_lightning_slaughter`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["lightning"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 雷 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `lightning_mastery` skill attempts to cast `chain_lightning`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `lightning_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 雷 spell (`chain_lightning`, `paralyzing_bolt`)
#### Scenario: 大師-tier 雷 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `lightning_mastery` skill attempts to cast `thunder_combo`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `lightning_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 雷 spell (`thunder_combo`, `lightning_strike`)
#### Scenario: 賢者-tier 雷 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `lightning_mastery` skill attempts to cast `heavens_thunder`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `lightning_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 雷 spell (`heavens_thunder`, `thunder_gods_haste`)
#### Scenario: 主宰-tier 雷 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `lightning_mastery` skill attempts to cast `judgement_thunder`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `lightning_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 雷 spell (`judgement_thunder`, `divine_lightning_slaughter`)
