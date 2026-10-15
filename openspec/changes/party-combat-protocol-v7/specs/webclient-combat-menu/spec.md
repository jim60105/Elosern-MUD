# Spec Delta

## MODIFIED Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 7.
For a valid active combat session, its available payload SHALL contain exactly
`schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`,
`secondary_actions`, `actors`, `choices`, `draft`, and `suggestions`; `available` SHALL be true, `kind`
SHALL be `combat`, and `suggestions` SHALL be exactly `{"status": "unavailable"}`.

#### Scenario: Active session produces canonical combat presentation
- **WHEN** a puppeted WebClient in a valid persistent combat session receives a full snapshot
- **THEN** `context_actions` reports that session's ID, mode, round, ordered participants, current actions, and the exact `suggestions` object `{"status": "unavailable"}` while a before/after comparison of canonical game state is unchanged

#### Scenario: Exploration does not receive fake combat actions
- **WHEN** the active puppet is in exploration mode
- **THEN** `context_actions` emits the exploration available form and contains no Attack, skill, target, Flee, or Forfeit descriptor

#### Scenario: Presenter failure remains isolated
- **WHEN** combat presentation raises while status and narrative remain healthy
- **THEN** only `context_actions` becomes correlated unavailable, status still renders, and normal text output remains usable

#### Scenario: Combat fields never leak outside a combat session
- **WHEN** the active puppet is in exploration mode or creation-pending
- **THEN** `context_actions` contains no `session`, `participants`, `root_actions`,
  `secondary_actions`, `actors`, `choices`, or `draft` field — the exploration available form (exploration mode) or
  the shared unavailable form is emitted instead

#### Scenario: Combat fields stay byte-identical across the version bump
- **WHEN** a v7 party-command fixture is validated by the server and client mirror
- **THEN** the exact v7 actor/choices/draft shape is accepted, v6 conditions and polarity remain present, and old-version or puppet-level skills payloads reject

#### Scenario: Absent location emits the shared unavailable form
- **WHEN** the puppet has an absent location
- **THEN** `context_actions` emits the registered common unavailable form and never
  fabricates combat-shaped fields

#### Scenario: The exploration form belongs to the context-actions capability
- **WHEN** `context_actions` emits the exploration available form in exploration mode
- **THEN** that form is the one owned by the `webclient-context-actions` capability

#### Scenario: Session fields are exact and constrained
- **WHEN** a combat `context_actions` payload is validated
- **THEN** `session` contains exactly `session_id`, `mode`, `round`, `round_revision`, `state`, and
  `reason`: session ID is bounded, mode is `hostile` or `guild_exam`, round is a
  non-negative safe integer, round_revision is a non-negative safe integer equal to the nonnull draft revision, state is `ready` or `recovery`, and reason is null or an
  exact object containing a stable code and a safe Traditional Chinese message

#### Scenario: Ready and recovery sessions carry consistent reason and actions
- **WHEN** a session record is strictly parsed
- **THEN** a ready session has a null reason, and a recovery session has a non-null
  reason, no personal round action, and one confirmed party surrender descriptor

#### Scenario: The presenter only reads and reconstructs the session record
- **WHEN** combat presentation is built
- **THEN** the presenter strictly reads and reconstructs the authenticated puppet's
  current `CombatSessionRecord`, preserves persisted participant order, emits no live
  object or filesystem reference, and mutates no traits, resources, buffs, sexual
  state, battlefield state, session state, quests, location, or world time

#### Scenario: Exploration actions are never fabricated in a combat session
- **WHEN** a valid active combat session renders `context_actions`
- **THEN** the panel never fabricates exploration actions alongside the combat form

#### Scenario: Version 6 adds read-only facts only
- **WHEN** the combat available form is serialized at version 6
- **THEN** its top-level field set is unchanged from version 5, every participant additionally carries `conditions`, every skill descriptor additionally carries `hostile` and `beneficial`, the presenter stays read-only, and the exploration and unavailable forms differ from version 5 only in `schema_version`

#### Scenario: Version 7 adds authoritative party facts
- **WHEN** the combat available form is serialized at version 7
- **THEN** it carries bounded actor summaries, one actor-scoped choices object and durable draft progress, retains participant conditions and skill polarity, stays read-only, and changes exploration/unavailable forms only in schema_version

### Requirement: Combat presentation enumerates complete deterministic choices
The requested actor's `choices.skills` field SHALL be an ordered array of category groups, each
carrying the category's stable key, a bounded display label, and an ordered array of one
or more sub-groups; each sub-group carries a nullable group key, a label non-null exactly
when the group key is non-null, and an ordered array of skill descriptors. Category
ordering SHALL follow `SkillCategory`'s declaration order (seven members after the
`holy_rite` addition; `movement` and `innate_gift` are retired).

#### Scenario: Stored skill order and passive exclusion are preserved within each sub-group
- **WHEN** a player owns active skills `wind_blade`, `fire_ball` in that stored order (both
  `elemental_magic`/`wind` and `elemental_magic`/`fire` respectively) and also owns a passive skill
- **THEN** the `elemental_magic` category's `wind` sub-group lists `wind_blade` and its `fire`
  sub-group lists `fire_ball`, the passive skill is excluded entirely, and innate active skills retain
  their deterministic handler order within their own category's sub-group

#### Scenario: Category ordering is enum order, independent of ownership order
- **WHEN** an entity owns skills from `martial_arts` and `elemental_magic` only, granted to
  `entity.db.skills` in an order where the martial-arts skill was imported after the elemental one
- **THEN** the `skills` array lists the `elemental_magic` category group before the `martial_arts`
  category group, because `elemental_magic` precedes `martial_arts` in `SkillCategory`'s declaration
  order

#### Scenario: The retired category keys are never emitted
- **WHEN** an entity owns the re-homed acquired passives `flight` and `elf_longevity` and the re-homed innate active `flee`
- **THEN** no category group carries category `"movement"` or `"innate_gift"` anywhere in the `skills` array; the reserved `flee` skill is omitted from personal commands and reaches only the confirmed party operation, and the two PASSIVE skills are excluded by passive filtering exactly as any other owned passive

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
  (all base active skills plus every registered sexual act) with the maximal currently registered usable item choices and 16 participants, and the resulting `context_actions`
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

#### Scenario: Owned holy-rite skills list as the seventh category and validate on both validators
- **WHEN** an entity owning `rite_lamb_mark` and `rite_martyrdom_vow` receives the `context_actions`
  panel
- **THEN** the panel carries a `holy_rite` category group labelled 神聖聖儀, last among the emitted
  categories, with both skills in its single `null` sub-group, and the mirrored client validator
  accepts the payload instead of rejecting the category key as unregistered

#### Scenario: Holy-rite sub-groups follow the fixed null-then-聖禮 order
- **WHEN** an entity owns both a null-group holy rite (`rite_lamb_mark`) and a `聖禮`-group one
  (`rite_anointing_touch`)
- **THEN** the `holy_rite` category group emits the `null` sub-group listing `rite_lamb_mark` before
  the `"聖禮"` sub-group listing `rite_anointing_touch`, independent of the order the two grants were
  stored

#### Scenario: Elemental sub-groups follow the element registry order
- **WHEN** an entity owns skills in several `elemental_magic` sub-groups
- **THEN** sub-group ordering within `elemental_magic` follows `ELEMENT_REGISTRY`'s
  declaration order

#### Scenario: Enhancement sub-groups follow the fixed null-天賦-身法 order
- **WHEN** an entity owns `enhancement` skills across its sub-groups
- **THEN** sub-group ordering within `enhancement` follows the fixed order `null` group,
  then `"天賦"`, then `"身法"`, independent of ownership order

#### Scenario: The MAX_SKILLS bound rationale
- **WHEN** the flattened skill-descriptor bound is evaluated
- **THEN** the `MAX_SKILLS` bound is `192` — raised from the previous `32` so the bound
  clears the current theoretical maximum of 157 owned active skills (91 base active
  skills including innate plus 65 registered sexual acts and the pre-existing
  `divine_sexual_arts`) with headroom for catalog growth, while remaining a multiple of
  16 consistent with the presentation-bounds family

#### Scenario: Top-level category-group count is separately bounded
- **WHEN** the count of top-level category-group entries is bounded
- **THEN** it is bounded by the number of `SkillCategory` members, while the `192`
  `MAX_SKILLS` bound applies to the flattened total across every category and sub-group

#### Scenario: The skill descriptor field set is schema-version-2 compatible
- **WHEN** a skill descriptor is serialized
- **THEN** it contains its stable key, registry label and description, exact resource
  cost, target specification, nullable element key, enabled state, nullable stable
  disabled reason, ordered valid participant IDs, applicable approved AREA
  shorthands, the optional freeform scales, and the two required booleans `hostile` and
  `beneficial` — otherwise byte-identical in shape to schema version 2's flat descriptor

#### Scenario: Participant ordering and field set are exact
- **WHEN** the participants array is serialized
- **THEN** participants are ordered from `player_ids` then `enemy_ids` and each contains
  a positive opaque identity, stable session token, bounded display name, team,
  living/fled/knocked-out state, current/maximum HP, a nullable server-authored
  portrait reference, and `conditions`: at most 8 rows of `code`, `label` and
  `severity`, the same condition codes, labels and severity vocabulary the status
  panel derives for an entity, in the status panel's order, empty when the entity
  carries none

#### Scenario: The portrait reference comes from the catalog the server actually builds
- **WHEN** the server derives a participant's `portrait_ref`
- **THEN** it derives the reference from the catalog it actually builds (character
  named-policy with the canonical-age check, generic-monster bestiary archetype, or
  unavailable placeholder)

#### Scenario: Payload bounds keep the envelope inside the OOB limit
- **WHEN** a combat `context_actions` payload is serialized
- **THEN** every list and string is within its explicit bound and the serialized
  envelope remains within the OOB protocol limit

#### Scenario: Each skill declares whether it is hostile or beneficial to its chosen targets
- **WHEN** the combat panel serializes `basic_attack`, `heal`, the cleanse skill, a skill applying a debuff-polarity buff to its targets, a gauge-transfer (drain) skill, a sexual-stimulus skill, a skill applying a buff-polarity buff to its targets, a damage skill whose damage is routed only to the `enemies` audience, a movement-only skill, and a skill that both damages and heals its chosen targets
- **THEN** `hostile` is true exactly when at least one effect routed to the chosen targets (the `selected` audience, recipient not actor-bound) is classified hostile, and `beneficial` exactly when one is classified beneficial, by the registry's static per-effect-kind classification (a buff application takes its buff definition's polarity: `debuff` hostile, `buff` beneficial); so the ten skills read `hostile`/`beneficial` as true/false, false/true, false/true, true/false, true/false, true/false, false/true, false/false, false/false and true/true; no amount, formula or current participant takes part, and the server and client validators reject a descriptor missing either field or carrying a non-boolean value

#### Scenario: Every effect kind is classified
- **WHEN** the classification table is checked against every effect dataclass the effect parser can produce
- **THEN** each kind is classified exactly once as `hostile`, `beneficial`, `neutral`, or `buff-definition` (buff applications), and an unclassified kind fails the test

#### Scenario: Participants carry their conditions
- **WHEN** a foe is poisoned and a companion is blessed in an active session, and a participant carries more than eight conditions
- **THEN** the foe's row carries the poisoned condition's `code`, `label` and `severity` as the status panel would derive them, the companion's the blessed one, the long list is cut to its first eight in the status panel's order, and an entity without condition state carries `[]` instead of failing the panel

### Requirement: Combat target selection sends one shape per TargetSpec
The browser SHALL derive target controls only from the validated skill descriptor.
NONE SHALL submit no target field. SELF SHALL display the commanded actor binding
but submit no target field. SINGLE SHALL submit `target_ids` containing exactly one
server-provided identity. AREA SHALL let Space toggle unique server-provided candidates
and Enter submit either a nonempty explicit `target_ids` list or one mutually exclusive
approved `target_shorthand`.

#### Scenario: SELF binds without an actor field
- **WHEN** the player submits an enabled SELF skill
- **THEN** combat.command names the authorized actor outside its skill payload; the skill payload has skill_key and no target ID or shorthand, and SELF binds the commanded actor

#### Scenario: AREA multi-selection is explicit and unique
- **WHEN** the player toggles two valid AREA candidates with Space and confirms
- **THEN** one request carries those two distinct server-provided IDs in presenter order and carries no shorthand

#### Scenario: AREA shorthand is mutually exclusive
- **WHEN** the player chooses the server-authored `all-enemies` descriptor
- **THEN** one request carries that shorthand and no target-ID field

#### Scenario: Selection is client-local and repairs on panel replacement
- **WHEN** focus or selections exist before submission and the panel is then replaced
- **THEN** focus and selection remained client-local until submission, and the
  replacement removed vanished selections and restored the nearest surviving focus in
  deterministic order

## ADDED Requirements

### Requirement: Party protocol publishes bounded actor choices and durable progress
Version 7 SHALL expose all allied actor summaries, one requested actor choices object and the durable draft. Choices SHALL carry complete actor skill/item/tactic availability and targets; progress SHALL carry session round/draft versions, required actors and confirmed entries. Server/client validators SHALL enforce exact fields, bounded values and identity relationships.

#### Scenario: Actor-local query
- **WHEN** an authorized read-only actor-choice request names a companion
- **THEN** the canonical panel shows that member catalog/resources/stock without a command, possession or time change

#### Scenario: Catalog and envelope bounds
- **WHEN** five allies exist and the chosen actor owns the complete obtainable skill catalog and usable items
- **THEN** the panel emits one complete choices catalog and all progress summaries within the 65,536-byte envelope, without truncation or five duplicate catalogs

#### Scenario: Strict mirror parity
- **WHEN** a payload has unknown fields, duplicate actor IDs, off-party draft actors, unsafe revisions or missing polarity
- **THEN** server and client mirrors reject the same malformed payload

### Requirement: Actor item summaries and reselection reasons are explicit bounded facts
Actor item rows SHALL include server-authored summary text of at most512 code points and at most128 distinct usable keys. Draft reselection_reasons SHALL carry at most five exact actor_id/reason rows, each joining a required actor in needs_selection_ids. Server and mirror SHALL reject missing, extra or contradictory fields.

#### Scenario: Companion-only item information
- **WHEN** a selected companion owns an item absent from commander inventory
- **THEN** its item row supplies its own bounded summary and targets without commander inventory lookups

#### Scenario: Invalid entry explanation
- **WHEN** a previously confirmed skill becomes unaffordable
- **THEN** canonical draft includes that member in needs_selection_ids with its exact bounded code/message reason while retaining other valid entries


### Requirement: Version 7 root keys and recovery choices are exact
Ready combat SHALL use root keys attack,skills,items,defend,dodge,taunt,retreat and secondary surrender. Recovery SHALL have no personal root choices, only surrender, empty actor summaries and null choices/draft. Ready choices SHALL describe one allied actor; all identity/list/revision bounds SHALL be mirrored.

#### Scenario: Recovery and stale legacy shape
- **WHEN** recovery renders or an old puppet-level skills form arrives
- **THEN** recovery cannot select a personal action and the legacy shape fails exact v7 validation

#### Scenario: Recovery retains the surrender admission revision
- **WHEN** a validly parsed session has unreconstructable participants and null draft choices
- **THEN** its session.round_revision remains authoritative for surrender prompt and confirmation, without deriving a revision from missing draft fields


