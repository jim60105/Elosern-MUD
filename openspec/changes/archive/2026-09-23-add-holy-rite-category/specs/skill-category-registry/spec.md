# skill-category-registry — delta for add-holy-rite-category

## RENAMED Requirements

- FROM: `### Requirement: SkillCategory enumerates exactly six presentation categories`
- TO: `### Requirement: SkillCategory enumerates exactly seven presentation categories`
- FROM: `### Requirement: SKILL_REGISTRY's entries partition exactly across the six categories`
- TO: `### Requirement: SKILL_REGISTRY's entries partition exactly across the seven categories`

## MODIFIED Requirements

### Requirement: SkillCategory enumerates exactly seven presentation categories
`world/skills/registry.py` SHALL declare `SkillCategory`, a `StrEnum` with exactly seven members in
this declaration order: `ELEMENTAL_MAGIC`, `MARTIAL_ARTS`, `ENHANCEMENT`, `DIVINE_MYSTERY`,
`UTILITY`, `SEXUAL_ACT`, `HOLY_RITE`. Declaration order is the frozen display order, so `HOLY_RITE`
SHALL be declared last and no existing member's position SHALL move. `MOVEMENT`, `INNATE_GIFT`,
`CHURCH`, and `RITUAL` SHALL NOT be members: the movement passives and innate traits are
acquisition-granted passives of the `ENHANCEMENT` family and survive only as display-level groups
inside it, and `CHURCH`/`RITUAL` are the rejected naming candidates for the family the seventh
member now names (`holy_rite`, 神聖聖儀 — church-block skills are named by their invoked rite, not by
the location).

#### Scenario: SkillCategory declares the exact member set in order
- **WHEN** `SkillCategory` is inspected
- **THEN** `list(SkillCategory)` equals `[ELEMENTAL_MAGIC, MARTIAL_ARTS, ENHANCEMENT, DIVINE_MYSTERY, UTILITY, SEXUAL_ACT, HOLY_RITE]`, in that exact order

#### Scenario: The retired branch names are absent
- **WHEN** the enum's value set is inspected
- **THEN** neither `"movement"` nor `"innate_gift"` is a member value

#### Scenario: The rejected naming candidates are absent
- **WHEN** the enum's value set is inspected
- **THEN** neither `"church"` nor `"ritual"` is a member value, and `"holy_rite"` is

### Requirement: SKILL_REGISTRY's entries partition exactly across the seven categories
Every key in `SKILL_REGISTRY` SHALL have a `category` that is a valid `SkillCategory` member. The
union of the seven categories' member sets, computed by grouping `SKILL_REGISTRY` by each entry's
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
- **THEN** the registry still partitions exactly across the seven categories, with the new entries in
  their declared category group and the category count unchanged at seven

#### Scenario: The re-homed keys land in their consolidated categories
- **WHEN** `flight`, `flash_step`, `elf_longevity`, `reincarnation_boon_elosia` and `reincarnation_boon_yuka` are inspected (with `world.rules.disengage` imported so `flee` is registered)
- **THEN** the first five are classified `ENHANCEMENT`, `flee` is classified `MARTIAL_ARTS`, and no key is classified a retired category

#### Scenario: The church-block actives land in holy_rite and nothing else moved
- **WHEN** the fifteen church-block ACTIVE rows `rite_heal_light`, `rite_cleanse`, `rite_calm`,
  `rite_bless_water`, `rite_sanctify_ground`, `rite_absolution`, `rite_lamb_mark`,
  `rite_martyrdom_vow`, `rite_anointing_touch`, `rite_milk_blessing`, `rite_holy_kiss`,
  `rite_confession_bed`, `rite_martial_blessing`, `rite_shelter`, and `rite_morning_devotion` are
  inspected
- **THEN** every one of them is classified `HOLY_RITE`, and the five Series C church passives
  (`poverty_vow`, `obedience`, `chastity_discipline`, `temple_endurance`, `public_devotion`) remain
  classified `ENHANCEMENT`

### Requirement: Category group vocabulary is closed per category
`ELEMENTAL_MAGIC` entries SHALL declare a non-null `group` that is a key of `ELEMENT_REGISTRY`.
`SEXUAL_ACT` entries SHALL declare a non-null `group`. `ENHANCEMENT` entries SHALL declare `group`
in the closed display-tag vocabulary `{None, "天賦", "身法"}`: the three former `INNATE_GIFT` traits
(`elf_longevity`, `reincarnation_boon_elosia`, `reincarnation_boon_yuka`) declare `"天賦"`, the two
former `MOVEMENT` passives (`flight`, `flash_step`) declare `"身法"`, and every other enhancement
member declares `None`. `HOLY_RITE` entries SHALL declare `group` in the closed vocabulary
`{None, "聖禮"}`: the four Series D sexual-ministry rows (`rite_anointing_touch`,
`rite_milk_blessing`, `rite_holy_kiss`, `rite_confession_bed`) declare `"聖禮"` — their carried
presentation metadata from the `SEXUAL_ACT` home, kept so the sub-group rule fires on the moved rows
— and every other `HOLY_RITE` member declares `None`. `MARTIAL_ARTS`, `DIVINE_MYSTERY` and `UTILITY`
entries SHALL declare `group is None`.

#### Scenario: Every elemental_magic member's group is a known element key
- **WHEN** every `SKILL_REGISTRY` entry classified `ELEMENTAL_MAGIC` is inspected
- **THEN** each entry's `group` is a non-null key present in `ELEMENT_REGISTRY`

#### Scenario: Every sexual_act member declares a non-null group
- **WHEN** every `SKILL_REGISTRY` entry classified `SEXUAL_ACT` is inspected
- **THEN** each entry's `group` is a non-null, non-empty string

#### Scenario: The enhancement display tags are exactly the re-homed keys
- **WHEN** every `SKILL_REGISTRY` entry classified `ENHANCEMENT` is inspected
- **THEN** its `group` is `None`, or `"天賦"` exactly for `elf_longevity`, `reincarnation_boon_elosia` and `reincarnation_boon_yuka`, or `"身法"` exactly for `flight` and `flash_step`

#### Scenario: The holy_rite group vocabulary is exactly the moved Series D rows
- **WHEN** every `SKILL_REGISTRY` entry classified `HOLY_RITE` is inspected
- **THEN** its `group` is `None`, or `"聖禮"` exactly for `rite_anointing_touch`,
  `rite_milk_blessing`, `rite_holy_kiss`, and `rite_confession_bed`

#### Scenario: Every ungrouped category's members declare a null group
- **WHEN** every `SKILL_REGISTRY` entry classified `MARTIAL_ARTS`, `DIVINE_MYSTERY`, or `UTILITY` is inspected
- **THEN** each such entry's `group` is `None`

### Requirement: Classifying a skill changes no other field
Assigning `category`/`group` to any `SKILL_REGISTRY` entry SHALL NOT change that entry's `kind`,
`cost`, `effects`, `element`, `target_spec`, or `faction_constraint` from their values before this
requirement's classification was introduced. The Phase B re-homing of the five acquired-passive keys
and `flee` SHALL likewise change only `category`/`group`. The `effects` pin for `divine_sexual_arts`
tracks the one authorised post-classification rewrite made by `integrate-divine-sexual-arts-catalog`
(the `sexual_event:` → `sexual_event_target:` prefix migration of the same declared event); no other
field of that entry changed. The `holy_rite` re-classification of the fifteen church-block ACTIVE
rows SHALL likewise change only `category` (the four Series D rows keep their `group="聖禮"`
untouched); in particular `rite_morning_devotion` keeps `kind=ACTIVE` and every row keeps its exact
`effects` value — the same two rows on rails, every other row the same declaration it carried —
because cast mechanics are a separate change's work.

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

#### Scenario: A moved church rite keeps every other field
- **WHEN** `SKILL_REGISTRY["rite_lamb_mark"]`, `SKILL_REGISTRY["rite_martyrdom_vow"]`, and
  `SKILL_REGISTRY["rite_morning_devotion"]` are inspected after the holy_rite re-classification
- **THEN** the first two keep `effects=["self_buff_apply:lamb_seal"]` and
  `effects=["session_stamp:martyr_key"]` respectively, all three keep their `kind`, `cost`,
  `element`, and `target_spec`, and each now carries `category` `HOLY_RITE` with `group` `None`
