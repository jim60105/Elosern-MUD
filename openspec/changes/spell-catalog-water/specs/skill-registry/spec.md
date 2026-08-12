## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 水-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 水-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["water"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `water_bolt` | 水箭術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `damage:water:magic` |
| `minor_heal` | 治癒滴露 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `heal:single` |
| `healing_spring` | 治癒之泉 | 術師 | `TargetSpec.AREA` | `mp=28` | `heal:area` |
| `water_shield` | 水盾術 | 術師 | `TargetSpec.SINGLE` | `mp=22` | `buff_apply:water_shield` |
| `abyssal_whirlpool` | 深海漩渦 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:water:magic`, `buff_apply:water_bind` |
| `wellspring_of_life` | 生命湧泉 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `heal:single` |
| `tsunami` | 海嘯術 | 賢者 | `TargetSpec.AREA` | `mp=95` | `damage:water:magic` |
| `tidal_revival` | 復生之潮 | 賢者 | `TargetSpec.SINGLE` | `mp=78` | `heal:single` |
| `sea_of_life` | 生命之海 | 主宰 | `TargetSpec.AREA` | `mp=160` | `heal:area` |
| `abyssal_tide` | 深淵巨潮 | 主宰 | `TargetSpec.AREA` | `mp=145` | `damage:water:magic` |

#### Scenario: All ten 水 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 水 keys (`water_bolt`, `minor_heal`, `healing_spring`, `water_shield`, `abyssal_whirlpool`, `wellspring_of_life`, `tsunami`, `tidal_revival`, `sea_of_life`, `abyssal_tide`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["water"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 水 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `water_mastery` skill attempts to cast `healing_spring`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `water_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 水 spell (`healing_spring`, `water_shield`)
#### Scenario: 大師-tier 水 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `water_mastery` skill attempts to cast `abyssal_whirlpool`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `water_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 水 spell (`abyssal_whirlpool`, `wellspring_of_life`)
#### Scenario: 賢者-tier 水 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `water_mastery` skill attempts to cast `tsunami`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `water_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 水 spell (`tsunami`, `tidal_revival`)
#### Scenario: 主宰-tier 水 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `water_mastery` skill attempts to cast `sea_of_life`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `water_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 水 spell (`sea_of_life`, `abyssal_tide`)
