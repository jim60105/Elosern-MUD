# webclient-combat-menu Delta Specification

## MODIFIED Requirements

### Requirement: Combat presentation enumerates complete deterministic choices
The combat panel's `skills` field SHALL be an ordered array of category groups. Each category group
SHALL contain the category's stable key, a bounded display label, and an ordered array of one or more
sub-groups; each sub-group SHALL contain a nullable group key, a label that is non-null exactly when
the group key is non-null, and an ordered array of skill descriptors. Category ordering SHALL follow
`SkillCategory`'s declaration order; sub-group ordering within `elemental_magic` SHALL follow
`ELEMENT_REGISTRY`'s declaration order. A category with zero owned skills SHALL be omitted from the
array entirely, not emitted with an empty `groups` array; a category whose skills carry no `group`
SHALL emit exactly one sub-group with a `null` group key and label. The total count of skill
descriptors across every category and sub-group, flattened, SHALL NOT exceed the `MAX_SKILLS` bound
of `192` — raised from the previous `32` so the bound clears the current theoretical maximum of 157
owned active skills (91 base active skills including innate plus 65 registered sexual acts and the
pre-existing `divine_sexual_arts`) with headroom for catalog growth, while remaining a multiple of
16 consistent with the presentation-bounds
family; this bound applies to the flattened total, not to the count of top-level category-group
entries, which is separately bounded by the number of `SkillCategory` members. Within each sub-group, skill
descriptors SHALL list each unique owned active `SkillDef` in `SkillHandler.owned_keys()` order after
passive filtering, including innate skills, without alphabetical reordering. Each skill descriptor
SHALL contain its stable key, registry label and description, exact resource cost, target
specification, nullable element key, enabled state, nullable stable disabled reason, ordered valid
participant IDs, and applicable approved AREA shorthands — byte-identical in shape to schema version
2's flat descriptor. Participants SHALL be ordered from `player_ids` then `enemy_ids` and SHALL
contain a positive opaque identity, stable session token, bounded display name, team,
living/fled/knocked-out state, current/maximum HP, and a nullable server-authored portrait reference.
`portrait_ref` SHALL equal the opaque art catalog key for that participant when the participant is
present in the `webclient-art-panel` portrait catalog — including an entry that resolves to a
placeholder card — and SHALL be `null` only when the participant is absent from that catalog. The
server SHALL derive the reference from the catalog it actually builds (character named-policy with
adult gate, generic-monster bestiary archetype, or unavailable placeholder), and the browser SHALL
NOT construct a portrait subject key or URL from entity data. Lists and strings SHALL have explicit
bounds and the serialized envelope SHALL remain within the OOB protocol limit.

#### Scenario: Stored skill order and passive exclusion are preserved within each sub-group
- **WHEN** a player owns active skills `wind_blade`, `fire_ball` in that stored order (both
  `elemental_magic`/`wind` and `elemental_magic`/`fire` respectively) and also owns a passive skill
- **THEN** the `elemental_magic` category's `wind` sub-group lists `wind_blade` and its `fire`
  sub-group lists `fire_ball`, the passive skill is excluded entirely, and innate active skills retain
  their deterministic handler order within their own category's sub-group

#### Scenario: Category ordering is enum order, independent of ownership order
- **WHEN** an entity owns skills from `movement` and `elemental_magic` only, granted to
  `entity.db.skills` in an order where the movement skill was imported after the elemental one
- **THEN** the `skills` array lists the `elemental_magic` category group before the `movement`
  category group, because `elemental_magic` precedes `movement` in `SkillCategory`'s declaration
  order

#### Scenario: An owned category with no members is omitted, not emitted empty
- **WHEN** an entity owns no skill classified `sexual_act`
- **THEN** the `skills` array contains no category group whose `category` is `"sexual_act"` — no
  entry with an empty `groups` array is emitted for it

#### Scenario: A category with no group carries exactly one null-keyed sub-group
- **WHEN** an entity owns one or more skills classified `martial_arts` (a category whose members
  never declare a `group`)
- **THEN** the `martial_arts` category group's `groups` array contains exactly one sub-group whose
  `group` and `label` are both `null`, listing every owned `martial_arts` skill

#### Scenario: The flattened skill-count bound rejects a payload whose total exceeds MAX_SKILLS even when its category-group count is small
- **WHEN** a hand-constructed `skills` payload has few top-level category-group entries but a
  flattened total skill count across all of their sub-groups exceeding `192`
- **THEN** validation rejects the payload, because the bound applies to the flattened total, not to
  the count of top-level category-group entries

#### Scenario: A payload at the raised bound passes validation
- **WHEN** a hand-constructed `skills` payload's flattened total is exactly `192`
- **THEN** validation accepts the payload

#### Scenario: A catalog-complete panel fits within the canonical JSON byte bound
- **WHEN** the combat view is built for an entity owning every currently obtainable active skill
  (all base active skills plus every registered sexual act) and the resulting `context_actions`
  payload is serialized
- **THEN** the panel builds without a presentation error and the canonical JSON size of the
  serialized payload is at or below `MAX_CANONICAL_JSON_BYTES` (65,536), and every array in the
  payload is within `MAX_LIST_ITEMS`

#### Scenario: Unavailable skill remains visible
- **WHEN** an owned active skill lacks resources, has no valid target, has an unavailable effect
  handler, or the actor cannot act
- **THEN** its descriptor remains focusable with `enabled: false`, one stable code, and a
  Traditional Chinese explanation derived from the rules preview

#### Scenario: Portrait reference is server-authored and nullable
- **WHEN** combat presentation is built after the art-panel change
- **THEN** each participant's `portrait_ref` equals the opaque art catalog key for that participant
  when the participant is present in the art catalog — including an entry that resolves to a
  placeholder — and is `null` only when the participant is absent from the catalog, and the browser
  never derives a subject key or URL from the participant
