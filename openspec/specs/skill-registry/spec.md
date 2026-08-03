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

### Requirement: SkillDef carries the action resolver's skill-owned faction constraint
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with the required fields `key`, `label`, `description`, `kind`,
`target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, and `faction_constraint`.
`label` and `description` SHALL be nonempty Traditional Chinese player-facing strings bounded to 128 and 512 Unicode code points respectively.
`faction_constraint` SHALL be a `FactionConstraint` value (`ANY`, `ALLY`, `ENEMY`, or `SELF_ONLY`)
and SHALL default to `ANY`. Its `cost` and `effects` collections SHALL reject mutation. Every
production registry entry, including dynamically registered innate skills, SHALL supply all ten
fields directly; no generated key fallback or permissive metadata default SHALL exist.

#### Scenario: Every skill exposes immutable targeting and presentation metadata
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected after startup registration
- **THEN** it has all ten documented fields, its `faction_constraint` is a
  `FactionConstraint`, and its bounded label and description are nonempty

#### Scenario: Direct offensive seed skills target enemies
- **WHEN** the `fire_ball` and `wind_blade` definitions are inspected
- **THEN** their `faction_constraint` is `FactionConstraint.ENEMY`

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

