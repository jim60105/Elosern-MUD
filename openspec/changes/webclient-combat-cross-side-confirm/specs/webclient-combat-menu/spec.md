## ADDED Requirements

### Requirement: A cast across sides asks for confirmation first
Aiming a harmful skill at the player's own side, or a restorative skill at the opposing side, SHALL stay allowed, and the client SHALL ask once for confirmation before sending it. The trigger SHALL use only the descriptor's `harms` and `restores` facts and the chosen targets' committed `team`; the payload and server validation SHALL stay unchanged.

#### Scenario: The trigger is a static predicate
- **WHEN** the client evaluates a submission
- **THEN** it is cross-side exactly when `harms` is true and the target set contains a `party` participant (the actor's side, the actor included), or `restores` is true and it contains a `foes` participant; no damage or healing amount, formula or prediction takes part

#### Scenario: The target set of each form
- **WHEN** the client evaluates a submission
- **THEN** the target set is the focused candidate for SINGLE, the actor for SELF, the explicit selection for AREA, every candidate of the shorthand's side for an AREA shorthand (`all-enemies` → `foes`, `all-allies` → `party`, `all` → both), and empty for NONE; Attack (`basic_attack`) is a SINGLE skill whose descriptor carries `harms: true`

#### Scenario: A harmful skill aimed at an ally asks first
- **WHEN** the player confirms Attack on a companion in the stage target step, by Enter, by its digit, and by a pointer click on its figure
- **THEN** no `combat.cast` is sent; a question card reading `確定要對友方使用〈基本攻擊〉？` opens centred in the stage's `choices` anchor with the focus on its safe answer 否; activating 是 sends exactly one `combat.cast` byte-identical to the payload the same choice sends without the question

#### Scenario: A harmful skill aimed at the actor asks first
- **WHEN** the player confirms a harmful SELF skill, and a harmful SINGLE skill on the controlled figure
- **THEN** a question card reading `確定要對自己使用〈<skill label>〉？` opens before anything is sent

#### Scenario: A restorative skill aimed at a foe asks first
- **WHEN** the player confirms a healing skill on a foe
- **THEN** a question card reading `確定要對敵方使用〈<skill label>〉？` opens before anything is sent

#### Scenario: A group or selection asks once if any member is cross-side
- **WHEN** the player confirms a harmful AREA skill with one foe and one companion selected, the same skill with `all`, the same skill with `all-enemies`, and a restorative AREA skill with `all-allies`
- **THEN** the first two open one question naming 友方, and the last two send at once with no question

#### Scenario: A skill that both harms and restores applies each fact to its side
- **WHEN** the player confirms a skill carrying `harms: true` and `restores: true` on a foe, on a companion, and with `all`
- **THEN** the first asks naming 敵方, the second naming 友方, and the third once naming 友方與敵方

#### Scenario: Same-side use never asks
- **WHEN** the player confirms Attack on a foe, a healing skill on a companion, a buff skill whose descriptor carries `harms: false` and `restores: false` on a foe, a NONE skill, Flee, and the Forfeit confirmation
- **THEN** each sends exactly as before with no question card

#### Scenario: Cancelling returns to the target step
- **WHEN** the question card is open and the player activates 否, activates its close control, or presses Escape
- **THEN** nothing is sent, the card closes, the stage target step is current again with the same focused position, the same selection, the same dim and markers, and DOM focus returns to `#action-dock`; one later Escape pops the target frame as before

#### Scenario: The question keeps the stage and the keys consistent
- **WHEN** the question card is open
- **THEN** the stage keeps the target step's dim, lit set and markers unchanged, the collapsed command card is inert beneath the question card, no dock key (arrows, digits, Enter, Space) moves or activates the target step, and the question card traps focus among its controls as the room cards' question does

#### Scenario: The question is accessible
- **WHEN** the question card opens
- **THEN** it is a modal dialog labelled by its question text, so assistive technology announces `確定要對友方使用〈基本攻擊〉？`, and its first focused control is 否

#### Scenario: A change under the question cancels it
- **WHEN** the question card is open and a committed `context_actions` replacement arrives, a combat round starts playing, or the committed mode leaves combat
- **THEN** the question card closes without sending; on a replacement the target step returns with the existing selection repair, and the server's validation still decides every sent cast

#### Scenario: A locked submission waits
- **WHEN** a mutation is in flight while the question card is open
- **THEN** 是 is disabled with the stated reason, 否 and the close control still work, and nothing is sent until the lock releases and the player activates 是

## MODIFIED Requirements

### Requirement: Combat presentation enumerates complete deterministic choices
The combat panel's `skills` field SHALL be an ordered array of category groups, each
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
- **THEN** no category group carries category `"movement"` or `"innate_gift"` anywhere in the `skills` array; `flee` (ACTIVE, so not passive-filtered) lists under the `martial_arts` category's null sub-group, and the two PASSIVE skills are excluded by passive filtering exactly as any other owned passive

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
  shorthands, the optional freeform scales, and the two required booleans `harms` and
  `restores` — otherwise byte-identical in shape to schema version 2's flat descriptor

#### Scenario: Participant ordering and field set are exact
- **WHEN** the participants array is serialized
- **THEN** participants are ordered from `player_ids` then `enemy_ids` and each contains
  a positive opaque identity, stable session token, bounded display name, team,
  living/fled/knocked-out state, current/maximum HP, and a nullable server-authored
  portrait reference

#### Scenario: The portrait reference comes from the catalog the server actually builds
- **WHEN** the server derives a participant's `portrait_ref`
- **THEN** it derives the reference from the catalog it actually builds (character
  named-policy with the canonical-age check, generic-monster bestiary archetype, or
  unavailable placeholder)

#### Scenario: Payload bounds keep the envelope inside the OOB limit
- **WHEN** a combat `context_actions` payload is serialized
- **THEN** every list and string is within its explicit bound and the serialized
  envelope remains within the OOB protocol limit

#### Scenario: Each skill declares whether it harms or restores its chosen targets
- **WHEN** the combat panel serializes `basic_attack`, a healing skill, a cleansing skill, a damage skill whose damage is routed only to the `enemies` audience, a skill whose only effects are buffs, and a skill that both damages and heals its chosen targets
- **THEN** `harms` is true exactly when the skill's registry declares a damage effect routed to the chosen targets (the `selected` audience), `restores` is true exactly when it declares a heal or cleanse effect routed to the chosen targets, both are derived from the registry's parsed effect declarations alone — never from a damage or healing amount, a formula or the current participants — so the six skills read `harms`/`restores` as true/false, false/true, false/true, false/false, false/false and true/true respectively, and the server and client validators reject a skill descriptor missing either field or carrying a non-boolean value
