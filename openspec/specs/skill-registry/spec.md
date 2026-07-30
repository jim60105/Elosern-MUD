## Purpose

Defines immutable skill metadata, shared targeting enums, representative seed definitions, and the
registry contract used to validate imported active and passive skill keys.

## Requirements

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

### Requirement: SkillDef carries exactly the seven fields design doc §5.2 specifies
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with exactly the fields `key`,
`kind`, `target_spec`, `cost`, `usable_out_of_combat`, `element`, and `effects` — no additional field
added and none of these dropped. Its `cost` and `effects` collections SHALL reject mutation so
registry definitions remain immutable beyond the dataclass's top level.

#### Scenario: Every SKILL_REGISTRY entry exposes exactly the seven documented fields
- **WHEN** any `SkillDef` instance in `SKILL_REGISTRY` is inspected via `dataclasses.fields()`
- **THEN** the field names are exactly `{key, kind, target_spec, cost, usable_out_of_combat, element,
  effects}`, in any order, with no additional field present

#### Scenario: kind is one of ACTIVE or PASSIVE
- **WHEN** any `SkillDef.kind` is inspected
- **THEN** it is a `SkillKind` enum member, either `ACTIVE` or `PASSIVE`

#### Scenario: target_spec is one of the four documented values
- **WHEN** any `SkillDef.target_spec` is inspected
- **THEN** it is a `TargetSpec` enum member, one of `NONE`, `SELF`, `SINGLE`, or `AREA`

#### Scenario: element is either a real lore-registry Element or None
- **WHEN** any `SkillDef.element` that is not `None` is inspected
- **THEN** it is an `Element` instance present in `world.lore.elements.ELEMENT_REGISTRY`'s values

#### Scenario: cost is a mapping of resource key to non-negative integer
- **WHEN** any `SkillDef.cost` is inspected
- **THEN** it is a `dict[str, int]` (possibly empty) whose values are all non-negative integers

#### Scenario: Nested skill-definition collections reject mutation
- **WHEN** a caller tries to alter a registry entry's `cost` dict or `effects` list
- **THEN** the operation raises and the process-wide registry definition remains unchanged

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
