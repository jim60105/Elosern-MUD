## Purpose

Defines immutable skill metadata, shared targeting enums, representative seed definitions, and the
registry contract used to validate imported active and passive skill keys.

## Requirements

### Requirement: SKILL_REGISTRY contains the full 雷-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 雷-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["lightning"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

| Key | 名稱 | 位階 | TargetSpec | Cost | effects |
|---|---|---|---|---|---|
| `spark_shock` | 電擊術 | 學徒 | `TargetSpec.SINGLE` | `mp=13` | `damage:lightning:magic` |
| `static_ward` | 靜電護罩 | 學徒 | `TargetSpec.SELF` | `mp=10` | `self_buff_apply:lightning_static_ward` |
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

### Requirement: SKILL_REGISTRY contains the full 冰-element spell set
`world/skills/registry.py`'s `SKILL_REGISTRY` SHALL declare all ten 冰-element spells from design doc
§4.4, each with the exact key, Traditional Chinese `label`, `SkillKind.ACTIVE`, the tier-appropriate
`TargetSpec`/`FactionConstraint` pair, `cost={"mp": <value>}`, `element=ELEMENT_REGISTRY["ice"]`, and
an `effects` list that parses cleanly under `skill-effects-typed-model`'s typed dispatch table. Each
spell's tier SHALL be derivable from its registry grouping (position and MP cost band) without a
dedicated tier field; the tier grouping is a data label only — the numeric cast gate is
retired, and the lineage gate that replaces it reads the registry tree, not the MP band.

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
| `eternal_ice_field` | 長夜冰原 | 主宰 | `TargetSpec.AREA` | `mp=158` | `damage:ice:magic`, `buff_apply:ice_freeze` |

#### Scenario: All ten 冰 spell keys exist with correct kind, target, and cost
- **WHEN** `SKILL_REGISTRY` is inspected for the ten 冰 keys (`ice_shard`, `frost_breath`, `ice_wall`, `frost_arrow_rain`, `permafrost_domain`, `ice_prison`, `blizzard`, `absolute_tundra`, `absolute_zero`, `eternal_ice_field`)
- **THEN** each key is present with `SkillKind.ACTIVE`, `element=ELEMENT_REGISTRY["ice"]`, the
  `TargetSpec`/`FactionConstraint` pair and `cost["mp"]` value documented in this change's `design.md`,
  and a nonempty `effects` list matching this change's `design.md`

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
`target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, `category`, and `faction_constraint`.
`label` and `description` SHALL be nonempty Traditional Chinese player-facing strings bounded to 128 and 512 Unicode code points respectively.
`faction_constraint` SHALL be a `FactionConstraint` value
and SHALL default to `ANY`. Every skill SHALL declare its `faction_constraint` explicitly: all attack and
recovery skills SHALL use `FactionConstraint.ANY` (freely targetable among enemies and allies); only a
skill whose effect is inherently self-only SHALL use `FactionConstraint.SELF_ONLY` and restrict its
target to the actor. Candidate selection SHALL NOT be restricted to enemies or allies only; an explicitly declared per-effect audience MAY deliver an individual component only to selected self/allies or enemies while leaving selection unrestricted; the legacy `ALLY`/`ENEMY`
enum values are retained for legacy test data and restrict nothing. Its `cost` and `effects` collections SHALL reject mutation. Every
production registry entry, including dynamically registered innate skills, SHALL supply all eleven
fields directly; no generated key fallback or permissive metadata default SHALL exist.

#### Scenario: Every skill exposes immutable targeting and presentation metadata
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected after startup registration
- **THEN** it has all eleven documented fields, its `faction_constraint` is a
  `FactionConstraint`, and its bounded label and description are nonempty

#### Scenario: Attack skills can hit companions
- **WHEN** a player casts any attack skill (`basic_attack`, `fire_ball`, `wind_blade`, `shadow_slash`) at an explicit companion target or an AREA selection including companions
- **THEN** the targets pass faction validation and receive damage for ordinary selected-audience attacks (with the friendly-fire penalty applying to companion hits); a declared enemy-only effect component does not damage the companion

#### Scenario: Recovery skills can target allies and foes
- **WHEN** a player casts a recovery skill at an ally, a companion, or an enemy
- **THEN** the target passes faction validation and ordinary selected-audience recovery applies; explicitly routed components follow their declared audience

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
malformed three-segment `"element_mastery_rank:性魔法:主宰"`, which never parsed as a recognized
prefix). `sexual_magic_mastery` remains the sole mastery-domain declaration for this skill; the
`element_mastery_rank` prefix itself left the recognized prefix set with the retired cast gate.

#### Scenario: reincarnation_boon_yuna parses as SexualMasteryEffect
- **WHEN** `SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects` is inspected
- **THEN** it contains exactly one `SexualMasteryEffect` instance and no `ElementMasteryEffect`

### Requirement: dual_blade_mastery exists as a higher-tier sibling to dual_wield_style
`SKILL_REGISTRY` SHALL contain `dual_blade_mastery` (雙刃旋舞), `ACTIVE`,
`TargetSpec.SINGLE`, `cost={"sp": 30}`, `effects=["damage:dark:physical"]`,
`faction_constraint=FactionConstraint.ANY`. This SHALL NOT replace or modify `dual_wield_style`.

#### Scenario: dual_blade_mastery is castable and independent of dual_wield_style
- **WHEN** a player casts `dual_blade_mastery` at a valid `SINGLE` target
- **THEN** the cast resolves successfully via the existing `damage` handler, and owning or not owning
  `dual_wield_style` has no bearing on this skill's availability or cost

### Requirement: dual_wield_style is a PASSIVE stance, not a castable ACTIVE skill
`dual_wield_style` SHALL declare `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, and an
empty `cost` (reclassified from the previous `SkillKind.ACTIVE` with `TargetSpec.SELF` and
`cost={"sp": 8}`, which had no working cast path — `weapon_style` is not registered in
`action.py`'s `_EFFECT_HANDLERS`, so an in-combat cast attempt unconditionally rejected
`UNKNOWN_EFFECT_ID` at effect resolution (out-of-combat attempts rejected earlier as
`SKILL_NOT_USABLE_OUT_OF_COMBAT`)). `effects=["weapon_style:dual_wield"]` SHALL NOT change: the
typed `WeaponStyleEffect` remains the declared stance representation, and the combat adjustment
defined by the `combat-modifier-table` capability (`dual_wield_style_atk_phys_bonus`) continues to
resolve from ownership via the `skill_owned` + `dual_wielding` rule row.

This requirement explicitly amends the sibling requirement
`dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style` (whose text says the
mastery skill "SHALL NOT replace or modify `dual_wield_style`"): the reclassification changes
`kind`/`target_spec`/`cost` only, never the skill's existence, its `effects` string, or its
independence from `dual_blade_mastery` — the sibling's intent (don't fold the stance into the
mastery skill) is preserved.

#### Scenario: dual_wield_style is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player who owns `dual_wield_style` as a passive skill attempts to cast it
- **THEN** the attempt is rejected with `SKILL_NOT_ACTIVE` at the resolver's ownership step (and
  `action_preview` reports the same `SKILL_NOT_ACTIVE` reason) — never `UNKNOWN_EFFECT_ID`

#### Scenario: Ownership still grants the rule-table adjustment
- **WHEN** an entity owns `dual_wield_style` as a passive skill and has two weapons equipped
- **THEN** `evaluate_combat_modifiers(entity)` returns the `atk_phys: 5` adjustment exactly as it
  did before this change

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
`world.lore.elements.ELEMENT_REGISTRY` entry and `effects=["passive_trait:element_mastery"]`, matching
the existing four mastery skills' (`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery`) shape
exactly (all eight move to the flavor form together with the retired cast gate).

#### Scenario: All eight elemental-mastery skills are present
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** it contains a `PASSIVE` entry for fire, water, wind, earth, lightning, ice, light, and dark
  mastery, each with `element` set to the corresponding `ELEMENT_REGISTRY` entry

### Requirement: divine_sexual_mastery and divine_sexual_arts exist as distinct skills
`SKILL_REGISTRY` SHALL contain `divine_sexual_mastery` (性魔法主宰, `PASSIVE`,
`effects=["sexual_magic_mastery"]`, flavor/title content not gating any other skill's castability in
this change) and `divine_sexual_arts` (神之秘法：性愛系統, `ACTIVE`, `usable_out_of_combat=True`, empty
`cost`, `effects=["sexual_event_target:stimulus_applied"]`), both gated by `can_use_divine_arts` per
the `divine-mystery` capability's requirement. `divine_sexual_arts` SHALL be registered through
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` catalogue row rather than an inline
`SKILL_REGISTRY` entry in `world/skills/registry.py`, so its `SKILL_REGISTRY` entry and its
`SEXUAL_ACT_REGISTRY` row are the same paired objects the catalogue import installs.

#### Scenario: divine_sexual_mastery does not gate divine_sexual_arts
- **WHEN** an elf entity owns `divine_sexual_arts` but not `divine_sexual_mastery`
- **THEN** casting `divine_sexual_arts` is not rejected for lacking `divine_sexual_mastery`

#### Scenario: divine_sexual_arts is registered through the catalogue
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` and `SEXUAL_ACT_REGISTRY["divine_sexual_arts"]` are
  inspected
- **THEN** both exist, share the key, and the `SkillDef` is one the sexual-acts catalogue package
  registered — `world/skills/registry.py` defines no inline entry for the key

#### Scenario: divine_sexual_arts carries the target-scoped stimulus effect
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"].effects` is inspected
- **THEN** it equals `["sexual_event_target:stimulus_applied"]` and its parsed effects resolve to a
  single `TargetSexualEventEffect`

#### Scenario: every world.skills import installs the catalogue rows
- **WHEN** a fresh process imports `world.skills.registry` (or any module under `world.skills`)
  before any other game module
- **THEN** `SKILL_REGISTRY` already contains every `SEXUAL_ACT_REGISTRY` key, including
  `divine_sexual_arts`, because `world/skills/__init__.py` installs the sexual-act catalogue as its
  final bootstrap edge — registry assembly never depends on which module the host imports first

### Requirement: light_sword_style deals damage via the standard damage convention
`light_sword_style` SHALL declare `effects=["damage:light:physical"]` (changed from the previously
inert `weapon_style:light_sword`), resolved by the already-registered `damage` effect handler.

#### Scenario: Casting light_sword_style deals light-elemental physical damage
- **WHEN** a player casts `light_sword_style` at a valid `SINGLE` target
- **THEN** the cast resolves successfully (no `UNKNOWN_EFFECT_ID` rejection) and the target takes
  light-elemental physical damage

### Requirement: Reincarnation boon labels match the preset character names
The three per-character 轉生特典 passives SHALL declare labels that read 轉生祝福·悠花
(`reincarnation_boon_yuka`), 轉生祝福·悠奈 (`reincarnation_boon_yuna`), and 轉生祝福·伊洛希雅
(`reincarnation_boon_elosia`) — each matching the `display_name` of the preset character whose kit
declares that boon in `PLAYER_PRESET_REGISTRY`. Their keys, costs, kinds, and target
specs SHALL NOT change, and each `effects` list keeps its shape with exactly one re-keying: the
伊洛希雅 boon's effect string is `growth_rate:practice:100` (D-A4 re-key of the retired
`growth_rate:magic:100` prefix; the old prefix fails registry load). The derived `status_display.yaml` row `reincarnation_boon_yuka_agility_bonus`
SHALL label itself 轉生祝福·悠花敏捷提升.

#### Scenario: Every preset-carried boon label equals its owner's display name exactly
- **WHEN** the label of each `reincarnation_boon_*` skill declared by a preset's skill kit is
  compared against that preset's `display_name`
- **THEN** the label equals exactly `轉生祝福·<display_name>` (轉生祝福·悠花, 轉生祝福·悠奈,
  轉生祝福·伊洛希雅), and the skill's `kind`, `target_spec`, `cost`, and `effects` are
  byte-identical to the shipped registry values (all PASSIVE, `TargetSpec.NONE`, empty cost,
  `growth_rate:practice:100` / `combat_prediction:武感` / `sexual_magic_mastery` respectively)

#### Scenario: The status display row follows the corrected name
- **WHEN** the `status_display.yaml` row keyed `reincarnation_boon_yuka_agility_bonus` is inspected
- **THEN** its label is 轉生祝福·悠花敏捷提升

### Requirement: Every skill declares usable_out_of_combat deliberately, under one written policy
`usable_out_of_combat` SHALL mean exactly "this skill may be *selected* while no combat session is
in progress"; it SHALL NOT mean the skill's effects may resolve without a battlefield, which
`action-resolution-pipeline`'s damaging-action gate governs independently.

Every entry of `SKILL_REGISTRY` SHALL declare a deliberate value at its own construction site — or,
for a generated family, at the builder that produces that family — judged by one policy: an `ACTIVE`
skill SHALL declare `True` unless casting it with no fight in progress is meaningless, because the
effect has nothing to act on, or would bypass a subsystem that owns the outcome. `PASSIVE` skills
SHALL also carry a deliberate value even though the capability step rejects them with
`RejectReason.SKILL_NOT_ACTIVE` before either out-of-combat gate is reached.

Skills carrying a `world.skills.effects.DamageEffect` SHALL declare `True`: their only use outside a
fight is opening one, and the damaging-action gate confines that use to a battlefield.

#### Scenario: Damage-carrying skills are selectable outside combat
- **WHEN** every `SKILL_REGISTRY` entry whose parsed `effects` include a `DamageEffect` is inspected
- **THEN** each declares `usable_out_of_combat=True`

#### Scenario: A damage skill selected outside combat still cannot resolve without a battlefield
- **WHEN** one of those skills is resolved with a `RoomActionContext`
- **THEN** it rejects with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, demonstrating that the flag
  governs selection and the gate governs resolution

#### Scenario: flee remains unselectable outside combat
- **WHEN** `SKILL_REGISTRY["flee"]` is inspected after `world.rules.disengage` has been imported
- **THEN** its `usable_out_of_combat` is `False`, declared at its own construction site in
  `world/rules/disengage.py`, because there is nothing to disengage from outside combat

#### Scenario: The value is declared at the construction site, never patched afterwards
- **WHEN** `world/skills/registry.py`, `world/skills/sexual_acts/_builder.py`, and
  `world/rules/disengage.py` are inspected
- **THEN** each skill's `usable_out_of_combat` is supplied as an argument at construction, and no
  module mutates the field on an already-built `SkillDef`

### Requirement: The set of skills declaring usable_out_of_combat False is a frozen inventory
`world/skills/tests/` SHALL assert that the set of `SKILL_REGISTRY` keys declaring
`usable_out_of_combat=False` equals an explicit literal set enumerated in the test. Because
`SkillDef`'s construction helpers default the field to `False`, a newly authored skill that omits a
deliberate value SHALL fall outside the pinned set and SHALL fail this assertion, naming the
undecided key. The assertion SHALL cover the hand-written definitions, every generated family, the
sexual-act catalog, and `flee` in one inventory.

#### Scenario: The inventory matches the registry exactly
- **WHEN** the frozen-inventory test runs against the current registry
- **THEN** the computed `False` set equals the enumerated set, with no extra and no missing key

#### Scenario: A new skill that omits a decision fails and is named
- **WHEN** a skill is added to `SKILL_REGISTRY` without supplying `usable_out_of_combat`
- **THEN** the frozen-inventory assertion fails and its failure message names that skill's key as
  undecided

#### Scenario: Flipping a pinned skill to True fails until the inventory is updated
- **WHEN** a skill currently enumerated in the `False` set is changed to declare `True` without
  editing the test
- **THEN** the frozen-inventory assertion fails, so every change of judgement is recorded in one
  place

### Requirement: Spell cost labels include a sixth tier with deterministic column precedence
Elemental spell cost classification SHALL include 神格 with single/direct costs 180 through 220 and area/strong costs 200 through 260, inclusive. It SHALL search all ascending tiers in the target-shape column before the opposite column. Labels SHALL NOT grant ownership, impose a race restriction, or introduce a numeric cast gate. Costs outside every band SHALL fail closed.

#### Scenario: Overlap honors shape
- **WHEN** synthetic SINGLE and AREA spells each cost 180 MP
- **THEN** SINGLE classifies as 神格 and AREA as 主宰

#### Scenario: Sixth band accepts boundaries
- **WHEN** synthetic AREA spells cost 200, 240 or 260 MP
- **THEN** each classifies as 神格 without dependence on caster race or stats

#### Scenario: Out of all bands stays invalid
- **WHEN** a synthetic elemental spell has a positive cost outside both columns of all tiers
- **THEN** classification rejects it instead of inventing a tier or silently omitting the label

### Requirement: Light spell progression composes executable recovery and judgment behavior
The light spell family SHALL provide the documented grace and judgment progression as executable skill behavior using the common effect, condition, recovery and reaction mechanisms. Branch and merge requirements SHALL gate use independently of ownership and preserve reverse-edge-derived proficiency caps. Recovery SHALL respect living-target HP bounds; mixed spells SHALL deliver damage and recovery/cleanse to their declared selected audiences; contact effects SHALL respect state gates and resistance; emergency peak effects SHALL retain ordinary phase locks. The apotheosis merge SHALL require both terminal branches, not the independent ordinary blessing leaf. The superseded stand-alone shield spell SHALL be removed without an alias. Verification SHALL use substantive program behavior and synthetic definitions, not an exact light key/count/label/cost/effect-table test contract.

#### Scenario: Branch and merge progression uses existing mechanics
- **WHEN** a synthetic two-root spell family has branching prerequisites and a two-parent capstone
- **THEN** use rejects until every parent threshold is met, and cap saturation does not prevent attaining a consuming edge

#### Scenario: Composite effects are actual state changes
- **WHEN** a configured spell family is exercised through ordinary action settlement
- **THEN** the declared healing, timed recovery, cleansing, target-dependent damage and state interactions produce their specified observable outcomes with one paid cast and atomic rollback

#### Scenario: Ordinary recovery and mixed policy remain distinct
- **WHEN** ordinary recovery targets an enemy while a mixed spell selects both teams
- **THEN** ordinary recovery still applies and the mixed spell follows its explicitly separate effect audiences

### Requirement: Water spell progression composes executable mana-tide behavior
The water spell family SHALL provide the documented two-root tide/deep-sea progression as executable skill behavior using the common effect, audience, policy, buff, modifier and reaction mechanisms: MP drain with caster recovery, MP-loss DoT tiers, an MP-diverting damage shield, marker-bonus and area MP restoration with a team share-bonus marker, execution-tier MP removal with bounded regen freeze, a source-qualified depletion reaction with a target-state damage redirect, a devastation area rung, and a two-parent capstone that drains every enemy and restores every ally in one paid cast. Branch and merge prerequisites SHALL gate use through the shared lineage engine independently of ownership, with prerequisite caps derived from the reverse-edge map (leaf caps documented as authoring-time data, unconsumed by runtime code). The superseded dev-era water spells (including the five HP-heal keys) SHALL be deleted wholesale without an alias or deprecation shim, rejecting ordinary casts as unknown skills.

#### Scenario: The mana-tide verb is observable at settlement
- **WHEN** synthetic water compositions mirroring the documented clauses resolve through ordinary action settlement
- **THEN** the target's MP pool, the caster's recovery, DoT ticks, shield diversion, restoration, suffocation lock, regen freeze and the capstone's enemy-drain/ally-restore all change observable state with one paid cast and atomic rollback

#### Scenario: Two roots, branch, and convergence gate through the lineage engine
- **WHEN** a synthetic family replicates the documented branching and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and prerequisite caps stay derived from the shared reverse-edge map

#### Scenario: The family stays non-healing and light stays complementary
- **WHEN** the water family is exercised against injured allies
- **THEN** no water node restores HP — MP-family effects only — while HP restoration remains another family's authored behavior

#### Scenario: Retired keys resolve as ordinary rejections
- **WHEN** a player casts a deleted dev-era key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast path could land on

### Requirement: Dark spell progression composes executable curse and erosion behavior
The dark spell family SHALL provide the documented two-root curse/erosion progression as executable skill behavior using the common effect, audience, policy, buff, modifier and reaction mechanisms: stat-debuff ladders on authored axes and durations, a psychological action lock on one buffs key independent of any physical-stillness key, damage-bearing erosion DoTs whose every actual tick loss is transferred in full to the grant-time origin caster and extinguished with either party's death, an execution rung that ignores defense, a devastation area rung, cast-time self-recovery keyed to a declared fraction of the caster's own missing HP, and a two-parent capstone stacking damage, devastation, a wide stat debuff and self-recovery as independent effect components. Branch and merge prerequisites SHALL gate use through the shared lineage engine independently of ownership, with prerequisite caps derived from the reverse-edge map (leaf cap unchanged).

#### Scenario: The curse ladder weakens observable stats at settlement
- **WHEN** synthetic dark debuff compositions mirroring the authored axes and durations resolve through ordinary action settlement and the clock advances
- **THEN** the victims' effective stats drop by the authored amounts for the authored durations and recover on expiry, and the feared victim's next turn is skipped by the shared action-lock consumer until the marker ends — while a physically-stilled victim's distinct key is untouched by the fear key and vice versa

#### Scenario: Erosion transfers its whole loss to the origin caster
- **WHEN** a synthetic damage-plus-erosion composition ticks a victim over several intervals, including one area composition with per-victim origins and one interval where the caster is dead or the victim reaches its HP floor
- **THEN** each living origin caster gains exactly the HP each of their victims actually lost, no credit flows after either party's death or the buff's expiry, and the victim's single loss dispatch and the round's death settlement are unchanged

#### Scenario: Recovery rides the caster's own missing HP, never the victim's
- **WHEN** a synthetic damage-plus-missing-fraction-self-recovery composition resolves from a wounded caster against a fuller enemy
- **THEN** the caster recovers exactly the authored fraction of their own missing HP clamped at their maximum, the enemy's HP state never enters the amount, and a dead caster revives nothing

#### Scenario: Execution and devastation rungs behave through the shared policies
- **WHEN** synthetic execution-rung and devastation-rung dark compositions hit a high-defense target and a mixed area
- **THEN** the execution rung ignores defense subtraction while the ordinary rung does not, and the devastation rung adds its authored maximum-HP fraction on hit through the existing rider with no dark-specific code

#### Scenario: Two roots, branch, and convergence gate through the lineage engine
- **WHEN** a synthetic family replicates the documented branching and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and prerequisite caps stay derived from the shared reverse-edge map

#### Scenario: Retired dev-era bindings resolve as ordinary rejections
- **WHEN** a caller references a deleted dev-era buff binding or casts a never-existing key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on

### Requirement: Earth spell progression composes executable terrain-and-guard behavior
The earth spell family SHALL provide the documented two-root 護甲/地形 progression as executable skill behavior using the common effect, audience, policy, buff, reaction, modifier and lineage mechanisms: a fixed-defense ladder on the defense axis at authored ceilings and durations, an accuracy debuff rung, ground-hazard marker rows whose standing-on-it fact is the live marker instance and whose damage ticks at the authored DoT rungs and durations, the ice slow-rung key reused as pure consumer data beside every fissure, a synergy strike priced once on a standing-on-the-marker target while ignoring defense unconditionally for every target, devastation area rungs, an on-physical-hit counter settlement at the authored coefficient mounted by a detectable self-buff and silent against magic attackers, and a two-parent capstone stacking damage, devastation, the top-rung full-field marker and the slow rung as independent effect components — with the retired bind node's 束縛 verb staying exclusively ice's.

#### Scenario: The defense ladder guards observable stats at settlement
- **WHEN** synthetic earth self-cast and ally-area defense compositions mirroring the authored ceilings and durations resolve through ordinary action settlement and the clock advances
- **THEN** each guardian's effective defense rises by exactly the authored amount for the authored duration, ally-area casts spare enemies, and defense recovers on expiry

#### Scenario: Fissure hazards burn whoever keeps standing on them
- **WHEN** a synthetic area composition applies a marker hazard plus the reused slow rung to a victim and the clock ticks past several intervals, then the victim flees the battlefield mid-duration and separately the hazard expires while its holder stays fighting
- **THEN** the standing victim loses exactly the authored per-interval DoT and carries the authored agility debuff, the hazard stops ticking the moment the holder leaves the battlefield while a non-marker buff of the holder persists unchanged, and expiry ends both the ticking and the standing-on-it fact

#### Scenario: The synergy strike prices the marker once and bypasses defense always
- **WHEN** a synthetic execution composition declaring the marker-fact predicate, a conditional multiplier and the unconditional bypass strikes the same high-defense target while standing on a fissure and while not, plus a target standing on a parallel-duration fissure rung
- **THEN** both marker rungs receive the same single multiplier application with defense ignored, the off-marker strike still ignores defense at base coefficient without the multiplier, and no strike receives the multiplier twice

#### Scenario: The carapace returns physical pain and ignores everything else
- **WHEN** a synthetic self-buff carrier of the counter rule is struck by a landed physical attack, a magic attack, a missed swing, and a damaging tick
- **THEN** only the physical attacker takes the holder's effective attack times the authored coefficient minus its defense exactly once, the attacker's own counter rule does not chain, and the tick and magic paths move no HP back to any attacker

#### Scenario: Devastation and execution rungs behave through the shared policies
- **WHEN** synthetic devastation and execution earth compositions hit a mixed area and a high-defense single target
- **THEN** the devastation rung adds its authored maximum-HP fraction on hit through the existing rider and the execution rung ignores defense subtraction, with no earth-specific code

#### Scenario: Two roots, branches, and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented two-root branching, both branch points, and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and prerequisite caps stay derived from the shared reverse-edge map

#### Scenario: Retired dev-era bindings resolve as ordinary rejections
- **WHEN** a caller references the deleted bind node or its control binding, or casts a never-existing key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on

### Requirement: Fire spell progression composes executable burn-and-immolation behavior
The fire spell family SHALL provide the documented HP・消滅 progression as executable skill behavior using the common effect, audience, policy, buff, reaction and lineage mechanisms: burn damage-over-time rows on the hp axis at the authored rungs and durations with the reused family key re-homed without alias, an on-physical-hit ignition of the attacker mounted by a detectable self-only armor buff through the shared outcome-reaction vocabulary (an ignition applied to the strike's source with grant-time attribution, never a reflected damage counter), a ground-lava marker hazard whose standing-on-it fact is the live marker instance and whose damage ticks at the authored DoT rung with the shared battlefield-exit extinguishment, a 處決級 execution rung that ignores defense subtraction through the shared damage policy, immolation cast costs priced as authored static coefficients beside a self-burn row that lands as an independent effect component regardless of the damage leg, and a three-way branch-point lineage whose two-parent 神格 capstone gates through the shared lineage engine with prerequisite caps derived from the shared reverse-edge map. No fire-specific behavior code SHALL exist: every clause above is data over the shipped event, marker, policy and lineage vocabularies.

#### Scenario: The burn ladder scorches at the authored rung and expires
- **WHEN** a synthetic single-target fire composition dealing its authored coefficient plus the family burn row resolves through ordinary action settlement and the clock advances past several tick intervals and then past expiry
- **THEN** the victim loses exactly the authored per-interval burn amount each interval for exactly the authored duration alongside the landed damage, the burned fact is true for every interval and false after expiry, and no other entity changes

#### Scenario: The burning armor ignites physical attackers and nothing else
- **WHEN** a synthetic self-only armor carrier is struck by a landed physical attack from a living attacker, then by a magic attack, a missed swing, a damaging tick, and a sourceless write, and separately by a physical attacker immune to the ignition and by one already carrying it
- **THEN** only the qualifying physical attacker holds the live authored ignition instance with grant-time attribution to the armor holder refreshed once per qualifying strike, the ignition ticks the attacker's hp at its authored rung while it lasts, the magic/miss/tick/sourceless paths and the immune attacker apply nothing, no damage ever moves back to any attacker, the attacker's own ignition never spawns a second event, and the ignition never disappears with the armor — it lives on the attacker's own clock

#### Scenario: The lava hazard burns whoever keeps standing on it and steps off when they leave
- **WHEN** a synthetic area fire composition applies the authored lava marker to a victim and the clock ticks past several intervals, then the victim flees the battlefield mid-duration, and separately the hazard expires while its holder stays fighting
- **THEN** the standing victim loses exactly the authored per-interval DoT each interval, the standing-on-it fact is true for every interval, the hazard stops ticking the moment the holder leaves the battlefield while the holder's non-marker buffs persist unchanged, and expiry ends both the ticking and the standing-on-it fact

#### Scenario: The execution rung ignores defense and the immolation costs are paid on cast
- **WHEN** a synthetic 處決級 composition strikes a high-defense target, and separately an immolation composition with its authored overflow coefficient and its self-burn cost component resolves with and without the damage leg landing
- **THEN** the execution strike's final damage skips the defense subtraction entirely, the immolation's damage settles at its authored static coefficient, the caster carries the authored self-burn instance ticking at its authored rung and duration whether or not the damage leg lands, and no healing of any kind is applied by the immolation composition

#### Scenario: The capstone burns enemies and itself as three independent components
- **WHEN** a synthetic two-parent capstone area composition with its authored static coefficient, its enemy-side authored burn component and its self-burn cost component resolves against a mixed battlefield
- **THEN** every selected enemy takes the authored coefficient damage and carries the authored enemy burn rung, the caster alone carries the authored self-burn rung, the ally targets take neither leg, and each component settles independently

#### Scenario: Branching and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented root chain, the three-way branch point, the branch-terminal leaves and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, the capstone unlocks only when BOTH authored parents reach their authored thresholds, each branch progresses independently, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era clauses resolve as ordinary rejections
- **WHEN** a caller casts a never-existing fire key through the ordinary cast surface after replacement, or a previously declared fire skill's off-tree healing clause is referenced as an effect binding
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on

### Requirement: Wind spell progression composes executable speed-and-knockback behavior
The wind spell family SHALL provide the documented 動作與閃避 progression as executable skill behavior using the common effect, audience, policy, buff, modifier, and lineage mechanisms: timed self/ally agility ladder rungs mounted as detectable buffs and settled through the shared merged combat-modifier bundle so the authored flat agility adjustments move the real agility-driven consumers (to-hit both poles, overwhelm estimation, resist scoring, flee contest) for exactly the authored durations and then stop; a same-axis bipolar rung whose mount raises its holder's agility while lowering its holder's attack accuracy through one validated modifier rule; an area ally rung whose agility adjustment lands on allies only, its defender-side term acting as evasion against incoming single-target strikes; knockback area rungs mounting the positional-marker rows at their authored world-second durations on enemy audiences through the same-settlement effect component (never a reflected or delayed reaction rule), with the shipped cross-primitive ground-marker sweep and the impossible-recipient refusals observing through the real casts; an unconditional two-roll single-target rung settling two independent strikes for one paid cast through the shared ordered-projection settlement; a 處決級 execution rung ignoring defense subtraction; devastation rungs at the shipped fraction magnitude; and the two-root branching lineage gating every rung through the shared prerequisite engine with the two-parent canopy unlocking only at both authored thresholds.

#### Scenario: The agility ladder speeds its holder on the real consumers and expires
- **WHEN** a synthetic self-cast composition mounts the authored ladder rung and the holder resolves physical exchanges and a flee contest against a control twin, then the clock advances past the authored duration
- **THEN** the holder's effective agility adjustment equals the authored flat rung on every agility-driven consumer for exactly the authored duration, the control twin without the mount is unmoved, and after expiry every consumer reads base values with the holder's non-buff state unchanged

#### Scenario: The bipolar rung trades accuracy for speed on its holder alone
- **WHEN** a synthetic carrier of the authored bipolar mount attacks and is attacked while a control twin fights the same opponents under fixed rolls
- **THEN** the carrier's own strikes carry the authored accuracy penalty while its defender-side agility raises its dodge threshold, the control twin shows neither pole, and the mount's non-holder state is untouched

#### Scenario: The ally domain speeds allies and skips enemies
- **WHEN** a synthetic area ally composition mounts its authored agility rung on a mixed battlefield of allies and enemies
- **THEN** every ally holder reads the authored flat agility adjustment on the merged bundle, no enemy reads any part of it, and an enemy's incoming single-target strikes against the allies resolve against the raised dodge thresholds

#### Scenario: The knockback storms hurl enemies out of position and sweep their footing
- **WHEN** a synthetic knockback area composition lands on enemies — one carrying a live ground-marker hazard and an ordinary buff, one defeated mid-settlement, and allied targets — and afterwards a displaced victim's ally attempts a single-target physical strike on it while a magic cast at it resolves
- **THEN** each living enemy target carries the authored positional row at its authored world-second duration with the out-of-position fact true, the ground-marker victim's hazard instance is swept at mount while its ordinary buff persists, the defeated recipient is refused, allies carry nothing, the follow-up melee strike against the displaced victim is gated, and the magic cast lands normally

#### Scenario: The unconditional flurry resolves two independent strikes for one cast
- **WHEN** a synthetic 連續兩次判定 composition strikes one target under each fixed roll pair (hit-hit, miss-hit, hit-miss, miss-miss) and separately crosses the target's remaining HP on the second roll
- **THEN** exactly two independent rolls are recorded with the authored coefficient on each landing strike, resources and practice are paid once, HP settles through the ordered projection with a single terminal defeat entry, and a policy-free single-strike control on the same target still rolls once

#### Scenario: The execution and devastation rungs settle at their authored rungs
- **WHEN** a synthetic 處決級 composition strikes a high-defense target and separately the authored devastation composition strikes a full-HP target under the shipped fraction rung
- **THEN** the execution strike's damage skips defense subtraction entirely at the authored coefficient, and the devastation strike adds the authored fraction-of-max term exactly like the shipped devastation rungs

#### Scenario: The two roots branch and the canopy gates on both parents
- **WHEN** synthetic progressions grind the mobility root chain and the destruction root's branch chains, then attempt the canopy before one authored parent reaches its threshold
- **THEN** each root progresses independently through the shared prerequisite engine, the branch point admits both authored children once met, the canopy rejects while either authored parent is below its threshold and admits only when both are met, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era keys resolve as ordinary rejections
- **WHEN** a caller casts a never-existing wind key through the ordinary cast surface after replacement, or applies the retired dev-era mobility buff keys
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
