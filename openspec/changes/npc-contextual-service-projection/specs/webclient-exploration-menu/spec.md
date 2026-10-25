# Spec Delta

## MODIFIED Requirements

### Requirement: The exploration panel is an exact read-only version-4 presentation panel
The production presentation registry SHALL register panel name `exploration` at schema version 5 with `available` true and `kind` `exploration`, and its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `move`, `look`, `interact`, `character`, `quests`, and `inventory`.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `exploration` reports schema version 5 and `kind == "exploration"`, the current Exits in `move`, the present room/entities/objects in `look`, and the present interact targets with their legal affordances, while a before/after comparison of canonical game state is unchanged

#### Scenario: A bound companion's possess affordance never degrades the panel
- **WHEN** the room contains a bound companion of the actor and the full `exploration` panel is
  rendered through the production presenter
- **THEN** the panel is available with the companion descriptor carrying the `explore.possess`
  affordance, no presenter exception is logged, and the panel is not internal-unavailable

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

#### Scenario: A delivery affordance carries its normalized dispatch payload
- **WHEN** the room contains a co-located bound delivery recipient and the full `exploration` panel is rendered through the production presenter
- **THEN** the target descriptor carries the `explore.deliver` affordance with exactly the normalized `params` (`npc_id` and `item_key`), and no other ordinary action affordance carries a params field

#### Scenario: In-conversation codes and keyword lists are rejected
- **WHEN** the server validator or the client mirror receives an exploration payload whose target carries a `keywords` list, or an affordance naming `explore.talk_scripted` or `explore.talk_freeform`, or whose `schema_version` is 2 or 3
- **THEN** the payload is rejected as a protocol error and is never adopted

#### Scenario: The author-editor navigation descriptor is accepted and carries no card
- **WHEN** the server validator or the client mirror receives an exploration payload whose NPC target carries a `navigate` affordance with surface `npc_persona`
- **THEN** the payload is accepted, and a descriptor carrying any field beyond the five navigation fields is rejected as a protocol error

#### Scenario: Move rows are bounded exit descriptors
- **WHEN** the presenter builds `move` for a room with current Exits
- **THEN** `move` is a bounded list of at most 12 exit descriptors, each containing exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`
- **AND** `exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses, `label` is a bounded localized direction/exit label, and `destination` is the canonical destination node ID
- **AND** `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the actor's location, so a locked or absent exit is a disabled row, never omitted, and the player learns it exists

#### Scenario: Look carries exactly room, entities, and objects
- **WHEN** the presenter builds the `look` section
- **THEN** it contains exactly `room`, `entities`, and `objects`: `room` is an exact room descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32 present character/NPC/monster descriptors each carrying an opaque identity, bounded display name, bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32 present object descriptors carrying an opaque identity and bounded display name

#### Scenario: Interact targets carry their exact target fields and a bounded affordance list
- **WHEN** the presenter builds `interact`
- **THEN** it is a bounded list of at most 32 present target descriptors, each carrying exactly `identity`, `display_name`, nullable `portrait_ref`, services, and a bounded `affordances` list of at most 8 descriptors
- **AND** a target descriptor carries no keyword list beyond its declared services routes, because a conversation's topics reach the browser only through the `dialogue` panel's `choices` once the conversation is open

#### Scenario: An action affordance carries exactly its five fields
- **WHEN** the presenter serializes an action affordance
- **THEN** it contains exactly `kind` (`"action"`), `action_id`, `label`, `enabled`, and nullable `disabled_reason`

#### Scenario: Accepted actions derive from the shared allowlist minus in-conversation codes
- **WHEN** the panel's accepted-action enumeration is assembled
- **THEN** it is derived from the shared `ACTION_CODE_ALLOWLIST` rather than a private duplicate, minus the two in-conversation codes `explore.talk_scripted` and `explore.talk_freeform`, which never appear on any target descriptor
- **AND** the target affordances the presenter emits are drawn from `explore.talk_open`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.possess`, `explore.possess_release`, and `explore.deliver`, which is exactly the client mirror's target-scoped action list

#### Scenario: Only the deliver affordance carries params
- **WHEN** the presenter emits target action affordances
- **THEN** exactly the `explore.deliver` action affordance additionally carries `params`, the shared delivery validator's normalized dispatch payload (`npc_id` and the bounded ASCII `item_key`), and every other action affordance carries no `params`, its dispatch payload being re-derived from the target identity at the dock

#### Scenario: A navigation affordance carries exactly its five fields and opens only a drawer
- **WHEN** the presenter serializes a navigation affordance
- **THEN** it contains exactly `kind` (`"navigate"`), `surface` (only npc_persona for an ordinary NPC editor), `label`, `enabled`, and nullable `disabled_reason`
- **AND** navigation affordances are dock-navigation descriptors only; they are NOT registered action adapters, never enter a `ui_action` payload, and only open the ordinary author editor; supported services use the separate exact target-bound route union

#### Scenario: Availability entries carry only the available boolean
- **WHEN** the presenter builds `character`, `quests`, and `inventory`
- **THEN** each is an availability entry with exactly `available` (boolean): `character` is available in exploration mode, and `quests`/`inventory` are available only when the `services` panel is registered and available

#### Scenario: A vocabulary-emitted possession entry never raises in the presenter
- **WHEN** the panel is rendered for a room whose legal vocabulary entries include a possession affordance
- **THEN** the presenter does not raise: the entry is either serialized as an accepted target affordance or folded into the target's single conversation affordance, so a bound companion standing in the room can never degrade the panel from within

#### Scenario: The presenter stays read-only over canonical data
- **WHEN** the `exploration` presenter builds its payload
- **THEN** it is built only from canonical room, entity, component, object, and service data, emits no live object or filesystem reference, does not mutate location, traits, knowledge, dialogue, quests, inventory, or world time, and uses the registered common unavailable form outside exploration mode

#### Scenario: Available schema versions cut over together
- **WHEN** either validator receives an available exploration panel with schema version 5, and then otherwise identical panels with version 4 or another unsupported version
- **THEN** only version 5 is accepted, including its non-null reference fields, and no dual-version conversion is performed

#### Scenario: Bounded independent services field
- **WHEN** an NPC interact descriptor is serialized
- **THEN** services has exact state none/ready/unreadable and at most 16 stable-key label/enabled/reason/route entries, independent of the eight general-affordance limit; Python and browser accept only schema 5

### Requirement: Exploration affordances are server-authored, never inferred from prose
Existing exploration affordances SHALL remain server-authored. Party invite SHALL use general identity and its separate four-member quota; same-owner temporary-only members SHALL remain normally recruitable. Party leave SHALL address source-aware general removal or selected private escort abandonment through the existing mission drawer, never detach a valid escort reason directly. Other conversation/service/combat/editor gates SHALL remain.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords and the player opens a conversation with it
- **THEN** its interact descriptor offers exactly one enabled 交談 `explore.talk_open` affordance and no keyword list, and once the conversation opens the `dialogue` panel's choices are exactly those two authored keywords

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room, with or without a scripted component
- **THEN** its interact descriptor offers exactly one 交談 `explore.talk_open` affordance and no `explore.talk_freeform` affordance, and the conversation that 交談 opens offers free-form speech

#### Scenario: An unbound generative NPC offers an invite
- **WHEN** an eligible present unbound or same-owner temporary-only LLMNPC has no general identity
- **THEN** its invite affordance is enabled below four valid general identities regardless of temporary count, otherwise disabled as full_party

#### Scenario: A bound companion offers leave instead of invite
- **WHEN** a present companion has general identity
- **THEN** its leave affordance offers general removal; a temporary-only eligible actor may also offer ordinary recruitment

#### Scenario: A living hostile monster offers engage
- **WHEN** a present living `Monster` is in the room and the actor has no active session
- **THEN** its interact descriptor offers `explore.engage`; an already-engaged actor receives no engage affordance

#### Scenario: No affordance is fabricated for a plain NPC
- **WHEN** a present NPC carries neither a dialogue component nor an eligible free-form surface nor a party binding
- **THEN** its interact descriptor contains no 交談, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

#### Scenario: A scripted host without a resolvable table shows a disabled 交談
- **WHEN** a present NPC carries a `ScriptedDialogue` component whose authored table cannot be resolved and is not an `LLMNPC`
- **THEN** its interact descriptor carries one disabled 交談 affordance with the `dialogue_unavailable` reason, and submitting `explore.talk_open` for it rejects with `not_dialogue_host`

#### Scenario: Every NPC target offers the author editor last
- **WHEN** the room holds a scripted host with a valid card, a plain NPC whose card was never initialized, and a living monster
- **THEN** the host's descriptor ends with an enabled 編輯人物設定 `npc_persona` navigation, the uninitialized NPC's ends with a disabled one carrying the `npc_persona.unavailable` reason, and the monster carries none

#### Scenario: The editor row survives the descriptor bound
- **WHEN** a target's other affordances already fill the eight-descriptor bound
- **THEN** the descriptor keeps the 編輯人物設定 navigation as its last entry and drops the lowest-priority other affordance

#### Scenario: A scripted host whose table cannot be resolved carries a disabled 交談
- **WHEN** a present NPC carries a resolved `ScriptedDialogue` component whose authored table cannot be resolved
- **THEN** it carries one disabled 交談 affordance with the stable `dialogue_unavailable` reason

#### Scenario: No in-conversation codes or keyword lists are offered
- **WHEN** the presenter builds target affordances
- **THEN** no target carries an `explore.talk_scripted` or `explore.talk_freeform` affordance or a keyword list: the host's authored keywords and free-form speech are offered by the dialogue surface once the conversation is open, and the shared vocabulary's per-keyword and free-form entries remain the source of suggestion cards

#### Scenario: Party invite eligibility and enablement
- **WHEN** party invite affordances are built
- **THEN** ordinary local free-form eligibility, ownership and general quota apply; already-general/foreign-bound actors are refused while same-owner temporary-only actors are recruitable

#### Scenario: Party leave targets only bound companions
- **WHEN** party leave affordances are built
- **THEN** only effective owned present companions receive them, and active escort reasons identify the affected missions for selected abandonment rather than blind detachment

#### Scenario: Engage targets only living hostile monsters outside combat
- **WHEN** the presenter decides whether to offer `explore.engage`
- **THEN** it is offered only for a present living hostile `Monster` when the actor has no active combat session

#### Scenario: A navigate service affordance needs an unambiguous usable host
- **WHEN** the presenter decides whether to offer a `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`)
- **THEN** the old guild/shop navigation descriptors are absent; the separate contextual services field targets this NPC with availability reasons and opens its existing selected-provider flow

#### Scenario: No affordance references a remote, absent, or ambiguous target
- **WHEN** the presenter builds any interact affordance
- **THEN** it references no remote, absent, or ambiguous host or target

#### Scenario: Adapters re-verify their descriptor's affordance at commit time
- **WHEN** an exploration adapter runs after the dispatcher's checks
- **THEN** it re-verifies, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition
- **AND** a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any memory, intent, party, session, or time state changes

#### Scenario: Dual membership preserves one row and independent controls
- **WHEN** a same-owner temporary-only actor is normally recruited and later has its general identity removed
- **THEN** its one effective roster row and escort controls remain until all valid escort reasons end

#### Scenario: Selected-provider services replace coarse navigation
- **WHEN** an NPC has supported services
- **THEN** the services field derives all route entries for that selected host; guild/shop navigate affordances are no longer emitted and another same-class bystander does not hide its entries
