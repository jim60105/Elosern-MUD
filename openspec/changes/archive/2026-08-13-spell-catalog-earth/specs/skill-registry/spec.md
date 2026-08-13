## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 土-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 土-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["earth"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `stone_shard` | 石礫術 | 學徒 | `TargetSpec.SINGLE` | `mp=12` | `damage:earth:magic` |
| `hardened_skin` | 硬化肌膚 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:earth_hardened_skin` |
| `stone_armor` | 岩甲術 | 術師 | `TargetSpec.SINGLE` | `mp=24` | `buff_apply:earth_stone_armor` |
| `dust_veil` | 沙塵術 | 術師 | `TargetSpec.AREA` | `mp=22` | `buff_apply:earth_dust_veil` |
| `earth_bind` | 地縛術 | 大師 | `TargetSpec.AREA` | `mp=42` | `buff_apply:earth_root` |
| `rockslide` | 岩壁崩落 | 大師 | `TargetSpec.AREA` | `mp=48` | `damage:earth:magic` |
| `earthquake` | 地震術 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:earth:magic` |
| `earthen_ward` | 大地庇護 | 賢者 | `TargetSpec.AREA` | `mp=75` | `buff_apply:earth_ward` |
| `mountain_collapse` | 山嶽崩落 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:earth:magic` |
| `earths_judgment` | 大地審判 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:earth:magic` |

#### Scenario: All ten 土 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 土 keys (`stone_shard`, `hardened_skin`, `stone_armor`, `dust_veil`, `earth_bind`, `rockslide`, `earthquake`, `earthen_ward`, `mountain_collapse`, `earths_judgment`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["earth"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 土 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `earth_mastery` skill attempts to cast `stone_armor`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `earth_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 土 spell (`stone_armor`, `dust_veil`)
#### Scenario: 大師-tier 土 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `earth_mastery` skill attempts to cast `earth_bind`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `earth_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 土 spell (`earth_bind`, `rockslide`)
#### Scenario: 賢者-tier 土 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `earth_mastery` skill attempts to cast `earthquake`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `earth_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 土 spell (`earthquake`, `earthen_ward`)
#### Scenario: 主宰-tier 土 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `earth_mastery` skill attempts to cast `mountain_collapse`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `earth_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 土 spell (`mountain_collapse`, `earths_judgment`)
