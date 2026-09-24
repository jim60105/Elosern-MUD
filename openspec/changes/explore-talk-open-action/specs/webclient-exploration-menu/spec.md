## ADDED Requirements

### Requirement: The exploration panel is an exact read-only version-3 presentation panel
The production presentation registry SHALL register panel name `exploration` at schema version 3. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `move`, `look`, `interact`, `character`, `quests`, and `inventory`; `available` SHALL be true and `kind` SHALL be `exploration`. `move` SHALL be a bounded list of at most 12 exit descriptors, each containing exactly `exit_ref`, `label`, `destination`, `enabled`, and nullable `disabled_reason`, where `exit_ref` is the same opaque 1..64-ASCII-character identifier the `local_map` move action uses, `label` is a bounded localized direction/exit label, `destination` is the canonical destination node ID, and `enabled`/`disabled_reason` reflect a currently present, traversable Exit from the actor's location (a locked or absent exit is a disabled row, never omitted, so the player learns it exists). `look` SHALL contain exactly `room`, `entities`, and `objects`: `room` is an exact room descriptor with a room marker for `explore.look`, `entities` is a bounded list of at most 32 present character/NPC/monster descriptors each carrying an opaque identity, bounded display name, bounded kind, and nullable opaque `portrait_ref`, and `objects` is a bounded list of at most 32 present object descriptors carrying an opaque identity and bounded display name. `interact` SHALL be a bounded list of at most 32 present target descriptors, each carrying exactly `identity`, `display_name`, nullable `portrait_ref`, and a bounded `affordances` list of at most 8 descriptors; a target descriptor SHALL carry no keyword list and no other field, because a conversation's topics reach the browser only through the `dialogue` panel's `choices` once the conversation is open. An action affordance SHALL contain exactly `kind` (`"action"`), `action_id`, `label`, `enabled`, and nullable `disabled_reason`. The panel's accepted-action enumeration SHALL be derived from the shared `ACTION_CODE_ALLOWLIST` rather than a private duplicate, minus the two in-conversation codes `explore.talk_scripted` and `explore.talk_freeform`, which SHALL NOT appear on any target descriptor: the target affordances the presenter emits are drawn from `explore.talk_open`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.possess`, `explore.possess_release`, and `explore.deliver`, which is exactly the client mirror's target-scoped action list. Exactly the `explore.deliver` action affordance additionally carries `params` — the shared delivery validator's normalized dispatch payload (`npc_id` and the bounded ASCII `item_key`) — and every other action affordance SHALL carry no `params` (its dispatch payload is re-derived from the target identity at the dock). A navigation affordance SHALL contain exactly `kind` (`"navigate"`), `surface` (one of `"guild"` or `"shop"`), `label`, `enabled`, and nullable `disabled_reason`. Navigation affordances are dock-navigation descriptors only — they are NOT registered action adapters, never enter a `ui_action` payload, and only tell the browser to open the corresponding service drawer. `character`, `quests`, and `inventory` SHALL each be availability entries with exactly `available` (boolean): `character` SHALL be available in exploration mode, and `quests`/`inventory` SHALL be available only when the `services` panel is registered and available. The presenter SHALL build the payload only from canonical room, entity, component, object, and service data, SHALL emit no live object or filesystem reference, SHALL NOT mutate location, traits, knowledge, dialogue, quests, inventory, or world time, and SHALL use the registered common unavailable form outside exploration mode. Rendering the panel for a room whose legal vocabulary entries include a possession affordance SHALL NOT raise inside the presenter: any entry the shared vocabulary may legally emit SHALL either be serialized as an accepted target affordance or be folded into the target's single conversation affordance, so a bound companion standing in the room can never degrade the panel from within. The server validator and the production client mirror SHALL reject a version-2 payload, a target carrying a `keywords` field, and a target affordance naming `explore.talk_scripted` or `explore.talk_freeform`.

#### Scenario: Exploration snapshot carries the exploration root
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `exploration` reports schema version 3 and `kind == "exploration"`, the current Exits in `move`, the present room/entities/objects in `look`, and the present interact targets with their legal affordances, while a before/after comparison of canonical game state is unchanged

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
- **THEN** the target descriptor carries the `explore.deliver` affordance with exactly the normalized `params` (`npc_id` and `item_key`), and no other action affordance carries a `params` field

#### Scenario: In-conversation codes and keyword lists are rejected
- **WHEN** the server validator or the client mirror receives an exploration payload whose target carries a `keywords` list, or an affordance naming `explore.talk_scripted` or `explore.talk_freeform`, or whose `schema_version` is 2
- **THEN** the payload is rejected as a protocol error and is never adopted

### Requirement: explore.talk_open opens a conversation with the host's greeting
The production action registry SHALL register `explore.talk_open`. Its payload SHALL accept exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session and SHALL reject, before writing anything and with the same stable codes and messages `explore.talk_scripted` uses: a possessed actor with the possession-refusal code; an `npc_id` that does not re-resolve to an NPC present in the actor's current location — never a stored, remote, or ambiguous reference — with `no_npc`; a host whose talk schedule gate blocks talk with `schedule_blocked` and the gate's reason; and an NPC that is not a conversable host with `not_dialogue_host`. A conversable host SHALL be an `LLMNPC`, or an NPC carrying a resolved `ScriptedDialogue` component whose authored dialogue table resolves. On success the adapter SHALL take the session line from the host's authored no-keyword greeting (`world.rules.dialogue.greeting_for`) and, when the host has none, from one fixed server-authored fallback line naming the host (`{name}看向你，等你開口。`) owned by `world/rules/player_messages.py`; it SHALL record the session through the deterministic dialogue-session seam, deliver the line to the actor's narrative (a greeting prefixed by the host's name and `說：`, the fallback verbatim), and return a deterministic success result that publishes a full snapshot at one newer revision, so the committed mode `dialogue` and the available `dialogue` panel — carrying that line and the host's authored choices — arrive atomically. The adapter SHALL make no LLM or network request, SHALL NOT advance the world clock, SHALL NOT change affinity, memory, party, quest, inventory, or any other state beyond the session, and SHALL NOT schedule an action-options generation. `explore.talk_open` SHALL be a member of the shared `ACTION_CODE_ALLOWLIST` and SHALL NOT be a suggestible action code, so no suggestion card or AI proposal names it.

#### Scenario: A scripted host opens with its greeting
- **WHEN** an actor submits `explore.talk_open` for a present scripted host whose authored table carries a greeting and two keywords
- **THEN** the action succeeds once, the character's session names that host with the greeting as its line, and the next committed presentation carries mode `dialogue` with the `dialogue` panel showing that line and exactly the two keyword choices

#### Scenario: A host without a greeting opens with the fixed fallback line
- **WHEN** an actor submits `explore.talk_open` for a present `LLMNPC` that carries no scripted component, or a scripted host whose table has no greeting
- **THEN** the session line is exactly the fixed fallback line naming the host, and the dialogue panel is available with that line

#### Scenario: A departed or non-host NPC rejects without writing
- **WHEN** an actor submits `explore.talk_open` for an NPC that left the room after render, for an identity that is not an NPC, or for a present NPC that is neither an `LLMNPC` nor a scripted host with a resolvable table
- **THEN** the adapter rejects with `no_npc` or `not_dialogue_host` respectively, and `db.dialogue_session` and the committed mode are unchanged

#### Scenario: A schedule-blocked host rejects with the gate's reason
- **WHEN** an actor submits `explore.talk_open` for a present host inside its talk-blocked schedule window
- **THEN** the adapter rejects with `schedule_blocked` and the schedule gate's message, and no session is written

#### Scenario: A possessed actor cannot open a conversation
- **WHEN** the puppeted actor is a possessed NPC and submits `explore.talk_open`
- **THEN** the adapter rejects with the possession-refusal code before resolving the host

#### Scenario: Opening a conversation touches nothing but the session
- **WHEN** a successful `explore.talk_open` settles with every LLM profile disabled
- **THEN** no network request is made, the world clock tick, affinity records, memories, and party bindings are byte-identical to before the action, and only `db.dialogue_session` changed

#### Scenario: A payload with extra or wrong fields is malformed
- **WHEN** a client submits `explore.talk_open` with `keyword_id`, `speech`, a missing `npc_id`, or a non-positive `npc_id`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter

### Requirement: The keyboard-first exploration dock roots at the scene overview and opens dialogue directly

In exploration and dialogue mode the exploration dock SHALL own the action-dock surface, and its root
frame SHALL be one scene overview composed only from the validated `exploration` panel and the
committed `context_actions` `suggestions` envelope. The overview SHALL present, in this reading order:

- an 出口 row with one chip per `move` row in payload order — a disabled row SHALL stay visible as a
  disabled chip carrying its server-authored reason, never omitted — and activating an enabled exit
  chip SHALL submit the unchanged `explore.move` payload;
- a 人物 row with one chip per `interact` target in payload order, followed by one look chip per
  `look.entities` descriptor that has no `interact` descriptor; activating a target chip SHALL open
  that target's verb popover and activating a look chip SHALL submit `explore.look` for it;
- a 物件 row with one chip per `look.objects` descriptor, whose activation SHALL submit
  `explore.look` for that object;
- a footer holding 查看房間 (submitting `explore.look` for the room), 等待／休息, and — whenever the
  suggestions envelope's status is not `unavailable` — 建議, labelled `建議 (N)` with N the number of
  cards the suggestions frame will list when that number is positive.

A row with no chip SHALL be omitted together with its label. The overview SHALL carry no 移動, 查看,
互動, 角色狀態, 任務, or 背包 entry: the character status, quest, and inventory surfaces are opened from
the top navigation bar, which is their sole keyboard-visible stop. Chips SHALL wrap inside the fixed
command region, and an overview taller than the region SHALL scroll inside it with the focused chip
kept in view. An exit chip SHALL carry the exit's direction glyph from the fixed table of canonical
direction words and, while enabled, the destination's display name resolved from the committed
`local_map` nodes; an exit label outside that table SHALL render verbatim with no guessed direction,
and a destination absent from the committed lattice SHALL fall back to the exit's own label.

The verb popover SHALL be one child frame of the overview, rendered as a card inside the command
region over the inert overview, with a head naming the target. It SHALL list that target's
server-authored affordances in payload order — 交談, which SHALL submit exactly one `explore.talk_open`
with the target's identity and no further step, party invitation and dismissal, engage,
delivery with its server-normalized parameters, and a `navigate`-kind guild or shop entry that opens
its drawer without pushing a frame — followed by 查看, which submits `explore.look` for the target,
and a back row. The popover SHALL offer no keyword list, no free-form dialogue row, and no path that
borrows the command line: a conversation's topics and free-form speech are offered only by the
dialogue surface once `explore.talk_open` has opened it. A disabled 交談 SHALL stay focusable with
its server-authored reason and SHALL submit nothing. A target with no mapped affordance SHALL still
open a popover holding 查看 and the back row. 等待／休息 SHALL open the three-operation waiting frame —
等待直到黎明 submitting the dawn daypart, 睡眠至完全恢復 submitting the sleep flag, and 休息 N 小時
opening the bounded custom-hours form — with every value parsed and validated server-side and no
client-side clock derivation (the form's own hours-to-whole-seconds unit conversion at the
presentation boundary is unit entry, not clock arithmetic, as pinned by the waiting-surface
requirement); 建議 SHALL open the suggestions frame owned by `webclient-options-surface`. Both SHALL
render inside the command region in place of the overview. Every child frame — the verb popover, the
waiting frame, and the suggestions frame — SHALL end with an enabled back row returning to its parent,
so pointer and keyboard users backtrack through the identical router path; Escape SHALL pop exactly
one level and SHALL restore the parent frame's previously focused entry (the chip that opened the
popover or the child frame).

When the committed location changes — a move from an exit chip, the minimap, or a typed command —
the dock SHALL return to the overview: any open popover or child frame SHALL be closed in the same
commit that publishes the new room, and no frame from the previous room SHALL remain activatable.
When a commit changes the mode from `exploration` to `dialogue` — a conversation opened from 交談, a
suggestion card, or a typed command — the dock SHALL likewise return to the overview in that commit,
so no popover or child frame stays open over the conversation.

The overview SHALL be navigated as rows of chips: ArrowLeft and ArrowRight SHALL move to the previous
and next chip in reading order, wrapping across the whole overview; ArrowUp and ArrowDown SHALL move
to the chip at the same position in the previous or next row, clamped to that row's last chip and
wrapping across rows, and SHALL be no-ops when the overview has one row. Enter SHALL open or submit
the focused entry. The popover and every other child frame SHALL be navigated as a vertical list.
Disabled entries SHALL remain focusable for their explanation but SHALL NOT submit, and held or
repeated Enter and any mutation while one is in flight or awaiting its declared presentation revision
SHALL be suppressed. The dock SHALL keep its rendered cells matched to the keyboard router's current
frame at every depth, so a back row, an Escape, or a panel replacement never leaves a deeper frame's
cells activatable while the router navigates the parent. The service surfaces SHALL be reached from
the top navigation bar and from a target's `navigate` affordance instead of a standalone Services
root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only arrows and Enter to activate an exit chip, then activates a scripted dialogue host's chip, chooses 交談, and then presses the digit of the first choice the dialogue surface offers
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open` with the host's identity, then `explore.talk_scripted` with the server-authored keyword ID, and the refreshed panels appear without a typed command

#### Scenario: The overview shows exits, people, and objects in one frame
- **WHEN** the committed exploration panel carries two exits, one dialogue host, and one object
- **THEN** the dock's root frame renders the 出口 row with two exit chips, the 人物 row with the host's chip, the 物件 row with the object's chip, and the footer with 查看房間 and 等待／休息, all in one frame with no tab to switch

#### Scenario: An empty row is omitted
- **WHEN** the committed exploration panel carries exits but no people and no objects
- **THEN** the overview renders the 出口 row and the footer only, and no 人物 or 物件 label or empty row is present

#### Scenario: A disabled exit stays visible with its reason
- **WHEN** the room has a locked exit and the player focuses its chip and presses Enter
- **THEN** the chip is rendered disabled with its disabled marker, its server-authored reason is readable, and no `ui_action` is emitted

#### Scenario: A person chip opens the verb popover in payload order
- **WHEN** the player activates the chip of a target whose affordances are 交談, 交易, and 戰鬥 in that payload order
- **THEN** a popover naming the target opens inside the command region listing 交談, 交易, 戰鬥, 查看, and the back row in that order, no `ui_action` is emitted, and the overview beneath takes no focus or activation

#### Scenario: 查看 in the popover looks at the target
- **WHEN** the player activates 查看 in a target's popover
- **THEN** exactly one `explore.look` with that target's identity is submitted

#### Scenario: 交談 enters the conversation in one step
- **WHEN** the player activates 交談 in a dialogue host's popover
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted and no frame is pushed, and the commit that makes the mode `dialogue` shows the dialogue surface with the host's opening line and choices while the dock has returned to the overview

#### Scenario: A generative host offers no separate free-form row
- **WHEN** the player opens the popover of an `LLMNPC` host
- **THEN** it lists one 交談 row and no 自由交談 row, and activating 交談 neither focuses nor expands the command line

#### Scenario: A navigate affordance opens its drawer without a frame
- **WHEN** the player activates a guild clerk's `navigate` affordance in its popover
- **THEN** the 任務 drawer opens from the unchanged `services` panel payload, no router frame is pushed by the open, and no `dock-menu` row region renders inside the drawer

#### Scenario: Waiting and suggestions open child frames in the panel
- **WHEN** the player activates 等待／休息, presses Escape, activates 建議, and presses Escape
- **THEN** each opens its frame inside the command region in place of the overview, and each Escape returns to the overview with the footer chip that opened it focused

#### Scenario: Movement returns the dock to the overview
- **WHEN** the verb popover or the waiting frame is open and the player moves by activating a minimap node
- **THEN** the commit that publishes the new room shows the new room's overview as the dock's only frame, and no chip, popover row, or waiting card from the previous room remains activatable

#### Scenario: Arrow keys follow the chip rows
- **WHEN** the overview has three exit chips and two person chips, focus is on the third exit chip, and the player presses ArrowRight, then ArrowUp
- **THEN** ArrowRight moves focus to the first person chip, and ArrowUp moves focus to the first exit chip, because it keeps the chip's position within its row

#### Scenario: Escape closes the popover and restores the opener
- **WHEN** a target's popover is open and the player presses Escape
- **THEN** exactly one level closes, the overview is active again with that target's chip focused, and no `ui_action` is emitted

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces available and the dock renders its root
- **THEN** the overview carries no 角色狀態, 任務, or 背包 entry, and those surfaces are opened from the top navigation bar

#### Scenario: Escape from a re-homed service or character sub-view leaves the exploration root clean
- **WHEN** the player opens the Character, Quests, or Inventory drawer from the top navigation while the dock is at the overview and presses Escape
- **THEN** the drawer closes without sending an action, the overview remains the dock's current frame with no sub-dock active, and no exploration frame bookkeeping is corrupted or re-rendered

#### Scenario: Disabled affordance explains without submitting
- **WHEN** focus moves to a disabled `explore.engage` or disabled 交談 row in a target's popover and the player presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` message is emitted

#### Scenario: A departed target's popover closes
- **WHEN** a target's popover is open and a commit removes that target from the room
- **THEN** the popover closes in that commit, the overview is the current frame, and focus lands on the nearest surviving chip

#### Scenario: The overview scrolls inside the fixed panel
- **WHEN** the room carries more chips than the command region can show and the player arrows to the last chip
- **THEN** the chips wrap inside the region, the overview scrolls inside it with the focused chip in view, and the command region's box is unchanged

#### Scenario: Mode change tears down the exploration dock atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration dock synchronously unloads, unregisters its keyboard handlers, discards local selection and speech state, and only the combat dock owns action-dock focus

## MODIFIED Requirements

### Requirement: Exploration affordances are server-authored, never inferred from prose
Every `interact` affordance SHALL be derived from canonical data with the same checks commands use, never from typeclass names, display prose, or other heuristics. Every present conversable host — an `LLMNPC`, or an NPC with a resolved dialogue component (`ScriptedDialogue`) whose authored dialogue table resolves — SHALL carry exactly one conversation affordance, labelled 交談 and naming `explore.talk_open`, listed before the target's other affordances; it SHALL be enabled unless the puppeted actor is a possessed NPC, in which case it SHALL be disabled with the stable possession-refusal code and message. An NPC with a resolved `ScriptedDialogue` component whose authored table cannot be resolved SHALL instead carry one disabled 交談 affordance with the stable `dialogue_unavailable` reason. No target SHALL carry an `explore.talk_scripted` or `explore.talk_freeform` affordance or a keyword list: the host's authored keywords and free-form speech are offered by the dialogue surface once the conversation is open, and the shared vocabulary's per-keyword and free-form entries remain the source of suggestion cards. `explore.party_invite` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`) that is not already a companion of the actor, SHALL be enabled when the actor's party has fewer than 4 companions and disabled with the full-party reason otherwise, and SHALL never be offered for an already-bound companion (the leave affordance covers it). `explore.party_leave` SHALL be offered only for a present NPC that is currently a bound companion of the actor. `explore.engage` SHALL be offered only for a present living hostile `Monster` when the actor has no active combat session. A `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`) SHALL be offered only when the current room has exactly one unambiguous `GuildStaff` or `Merchant` host for a service the actor can use, and it opens the corresponding service drawer rather than inventing a mutation. No affordance SHALL reference a remote, absent, or ambiguous host or target. Every adapter SHALL re-verify at commit time, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition — so a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any memory, intent, party, session, or time state changes.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords and the player opens a conversation with it
- **THEN** its interact descriptor offers exactly one enabled 交談 `explore.talk_open` affordance and no keyword list, and once the conversation opens the `dialogue` panel's choices are exactly those two authored keywords

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room, with or without a scripted component
- **THEN** its interact descriptor offers exactly one 交談 `explore.talk_open` affordance and no `explore.talk_freeform` affordance, and the conversation that 交談 opens offers free-form speech

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
- **THEN** its interact descriptor contains no 交談, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

#### Scenario: A scripted host without a resolvable table shows a disabled 交談
- **WHEN** a present NPC carries a `ScriptedDialogue` component whose authored table cannot be resolved and is not an `LLMNPC`
- **THEN** its interact descriptor carries one disabled 交談 affordance with the `dialogue_unavailable` reason, and submitting `explore.talk_open` for it rejects with `not_dialogue_host`

## REMOVED Requirements

### Requirement: The exploration panel is an exact read-only version-2 presentation panel
**Reason**: The panel moves to schema version 3 (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §8.1): the target-level `keywords` list is deleted and the in-conversation codes `explore.talk_scripted` / `explore.talk_freeform` leave the target affordances, replaced by one `explore.talk_open` 交談 per conversable host. The requirement's title names the version, so it is replaced rather than modified.
**Migration**: "The exploration panel is an exact read-only version-3 presentation panel" restates every field and bound except the keyword list. Tests annotated with the old ID re-anchor to the new one.

### Requirement: The exploration dock is keyboard-first and roots at the scene overview
**Reason**: 交談 no longer opens a scripted-keyword frame or borrows the command line for free-form dialogue; it submits `explore.talk_open` directly (design §8.1). The requirement's "交談 keeps the scripted keyword frame" scenario describes a frame that no longer exists, and a MODIFIED block cannot drop it.
**Migration**: "The keyboard-first exploration dock roots at the scene overview and opens dialogue directly" restates the overview, the popover, the waiting and suggestions frames, the back and Escape rules, the room-change reset, the suppression rules, and the mode teardown, and adds the one-step 交談 and the reset when a conversation opens. Tests annotated with the old ID re-anchor to the new one.
