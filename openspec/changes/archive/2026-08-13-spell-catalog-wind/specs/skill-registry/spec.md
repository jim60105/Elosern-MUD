## ADDED Requirements

### Requirement: SKILL_REGISTRY contains the full 風-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 風-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["wind"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Nine
of the ten declare `SkillKind.ACTIVE`; `flight` stays `SkillKind.PASSIVE` per `movement-skill-waiver`.
Each spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field, for `element-mastery-cast-gate`'s `can_cast_spell_tier` to consume.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `wind_blade` | 風刃術 | 學徒 | `TargetSpec.AREA` | `mp=14` | `damage:wind:magic` |
| `gale_step` | 疾風術 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:wind_haste` |
| `flight` | 飛行術 | 術師 | `TargetSpec.SELF` | `mp=22` | `movement:flight` |
| `tornado_blade` | 龍捲風刃 | 術師 | `TargetSpec.SINGLE` | `mp=26` | `damage:wind:magic` |
| `storm_domain` | 暴風領域 | 大師 | `TargetSpec.AREA` | `mp=50` | `damage:wind:magic` |
| `gale_dance_strike` | 疾風刃舞 | 大師 | `TargetSpec.SINGLE` | `mp=40` | `damage:wind:magic` |
| `heavens_wrath_storm` | 天譴風暴 | 賢者 | `TargetSpec.AREA` | `mp=90` | `damage:wind:magic` |
| `haste_domain` | 神速領域 | 賢者 | `TargetSpec.AREA` | `mp=70` | `buff_apply:wind_haste_domain` |
| `vacuum_severance` | 真空斬滅 | 主宰 | `TargetSpec.SINGLE` | `mp=130` | `damage:wind:magic` |
| `sky_tempest` | 蒼穹暴風 | 主宰 | `TargetSpec.AREA` | `mp=150` | `damage:wind:magic` |

#### Scenario: All ten 風 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 風 keys (`wind_blade`, `gale_step`, `flight`, `tornado_blade`, `storm_domain`, `gale_dance_strike`, `heavens_wrath_storm`, `haste_domain`, `vacuum_severance`, `sky_tempest`)
- **THEN** each key is present with its documented kind (nine `SkillKind.ACTIVE`; `flight` stays
  `SkillKind.PASSIVE` per `movement-skill-waiver`), `element=ELEMENT_REGISTRY["wind"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

#### Scenario: 術師-tier 風 spells are gated at magic level 16 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 15 with no `wind_mastery` skill attempts to cast `tornado_blade`
  (術師-tier), **AND** a separate entity at magic level 1 that owns `wind_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 術師-tier 風 spell (`tornado_blade`). `flight` shares the
  table's 術師 MP band but is a PASSIVE movement skill and is never cast-gated.
#### Scenario: 大師-tier 風 spells are gated at magic level 31 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 30 with no `wind_mastery` skill attempts to cast `storm_domain`
  (大師-tier), **AND** a separate entity at magic level 1 that owns `wind_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 大師-tier 風 spell (`storm_domain`, `gale_dance_strike`)
#### Scenario: 賢者-tier 風 spells are gated at magic level 71 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 70 with no `wind_mastery` skill attempts to cast `heavens_wrath_storm`
  (賢者-tier), **AND** a separate entity at magic level 1 that owns `wind_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 賢者-tier 風 spell (`heavens_wrath_storm`, `haste_domain`)
#### Scenario: 主宰-tier 風 spells are gated at magic level 91 without mastery, and unlocked below that level with mastery
- **WHEN** an entity at magic level 90 with no `wind_mastery` skill attempts to cast `vacuum_severance`
  (主宰-tier), **AND** a separate entity at magic level 1 that owns `wind_mastery` attempts to cast
  the same spell
- **THEN** `can_cast_spell_tier` (from `element-mastery-cast-gate`) rejects the first entity's cast and
  permits the second entity's cast, for every 主宰-tier 風 spell (`vacuum_severance`, `sky_tempest`)

#### Scenario: The pre-existing 風 anchor skill(s) were recosted per §4.3, not duplicated
- **WHEN** `SKILL_REGISTRY` is inspected for `wind_blade` and `flight`
- **THEN** each is present exactly once (no duplicate key), with its `cost["mp"]` updated
  (`wind_blade` from `mp=24` to `mp=14`; `flight` from `mp=10` to `mp=22`), and every other field (`label`, `target_spec`, `element`, `effects`) unchanged from before
  this change
