# webclient-exploration-menu — delta for add-holy-rite-category

## MODIFIED Requirements

### Requirement: Character panel skills are grouped by category with the same ordering rule as the combat panel
Each of `actives` and `passives` SHALL be an ordered array of category groups, structurally identical
in shape to `context_actions`'s `skills` field: each category group SHALL contain the category's
stable key, a bounded display label, and an ordered array of one or more sub-groups; each sub-group
SHALL contain a nullable group key, a label that is non-null exactly when the group key is non-null,
and an ordered array of `{key, label}` skill rows, each bounded the same as the prior version's
passive-row bounds. Category ordering SHALL follow `SkillCategory`'s declaration order (seven members
after the `holy_rite` addition; `movement` and `innate_gift` are no longer categories); sub-group
ordering within `elemental_magic` SHALL follow `ELEMENT_REGISTRY`'s declaration order; sub-group
ordering within `enhancement` SHALL follow the fixed order `null` group, then `"天賦"`, then
`"身法"`, independent of ownership order; sub-group ordering within `holy_rite` SHALL follow the
fixed order `null` group, then `"聖禮"`, independent of ownership order. A category with zero owned
skills of that kind (active or passive) SHALL be omitted from the corresponding array entirely; a
category whose skills carry no `group` SHALL emit exactly one sub-group with a `null` group key and
label. Within each sub-group, skill rows SHALL be ordered as `SkillHandler.owned_keys()` returns
them, without alphabetical reordering. The total count of skill rows across every category and
sub-group, flattened, SHALL NOT exceed 32 for `passives` and SHALL NOT exceed 32 for `actives`,
tracked as independent bounds; these bounds apply to the flattened totals, not to the count of
top-level category-group entries in either array, which is separately bounded by the number of
`SkillCategory` members plus exactly one — the extra slot carrying the presentation-only synthetic
fallback group (category `"unknown"`) for keys absent from `SKILL_REGISTRY`, so an entity owning
skills in every real category plus one unregistered key still renders.

#### Scenario: Innate active skills are visible for the first time
- **WHEN** the character panel is built for a freshly created character with no imported skill data
- **THEN** `actives` contains a `martial_arts` category group whose one sub-group lists both `flee`
  and `basic_attack` (re-homed together by the Phase B taxonomy consolidation; `flee` is no longer
  presented under a `movement` category)

#### Scenario: Category ordering matches the combat panel's rule
- **WHEN** an entity owns skills from `martial_arts` and `elemental_magic` only
- **THEN** the `actives` array lists the `elemental_magic` category group before the `martial_arts`
  category group, matching `SkillCategory`'s declaration order

#### Scenario: Re-homed acquisition tags render as enhancement sub-groups
- **WHEN** an entity owns the passive skills `flight` and `elf_longevity`
- **THEN** `passives` contains no `movement` or `innate_gift` category group, and the `enhancement`
  category group carries its untagged sub-group (if any), then the `"天賦"` sub-group listing
  `elf_longevity`, then the `"身法"` sub-group listing `flight`, in that fixed order

#### Scenario: An empty active or passive category is omitted
- **WHEN** an entity owns no `PASSIVE`-kind skill classified `sexual_act`
- **THEN** `passives` contains no category group whose `category` is `"sexual_act"`

#### Scenario: A category with no group carries exactly one null-keyed sub-group
- **WHEN** an entity owns one or more `martial_arts` skills (a category whose members never declare a
  `group`)
- **THEN** the `martial_arts` category group's `groups` array contains exactly one sub-group whose
  `group` and `label` are both `null`

#### Scenario: The flattened row-count bound rejects a payload whose total exceeds the limit even when its category-group count is small
- **WHEN** a hand-constructed `passives` (or `actives`) payload has few top-level category-group
  entries but a flattened total row count across all of their sub-groups exceeding 32
- **THEN** validation rejects the payload, because the bound applies to the flattened total, not to
  the count of top-level category-group entries

#### Scenario: A skill key absent from the registry degrades to its own key rather than raising
- **WHEN** an entity's stored skill data names a key absent from `SKILL_REGISTRY`
- **THEN** the panel does not raise, and that key appears as a `{key, label}` row (with `label`
  equal to `key`) inside one synthetic category group appended after every real `SkillCategory`
  group, in whichever of `actives`/`passives` its original stored bucket indicates

#### Scenario: Owned holy-rite rows list in the seventh group under the client bound
- **WHEN** the character panel is built for an entity owning the ACTIVE rites `rite_lamb_mark` and
  `rite_anointing_touch` and the PASSIVE `poverty_vow`
- **THEN** `actives` ends with a `holy_rite` group (label 神聖聖儀) whose `null` sub-group lists
  `rite_lamb_mark` and whose `"聖禮"` sub-group lists `rite_anointing_touch` in that fixed order;
  `passives` carries no `holy_rite` group because `poverty_vow` stays `enhancement`; and an entity
  owning skills in all seven real categories plus one unregistered key still renders inside the
  group bound of eight (`len(SkillCategory) + 1`, mirrored by the client constant)
