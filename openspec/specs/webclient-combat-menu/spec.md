## Purpose

Exact combat context actions panel, keyboard menu, allowlisted combat adapters, shared side-effect-free availability, EventLog delivery, and active-combat reconnect for the browser WebClient, with full Telnet parity.

## Requirements

### Requirement: Combat context actions are an exact read-only panel
The production presentation registry SHALL register `context_actions` schema version 5. For a valid active combat session, its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, `skills`, and `suggestions`; `available` SHALL be true, `kind` SHALL be `combat`, and `suggestions` SHALL be exactly `{"status": "unavailable"}`. `session` SHALL contain exactly `session_id`, `mode`, `round`, `state`, and `reason`: session ID SHALL be bounded, mode SHALL be `hostile` or `guild_exam`, round SHALL be a non-negative safe integer, state SHALL be `ready` or `recovery`, and reason SHALL be null or an exact object containing stable code and safe Traditional Chinese message. A ready session SHALL have a null reason; a recovery session SHALL have a non-null reason, no cast/flee action, and one confirmed Forfeit descriptor when its record is strictly parsed. The presenter SHALL strictly read and reconstruct the authenticated puppet's current `CombatSessionRecord`, SHALL preserve persisted participant order, SHALL emit no live object or filesystem reference, and SHALL NOT mutate traits, resources, buffs, sexual state, battlefield state, session state, quests, location, or world time. **Outside a valid active combat session the combat form SHALL never be emitted** — the panel instead emits the exploration available form owned by the `webclient-context-actions` capability (in exploration mode) or the registered common unavailable form (creation-pending or absent location); it SHALL never fabricate combat-shaped fields, and it SHALL never fabricate exploration actions in a combat session.

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

### Requirement: Availability uses shared side-effect-free rules preview
The combat presenter, Telnet action listing, and combat adapters SHALL consume the same deterministic preview boundary. Availability SHALL include ownership and active kind, resources, exact target shape, presence/alive/range/faction candidate checks, action capability including `actions_per_turn == 0`, effect-handler availability, and time metadata. Preview state is advisory; every submitted action SHALL repeat authoritative validation against current canonical state before initiative.

#### Scenario: Preview and adapter agree on a disabled skill
- **WHEN** a skill is displayed as disabled because SP is insufficient and a modified client nevertheless submits it at the current presentation revision
- **THEN** the adapter rejects with the matching stable rule reason before initiative, no NPC acts, and round count and world time remain unchanged

#### Scenario: State can change after a valid preview
- **WHEN** a skill was enabled in revision N but canonical target state changes before its revision-N submission is admitted
- **THEN** current domain validation rejects or filters it according to target rules without trusting the earlier descriptor

### Requirement: The combat action dock follows the approved keyboard hierarchy
In combat mode the action root SHALL present Attack, Skills, Items, Defend, and Flee in that stable order, with confirmed Forfeit under a secondary menu. Attack SHALL select targets for innate `basic_attack`; Skills SHALL open the committed skill categories as a bounded master-detail rather than one flat list; Items and Defend SHALL remain focusable but disabled with code `not_implemented`; Flee SHALL invoke the innate flee path; and Forfeit SHALL require an explicit confirmation screen. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop one level, and disabled entries SHALL send no packet.

The root SHALL render as a single row of icon-and-label tabs and SHALL declare a column count equal to its item count — including the recovery state, whose root is the confirmed Forfeit path alone — so the horizontal arrow keys traverse the tabs in their rendered order and the vertical arrow keys are a no-op on the root. The Skills tab SHALL carry a count badge equal to the flattened count of skill descriptors the committed panel actually lists.

The skill master-detail SHALL be: a category frame listing one entry per committed category group with its label and its own descriptor count; then, only when that category carries more than one sub-group, a group frame listing its sub-groups; then the skill frame listing that group's descriptors, each row carrying the skill's label and resource cost, beside the detail pane that names the focused skill, its description, its cost, its target requirement, and its server-authored reason when it is unavailable. A category carrying exactly one sub-group SHALL open the skill frame directly, so no level ever offers a single choice. Every level SHALL preserve the committed panel's order exactly and SHALL NOT reorder, filter, merge, or paginate it, and SHALL NOT render a badge or field the descriptor does not carry — in particular no out-of-combat marker, which no presenter serializes. The focused row SHALL be scrolled into view within the dock's bounded row region on every frame render and focus change. Escape SHALL pop exactly one of these levels at a time, and the subsequent scale and target steps SHALL be unchanged in behaviour and in payload.

Combat SHALL additionally present a display-only participant frame in the HUD island area, grouping the committed participants into the player's side and the opposing side in presenter order, each showing its session token, display name, current and maximum hit points as numerals, and its state with an explicit text marker for any non-active state. Each participant's portrait SHALL be resolved only by looking its server-authored `portrait_ref` up in the committed art panel's portrait catalog, with no client-constructed subject key or URL and no portrait at all for a null reference or an unavailable art panel. The frame SHALL NOT be a row container, a tab stop, or part of the dock's composite widget; target selection remains the dock's target frame.

The Forfeit confirmation SHALL render as an explicit warning panel stating what forfeiting does, with a cancel row and a confirm row; only the confirm row SHALL submit, carrying the current session identifier.

#### Scenario: Basic attack completes without typed input
- **WHEN** a player uses only arrows and Enter to choose Attack and one valid enemy
- **THEN** the browser submits `combat.cast` for `basic_attack` exactly once and the ordinary combat-session path resolves the result

#### Scenario: Placeholder mechanics cannot be invoked
- **WHEN** the player focuses Items or Defend and presses Enter
- **THEN** its `not_implemented` explanation remains readable and no `ui_action` message is emitted

#### Scenario: Forfeit requires confirmation
- **WHEN** the player opens the secondary Forfeit entry but has not confirmed
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

#### Scenario: The root tab geometry matches its rendered order
- **WHEN** the player presses the horizontal arrow keys on the combat root
- **THEN** focus moves through Attack, Skills, Items, Defend, Flee, and Forfeit in their rendered order, and the vertical arrow keys move focus nowhere

#### Scenario: The participant frame renders the committed session
- **WHEN** a combat session commits participants on both teams, one of them fled or knocked out
- **THEN** the participant frame renders both sides in presenter order with each participant's token, display name, current and maximum hit points, and an explicit text marker for the non-active state, and it is not reachable by sequential keyboard navigation

#### Scenario: A participant portrait comes only from the catalog
- **WHEN** a participant carries a `portrait_ref` present in the committed portrait catalog, and another carries `null`
- **THEN** the first renders that catalog entry (including its placeholder card) and the second renders no portrait, and the browser constructs no subject key or URL

#### Scenario: The forfeit confirmation is an explicit two-step panel
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, no mutation is sent, and only activating the confirm row emits one `combat.forfeit` carrying the current session identifier

### Requirement: Combat target selection sends one shape per TargetSpec
The browser SHALL derive target controls only from the validated skill descriptor. NONE SHALL submit no target field. SELF SHALL display the authenticated actor binding but submit no target field. SINGLE SHALL submit `target_ids` containing exactly one server-provided identity. AREA SHALL let Space toggle unique server-provided candidates and Enter submit either a nonempty explicit `target_ids` list or one mutually exclusive approved `target_shorthand`. Focus and selection SHALL remain client-local until submission, and a panel replacement SHALL remove vanished selections and restore the nearest surviving focus in deterministic order.

#### Scenario: SELF binds without an actor field
- **WHEN** the player submits an enabled SELF skill
- **THEN** the payload contains `skill_key` and no actor, participant, target ID, or shorthand field, and the server binds the authenticated puppet

#### Scenario: AREA multi-selection is explicit and unique
- **WHEN** the player toggles two valid AREA candidates with Space and confirms
- **THEN** one request carries those two distinct server-provided IDs in presenter order and carries no shorthand

#### Scenario: AREA shorthand is mutually exclusive
- **WHEN** the player chooses the server-authored `all-enemies` descriptor
- **THEN** one request carries that shorthand and no target-ID field

### Requirement: Menu target shorthands are convenience UI

The combat menu's target-selection options (`all-enemies`, `all-allies`, `all`) SHALL be presented as conveniences for constructing the target list; the underlying skills accept any explicit target their scope allows (enemy or ally for `ANY` skills), and the menu SHALL also allow explicit ally selection where the skill permits it.

#### Scenario: Menu shorthands do not restrict targeting

- **WHEN** the combat menu offers `all-enemies` for a damage skill
- **THEN** the option is a convenience expansion; selecting an explicit ally target for the same skill is equally valid and submits normally

### Requirement: Production combat actions are narrow and server-authoritative
The production action registry SHALL register exactly `combat.cast`, `combat.flee`, and `combat.forfeit` for this delivery unit in addition to no unrelated gameplay adapter. `combat.cast` SHALL accept only the TargetSpec-dependent exact payload forms and SHALL reject the reserved `flee` skill key; `combat.flee` SHALL accept exactly an empty object; and `combat.forfeit` SHALL accept exactly the current bounded session ID as a stale-selection guard. Every adapter SHALL obtain the actor from the authenticated session, re-read the active session, re-resolve referenced IDs from its participants, invoke a public combat-session API, and SHALL NOT assign `.db`, traits, buffs, sexual state, location, quests, wallet, inventory, or battlefield members directly.

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

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog and terminal
message through Evennia's ordinary escaped text output path. The dispatcher SHALL then publish
canonical `status`, `context_actions`, and `art` replacements at one newer revision before sending
the matching safe `ui_action_result`, so a combat result that changes the participant roster, combat
mode, or session state replaces the portrait catalog and scene in the same `ui_update`. The browser
SHALL keep submission locked until that declared presentation revision is accepted. It SHALL NOT
parse narrative prose to update resources, participants, round, art, or menu state.

#### Scenario: One combat round updates text, panels, and art
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status, combat choices, and the art catalog
  reflect committed state at one newer revision, and the dock unlocks only after that revision is
  accepted

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

### Requirement: Reconnect rebuilds combat without replaying intent
WebSocket loss SHALL preserve the last rendered combat view under the foundation offline overlay and lock every combat mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild the current session ID, mode, round, participants, status, skills, targets, and root menu from canonical persistence even when its revision is lower than the retired epoch. The browser SHALL discard old-epoch packets, SHALL NOT restore an unsubmitted target selection as authority, and SHALL NOT resubmit an uncertain prior mutation.

#### Scenario: Active combat reconnect resumes the same round boundary
- **WHEN** transport disconnects after a valid nonterminal round and reconnects without another game action
- **THEN** the new snapshot shows the same persisted session and round, starts at the combat root, and no additional round or world time is consumed

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending a cast but before its result is observed
- **THEN** reconnect synchronizes canonical combat state, displays the uncertain-result notice, and sends no automatic replacement cast

#### Scenario: Unreconstructable participant offers safe recovery
- **WHEN** a strictly parsed active record references a participant that can no longer be reconstructed
- **THEN** combat presentation exposes a bounded recovery state with no cast or flee action, retains confirmed Forfeit and ordinary text access, and performs no mutation while rendering

### Requirement: Combat browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise basic attack, active skill selection, NONE, SELF, SINGLE, AREA explicit and shorthand targeting, Flee, Forfeit confirmation, disabled reasons, stale and duplicate submission behavior, EventLog narrative delivery, and active-session reconnect. At 1440x900 and 1280x720, narrative, true HP/MP/SP status, applied modifier text, and the active action controls SHALL remain visible and usable. Tests SHALL use deterministic fixtures and SHALL make no remote, LLM, or image-generation request.

#### Scenario: Complete target matrix passes in Chromium
- **WHEN** the required browser entry point runs against deterministic skills covering all four TargetSpec values
- **THEN** every flow completes using keyboard controls and each emitted action has its exact expected payload shape

#### Scenario: Minimum viewport retains combat essentials
- **WHEN** combat renders at 1280x720 with a disabled skill focused
- **THEN** the player can read narrative, numeric resources, applied modifiers, the disabled reason, and action controls without overlap preventing operation

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
`is_freeform_eligible` and the skill-anchored `freeform_scales_for(actor, skill)` ladder set is
non-empty (mastery entitlement anchored to the CAST skill's own proficiency — the array lists
exactly the rungs the actor's proficiency in that skill unlocks). The array SHALL be strictly
ascending, exactly one entry
per allowed scale, each entry an exact object containing the numeric `scale`, the canonical label of that scale
(`1/4`, `1/2`, `1`, `2`, `4` — a label never pairs with any other scale), and the server-computed
scaled `mp_cost` (via `scaled_mp_cost`, so the browser never performs rounding). Every other
skill — including eligible spells of a non-master — SHALL omit the field
entirely. The feature is deliberately a surprise: a player without the element's mastery SHALL see
no scale selector, no freeform text, and no other indication that scaling exists in any rendered
panel.

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

### Requirement: The combat dock offers a scale-choice step only for masters
When the focused skill carries `freeform_scales`, the keyboard dock SHALL insert one 威力-choice
menu between skill selection and target selection, listing exactly the entries the actor's current
ladder unlocks (label plus scaled `mp_cost`) in ascending order with `1` preselected, and SHALL include the chosen numeric `scale` in the
eventual cast payload for every target form (NONE, SELF, SINGLE, and AREA, including shorthands).
Arrow keys SHALL navigate, Enter SHALL confirm the choice and open the target flow, and Escape SHALL
pop back to the skill list. The chosen scale SHALL live in the same client-local selection state the
dock already rebuilds after a panel replacement: a still-valid choice is preserved, and an
invalidation resets deterministically to `1`. A skill without `freeform_scales` SHALL skip the step
entirely, so the flow and payload for every existing skill are byte-identical to today.

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
