## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 暗-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 暗-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["dark"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `shadow_bolt` | 暗影箭 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:dark:magic` |
| `weaken` | 衰弱術 | 學徒 | `TargetSpec.SINGLE` | `mp=11` | `buff_apply:dark_atk_down` |
| `curse` | 詛咒術 | 術師 | `TargetSpec.SINGLE` | `mp=26` | `buff_apply:dark_curse` |
| `dark_burst` | 闇裂術 | 術師 | `TargetSpec.AREA` | `mp=29` | `damage:dark:magic` |
| `dark_corrosion_domain` | 闇蝕領域 | 大師 | `TargetSpec.AREA` | `mp=47` | `damage:dark:magic`, `buff_apply:dark_corrosion` |
| `shadow_torment` | 暗影凌遲 | 大師 | `TargetSpec.SINGLE` | `mp=41` | `damage:dark:magic`, `buff_apply:dark_corrosion` |
| `abyss_devour` | 深淵吞噬 | 賢者 | `TargetSpec.SINGLE` | `mp=85` | `damage:dark:magic` |
| `dark_dominion` | 黑暗支配 | 賢者 | `TargetSpec.AREA` | `mp=72` | `buff_apply:fear` |
| `void_annihilation` | 終焉黑洞 | 主宰 | `TargetSpec.AREA` | `mp=155` | `damage:dark:magic` |
| `netherworld_judgment` | 冥府審判 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:dark:magic` |

#### Scenario: All ten 暗 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 暗 keys (`shadow_bolt`, `weaken`, `curse`, `dark_burst`, `dark_corrosion_domain`, `shadow_torment`, `abyss_devour`, `dark_dominion`, `void_annihilation`, `netherworld_judgment`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["dark"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 暗 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `dark_mastery` skill attempts to cast `curse`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `dark_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 暗 spell (`curse`, `dark_burst`)
#### Scenario: 大師-tier 暗 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `dark_mastery` skill attempts to cast `dark_corrosion_domain`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `dark_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 暗 spell (`dark_corrosion_domain`, `shadow_torment`)
#### Scenario: 賢者-tier 暗 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `dark_mastery` skill attempts to cast `abyss_devour`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `dark_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 暗 spell (`abyss_devour`, `dark_dominion`)
#### Scenario: 主宰-tier 暗 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `dark_mastery` skill attempts to cast `void_annihilation`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `dark_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 暗 spell (`void_annihilation`, `netherworld_judgment`)
