## Purpose

The read-only version-1 `exploration` panel and version-1 `character` panel, the eight exact allowlisted exploration adapters, the free-form dialogue composition root with offline degrade, the keyboard-first exploration dock that re-homes the service submenus, minimap movement submission, the client-local portrait-focus seam, and the Node/browser acceptance boundary.

## Requirements

### Requirement: The exploration panel is an exact read-only version-1 presentation panel
The production presentation registry SHALL register panel name `exploration` at schema version 1. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `move`, `look`, `interact`, `character`, `quests`, and `inventory`; `available` SHALL be true and `kind` SHALL be `exploration`. `move` SHALL be a bounded list of at most 12 exit descriptors, each containing exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`, where `exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses, `label` is a bounded localized direction/exit label, `destination` is the canonical destination node ID, and `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the actor's location (a locked or absent exit is a disabled row, never omitted, so the player learns it exists). `look` SHALL contain exactly `room`, `entities`, and `objects`: `room` is an exact room descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32 present character/NPC/monster descriptors each carrying an opaque identity, bounded display name, bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32 present object descriptors carrying an opaque identity and bounded display name. `interact` SHALL be a bounded list of at most 32 present target descriptors, each carrying exactly `identity`, `display_name`, nullable `portrait_ref`, a bounded `affordances` list of at most 8 descriptors, and — only for a scripted dialogue host — a bounded `keywords` list of at most 16 scripted keyword descriptors. An action affordance SHALL contain exactly `kind` (`"action"`), `action_id` (one of `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`), `label`, `enabled`, and nullable `disabled_reason`. A navigation affordance SHALL contain exactly `kind` (`"navigate"`), `surface` (one of `"guild"` or `"shop"`), `label`, `enabled`, and nullable `disabled_reason`. Navigation affordances are dock-navigation descriptors only — they are NOT registered action adapters, never enter a `ui_action` payload, and only tell the browser to open the corresponding `services` submenu. `character`, `quests`, and `inventory` SHALL each be availability entries with exactly `available` (boolean): `character` SHALL be available in exploration mode, and `quests`/`inventory` SHALL be available only when the `services` panel is registered and available. The presenter SHALL build the payload only from canonical room, entity, component, object, and service data, SHALL emit no live object or filesystem reference, SHALL NOT mutate location, traits, knowledge, dialogue, quests, inventory, or world time, and SHALL use the registered common unavailable form outside exploration mode.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `exploration` reports `kind == "exploration"`, the current Exits in `move`, the present room/entities/objects in `look`, and the present interact targets with their legal affordances, while a before/after comparison of canonical game state is unchanged

#### Scenario: Combat and creation do not receive fabricated exploration
- **WHEN** the active puppet is in an active combat session or is creation-pending
- **THEN** `exploration` uses its schema-valid unavailable form and contains no exit, entity, object, or affordance row

#### Scenario: A locked exit is disclosed but disabled
- **WHEN** the current room has an exit that exists but the actor cannot traverse
- **THEN** `move` contains that exit as a disabled row with a stable reason and no `explore.move` can succeed through it

#### Scenario: Quests and inventory respect the services capability
- **WHEN** the `services` panel is registered and available in exploration mode
- **THEN** `quests` and `inventory` are available; when the services capability is absent, both are unavailable and the dock shows no dead functional entry

#### Scenario: Presenter failure remains isolated
- **WHEN** the `exploration` presenter raises while status and narrative remain healthy
- **THEN** only `exploration` becomes correlated unavailable and normal text output remains usable

### Requirement: Exploration affordances are server-authored, never inferred from prose
Every `interact` affordance SHALL be derived from canonical data with the same checks commands use, never from typeclass names, display prose, or other heuristics. `explore.talk_scripted` SHALL be offered only for a present NPC with a resolved dialogue component (`OnboardingGuide` or `ScriptedDialogue`); the target descriptor then SHALL carry a bounded list of at most 16 scripted keyword descriptors (each exactly `keyword_id` and bounded `label`) derived from the dialogue table registry, and the talk_scripted affordance itself SHALL carry no keyword list (the scripted buttons live on the target so the interact payload stays within the protocol's global JSON-depth bound). `explore.talk_freeform` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`). `explore.party_invite` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`) that is not already a companion of the actor, SHALL be enabled when the actor's party has fewer than 4 companions and disabled with the full-party reason otherwise, and SHALL never be offered for an already-bound companion (the leave affordance covers it). `explore.party_leave` SHALL be offered only for a present NPC that is currently a bound companion of the actor. `explore.engage` SHALL be offered only for a present living hostile `Monster` when the actor has no active combat session. A `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`) SHALL be offered only when the current room has exactly one unambiguous `GuildStaff` or `Merchant` host for a service the actor can use, and it opens the corresponding services submenu rather than inventing a mutation. No affordance SHALL reference a remote, absent, or ambiguous host or target. Every adapter SHALL re-verify at commit time, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition — so a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any onboarding, memory, intent, party, session, or time state changes.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords
- **THEN** its interact descriptor offers `explore.talk_scripted` with exactly those two keyword buttons and no free-form affordance

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room
- **THEN** its interact descriptor offers `explore.talk_freeform` and, when it also carries a scripted component, the scripted affordance as well

#### Scenario: An unbound generative NPC offers an invite
- **WHEN** a present `LLMNPC` is not a companion of the actor and the party has room
- **THEN** its interact descriptor offers `explore.party_invite` enabled; with four companions already the affordance is disabled with the full-party reason

#### Scenario: A bound companion offers leave instead of invite
- **WHEN** a present NPC is currently a companion of the actor
- **THEN** its interact descriptor offers `explore.party_leave` and never an `explore.party_invite`

#### Scenario: A living hostile monster offers engage
- **WHEN** a present living `Monster` is in the room and the actor has no active session
- **THEN** its interact descriptor offers `explore.engage`; an already-engaged actor receives no engage affordance

#### Scenario: No affordance is fabricated for a plain NPC
- **WHEN** a present NPC carries neither a dialogue component nor an eligible free-form surface nor a party binding
- **THEN** its interact descriptor contains no talk, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

### Requirement: The character panel is an exact read-only version-3 panel
The production presentation registry SHALL register panel name `character` at schema version 3. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `traits`, `actives`, `passives`, `equipment`, `disguise`, `guild`, `wallet`, and `persona`; `available` SHALL be true and `kind` SHALL be `character`. `traits` SHALL be a bounded list of at most 32 rows, each containing exactly `key`, `label`, `current`, and nullable `max`, derived from canonical trait values (gauges report current and maximum; static traits report the base value). `actives` and `passives` SHALL each be an ordered, category-grouped list of skills owned through `SkillHandler.owned_keys()`, filtered to `SkillKind.ACTIVE` and `SkillKind.PASSIVE` respectively — never read from raw imported-skill storage — with the exact grouped shape and ordering defined by this capability's skill-grouping requirement below. `equipment` SHALL be a bounded list of at most 32 rows, each with exactly `slot`, `item_key`, and bounded `display_name`, derived from canonical equipment state. `disguise` SHALL contain exactly `active` (boolean), `description` (bounded string), and a bounded list of at most 32 `displayed` rows, each with exactly `key`, `label`, and `value`, describing the outwardly displayed values when `disguise_active` is true and empty otherwise; it SHALL NEVER substitute disguised values for true traits. `guild` SHALL contain exactly `rank` (nullable rank key) and `merit` (non-negative safe integer). `wallet` SHALL be a non-negative safe integer of copper. `persona` SHALL contain exactly `background` (a nullable bounded string from the character's persona record, omitted content rendered as `null`); the section is display-only and is never used to infer any mechanical value. The presenter SHALL strictly read canonical records and registries through the no-mutation status/service read models — sharing the same canonical trait/equipment/disguise source the compact `status` panel builds from, so the two panels never diverge — SHALL emit no live object reference, SHALL NOT mutate traits, equipment, disguise, guild, wallet, persona, or world time, and SHALL use the common unavailable form outside exploration mode.

#### Scenario: Expanded state shows true values and an honest disguise
- **WHEN** an elf with active disguise opens the Character root
- **THEN** `traits` report the true values, `disguise` lists the displayed values with `active == true`, and no trait row substitutes a disguised value for a true one

#### Scenario: Undisguised actor has an empty displayed list
- **WHEN** an actor has no active disguise
- **THEN** `disguise.active` is false, `displayed` is empty, and the panel still reports true traits, actives, passives, equipment, guild rank, wallet, and the persona background

#### Scenario: The panel reports the player's own background
- **WHEN** an active character's persona record carries a non-empty `background`
- **THEN** `persona.background` equals that text verbatim and the panel renders it as a display-only row

#### Scenario: A character without a background reports null
- **WHEN** an active character has no persona record or no background key
- **THEN** `persona.background` is `null` and no placeholder text is rendered

#### Scenario: Character panel stays read-only
- **WHEN** the character panel is built for a fully-progressed actor
- **THEN** traits, actives, passives, equipment, disguise, guild, wallet, persona, and world time are byte-for-byte unchanged

### Requirement: Character panel skills are grouped by category with the same ordering rule as the combat panel
Each of `actives` and `passives` SHALL be an ordered array of category groups, structurally identical
in shape to `context_actions`'s `skills` field: each category group SHALL contain the category's
stable key, a bounded display label, and an ordered array of one or more sub-groups; each sub-group
SHALL contain a nullable group key, a label that is non-null exactly when the group key is non-null,
and an ordered array of `{key, label}` skill rows, each bounded the same as the prior version's
passive-row bounds. Category ordering SHALL follow `SkillCategory`'s declaration order; sub-group
ordering within `elemental_magic` SHALL follow `ELEMENT_REGISTRY`'s declaration order. A category with
zero owned skills of that kind (active or passive) SHALL be omitted from the corresponding array
entirely; a category whose skills carry no `group` SHALL emit exactly one sub-group with a `null`
group key and label. Within each sub-group, skill rows SHALL be ordered as `SkillHandler.owned_keys()`
returns them, without alphabetical reordering. The total count of skill rows across every category
and sub-group, flattened, SHALL NOT exceed 32 for `passives` and SHALL NOT exceed 32 for `actives`,
tracked as independent bounds; these bounds apply to the flattened totals, not to the count of
top-level category-group entries in either array, which is separately bounded by the number of
`SkillCategory` members plus exactly one — the extra slot carrying the presentation-only synthetic
fallback group (category `"unknown"`) for keys absent from `SKILL_REGISTRY`, so an entity owning
skills in every real category plus one unregistered key still renders.

#### Scenario: Innate active skills are visible for the first time
- **WHEN** the character panel is built for a freshly created character with no imported skill data
- **THEN** `actives` contains a `movement` category group whose one sub-group lists `flee`, and a
  `martial_arts` category group whose one sub-group lists `basic_attack` — both previously absent from
  every out-of-combat listing

#### Scenario: Category ordering matches the combat panel's rule
- **WHEN** an entity owns skills from `movement` and `elemental_magic` only
- **THEN** the `actives` array lists the `elemental_magic` category group before the `movement`
  category group, matching `SkillCategory`'s declaration order

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

### Requirement: explore.move traverses a re-resolved Exit through the shared movement path
The production action registry SHALL register `explore.move`. Its payload SHALL accept exactly `exit_ref` (1..64 ASCII characters) and `current_node` (a canonical node ID). The adapter SHALL obtain the actor from the authenticated session, verify the actor's current node ID equals `current_node` (the stale guard), re-resolve the Exit from the actor's location by the opaque `exit_ref`, re-check that the Exit's location is the actor's location and that its destination exists, re-check the `traverse` lock against the actor, and then invoke the Exit's own traversal method so `MovementCostMixin.at_post_traverse` charges the shared `CLOCK_YAML["command_defaults"]["move"]` cost and records the destination node through `record_arrival`. The adapter SHALL NOT relocate the actor directly, SHALL NOT accept a destination room ID, SHALL NOT charge time itself, and SHALL NOT assign location, knowledge, or clock state directly. A missing exit, a wrong node guard, a denied lock, or an active combat session (the `at_pre_move` veto) SHALL reject with a stable code and Traditional Chinese message and SHALL NOT advance the clock or record discovery. On success the adapter SHALL publish a full snapshot at one newer revision so the location change, clock charge, map, header, and shop/quest state refresh together.

#### Scenario: Keyboard movement charges the same 30 seconds as the command path
- **WHEN** an actor submits `explore.move` with a valid `exit_ref` and matching `current_node` for a traversable exit
- **THEN** the Exit traverses, `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, the actor's location is the destination, the destination node is recorded, and the snapshot reflects the new location

#### Scenario: A stale current_node guard performs no traversal
- **WHEN** an actor submits `explore.move` with a `current_node` that no longer matches the actor's location
- **THEN** the adapter rejects before any traversal, no time is charged, no knowledge is recorded, and the actor's location is unchanged

#### Scenario: A missing or locked exit rejects without charging
- **WHEN** an actor submits an `exit_ref` that is absent from the actor's room or whose `traverse` lock denies the actor
- **THEN** the adapter rejects with a stable reason, `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded

#### Scenario: Combat blocks menu movement
- **WHEN** an actor in an active combat session submits `explore.move`
- **THEN** the `at_pre_move` veto rejects the traversal, no time is charged, and no knowledge is recorded

### Requirement: explore.look reuses the command appearance path and preserves onboarding look hooks
The production action registry SHALL register `explore.look`. Its payload SHALL accept exactly one of `room` (the exact boolean true) or `target_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve `target_id` against the actor's current location's present contents when given — never from a stored, remote, or ambiguous reference — and re-verify presence and ordinary display/access rules, and route the look through the same appearance path the `look` command uses — for the room marker, `PlayerCharacter.at_look(actor.location)`, and for a target, the ordinary target display path — so the `PlayerCharacter.at_look` onboarding look-hook still advances the arrival beat. The adapter SHALL present the returned appearance through the escaped text output path, SHALL NOT parse the text to infer state, SHALL NOT mutate traits, knowledge, location, or time, and SHALL publish no panel replacement beyond the ordinary result. A missing, remote, unpermitted, or no-longer-present target SHALL reject with a stable code and message and SHALL NOT advance onboarding.

#### Scenario: Looking at the room advances the onboarding look beat
- **WHEN** an onboarding actor at the South Gate submits `explore.look` with the room marker
- **THEN** the actor receives the room appearance text and the guidance continuation, and `first_arrival_seen`/`onboarding_beat` advance exactly as the `look` command would

#### Scenario: Looking at a present entity uses ordinary display rules
- **WHEN** an actor submits `explore.look` with a present target's `target_id`
- **THEN** the actor receives that entity's ordinary appearance text and no canonical state changes

#### Scenario: A tampered target cannot be inspected
- **WHEN** an actor submits `explore.look` with a `target_id` that is not present or not permitted
- **THEN** the adapter rejects with a stable reason, no appearance is emitted, and no onboarding state changes

### Requirement: explore.talk_scripted invokes the deterministic dialogue API with keyword buttons
The production action registry SHALL register `explore.talk_scripted`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `keyword_id` (a 1..64-character non-empty string). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and re-verify presence, a resolved dialogue component, and the keyword's presence in the host's dialogue table, and then call `world.rules.onboarding.talk_response(npc, actor, keyword_id)` — the same deterministic API the `talk` command uses — so an `OnboardingGuide` host records the seen keyword and a `ScriptedDialogue` host answers without state change. The adapter SHALL present the authored response through the escaped text path, SHALL NOT invent a response, and SHALL NOT assign dialogue, guide, or component state directly. A missing NPC, a no-longer-present NPC, a non-host, an unregistered keyword, or a present-but-unreachable NPC SHALL reject with a stable code and message and SHALL NOT write guide state.

#### Scenario: Scripted keyword buttons match authored behavior
- **WHEN** an actor submits `explore.talk_scripted` for a present dialogue host with a registered keyword
- **THEN** the player receives the authored response, and a guard host records the keyword on `guide_progress` exactly as `talk` would

#### Scenario: An unregistered keyword rejects without writing
- **WHEN** an actor submits a `keyword_id` absent from the host's dialogue table
- **THEN** the adapter rejects with a stable reason, no response is fabricated, and no guide state is written

#### Scenario: A no-longer-present NPC rejects before any dialogue API
- **WHEN** an actor submits `explore.talk_scripted` for an NPC that was present at render but has since left the room
- **THEN** the adapter re-resolves the NPC from the actor's current location, rejects with a stable reason before calling `talk_response`, and no guide progress, memory, or component state changes

### Requirement: explore.talk_freeform runs the guarded dialogue seam through an injected client
The production action registry SHALL register `explore.talk_freeform`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `speech` (a non-empty string of at most 512 code points). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and re-verify presence and free-form eligibility (an `LLMNPC`), obtain the `npc_dialogue` profile client from the exploration composition root (a live `OpenAICompatClient` when the profile is enabled, or a non-`None` offline stub when disabled — the stub is never called because the guardrail degrades before any transport work), and run `npc.at_talked_to(speech, actor, client)`. The seam SHALL present the reply or the degraded authored greeting/silence through the escaped text path, record chat memory, and route any verified intent through the deterministic applier; an illegal or unverifiable AI intent SHALL be discarded while the speech is kept. The adapter SHALL return a Deferred that resolves to a safe success result after the seam settles, SHALL publish a full snapshot at one newer revision so any applied intent (including a `request_guild_exam` mode change) refreshes atomically, and SHALL NOT assign memory, intent, guild, quest, inventory, or combat state directly. A missing, no-longer-present, or non-eligible NPC SHALL reject synchronously with a stable code before any client or transport work. With the LLM entirely offline the action SHALL still complete through the authored greeting or silence with no network request and no state change beyond the permitted degrade path.

#### Scenario: Free-form dialogue retains its server-held target
- **WHEN** an actor submits `explore.talk_freeform` for a present `LLMNPC` with bounded speech
- **THEN** the seam runs `at_talked_to` with the injected client, the reply (or degraded greeting/silence) is presented, memory is recorded, and a verified intent is applied through the deterministic applier

#### Scenario: Offline free-form dialogue degrades to greeting or silence
- **WHEN** the `npc_dialogue` profile is disabled or unreachable and the actor submits `explore.talk_freeform`
- **THEN** the player receives the authored greeting or silence, no network request is made, and no unintended state changes

#### Scenario: An illegal AI intent is discarded while the speech is kept
- **WHEN** the guarded pipeline resolves a reply whose intent the deterministic applier cannot verify
- **THEN** the speech is presented, the intent is discarded, and no guild, quest, inventory, or combat state changes

#### Scenario: A tampered NPC ID is rejected before any client work
- **WHEN** an actor submits `explore.talk_freeform` with an `npc_id` that is not a present eligible `LLMNPC`
- **THEN** the adapter rejects with a stable reason and the injected client is never invoked

### Requirement: Freeform-talk completion rechecks presence before applying intents

The freeform-talk adapter SHALL re-run the co-location and interactability checks when the deferred reply settles, before any intent application, and SHALL return a clear stale-completion result when the checks fail.

#### Scenario: Deferred reply after the player moved is discarded
- **WHEN** the player sends freeform talk and moves away before the reply arrives
- **THEN** the adapter shows the speech, discards the intent, and reports the stale context to the player

### Requirement: explore.party_invite proposes a party through the guarded dialogue seam
The production action registry SHALL register `explore.party_invite`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `message` (a string of at most 512 code points, possibly empty). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — re-verify presence, free-form eligibility (an `LLMNPC`), no existing binding, and a party below the 4-companion bound, obtain the `npc_dialogue` profile client from the exploration composition root (a live `OpenAICompatClient` when the profile is enabled, or a non-`None` offline stub when disabled — the stub is never called because the guardrail degrades before any transport work), and run `npc.run_npc_exchange(message, actor, client)`. On the degraded terminal the adapter SHALL apply the fixed threshold decision (`affinity >= 70`) with deterministic accept/reject lines; otherwise it SHALL present the reply's speech and route the reply's intent through `apply_npc_intent`, rendering the join, refusal, full-party, duplicate, and remote notifications with the same fixed Traditional Chinese messages the `invite` command uses, and SHALL never override an AI decision with the threshold. The adapter SHALL return a Deferred that resolves to a safe success result after the seam settles, SHALL publish a full snapshot at one newer revision so the applied membership binding refreshes atomically, and SHALL NOT assign memory, intent, party, or affinity state directly. A missing, no-longer-present, non-eligible, already-bound NPC or a full party SHALL reject synchronously with a stable code before any client or transport work.

#### Scenario: An invited generative NPC joins through the webclient
- **WHEN** an actor submits `explore.party_invite` for a present unbound `LLMNPC` and the dialogue reply carries `party_invite` with `accept: true`
- **THEN** the NPC's speech is shown, `join_party` binds the companion, and the actor receives the join notification

#### Scenario: Offline webclient invites fall back to the fixed threshold
- **WHEN** the `npc_dialogue` profile is disabled or unreachable and the actor submits `explore.party_invite`
- **THEN** the invitation accepts on `affinity >= 70` with a deterministic acceptance line and rejects below it, with no network request

#### Scenario: A full party blocks the webclient invite before the AI call
- **WHEN** an actor with 4 companions submits `explore.party_invite`
- **THEN** the adapter rejects synchronously with the full-party reason and the dialogue seam is never invoked

### Requirement: explore.party_leave dismisses a bound companion without affinity change
The production action registry SHALL register `explore.party_leave`. Its payload SHALL accept exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — re-verify that the NPC is currently a bound companion, and dismiss it through `world/rules/party.py::leave_party(npc, actor, reason="dismissed")`. Dismissal SHALL NOT change affinity in either direction, SHALL notify the actor with the fixed Traditional Chinese dismissal message shared with the `leave` command, SHALL publish a full snapshot at one newer revision, and SHALL NOT assign party or affinity state directly. A missing, no-longer-present, or unbounded NPC SHALL reject synchronously with a stable code and no state change.

#### Scenario: Webclient dismissal removes the binding
- **WHEN** an actor submits `explore.party_leave` for a present bound companion
- **THEN** the binding is removed through `leave_party(reason="dismissed")`, affinity is unchanged, and the actor receives the dismissal notification

#### Scenario: A webclient leave on an unbounded target rejects
- **WHEN** an actor submits `explore.party_leave` for a present NPC that is not a companion
- **THEN** the adapter rejects with a stable reason and no party or affinity state changes

### Requirement: explore.engage delegates to the existing engage contract
The production action registry SHALL register `explore.engage`. Its payload SHALL accept exactly `monster_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve the monster from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and call `world.rules.combat_session.engage(actor, monster)` — re-verifying a `PlayerCharacter` with no active session, a living hostile `Monster` in the same room, and recording the initial overwhelm classification. The adapter SHALL NOT assign session, battlefield, skip-safety, or location state directly and SHALL NOT run any combat action. On success the completion SHALL publish `status` and `context_actions` at one newer revision with the mode change to `combat` so the browser tears down the exploration dock and mounts the ordinary combat menu; `services` and `exploration` SHALL be unavailable in combat mode. A rejection SHALL publish the safe stable reason and SHALL NOT create a session or advance time.

#### Scenario: Engage transitions to the combat dock
- **WHEN** an actor submits `explore.engage` for a present living hostile monster
- **THEN** `engage` returns its record, the update carries mode `combat` and a `context_actions` combat payload, the exploration dock unloads, and no exploration mutation is admitted in combat mode

#### Scenario: Engage rejects a remote or non-hostile target
- **WHEN** an actor submits `explore.engage` for a target that is absent, dead, or not a hostile `Monster`
- **THEN** the adapter rejects with a stable reason, no session is created, and the exploration dock remains usable

### Requirement: explore.wait obeys the shared skip safety and clock API
The production action registry SHALL register `explore.wait`. Its payload SHALL accept exactly one of `daypart` (one of `midnight`, `dawn`, `noon`, `dusk`), `seconds` (a positive integer no greater than the documented WebClient skip maximum, a protocol-level bound that never changes command behavior), or `sleep` (the exact boolean true). The adapter SHALL obtain the actor from the authenticated session, recheck `evaluate_skip_safety(actor)` against current canonical state (active combat or a co-located living monster rejects), compute the seconds exactly as the matching command does — through the shared `world/rules` skip helper that `rest`/`sleep`/`wait` also consume, so `seconds_until_daypart` for a daypart, the bounded full-regen computation for `sleep`, and the submitted `seconds` verbatim for a duration can never diverge between command and WebClient — and then call `get_world_clock().advance(seconds, AdvanceSource.SKIP, [actor])`. The adapter SHALL present the returned `ScheduledEvent` summary through the escaped text path, SHALL NOT advance time itself or let the browser choose an unsafe value, and SHALL publish a full snapshot at one newer revision so the advanced header, status, shop hours, and quest deadlines refresh together. An unsafe location, active combat, unknown daypart, or out-of-bounds duration SHALL reject with a stable code and message and SHALL NOT advance the clock.

#### Scenario: Wait until dawn advances to the next occurrence
- **WHEN** a safe actor submits `explore.wait` with `daypart: "dawn"`
- **THEN** the clock advances by exactly `seconds_until_daypart(calendar, "dawn")` with `AdvanceSource.SKIP` and the summary reports the elapsed duration

#### Scenario: An unsafe skip rejects before any clock advance
- **WHEN** an actor in a room with a living monster submits `explore.wait`
- **THEN** the adapter rejects with the matching safety reason, `get_world_clock().tick` is unchanged, and no event settles

#### Scenario: A custom duration is parsed server-side
- **WHEN** a safe actor submits `explore.wait` with `seconds: 3600`
- **THEN** the clock advances by exactly 3600 seconds with `AdvanceSource.SKIP`, and a value above the protocol bound is rejected before any advance

### Requirement: The exploration dock is keyboard-first and re-homes the service submenus
In exploration mode the exploration dock SHALL own the action-dock surface and SHALL present the stable root Move, Look, Interact, Character, Quests, Inventory, and Wait in that order, composed only from the validated `exploration` panel. Move SHALL open the exit list and submit `explore.move`; Look SHALL open room/entity/object inspection and submit `explore.look`; Interact SHALL first select a present target and then show only that target's server-authored affordances (scripted dialogue keywords as finite buttons, free-form dialogue, engage, or a `navigate`-kind guild/shop service entry); Character SHALL open the validated `character` panel; Quests and Inventory SHALL open the corresponding `services` panel submenus (guild quest log and inventory respectively); Wait SHALL open a rest/wait menu of the four named daypart boundaries plus a bounded custom-duration form and a sleep-to-full-regen entry, with every value parsed and validated server-side and no client-side clock arithmetic. A root entry whose capability surface is absent SHALL NOT render as a dead functional entry. Every exploration submenu — Move, Look, Interact, Wait, each target-affordance menu, and each scripted-keyword menu — SHALL end with an enabled back row that returns to its parent menu (the root has no back row), so pointer and keyboard users backtrack through the identical router path; Escape SHALL pop exactly one level. The dock SHALL render the approved command surface — the root as one equal-width row of grid cells beneath the shortcut guidance line, and each submenu as a grid of cells beside a detail pane that names the focused item and its availability — with the focused cell marked by a seal-red fill plus a leading glyph and disabled cells dimmed but focusable. The dock SHALL keep its rendered cells matched to the keyboard router's current frame at every navigation depth, so a back row, an Escape, or a pointer click on a parent row never leaves a deeper menu's cells on screen while the router navigates the parent. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop exactly one level, disabled entries SHALL remain focusable for their explanation but SHALL NOT submit, and held/repeated Enter and any mutation while one is in flight or awaiting its declared presentation revision SHALL be suppressed. The service dock SHALL be re-homed under the Interact/Quests/Inventory roots instead of a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only arrows and Enter to open Move, select an exit, and later open Interact and choose a scripted keyword
- **THEN** the browser submits exactly `explore.move` then `explore.talk_scripted` with the server-authored IDs, and the refreshed panels appear without a typed command

#### Scenario: The dock renders the mockup grid with a guidance line and detail pane
- **WHEN** the exploration dock is mounted
- **THEN** the root renders as one equal-width row of grid cells beneath the shortcut guidance line, each submenu renders as a grid of cells beside a detail pane that names the focused item and its availability, the focused cell carries a seal-red fill plus a leading glyph, and disabled cells are dimmed but focusable

#### Scenario: A pointer user backs out of a submenu
- **WHEN** a player clicks the Look root entry, then clicks the back cell of the Look submenu
- **THEN** the router returns to the root frame, the dock renders the root cells again, no `ui_action` is sent, and no typed command is required

#### Scenario: A back cell returns to the exact parent menu
- **WHEN** a player navigates Interact → a target's affordances → scripted keywords and activates the back cell at each level
- **THEN** the dock returns to the target-affordance menu and then to the Interact target list, rendering that parent's cells at every step

#### Scenario: Escape keeps the rendered cells matched to the router frame at any depth
- **WHEN** the player presses Escape from a target-affordance or scripted-keyword submenu that is more than one level deep
- **THEN** exactly one menu level closes, the parent menu's cells render immediately, and the prior focused item is restored

#### Scenario: Escape from a re-homed service or character sub-view leaves the exploration root clean
- **WHEN** the player opens Character or a Quests/Inventory service submenu from the exploration root and presses Escape
- **THEN** the sub-view closes without sending an action, the exploration root remains the dock's current frame, and no exploration submenu bookkeeping is corrupted or re-rendered

#### Scenario: Disabled affordance explains without submitting
- **WHEN** focus moves to a disabled `explore.engage` affordance and the player presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` message is emitted

#### Scenario: Quests and Inventory reach the services submenus
- **WHEN** the player opens Quests from the exploration root and the `services` panel is available
- **THEN** the quest-log submenu renders from the unchanged `services` panel payload and its `guild.quest_*` actions

#### Scenario: Mode change tears down the exploration dock atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration dock synchronously unloads, unregisters its keyboard handlers, discards local selection and speech state, and only the combat dock owns action-dock focus

### Requirement: Portrait focus stays client-local against the art catalog seam
Exploration descriptors SHALL carry a nullable opaque `portrait_ref` that references entries in the server-authored art `portrait_catalog` when the art capability supplies one and `null` otherwise. The browser SHALL switch portrait focus only among verified catalog values emitted by the server, SHALL NOT construct portrait subject keys or URLs from entity data, SHALL NOT send a focus mutation or input message, and SHALL NOT treat a `portrait_ref: null` descriptor or an absent catalog as a failure — look, interact, and dialogue proceed normally with no portrait card.

#### Scenario: Absence of art never blocks exploration
- **WHEN** the art catalog is absent or a descriptor carries `portrait_ref: null`
- **THEN** look, interact, and dialogue operate normally, and no portrait card or focus packet is produced

#### Scenario: Catalog-driven focus is verified
- **WHEN** the server supplies a `portrait_catalog` and an exploration descriptor references a catalog identity
- **THEN** client-local focus switches only to that server-verified value and no subject key or URL is constructed by the browser

### Requirement: Exploration actions reject stale, duplicate, and tampered input without mutation
Every exploration action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` mismatch SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. After those checks, commit-time domain revalidation is authoritative: an exit, NPC, monster, keyword, or daypart that changed between render and submit is handled against current canonical state, and a tampered `exit_ref`, `current_node`, `npc_id`, `monster_id`, `keyword_id`, `speech`, `daypart`, or `seconds` that fails current revalidation SHALL be rejected with a stable code and Traditional Chinese message with no location, time, knowledge, dialogue, quest, inventory, combat, or onboarding change. A transport drop after submit SHALL NOT be auto-retried; reconnect SHALL rebuild the dock from the new-epoch full snapshot and display the uncertain-result notice.

#### Scenario: Stale revision cannot move or talk twice
- **WHEN** an older-revision `explore.move` or `explore.talk_freeform` is submitted after a newer revision is active
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without changing location, clock, or dialogue

#### Scenario: Tampered exit or NPC references perform nothing
- **WHEN** a tampered `exit_ref`/`current_node` or `npc_id` fails current domain revalidation
- **THEN** the adapter rejects before any traversal, dialogue, or time advance, and canonical state is unchanged

#### Scenario: A target that left the room rejects at commit time
- **WHEN** an NPC, monster, or object referenced by `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, or `explore.engage` was present at render but has left the actor's location (or changed type/eligibility) by submit
- **THEN** the adapter re-resolves it from the actor's current location's present contents, rejects with a stable reason before the display, dialogue, or engage API is invoked, and no onboarding, memory, intent, session, or time state changes

#### Scenario: Reconnect rebuilds exploration without replaying intent
- **WHEN** the transport disconnects after sending `explore.talk_freeform` and reconnects without another action
- **THEN** the new-epoch snapshot rebuilds the dock from canonical location, knowledge, and NPC state, the uncertain-result notice is shown, and no dialogue or mutation is automatically replayed

### Requirement: Exploration browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1440x900 and 1280x720: grid, wilderness, instance, and interior movement through `explore.move` with matching time and map updates; look at the room advancing the onboarding look beat and look at present entities; scripted keyword dialogue and free-form dialogue with offline degrade to greeting/silence; engage transitioning to the combat dock; wait/rest daypart and duration acceptance plus safety rejections; stale, duplicate, and tampered rejections; service submenus reachable through Quests/Inventory; and reconnect retention. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, SHALL assert that no take/drop control and no remote or ambiguous host control is rendered, and SHALL assert that `portrait_ref: null` produces no portrait card and no focus packet.

#### Scenario: A full exploration journey completes in Chromium
- **WHEN** a seeded actor uses arrows and Enter to move through an exit, look at the room, talk to a scripted host, open Quests, and wait until dawn
- **THEN** each step submits exactly one expected `ui_action`, the narrative and panels refresh together, and no typed command is required

#### Scenario: Offline dialogue still completes in the browser
- **WHEN** the LLM is offline and the player chooses free-form dialogue for an `LLMNPC`
- **THEN** the authored greeting or silence appears, the dock unlocks, and no remote request is made

#### Scenario: No take or drop control is rendered
- **WHEN** the exploration dock is open in any room
- **THEN** no `explore.take`/`explore.drop` affordance or generic object-mutation control exists anywhere in the rendered surface

### Requirement: Exploration move rows advertise canonical destinations
The exploration menu's wilderness move rows SHALL use the canonical destination resolver so the advertised destination equals the node the player actually arrives at.

#### Scenario: Move row destination matches actual arrival
- **WHEN** the exploration menu lists wilderness move rows
- **THEN** each row's destination is the canonical arrival node, including the gateway south row that returns to the grid
