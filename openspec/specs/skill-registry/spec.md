## Purpose

Defines immutable skill metadata, shared targeting enums, representative seed definitions, and the
registry contract used to validate imported active and passive skill keys.
## Requirements
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

### Requirement: SKILL_REGISTRY exists at the exact path change 4 forward-declared
`world/skills/registry.py` SHALL define a module-level `SKILL_REGISTRY: dict[str, SkillDef]` importable
as `world.skills.registry.SKILL_REGISTRY`, matching the exact module path and symbol name change 4
(`import-contract`) forward-declared and reads via `from world.skills.registry import SKILL_REGISTRY`.

#### Scenario: The registry is importable at the forward-declared path
- **WHEN** `from world.skills.registry import SKILL_REGISTRY` is executed
- **THEN** the import succeeds and `SKILL_REGISTRY` is a non-empty `dict[str, SkillDef]`

#### Scenario: Change 4's self-arming skill-registry test transitions from skipped to passing
- **WHEN** change 4's `world/imports/tests/test_skill_registry_self_arming.py` is run after this
  change lands
- **THEN** the test is no longer skipped, and it passes — asserting that a definitely-unknown skill
  key (e.g. `"definitely_not_a_real_skill_xyz"`) is rejected, not warned, by change 4's `_check_skills()`

#### Scenario: A known skill key from this registry is not rejected by change 4's validator
- **WHEN** change 4's `_check_skills()` is called with a `skills`/`passives` list containing a key
  present in `SKILL_REGISTRY` (e.g. `"fire_ball"`)
- **THEN** no rejection is produced for that key

### Requirement: Skills declare only self-only or free target scope
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with the required fields `key`, `label`, `description`, `kind`,
`target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, and `faction_constraint`.
`label` and `description` SHALL be nonempty Traditional Chinese player-facing strings bounded to 128 and 512 Unicode code points respectively.
`faction_constraint` SHALL be a `FactionConstraint` value
and SHALL default to `ANY`. Every skill SHALL declare its `faction_constraint` explicitly: all attack and
recovery skills SHALL use `FactionConstraint.ANY` (freely targetable among enemies and allies); only a
skill whose effect is inherently self-only SHALL use `FactionConstraint.SELF_ONLY` and restrict its
target to the actor. No skill SHALL be restricted to enemies or allies only; the legacy `ALLY`/`ENEMY`
enum values are retained for legacy test data and restrict nothing. Its `cost` and `effects` collections SHALL reject mutation. Every
production registry entry, including dynamically registered innate skills, SHALL supply all ten
fields directly; no generated key fallback or permissive metadata default SHALL exist.

#### Scenario: Every skill exposes immutable targeting and presentation metadata
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected after startup registration
- **THEN** it has all ten documented fields, its `faction_constraint` is a
  `FactionConstraint`, and its bounded label and description are nonempty

#### Scenario: Attack skills can hit companions
- **WHEN** a player casts any attack skill (`basic_attack`, `fire_ball`, `wind_blade`, `shadow_slash`) at an explicit companion target or an AREA selection including companions
- **THEN** the targets pass faction validation and receive damage (with the friendly-fire penalty applying to companion hits)

#### Scenario: Recovery skills can target allies and foes
- **WHEN** a player casts a recovery skill at an ally, a companion, or an enemy
- **THEN** the target passes faction validation and the skill resolves normally

#### Scenario: Self-only skills accept only the actor
- **WHEN** a `SELF_ONLY` skill is validated against any target other than the actor
- **THEN** the target is rejected at the faction check

#### Scenario: No skill is enemy-restricted
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** no skill declares an ENEMY-only or ALLY-only constraint

#### Scenario: Innate skills have curated display text
- **WHEN** `basic_attack` and dynamically registered `flee` are presented to a player
- **THEN** both use their explicit registry label and description rather than exposing a generated key or raw effect ID

#### Scenario: Existing constructors do not receive a compatibility default
- **WHEN** a caller constructs `SkillDef` without `label` or `description`
- **THEN** construction fails and the caller must be updated to the current exact definition contract

### Requirement: SkillKind and TargetSpec are forward-declared for change 8 to import
`world/skills/registry.py` SHALL define `SkillKind` (`ACTIVE`, `PASSIVE`) and `TargetSpec` (`NONE`,
`SELF`, `SINGLE`, `AREA`) as plain `StrEnum`s with no behavior beyond their member values, documented
as the enums change 8 (`action-resolver`) is expected to import rather than redefine.

#### Scenario: TargetSpec has exactly the four documented members
- **WHEN** `TargetSpec` is inspected
- **THEN** it has exactly the members `NONE`, `SELF`, `SINGLE`, `AREA` and no others

#### Scenario: SkillKind has exactly the two documented members
- **WHEN** `SkillKind` is inspected
- **THEN** it has exactly the members `ACTIVE`, `PASSIVE` and no others

#### Scenario: Both enums carry zero behavior beyond their values
- **WHEN** `SkillKind` and `TargetSpec` are inspected
- **THEN** neither defines any method beyond what `StrEnum` provides — they are pure data, matching
  the same forward-declaration pattern change 4's `world/lore/sexual_vocab.py` already established

### Requirement: The seed registry spans every skill category inventoried from the sample cards
`SKILL_REGISTRY` SHALL include at least one representative `SkillDef` for each of: stat multipliers,
elemental mastery, direct spells, weapon arts, the display-only disguise skill, the partial-conferral
skill, ordinary passives, and at least one per-character-unique passive — without requiring an
exhaustive transcription of every skill mentioned on every sample card.

#### Scenario: At least one stat-multiplier skill exists for each documented tier
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains entries whose `effects` include a `stat_multiply:` entry at `100`-scale,
  `1000`-scale, and a third, smaller scale for the "basic" tier

#### Scenario: All four elemental-mastery skills are present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains a `PASSIVE` entry for fire, dark, wind, and light mastery, each with `element`
  set to the corresponding `world.lore.elements.ELEMENT_REGISTRY` entry

#### Scenario: The conferral skill (統御術) and the disguise skill (狀態偽裝) are both present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains exactly one `ACTIVE` entry whose `effects` include `"confer_skill_partial"`,
  and exactly one `ACTIVE` entry whose `effects` include `"set_disguise"`

#### Scenario: At least three per-character-unique passives exist under distinct keys
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains at least three distinct keys representing a 轉生特典-pattern passive, each with
  a different `effects` entry, none sharing a single generic "reincarnation boon" key

### Requirement: body_enhancement family is PASSIVE, not ACTIVE
`body_enhancement`, `body_enhancement_extreme`, and `body_enhancement_basic` SHALL declare
`kind=SkillKind.PASSIVE` (reclassified from the previous `SkillKind.ACTIVE`, which had no working cast
path — `stat_multiply` was never registered in `action.py`'s `_EFFECT_HANDLERS`, so every cast attempt
unconditionally rejected `UNKNOWN_EFFECT_ID`). Ownership continues to apply the multiplier via
`SkillHandler.effective_value` exactly as before; this requirement changes only `kind`, not any
multiplier math.

#### Scenario: body_enhancement is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player attempts to cast `body_enhancement`
- **THEN** the attempt is rejected the same way casting any other `PASSIVE` skill is rejected (not
  `UNKNOWN_EFFECT_ID`)

#### Scenario: Ownership still applies the multiplier unconditionally
- **WHEN** an entity owns `body_enhancement_extreme` as a passive skill
- **THEN** `entity.skills.effective_value("atk_phys")` reflects the `stat_multiply:atk_phys:1000`
  multiplier exactly as it did before this change

### Requirement: flight and flash_step are PASSIVE
`flight` and `flash_step` SHALL declare `kind=SkillKind.PASSIVE` (reclassified from the previous
`SkillKind.ACTIVE`, which had no working cast path — `movement` was never registered in `action.py`'s
`_EFFECT_HANDLERS`). Ownership alone triggers the waiver behavior defined by the
`movement-cost-charging` capability; no cast action exists for either skill.

#### Scenario: flight is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player attempts to cast `flight`
- **THEN** the attempt is rejected the same way casting any other `PASSIVE` skill is rejected

### Requirement: reincarnation_boon_yuna's effect string is well-formed
`reincarnation_boon_yuna` SHALL declare `effects=["sexual_magic_mastery"]` (corrected from the
malformed three-segment `"element_mastery_rank:性魔法:主宰"`, which did not parse as a recognized
prefix and was inconsistent with every other mastery skill's two-segment form). This fix is a
prerequisite for this change's own registry-load-time validation to succeed on import.

#### Scenario: reincarnation_boon_yuna parses as SexualMasteryEffect
- **WHEN** `SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects` is inspected
- **THEN** it contains exactly one `SexualMasteryEffect` instance and no `ElementMasteryEffect`

### Requirement: dual_blade_mastery exists as a higher-tier sibling to dual_wield_style
`SKILL_REGISTRY` SHALL contain `dual_blade_mastery` (雙刀流·宗師級), `ACTIVE`,
`TargetSpec.SINGLE`, `cost={"sp": 30}`, `effects=["damage:dark:physical"]`,
`faction_constraint=FactionConstraint.ANY`. This SHALL NOT replace or modify `dual_wield_style`.

#### Scenario: dual_blade_mastery is castable and independent of dual_wield_style
- **WHEN** a player casts `dual_blade_mastery` at a valid `SINGLE` target
- **THEN** the cast resolves successfully via the existing `damage` handler, and owning or not owning
  `dual_wield_style` has no bearing on this skill's availability or cost

### Requirement: guardian_instinct and blade_art_mastery display text reflects character-sheet flavor
`guardian_instinct`'s label/description SHALL read as 護主本能-flavored, and `blade_art_mastery`'s
description SHALL explicitly cover both 劍術 and 刀術. Neither skill's `key` or `effects` SHALL change.

#### Scenario: Effect behavior is unchanged
- **WHEN** `guardian_instinct` and `blade_art_mastery`'s `effects` lists are inspected after this
  change
- **THEN** both are byte-identical to their pre-change values — only `label`/`description` differ

### Requirement: All eight elements have a mastery skill
`SKILL_REGISTRY` SHALL contain `water_mastery`, `earth_mastery`, `lightning_mastery`, and
`ice_mastery`, each `PASSIVE`, `TargetSpec.NONE`, with `element` set to the corresponding
`world.lore.elements.ELEMENT_REGISTRY` entry and `effects=["element_mastery_rank:主宰"]`, matching the
existing four mastery skills' (`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery`) shape
exactly.

#### Scenario: All eight elemental-mastery skills are present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains a `PASSIVE` entry for fire, water, wind, earth, lightning, ice, light, and dark
  mastery, each with `element` set to the corresponding `ELEMENT_REGISTRY` entry

### Requirement: divine_sexual_mastery and divine_sexual_arts exist as distinct skills
`SKILL_REGISTRY` SHALL contain `divine_sexual_mastery` (性魔法主宰, `PASSIVE`,
`effects=["sexual_magic_mastery"]`, flavor/title content not gating any other skill's castability in
this change) and `divine_sexual_arts` (神之秘法：性愛系統, `ACTIVE`, `usable_out_of_combat=True`, empty
`cost`, `effects=["sexual_event:<name>"]`), both gated by `can_use_divine_arts` per the `divine-mystery`
capability's requirement.

#### Scenario: divine_sexual_mastery does not gate divine_sexual_arts
- **WHEN** an elf entity owns `divine_sexual_arts` but not `divine_sexual_mastery`
- **THEN** casting `divine_sexual_arts` is not rejected for lacking `divine_sexual_mastery`

### Requirement: light_sword_style deals damage via the standard damage convention
`light_sword_style` SHALL declare `effects=["damage:light:physical"]` (changed from the previously
inert `weapon_style:light_sword`), resolved by the already-registered `damage` effect handler.

#### Scenario: Casting light_sword_style deals light-elemental physical damage
- **WHEN** a player casts `light_sword_style` at a valid `SINGLE` target
- **THEN** the cast resolves successfully (no `UNKNOWN_EFFECT_ID` rejection) and the target takes
  light-elemental physical damage

