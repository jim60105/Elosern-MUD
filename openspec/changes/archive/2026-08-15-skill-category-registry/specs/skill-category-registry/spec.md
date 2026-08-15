## ADDED Requirements

### Requirement: SkillCategory enumerates exactly eight presentation categories
`world/skills/registry.py` SHALL declare `SkillCategory`, a `StrEnum` with exactly eight members in
this declaration order: `ELEMENTAL_MAGIC`, `MARTIAL_ARTS`, `ENHANCEMENT`, `INNATE_GIFT`, `MOVEMENT`,
`DIVINE_MYSTERY`, `UTILITY`, `SEXUAL_ACT`.

#### Scenario: SkillCategory declares the exact member set in order
- **WHEN** `SkillCategory` is inspected
- **THEN** `list(SkillCategory)` equals `[ELEMENTAL_MAGIC, MARTIAL_ARTS, ENHANCEMENT, INNATE_GIFT, MOVEMENT, DIVINE_MYSTERY, UTILITY, SEXUAL_ACT]`, in that exact order

### Requirement: Every SkillDef declares a required category and an optional group
`SkillDef` SHALL declare `category: SkillCategory` with no default value, and `group: str | None`
defaulting to `None`. A `SkillDef` SHALL NOT be constructible without an explicit `category` argument.
`SkillDef.__post_init__` SHALL raise `ValueError` naming the skill's key when `group` is present and
is not a non-empty string.

#### Scenario: Constructing a SkillDef without category raises
- **WHEN** `SkillDef(...)` is constructed with every other required field supplied but `category`
  omitted
- **THEN** construction raises `TypeError` for the missing required argument

#### Scenario: An empty-string group raises at construction
- **WHEN** `SkillDef(...)` is constructed with `group=""`
- **THEN** `__post_init__` raises `ValueError` naming the skill's key

#### Scenario: A non-string group raises at construction
- **WHEN** `SkillDef(...)` is constructed with `group=123`
- **THEN** `__post_init__` raises `ValueError` naming the skill's key (not `AttributeError`)

#### Scenario: A None group is accepted
- **WHEN** `SkillDef(...)` is constructed with `group` omitted (defaulting to `None`)
- **THEN** construction succeeds and `skill.group` is `None`

### Requirement: SKILL_REGISTRY's 117 entries partition exactly across the eight categories
Every key in `SKILL_REGISTRY` SHALL have a `category` that is a valid `SkillCategory` member. The
union of the eight categories' member sets, computed by grouping `SKILL_REGISTRY` by each entry's
`category`, SHALL equal `set(SKILL_REGISTRY.keys())` exactly, with no key counted in more than one
category and no category naming a key absent from `SKILL_REGISTRY`.

#### Scenario: Every registry key has a valid category
- **WHEN** `SKILL_REGISTRY` is iterated
- **THEN** every entry's `category` is a member of `SkillCategory`

#### Scenario: The per-category partition covers the registry exactly
- **WHEN** `SKILL_REGISTRY`'s keys are compared against the union of keys grouped by `category`
- **THEN** the two sets are identical, and no key appears in more than one category's group

### Requirement: elemental_magic and sexual_act members declare a non-null group; every other category's members declare a null group
Every `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` SHALL declare a non-null `group` that is a
key of `ELEMENT_REGISTRY`. Every entry classified `SEXUAL_ACT` SHALL declare a non-null `group`. Every
entry classified `MARTIAL_ARTS`, `ENHANCEMENT`, `INNATE_GIFT`, `MOVEMENT`, `DIVINE_MYSTERY`, or
`UTILITY` SHALL declare `group is None`.

#### Scenario: Every elemental_magic member's group is a known element key
- **WHEN** every `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** each entry's `group` is a non-null key present in `ELEMENT_REGISTRY`

#### Scenario: Every sexual_act member declares a non-null group
- **WHEN** every `SKILL_REGISTRY` entry classified `SEXUAL_ACT` is inspected
- **THEN** each entry's `group` is a non-null, non-empty string

#### Scenario: Every ungrouped category's members declare a null group
- **WHEN** every `SKILL_REGISTRY` entry classified `MARTIAL_ARTS`, `ENHANCEMENT`, `INNATE_GIFT`,
  `MOVEMENT`, `DIVINE_MYSTERY`, or `UTILITY` is inspected
- **THEN** each such entry's `group` is `None`

### Requirement: Classifying a skill changes no other field
Assigning `category`/`group` to any `SKILL_REGISTRY` entry SHALL NOT change that entry's `kind`,
`cost`, `effects`, `element`, `target_spec`, or `faction_constraint` from their values before this
requirement's classification was introduced.

#### Scenario: divine_sexual_arts keeps its mechanics after reclassification
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` is inspected after classification
- **THEN** `requires_divine_arts` is `True`, `effects` still contains `"sexual_event:stimulus_applied"`, and `kind`, `cost`, `target_spec` are unchanged from their pre-classification values, while `category` is `SEXUAL_ACT` and `group` is `"神之秘法"`

#### Scenario: An elemental spell's element field is unaffected by its group assignment
- **WHEN** any `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** its `element` field's key equals its `group` value, and its `effects` are unchanged from their pre-classification values
