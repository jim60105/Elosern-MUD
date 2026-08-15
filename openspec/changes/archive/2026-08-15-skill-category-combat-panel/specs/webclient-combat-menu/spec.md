## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 3. For a valid active combat session, its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, and `skills`; `available` SHALL be true and `kind` SHALL be `combat`. `session` SHALL contain exactly `session_id`, `mode`, `round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be `hostile` or `guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or `recovery`, and reason SHALL be null or an exact object containing stable code and safe Traditional Chinese message. A ready session SHALL have a null reason; a recovery session SHALL have a non-null reason, no cast/flee action, and one confirmed Forfeit descriptor when its record is strictly parsed. The presenter SHALL strictly read and reconstruct the authenticated puppet's current `CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live object or filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state, battlefield state, session state, quests, location, or world time. Outside combat it SHALL use the registered common unavailable form rather than fabricate exploration actions.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, and current actions while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet has no combat session
- **THEN** `context_actions` uses its schema-valid unavailable form and contains no Attack, skill, target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal text output remains usable

### Requirement: Combat presentation enumerates complete deterministic choices
The combat panel's `skills` field SHALL be an ordered array of category groups. Each category group
SHALL contain the category's stable key, a bounded display label, and an ordered array of one or more
sub-groups; each sub-group SHALL contain a nullable group key, a label that is non-null exactly when
the group key is non-null, and an ordered array of skill descriptors. Category ordering SHALL follow
`SkillCategory`'s declaration order; sub-group ordering within `elemental_magic` SHALL follow
`ELEMENT_REGISTRY`'s declaration order. A category with zero owned skills SHALL be omitted from the
array entirely, not emitted with an empty `groups` array; a category whose skills carry no `group`
SHALL emit exactly one sub-group with a `null` group key and label. The total count of skill
descriptors across every category and sub-group, flattened, SHALL NOT exceed the existing `MAX_SKILLS`
bound; this bound applies to the flattened total, not to the count of top-level category-group
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
  flattened total skill count across all of their sub-groups exceeding `MAX_SKILLS`
- **THEN** validation rejects the payload, because the bound applies to the flattened total, not to
  the count of top-level category-group entries

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

## ADDED Requirements

### Requirement: Telnet combat actions renders identical category and group structure
`commands/combat.py`'s `CmdCombatActions` SHALL render the same category and sub-group structure and
ordering as the WebClient `context_actions` panel, computed through the same shared grouping function
in `world/rules/combat_view.py`. Each rendered category SHALL show its display label as a heading; each
non-null sub-group SHALL show its display label as a sub-heading; skills within a sub-group SHALL be
listed in the same order the WebClient panel would list them.

#### Scenario: Telnet output groups skills identically to the WebClient panel
- **WHEN** `combat actions` is invoked by a player owning skills across two categories, one of which
  (`elemental_magic`) spans two elements
- **THEN** the rendered text shows both category headings in `SkillCategory` declaration order, and
  the `elemental_magic` heading is followed by its two element sub-headings in `ELEMENT_REGISTRY`
  order, each listing its skills in `owned_keys()` order

#### Scenario: A category with no group shows no sub-heading
- **WHEN** `combat actions` is invoked by a player owning `martial_arts` skills
- **THEN** the `martial_arts` heading's skills are listed directly beneath it with no sub-heading line
