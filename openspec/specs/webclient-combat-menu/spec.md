## Purpose

Exact combat context actions panel, keyboard menu, allowlisted combat adapters, shared side-effect-free availability, EventLog delivery, and active-combat reconnect for the browser WebClient, with full Telnet parity.

## Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 5.
For a valid active combat session, its available payload SHALL contain exactly
`schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`,
`secondary_actions`, `skills`, and `suggestions`; `available` SHALL be true, `kind`
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
  `secondary_actions`, or `skills` field — the exploration available form (exploration mode) or
  the shared unavailable form is emitted instead

#### Scenario: Combat fields stay byte-identical across the version bump
- **WHEN** a v4-compatible combat fixture is validated by the version-5 validator and the client mirror
- **THEN** every combat field serializes exactly as it did at schema version 4, with only `schema_version` equal to 5 and the `suggestions` object added

#### Scenario: Absent location emits the shared unavailable form
- **WHEN** the puppet has an absent location
- **THEN** `context_actions` emits the registered common unavailable form and never
  fabricates combat-shaped fields

#### Scenario: The exploration form belongs to the context-actions capability
- **WHEN** `context_actions` emits the exploration available form in exploration mode
- **THEN** that form is the one owned by the `webclient-context-actions` capability

#### Scenario: Session fields are exact and constrained
- **WHEN** a combat `context_actions` payload is validated
- **THEN** `session` contains exactly `session_id`, `mode`, `round`, `state`, and
  `reason`: session ID is bounded, mode is `hostile` or `guild_exam`, round is a
  non-negative safe integer, state is `ready` or `recovery`, and reason is null or an
  exact object containing a stable code and a safe Traditional Chinese message

#### Scenario: Ready and recovery sessions carry consistent reason and actions
- **WHEN** a session record is strictly parsed
- **THEN** a ready session has a null reason, and a recovery session has a non-null
  reason, no cast/flee action, and one confirmed Forfeit descriptor

#### Scenario: The presenter only reads and reconstructs the session record
- **WHEN** combat presentation is built
- **THEN** the presenter strictly reads and reconstructs the authenticated puppet's
  current `CombatSessionRecord`, preserves persisted participant order, emits no live
  object or filesystem reference, and mutates no traits, resources, buffs, sexual
  state, battlefield state, session state, quests, location, or world time

#### Scenario: Exploration actions are never fabricated in a combat session
- **WHEN** a valid active combat session renders `context_actions`
- **THEN** the panel never fabricates exploration actions alongside the combat form

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
  disabled reason, ordered valid participant IDs, and applicable approved AREA
  shorthands — byte-identical in shape to schema version 2's flat descriptor

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

### Requirement: Availability uses shared side-effect-free rules preview
The combat presenter, Telnet action listing, and combat adapters SHALL consume the same deterministic preview boundary. Availability SHALL include ownership and active kind, resources, exact target shape, presence/alive/range/faction candidate checks, action capability including `actions_per_turn == 0`, effect-handler availability, and time metadata. Preview state is advisory; every submitted action SHALL repeat authoritative validation against current canonical state before initiative.

#### Scenario: Preview and adapter agree on a disabled skill
- **WHEN** a skill is displayed as disabled because SP is insufficient and a modified client nevertheless submits it at the current presentation revision
- **THEN** the adapter rejects with the matching stable rule reason before initiative, no NPC acts, and round count and world time remain unchanged

#### Scenario: State can change after a valid preview
- **WHEN** a skill was enabled in revision N but canonical target state changes before its revision-N submission is admitted
- **THEN** current domain validation rejects or filters it according to target rules without trusting the earlier descriptor

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL preserve the root inventory of the client
combat-menu resolver (the root list of `web/static/webclient/js/elosern/combat_menu.js`:
Attack, Skills, Items, the client-local Bag drawer opener, Defend, Flee, and the
confirmed Forfeit entry) and their existing availability/order. No new root action SHALL
be introduced. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop
one level, and disabled entries SHALL send no packet.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.cast` for `basic_attack` exactly once and the ordinary combat-session path resolves the result

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the player focuses Items or Defend and presses Enter
- **THEN** its `not_implemented` explanation remains readable and no `ui_action` message is emitted

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the Forfeit entry but has not confirmed
- **THEN** no mutation is sent, and Escape returns exactly one menu level without ending combat

#### Scenario: Skills opens a bounded master-detail
- **WHEN** the player opens Skills in combat with skills owned across several categories
- **THEN** the dock lists one row per committed category with its label and its own descriptor count, in the panel's order, instead of one flat list of every owned skill

#### Scenario: A single-sub-group category skips the group level
- **WHEN** the player opens a category whose committed payload carries exactly one sub-group
- **THEN** the skill frame opens directly, and Escape from it returns to the category frame

#### Scenario: A multi-sub-group category presents its groups first
- **WHEN** the player opens a category whose committed payload carries more than one sub-group
- **THEN** the dock lists one row per sub-group in the panel's order, and opening one lists exactly that group's skills in the panel's order

#### Scenario: The master-detail changes no cast payload
- **WHEN** the player reaches a target through the category and group frames and confirms a cast
- **THEN** the emitted `combat.cast` payload is byte-identical to the payload the same skill, scale, and target produce without the master-detail

#### Scenario: The root list geometry matches its rendered order
- **WHEN** the player presses the arrow keys on the combat root
- **THEN** focus moves through the current resolver's root items in their rendered order with the vertical arrow keys, and the horizontal arrow keys move focus nowhere

#### Scenario: A single-target frame is a vertical list
- **WHEN** the player opens Attack with an ally and two foes listed as candidates
- **THEN** the target rows render in one column in the server's order, each marked as ally or foe, ArrowDown moves to the next candidate, and ArrowRight moves focus nowhere

#### Scenario: Categories and groups are vertical lists
- **WHEN** the player opens Skills with several categories, and later a category with several sub-groups
- **THEN** each frame renders one row per entry in a single column, ArrowDown moves to the next entry and wraps at the end, and ArrowRight moves focus nowhere

#### Scenario: The participant frame renders the committed session
- **WHEN** a combat session commits participants on both teams, one of them fled or knocked out
- **THEN** the participant frame renders both sides in presenter order with each participant's token, display name, current and maximum hit points, and an explicit text marker for the non-active state, and it is not reachable by sequential keyboard navigation

#### Scenario: A participant portrait comes only from the catalog
- **WHEN** a participant carries a `portrait_ref` present in the committed portrait catalog, and another carries `null`
- **THEN** the first renders that catalog entry (including its placeholder card) and the second renders no portrait, and the browser constructs no subject key or URL

#### Scenario: The forfeit confirmation is an explicit two-step panel
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, no mutation is sent, and only activating the confirm row emits one `combat.forfeit` carrying the current session identifier

#### Scenario: The forfeit warning states the consequence
- **WHEN** the forfeit confirmation screen renders
- **THEN** it is an explicit warning panel stating what forfeiting does

#### Scenario: Each root action keeps its dedicated route
- **WHEN** the player activates each entry of the preserved root inventory
- **THEN** Attack selects targets for innate `basic_attack`; Skills opens the committed
  skill categories as a bounded master-detail rather than one flat list; Items and
  Defend remain focusable but disabled with code `not_implemented`; Flee invokes the
  innate flee path; and Forfeit requires an explicit confirmation screen, retaining its
  explicit confirmation route

#### Scenario: The root is a wrapping single-column vertical list
- **WHEN** the combat root (including the recovery root) renders with more than one row
- **THEN** it renders as a single vertical icon-and-label list with one column, Up/Down
  traverse and wrap in rendered order, and Left/Right are no-ops at root

#### Scenario: The Skills row carries the committed descriptor count
- **WHEN** the root list renders the Skills row
- **THEN** it carries a neutral inline count equal to the committed descriptor count and
  omits the count at zero

#### Scenario: Deeper frames replace the root list with one active container
- **WHEN** the player opens a frame deeper than the root
- **THEN** it replaces the root list and retains one active row container

#### Scenario: Confirmation frames follow server candidate order with side markers
- **WHEN** the single-target, self, or no-target confirmation frame renders
- **THEN** it renders as the same single-column list in the server's candidate order,
  each target row marked by its side as well as its name, and the AREA frame keeps its
  token grid

#### Scenario: Root detail copy is explanatory only
- **WHEN** the detail beside a root row carries client-local explanatory copy describing
  what the command opens or does
- **THEN** it states no gameplay value, and every count it shows is derived from the
  committed descriptors

#### Scenario: The master-detail never renders uncarried fields
- **WHEN** a master-detail level renders committed entries
- **THEN** it preserves the committed panel's order exactly, does not reorder, filter,
  merge, or paginate it, and renders no badge or field the descriptor does not carry —
  in particular no out-of-combat marker, which no presenter serializes

#### Scenario: Focus stays visible in the bounded row region
- **WHEN** a frame renders or focus changes
- **THEN** the focused row is scrolled into view within the dock's bounded row region

#### Scenario: Escape pops exactly one master-detail level
- **WHEN** the player presses Escape inside the master-detail
- **THEN** exactly one of its levels pops at a time, and the subsequent scale and target
  steps are unchanged in behaviour and in payload

#### Scenario: The participant frame is display-only in the HUD island
- **WHEN** combat presents the participant frame in the HUD island area
- **THEN** it is not a row container, not a tab stop, and not part of the dock's
  composite widget; target selection remains the dock's target frame

#### Scenario: Category frames carry per-row descriptor counts
- **WHEN** the category or group frame renders its entries
- **THEN** it renders the same single-column vertical list with each row carrying its
  own descriptor count, Up/Down move between categories or groups, and Left/Right are
  no-ops there

#### Scenario: The skill frame lists descriptors beside a detail pane
- **WHEN** the player reaches the skill frame of the master-detail
- **THEN** it lists that group's descriptors, each row carrying the skill's label and
  resource cost, beside the detail pane that names the focused skill, its description,
  its cost, its target requirement, and its server-authored reason when it is
  unavailable

#### Scenario: No level ever offers a single choice
- **WHEN** the master-detail walks the category → group → skill levels
- **THEN** a category frame lists one entry per committed category group with its label
  and its own descriptor count; a group frame is shown only when that category carries
  more than one sub-group; and a category carrying exactly one sub-group opens the
  skill frame directly, so no level ever offers a single choice

#### Scenario: Participant hit points are numerals and missing art means no portrait
- **WHEN** the participant frame renders committed participants, or the art panel is
  unavailable
- **THEN** each participant shows its session token, display name, current and maximum
  hit points as numerals, and its state with an explicit text marker for any non-active
  state, and a null reference or an unavailable art panel yields no portrait at all with
  no client-constructed subject key or URL

### Requirement: Combat target selection sends one shape per TargetSpec
The browser SHALL derive target controls only from the validated skill descriptor.
NONE SHALL submit no target field. SELF SHALL display the authenticated actor binding
but submit no target field. SINGLE SHALL submit `target_ids` containing exactly one
server-provided identity. AREA SHALL let Space toggle unique server-provided candidates
and Enter submit either a nonempty explicit `target_ids` list or one mutually exclusive
approved `target_shorthand`.

#### Scenario: SELF binds without an actor field
- **WHEN** the player submits an enabled SELF skill
- **THEN** the payload contains `skill_key` and no actor, participant, target ID, or shorthand field, and the server binds the authenticated puppet

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

### Requirement: Menu target shorthands are convenience UI

The combat menu's target-selection options (`all-enemies`, `all-allies`, `all`) SHALL be presented as conveniences for constructing the target list; the underlying skills accept any explicit target their scope allows (enemy or ally for `ANY` skills), and the menu SHALL also allow explicit ally selection where the skill permits it.

#### Scenario: Menu shorthands do not restrict targeting

- **WHEN** the combat menu offers `all-enemies` for a damage skill
- **THEN** the option is a convenience expansion; selecting an explicit ally target for the same skill is equally valid and submits normally

### Requirement: Production combat actions are narrow and server-authoritative
The production action registry SHALL register exactly `combat.cast`, `combat.flee`, and
`combat.forfeit` for this delivery unit in addition to no unrelated gameplay adapter.
`combat.cast` SHALL accept only the TargetSpec-dependent exact payload forms and SHALL
reject the reserved `flee` skill key; `combat.flee` SHALL accept exactly an empty
object; and `combat.forfeit` SHALL accept exactly the current bounded session ID as a
stale-selection guard.

#### Scenario: Tampered remote target cannot enter combat resolution
- **WHEN** `combat.cast` carries a valid ObjectDB ID that is not a participant in the authenticated actor's current session
- **THEN** the adapter rejects before preflight or initiative and no state changes

#### Scenario: Flee cannot select another actor
- **WHEN** a client submits `combat.flee`
- **THEN** the adapter builds the innate SELF request for the session puppet and accepts no actor or target field

#### Scenario: Flee has only one graphical action path
- **WHEN** a modified client submits `combat.cast` with `skill_key` equal to `flee`
- **THEN** the cast adapter rejects before session submission and only the exact empty `combat.flee` action can request the innate flee path

#### Scenario: Stale Forfeit confirmation cannot end a replacement session
- **WHEN** a Forfeit payload names a session ID that no longer equals the actor's active record
- **THEN** the adapter rejects without settling or clearing the current session

#### Scenario: Adapters are session-derived and side-effect-free by hand
- **WHEN** any of the three combat adapters runs
- **THEN** it obtains the actor from the authenticated session, re-reads the active
  session, re-resolves referenced IDs from its participants, invokes a public
  combat-session API, and assigns no `.db`, traits, buffs, sexual state, location,
  quests, wallet, inventory, or battlefield members directly

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog
and terminal message through Evennia's ordinary escaped text output path. The dispatcher
SHALL then publish canonical `status`, `context_actions`, and `art` replacements at one
newer revision before sending the matching safe `ui_action_result`, so a combat result
that changes the participant roster, combat mode, or session state replaces the portrait
catalog and scene in the same `ui_update`.

#### Scenario: One combat round updates text, panels, and art
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status, combat choices, and the art catalog
  reflect committed state at one newer revision, and the dock unlocks only after that revision is
  accepted and the round's beat playback has ended

#### Scenario: A defeated or fled participant leaves the art catalog in the same revision
- **WHEN** an accepted combat action removes a participant from the session (defeat, flee, or
  terminal settlement)
- **THEN** the `art` panel at the same newer revision no longer contains that participant's catalog
  entry, and the browser never keeps a portrait for a no-longer-present entity

#### Scenario: Rejected preflight emits no fabricated combat prose
- **WHEN** current deterministic validation rejects before initiative
- **THEN** no combat EventLog is fabricated, the result contains a stable safe reason, and refreshed panel state permits another legal choice

#### Scenario: Duplicate request does not repeat a round or prose
- **WHEN** one live request ID is delivered twice
- **THEN** the adapter and combat round execute once, EventLog text is emitted once, and the duplicate receives the cached result

#### Scenario: The round's beats ride the status revision
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** the same `ui_update` that carries `status` also carries `combat_beats` for that round, and the `ui_action_result` names that revision and carries no beat, EventLog, or round-record field

#### Scenario: Ordinary rounds publish their beats panel
- **WHEN** the settled action was an ordinary round
- **THEN** the same publication also carries the `combat_beats` panel owned by the
  `webclient-combat-beats` capability, at the same revision as `status`

#### Scenario: The beats panel is the only structured round account
- **WHEN** a round's exchange is represented to the client
- **THEN** the `combat_beats` panel is the only structured account of it, and the text
  output stays the authoritative narrative

#### Scenario: Submission stays locked until presentation settles
- **WHEN** the client holds a pending combat submission
- **THEN** submission stays locked until the declared presentation revision is accepted
  and, when the client plays that publication's round beat by beat, until the round's
  playback has ended or the player has ended it, as "A combat round plays beat by beat"
  defines

#### Scenario: The browser never parses narrative prose for state
- **WHEN** combat narrative prose arrives
- **THEN** the browser does not parse it to update resources, participants, round, art,
  beats, or menu state

### Requirement: A combat round plays beat by beat
When a committed publication carries an available `combat_beats` panel whose round the
client has not presented in the current epoch, and that publication completes the
player's own `combat.cast`, `combat.flee`, or `inventory.use` action, the client SHALL
present that round as one step per beat, in the beats' order, attached to that action's
response. A round seen in any other way, including after a reconnect, SHALL NOT be
presented as steps, and no round SHALL be presented twice.

#### Scenario: A round plays one beat per page
- **WHEN** the effective level is `full` and an accepted basic attack settles a non-terminal round with a
  `roll` beat and a `damage` beat
- **THEN** the message window types the roll beat's text as a page, then after the beat pause types the
  damage beat's text as the next page, and then shows the round's closing line as the next page

#### Scenario: Displayed hit points follow the beats and snap at the end
- **WHEN** a foe at 30 hit points takes damage beats with `hp_after` 18 and then 0 in a playing round
- **THEN** the participant frame shows 30, then 18 after the first damage beat, then 0 after the
  second, and once the round ends it shows the committed value

#### Scenario: The command panel unlocks after playback and the revision
- **WHEN** the declared revision of a combat action is accepted while its round is still playing
- **THEN** the dock accepts no activation and sends no `ui_action` until the round has ended, and
  accepts the next activation once it has

#### Scenario: A click ends the round
- **WHEN** a round is playing its first of three beats and the player clicks the message window
- **THEN** the lock from playback clears at once, every displayed hit-point value equals the committed
  value, and the window shows the page after the beat pages

#### Scenario: A typed command ends the round
- **WHEN** a round is playing and the player sends a typed command
- **THEN** the round ends before the command's input line is appended, and the command's response is
  presented from its first page

#### Scenario: Reduced keeps the order and the pauses
- **WHEN** the effective level is `reduced` and a round with three beats plays
- **THEN** each beat page appears in full at once, each next beat follows after the 400ms beat pause,
  and the order equals the beats' order

#### Scenario: Off presents the beats as text pages
- **WHEN** the effective level is `off` and a round with two beats settles
- **THEN** the command panel unlocks as soon as the declared revision is accepted, and the reader turns
  one page per beat, each holding that beat's text, followed by the round's closing line

#### Scenario: The round that ends the fight plays its beats
- **WHEN** an accepted attack defeats the last foe and the full snapshot commits mode `exploration`
  with an available `combat_beats` panel
- **THEN** the mode, the exploration surfaces, and the store's view carry `exploration` at once, the
  round's beats are presented in order ending with the defeat beat, and the outcome lines follow them

#### Scenario: Without beats the round pages as text
- **WHEN** an accepted combat action's publication carries the unavailable `combat_beats` form
- **THEN** the round's narrative is paged as an ordinary response, the vitals move once to the committed
  values, and the dock unlocks when the declared revision is accepted

#### Scenario: A reconnect replays no round
- **WHEN** the client reconnects after a round has played, or reloads while a round is playing
- **THEN** no beat is presented again, the window shows the last page of the last response fully shown,
  and every displayed value is the committed value

#### Scenario: An unknown participant is text only
- **WHEN** a beat's target names no participant known to the client
- **THEN** its text is presented as its page and no displayed hit-point value changes for it

#### Scenario: The ending round presents like any round
- **WHEN** the completing publication has already committed mode `exploration` (the
  round that ends the fight)
- **THEN** that round SHALL be presented the same way, and its committed exploration
  state is not held back

#### Scenario: A beat is exactly its plain text as one page
- **WHEN** a playing round's beats are paged into the message window
- **THEN** each beat is one page holding exactly the beat's text as plain text, split
  over more pages only when it does not fit one

#### Scenario: Beat pages replace the round's own event lines
- **WHEN** a playing response is paged
- **THEN** the response's first lines, one per event log the beats name, are not paged
  again, every later line of the response (the round's closing line, a fight's outcome
  and aftermath) follows the beat pages as ordinary pages, and the log keeps every line
  unchanged

#### Scenario: Full and reduced motion play the round by itself
- **WHEN** the effective motion level is `full` or `reduced`
- **THEN** the round plays by itself: each beat page is revealed at the reader's text
  speed (instant below `full`); once fully shown, the beat's stage gesture plays as
  `webclient-contextual-hud` "Combat beats are choreographed on the stage at the motion
  level" defines, and the next beat follows after that gesture and the beat pause of the
  client's motion tokens (400ms at `full` and at `reduced`)

#### Scenario: Off never plays the round by itself
- **WHEN** the effective motion level is `off`
- **THEN** the round does not play by itself: its beat pages and the following pages are
  ordinary pages the reader turns, and presentation of the round ends at once

#### Scenario: Displayed hit points track damage beats in both surfaces
- **WHEN** a playing round damages a participant whose previous committed hit points are
  known
- **THEN** that participant displays its previous committed value until its first damage
  beat, and after each of its damage beats that beat's `hp_after`, in the vitals and in
  the participant frame

#### Scenario: Playback end snaps every value and nothing else follows the beats
- **WHEN** a round's presentation ends
- **THEN** every displayed value is the committed `status` and participant value, and no
  other resource, marker, or visibility rule follows the beats

#### Scenario: Playback lock stacks on the revision lock
- **WHEN** a round plays by itself while the declared-revision lock is also pending
- **THEN** the command panel stays locked under both, and unlocks when both have cleared

#### Scenario: Pointer or keyboard skip ends the round at once
- **WHEN** the pointer activates the message window, or the player presses Enter or
  Space on its page surface, during playback
- **THEN** the round ends at once: every displayed value becomes the committed value,
  the lock from playback clears, and the window shows the response's first page after
  the beat pages, or the last beat page fully shown when none follows

#### Scenario: Transport loss ends the round without presenting the rest
- **WHEN** a new transport generation arrives or the client detaches during playback
- **THEN** the round ends without presenting the rest

#### Scenario: The unavailable form keeps only the revision lock
- **WHEN** the completing publication carries the unavailable `combat_beats` form
- **THEN** the round is paged as its ordinary narrative response, the vitals move once
  to the committed values, and the lock is the declared-revision lock alone

#### Scenario: The presentation never touches prose, timing, or requests
- **WHEN** any part of the beat presentation runs
- **THEN** it parses no narrative prose, delays no committed value or mode, and changes
  no request

### Requirement: Reconnect rebuilds combat without replaying intent
WebSocket loss SHALL preserve the last rendered combat view under the foundation offline
overlay and lock every combat mutation. After reconnect, the first valid new-epoch
snapshot SHALL rebuild the current session ID, mode, round, participants, status,
skills, targets, and root menu from canonical persistence even when its revision is
lower than the retired epoch.

#### Scenario: Active combat reconnect resumes the same round boundary
- **WHEN** transport disconnects after a valid nonterminal round and reconnects without another game action
- **THEN** the new snapshot shows the same persisted session and round, starts at the combat root, and no additional round or world time is consumed

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending a cast but before its result is observed
- **THEN** reconnect synchronizes canonical combat state, displays the uncertain-result notice, and sends no automatic replacement cast

#### Scenario: Unreconstructable participant offers safe recovery
- **WHEN** a strictly parsed active record references a participant that can no longer be reconstructed
- **THEN** combat presentation exposes a bounded recovery state with no cast or flee action, retains confirmed Forfeit and ordinary text access, and performs no mutation while rendering

#### Scenario: Epoch hygiene on reconnect
- **WHEN** the browser reconnects into a new epoch
- **THEN** it discards old-epoch packets, restores no unsubmitted target selection as
  authority, and resubmits no uncertain prior mutation

### Requirement: Combat browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise basic attack, active skill
selection, NONE, SELF, SINGLE, AREA explicit and shorthand targeting, Flee, Forfeit
confirmation, disabled reasons, stale and duplicate submission behavior, EventLog
narrative delivery, and active-session reconnect. Tests SHALL use deterministic fixtures
and SHALL make no remote, LLM, or image-generation request.

#### Scenario: Complete target matrix passes in Chromium
- **WHEN** the required browser entry point runs against deterministic skills covering all four TargetSpec values
- **THEN** every flow completes using keyboard controls and each emitted action has its exact expected payload shape

#### Scenario: Minimum viewport retains combat essentials
- **WHEN** combat renders at the 1451x790 reference viewport with a disabled skill focused
- **THEN** the player can read narrative, numeric resources, applied modifiers, the disabled reason, and action controls without overlap preventing operation

#### Scenario: Both reference viewports keep combat usable
- **WHEN** the suite runs at 1451x790 and at 2560x1440
- **THEN** narrative, true HP/MP/SP status, applied modifier text, and the active action
  controls remain visible and usable

### Requirement: Terminal combat outcomes refresh all mode-relevant panels

A terminal combat result (victory, defeat, flee, forfeit, exam outcome) SHALL publish a full snapshot (or equivalently refresh every panel the mode change touches: exploration, character, services, local_map, status, context_actions, art), so no panel retains pre-combat or combat-stale state after the mode returns to exploration.

#### Scenario: Exploration panels are fresh after a terminal outcome

- **WHEN** a combat session ends terminally and the mode switches back to exploration
- **THEN** the exploration/character/services/local_map payloads reflect the post-settlement canonical state (defeated monster gone, current HP, settled world time)

#### Scenario: Non-terminal rounds keep partial updates

- **WHEN** an ordinary (non-terminal) combat round completes
- **THEN** the existing status/context_actions/art partial update is unchanged

### Requirement: Combat menu availability reflects handler context

A skill SHALL be marked unavailable in the combat menu when the session's `event_context` cannot supply every context key its effects require; the menu SHALL never advertise a skill that preflight would reject for missing context.

#### Scenario: Context-less skills are disabled

- **WHEN** the combat menu renders while the session context lacks disguise/dominion keys
- **THEN** `status_disguise` and `dominion_art` appear unavailable (disabled), and submitting them is rejected before initiative

### Requirement: The combat panel hides freeform casting from non-masters
A skill descriptor SHALL include a `freeform_scales` array only when the skill is
`is_freeform_eligible` and the skill-anchored `freeform_scales_for(actor, skill)` ladder
set is non-empty. The array SHALL be strictly ascending, one entry per allowed scale,
each an exact object with the numeric `scale`, that scale's canonical label, and the
server-computed scaled `mp_cost` (via `scaled_mp_cost`).

#### Scenario: A master's eligible spells advertise their unlocked scales
- **WHEN** a `wind_mastery` holder whose `wind_blade` proficiency reaches level 10 has its combat
  panel built
- **THEN** `wind_blade` carries `freeform_scales` with exactly the five entries in ascending order
  (e.g. `{scale: 0.25, label: "1/4", mp_cost: 4}`, `{scale: 0.5, label: "1/2", mp_cost: 7}`,
  `{scale: 1.0, label: "1", mp_cost: 14}`, `{scale: 2.0, label: "2", mp_cost: 28}`,
  `{scale: 4.0, label: "4", mp_cost: 56}`) and `gale_step` (ineligible) omits it

#### Scenario: A non-master's panel reveals nothing
- **WHEN** an entity without `wind_mastery` (even one with a magic level unlocking the spells) sees
  its combat panel
- **THEN** no skill descriptor contains a `freeform_scales` field, and no rendered text mentions
  scales, magnitudes, or proportional casting

#### Scenario: Mastery entitlement anchors to the cast skill
- **WHEN** the `freeform_scales` ladder for a skill is computed
- **THEN** the entitlement is anchored to the CAST skill's own proficiency — the array
  lists exactly the rungs the actor's proficiency in that skill unlocks

#### Scenario: Scale labels are canonical and never cross-paired
- **WHEN** `freeform_scales` entries carry their labels
- **THEN** the canonical labels are `1/4`, `1/2`, `1`, `2`, `4` — a label never pairs
  with any other scale

#### Scenario: The server does the rounding
- **WHEN** a scaled `mp_cost` is produced for a `freeform_scales` entry
- **THEN** it is server-computed via `scaled_mp_cost`, so the browser never performs
  rounding

#### Scenario: Every other skill omits the field entirely
- **WHEN** a skill is not freeform-eligible, or is an eligible spell of a non-master
- **THEN** its descriptor omits the `freeform_scales` field entirely

#### Scenario: The feature stays a surprise
- **WHEN** a player without the element's mastery renders any panel
- **THEN** they see no scale selector, no freeform text, and no other indication that
  scaling exists

### Requirement: The combat dock offers a scale-choice step only for masters
When the focused skill carries `freeform_scales`, the keyboard dock SHALL insert one
威力-choice menu between skill selection and target selection, listing exactly the
entries the actor's current ladder unlocks (label plus scaled `mp_cost`) in ascending
order with `1` preselected, and SHALL include the chosen numeric `scale` in the eventual
cast payload for every target form (NONE, SELF, SINGLE, and AREA, including shorthands).

#### Scenario: A master picks double power for a single-target spell
- **WHEN** the player focuses `wind_blade`, chooses 威力 `2` in the scale menu, then confirms one
  target
- **THEN** the browser submits `combat.cast` with `skill_key`, `scale: 2.0`, and the chosen
  `target_ids`, and the command echo labels the cast with the chosen magnitude

#### Scenario: A scaled AREA cast keeps the shorthand form
- **WHEN** the player chooses scale `1/2` and then the `all-enemies` shorthand for an eligible AREA
  spell
- **THEN** one request carries `skill_key`, `scale: 0.5`, and `target_shorthand: "all-enemies"` and
  no target-ID field

#### Scenario: Non-masters keep today's exact flow
- **WHEN** any player focuses any skill that lacks `freeform_scales`
- **THEN** no scale step appears, and the emitted payload contains no `scale` field, identical to
  the pre-change payloads

#### Scenario: Scale-menu keys match the dock
- **WHEN** the 威力-choice menu is open
- **THEN** arrow keys navigate, Enter confirms the choice and opens the target flow, and
  Escape pops back to the skill list

#### Scenario: The chosen scale rides the shared selection state
- **WHEN** a panel replacement rebuilds the dock's client-local selection state
- **THEN** the chosen scale lives in that same state: a still-valid choice is preserved,
  and an invalidation resets deterministically to `1`

#### Scenario: Skills without scales keep byte-identical flows
- **WHEN** a skill without `freeform_scales` is focused
- **THEN** the scale step is skipped entirely, and the flow and payload for every
  existing skill are byte-identical to today

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
