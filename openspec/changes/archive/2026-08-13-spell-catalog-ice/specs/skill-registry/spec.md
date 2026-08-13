## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 冰-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 冰-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["ice"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `ice_shard` | 冰錐術 | 學徒 | `TargetSpec.SINGLE` | `mp=13` | `damage:ice:magic` |
| `frost_breath` | 凍結之息 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `buff_apply:ice_slow` |
| `ice_wall` | 冰牆術 | 術師 | `TargetSpec.SINGLE` | `mp=25` | `buff_apply:ice_wall` |
| `frost_arrow_rain` | 冷凍箭雨 | 術師 | `TargetSpec.AREA` | `mp=28` | `damage:ice:magic` |
| `permafrost_domain` | 永凍領域 | 大師 | `TargetSpec.AREA` | `mp=48` | `buff_apply:ice_freeze` |
| `ice_prison` | 冰封監牢 | 大師 | `TargetSpec.SINGLE` | `mp=44` | `buff_apply:ice_prison` |
| `blizzard` | 暴風雪 | 賢者 | `TargetSpec.AREA` | `mp=88` | `damage:ice:magic` |
| `absolute_tundra` | 絕對凍土 | 賢者 | `TargetSpec.AREA` | `mp=82` | `damage:ice:magic`, `buff_apply:ice_freeze` |
| `absolute_zero` | 絕對零度 | 主宰 | `TargetSpec.SINGLE` | `mp=140` | `damage:ice:magic`, `buff_apply:ice_freeze` |
| `eternal_ice_field` | 永夜冰原 | 主宰 | `TargetSpec.AREA` | `mp=158` | `damage:ice:magic`, `buff_apply:ice_freeze` |

#### Scenario: All ten 冰 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 冰 keys (`ice_shard`, `frost_breath`, `ice_wall`, `frost_arrow_rain`, `permafrost_domain`, `ice_prison`, `blizzard`, `absolute_tundra`, `absolute_zero`, `eternal_ice_field`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["ice"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 冰 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `ice_mastery` skill attempts to cast `ice_wall`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `ice_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 冰 spell (`ice_wall`, `frost_arrow_rain`)
#### Scenario: 大師-tier 冰 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `ice_mastery` skill attempts to cast `permafrost_domain`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `ice_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 冰 spell (`permafrost_domain`, `ice_prison`)
#### Scenario: 賢者-tier 冰 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `ice_mastery` skill attempts to cast `blizzard`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `ice_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 冰 spell (`blizzard`, `absolute_tundra`)
#### Scenario: 主宰-tier 冰 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `ice_mastery` skill attempts to cast `absolute_zero`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `ice_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 冰 spell (`absolute_zero`, `eternal_ice_field`)
