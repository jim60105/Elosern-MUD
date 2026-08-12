## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 火-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 火-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["fire"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `fire_ball` | 火球術 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:fire:magic` |
| `fire_arrow` | 火焰箭 | 學徒 | `TargetSpec.SINGLE` | `mp=10` | `damage:fire:magic` |
| `firestorm` | 火焰風暴 | 術師 | `TargetSpec.AREA` | `mp=30` | `damage:fire:magic` |
| `scorching_wave` | 灼熱波動 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `damage:fire:magic`, `buff_apply:fire_scorch` |
| `lava_burst` | 熔岩術 | 大師 | `TargetSpec.AREA` | `mp=52` | `damage:fire:magic` |
| `infernal_wrap` | 業火纏繞 | 大師 | `TargetSpec.SINGLE` | `mp=42` | `damage:fire:magic` |
| `dragon_flame` | 龍炎術 | 賢者 | `TargetSpec.AREA` | `mp=95` | `damage:fire:magic` |
| `hellfire` | 煉獄業火 | 賢者 | `TargetSpec.SINGLE` | `mp=78` | `damage:fire:magic` |
| `phoenix_eternal_flame` | 不滅鳳凰焰 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:fire:magic`, `self_heal` |
| `world_ending_blaze` | 焚世終焰 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:fire:magic` |

#### Scenario: All ten 火 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 火 keys (`fire_ball`, `fire_arrow`, `firestorm`, `scorching_wave`, `lava_burst`, `infernal_wrap`, `dragon_flame`, `hellfire`, `phoenix_eternal_flame`, `world_ending_blaze`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["fire"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 火 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `fire_mastery` skill attempts to cast `firestorm`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `fire_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 火 spell (`firestorm`, `scorching_wave`)
#### Scenario: 大師-tier 火 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `fire_mastery` skill attempts to cast `lava_burst`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `fire_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 火 spell (`lava_burst`, `infernal_wrap`)
#### Scenario: 賢者-tier 火 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `fire_mastery` skill attempts to cast `dragon_flame`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `fire_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 火 spell (`dragon_flame`, `hellfire`)
#### Scenario: 主宰-tier 火 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `fire_mastery` skill attempts to cast `phoenix_eternal_flame`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `fire_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 火 spell (`phoenix_eternal_flame`, `world_ending_blaze`)

#### Scenario: The pre-existing 火 anchor skill(s) were recosted per §4.3, not duplicated
- **WHEN** `SKILL_REGISTRY` is inspected for `fire_ball`
- **THEN** it is present exactly once (no duplicate key), with its `cost["mp"]` updated
  (`fire_ball` from `mp=20` to `mp=14`), and every other field (`label`, `target_spec`, `element`, `effects`) unchanged from before
  this change
