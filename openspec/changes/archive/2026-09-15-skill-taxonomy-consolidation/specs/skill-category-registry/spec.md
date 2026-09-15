## RENAMED Requirements

- FROM: `### Requirement: SkillCategory enumerates exactly eight presentation categories`
- TO: `### Requirement: SkillCategory enumerates exactly six presentation categories`

- FROM: `### Requirement: SKILL_REGISTRY's entries partition exactly across the eight categories`
- TO: `### Requirement: SKILL_REGISTRY's entries partition exactly across the six categories`

- FROM: `### Requirement: elemental_magic and sexual_act members declare a non-null group; every other category's members declare a null group`
- TO: `### Requirement: Category group vocabulary is closed per category`

## MODIFIED Requirements

### Requirement: SkillCategory enumerates exactly six presentation categories
`world/skills/registry.py` SHALL declare `SkillCategory`, a `StrEnum` with exactly six members in
this declaration order: `ELEMENTAL_MAGIC`, `MARTIAL_ARTS`, `ENHANCEMENT`, `DIVINE_MYSTERY`,
`UTILITY`, `SEXUAL_ACT`. `MOVEMENT` and `INNATE_GIFT` SHALL NOT be members: the movement passives
and innate traits are acquisition-granted passives of the `ENHANCEMENT` family and survive only as
display-level groups inside it.

#### Scenario: SkillCategory declares the exact member set in order
- **WHEN** `SkillCategory` is inspected
- **THEN** `list(SkillCategory)` equals `[ELEMENTAL_MAGIC, MARTIAL_ARTS, ENHANCEMENT, DIVINE_MYSTERY, UTILITY, SEXUAL_ACT]`, in that exact order

#### Scenario: The retired branch names are absent
- **WHEN** the enum's value set is inspected
- **THEN** neither `"movement"` nor `"innate_gift"` is a member value

### Requirement: SKILL_REGISTRY's entries partition exactly across the six categories
Every key in `SKILL_REGISTRY` SHALL have a `category` that is a valid `SkillCategory` member. The
union of the six categories' member sets, computed by grouping `SKILL_REGISTRY` by each entry's
`category`, SHALL equal `set(SKILL_REGISTRY.keys())` exactly, with no key counted in more than one
category and no category naming a key absent from `SKILL_REGISTRY`.

#### Scenario: Every registry key has a valid category
- **WHEN** `SKILL_REGISTRY` is iterated
- **THEN** every entry's `category` is a member of `SkillCategory`

#### Scenario: The per-category partition covers the registry exactly
- **WHEN** `SKILL_REGISTRY`'s keys are compared against the union of keys grouped by `category`
- **THEN** the two sets are identical, and no key appears in more than one category's group

#### Scenario: A later proposal fills exactly one module with no other file touched
- **WHEN** a later change registers new skills into exactly one module
- **THEN** the registry still partitions exactly across the six categories, with the new entries in
  their declared category group and the category count unchanged at six

#### Scenario: The re-homed keys land in their consolidated categories
- **WHEN** `flight`, `flash_step`, `elf_longevity`, `reincarnation_boon_elosia` and `reincarnation_boon_yuka` are inspected (with `world.rules.disengage` imported so `flee` is registered)
- **THEN** the first five are classified `ENHANCEMENT`, `flee` is classified `MARTIAL_ARTS`, and no key is classified a retired category

### Requirement: Category group vocabulary is closed per category
`ELEMENTAL_MAGIC` entries SHALL declare a non-null `group` that is a key of `ELEMENT_REGISTRY`.
`SEXUAL_ACT` entries SHALL declare a non-null `group`. `ENHANCEMENT` entries SHALL declare `group`
in the closed display-tag vocabulary `{None, "天賦", "身法"}`: the three former `INNATE_GIFT` traits
(`elf_longevity`, `reincarnation_boon_elosia`, `reincarnation_boon_yuka`) declare `"天賦"`, the two
former `MOVEMENT` passives (`flight`, `flash_step`) declare `"身法"`, and every other enhancement
member declares `None`. `MARTIAL_ARTS`, `DIVINE_MYSTERY` and `UTILITY` entries SHALL declare
`group is None`.

#### Scenario: Every elemental_magic member's group is a known element key
- **WHEN** every `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** each entry's `group` is a non-null key present in `ELEMENT_REGISTRY`

#### Scenario: Every sexual_act member declares a non-null group
- **WHEN** every `SKILL_REGISTRY` entry classified `SEXUAL_ACT` is inspected
- **THEN** each entry's `group` is a non-null, non-empty string

#### Scenario: The enhancement display tags are exactly the re-homed keys
- **WHEN** every `SKILL_REGISTRY` entry classified `ENHANCEMENT` is inspected
- **THEN** its `group` is `None`, or `"天賦"` exactly for `elf_longevity`, `reincarnation_boon_elosia` and `reincarnation_boon_yuka`, or `"身法"` exactly for `flight` and `flash_step`

#### Scenario: Every ungrouped category's members declare a null group
- **WHEN** every `SKILL_REGISTRY` entry classified `MARTIAL_ARTS`, `DIVINE_MYSTERY`, or `UTILITY` is inspected
- **THEN** each such entry's `group` is `None`

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

### Requirement: Classifying a skill changes no other field
Assigning `category`/`group` to any `SKILL_REGISTRY` entry SHALL NOT change that entry's `kind`,
`cost`, `effects`, `element`, `target_spec`, or `faction_constraint` from their values before this
requirement's classification was introduced. The Phase B re-homing of the five acquired-passive keys
and `flee` SHALL likewise change only `category`/`group`. The `effects` pin for `divine_sexual_arts`
tracks the one authorised post-classification rewrite made by `integrate-divine-sexual-arts-catalog`
(the `sexual_event:` → `sexual_event_target:` prefix migration of the same declared event); no other
field of that entry changed.

#### Scenario: divine_sexual_arts keeps its mechanics after reclassification
- **WHEN** `SKILL_REGISTRY["divine_sexual_arts"]` is inspected after classification
- **THEN** `requires_divine_arts` is `True`, `effects` equals `["sexual_event_target:stimulus_applied"]`,
  and `kind`, `cost`, `target_spec` are unchanged from their pre-classification values, while
  `category` is `SEXUAL_ACT` and `group` is `"神之秘法"`

#### Scenario: A re-homed acquired passive keeps its mechanics
- **WHEN** `SKILL_REGISTRY["flight"]` and `SKILL_REGISTRY["reincarnation_boon_yuka"]` are inspected after Phase B re-homing
- **THEN** `flight` keeps `kind=PASSIVE`, `cost={"mp": 22}`, `effects=["movement:flight"]` and its wind `element`; `reincarnation_boon_yuka` keeps `kind=PASSIVE` and `effects=["combat_prediction:武感"]`; only `category`/`group` differ from their pre-Phase-B values

#### Scenario: An elemental spell's element field is unaffected by its group assignment
- **WHEN** any `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** its `element` field's key equals its `group` value, and its `effects` are unchanged from their pre-classification values
