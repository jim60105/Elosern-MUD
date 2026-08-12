## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 光-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 光-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["light"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `heal` | 治癒術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `heal:single` |
| `light_arrow` | 光箭術 | 學徒 | `TargetSpec.SINGLE` | `mp=14` | `damage:light:magic` |
| `purify` | 淨化術 | 術師 | `TargetSpec.SINGLE` | `mp=22` | `cleanse:status` |
| `mass_heal` | 群體治癒 | 術師 | `TargetSpec.AREA` | `mp=30` | `heal:area` |
| `advanced_heal` | 高級治癒 | 大師 | `TargetSpec.SINGLE` | `mp=46` | `heal:single` |
| `holy_shield` | 聖盾術 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `buff_apply:light_holy_shield` |
| `holy_radiance` | 神聖光輝 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:light:magic` |
| `revival_light` | 復甦之光 | 賢者 | `TargetSpec.SINGLE` | `mp=82` | `heal:single` |
| `goddess_blessing` | 女神降福 | 主宰 | `TargetSpec.AREA` | `mp=145` | `heal:area`, `buff_apply:light_blessing` |
| `heavens_judgment_light` | 天啟聖裁 | 主宰 | `TargetSpec.SINGLE` | `mp=135` | `damage:light:magic` |

#### Scenario: All ten 光 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 光 keys (`heal`, `light_arrow`, `purify`, `mass_heal`, `advanced_heal`, `holy_shield`, `holy_radiance`, `revival_light`, `goddess_blessing`, `heavens_judgment_light`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["light"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 光 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `light_mastery` skill attempts to cast `purify`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `light_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 光 spell (`purify`, `mass_heal`)
#### Scenario: 大師-tier 光 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `light_mastery` skill attempts to cast `advanced_heal`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `light_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 光 spell (`advanced_heal`, `holy_shield`)
#### Scenario: 賢者-tier 光 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `light_mastery` skill attempts to cast `holy_radiance`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `light_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 光 spell (`holy_radiance`, `revival_light`)
#### Scenario: 主宰-tier 光 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `light_mastery` skill attempts to cast `goddess_blessing`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `light_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 光 spell (`goddess_blessing`, `heavens_judgment_light`)
