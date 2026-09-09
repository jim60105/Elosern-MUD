# webclient-exploration-menu delta

## ADDED Requirements

### Requirement: The waiting surface offers exactly three operations
The exploration dock's Wait frame SHALL offer exactly three operations and no other time boundary: 等待直到黎明, submitting `explore.wait` with the `dawn` daypart; 睡眠至完全恢復, submitting `explore.wait` with the exact `sleep` flag; and 休息 N 小時, opening the bounded custom-duration form instead of dispatching. The rendered frame SHALL show exactly those three cards plus the frame's back row, and the card whose item key equals the keyboard router's focused key SHALL carry the focused treatment. The custom form SHALL accept hours with fractional input allowed, SHALL bound the value to at least one second and at most the documented WebClient skip maximum (twelve hours), SHALL convert hours to whole seconds exactly once at the presentation boundary, and SHALL dispatch that value as the unchanged `explore.wait` `seconds` payload; it SHALL NOT derive or display a resulting world time, and a rejected or out-of-bounds value SHALL show a Traditional Chinese bound message with no dispatch. The remaining exploration root structure and the server-side skip maximum are unchanged, and the four-daypart payload vocabulary stays valid for the text commands and authored suggestion rows that still use it.

#### Scenario: The waiting frame renders the three operations
- **WHEN** the player opens Wait in exploration mode
- **THEN** the frame renders exactly 等待直到黎明, 睡眠至完全恢復, and 休息 N 小時 plus a back row, with no midnight, noon, or dusk control, and the card matching the router's focused key carries the focused treatment while the others do not

#### Scenario: The hours form dispatches whole seconds exactly once
- **WHEN** the player enters `1.5` hours in the 休息 form and confirms
- **THEN** exactly one `ui_action` is submitted — `explore.wait` with `seconds: 5400` — the form closes, and no resulting world time is displayed before the server snapshot arrives

#### Scenario: An out-of-bounds hours value errors without dispatching
- **WHEN** the player enters `12.01` hours (or clears the field) and confirms
- **THEN** the form shows the bounded Traditional Chinese message, emits no `ui_action`, and stays open for correction

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight or the client awaits its declared presentation revision
- **THEN** all three waiting controls are disabled and Enter or pointer activation on them submits nothing

### Requirement: explore.practice advances the clock for one declared skill
The production action registry SHALL register `explore.practice` with a payload of exactly `skill` (a bounded non-space key of at most 64 characters) and `seconds` (the same positive-integer bound as the `explore.wait` `seconds` payload). The adapter SHALL recheck `evaluate_skip_safety(actor)` against current canonical state and the declared skill through the rules' practice preflight before any advance, rejecting a combat, hostility, or unsafe-location context with the shared skip-safety rejection and an unknown or capped skill with the stable codes `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED`, each with zero clock advance and no surviving practice booking. Skill ownership and cap SHALL be revalidated at commit time against current canonical state. On success the adapter SHALL perform exactly one `AdvanceSource.SKIP` advance carrying the booking, so the clock's existing whole-hour practice settlement stage remains the sole writer of practice progression — plain rest, sleep, and unlabeled skips grant nothing — SHALL clear a stale booking on rejection paths, and SHALL publish a full snapshot at exactly one newer revision whose summary line (prefixed 修煉結束。) reaches the narrative through the escaped text path.

#### Scenario: Declared practice grows only the booked skill
- **WHEN** a safe actor who owns an uncapped active skill submits `explore.practice` with that `skill` and `seconds: 7200`
- **THEN** the clock advances exactly 7200 seconds with `AdvanceSource.SKIP`, only that skill's proficiency grows under the whole-hour settlement rule, and the full snapshot arrives at exactly one newer revision

#### Scenario: Unknown or capped practice skills advance nothing
- **WHEN** the submitted `skill` is unknown to the actor or already capped
- **THEN** the result carries the stable code `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED` with a Traditional Chinese message, the clock is unchanged, and no practice booking survives the rejection

#### Scenario: An ambiguous practice payload rejects at the validator
- **WHEN** an `explore.practice` payload omits `skill` or `seconds`, carries an extra field, or carries `seconds` outside the documented bound
- **THEN** the dispatcher rejects it with outcome `rejected` and stable code `malformed_payload` without invoking the adapter

#### Scenario: A failed advance rolls back clock and booking
- **WHEN** the shared skip advance raises after the booking was recorded
- **THEN** the clock growth and the booking are both restored, the rejection renders without a partial practice grant, and no skill progression is applied

## MODIFIED Requirements

### Requirement: The exploration dock is keyboard-first and re-homes the service submenus

In exploration mode the exploration dock SHALL own the action-dock surface and SHALL present the stable root Move, Look, Interact, Character, Quests, Inventory, and Wait in that order, composed only from the validated `exploration` panel, followed by Suggestions whenever the committed `context_actions` `suggestions` envelope's status is not `unavailable`. Move SHALL open the exit list and submit `explore.move` — and the move submenu SHALL be navigated by the keyboard router as a single-column list (up/down arrows cycle the move frame's items: the exit rows in order, then the `back` row; left/right arrows are no-ops), because the rendered exit-outlet grid is width-adaptive and the DOM-independent router SHALL NOT assume a fixed rendered column count; Look SHALL open room/entity/object inspection and submit `explore.look`; Interact SHALL first select a present target and then show only that target's server-authored affordances (scripted dialogue keywords as finite buttons, free-form dialogue, engage, or a `navigate`-kind guild/shop service entry); Character SHALL open the validated `character` panel; Quests and Inventory SHALL open the corresponding `services` panel submenus (guild quest log and inventory respectively); Wait SHALL open the three-operation waiting surface — 等待直到黎明 submitting the dawn daypart, 睡眠至完全恢復 submitting the sleep flag, and 休息 N 小時 opening the bounded custom-hours form — with every value parsed and validated server-side and no client-side clock derivation (the form's own hours-to-whole-seconds unit conversion at the presentation boundary is unit entry, not clock arithmetic, as pinned by the waiting-surface requirement); Suggestions SHALL open the suggestions frame owned by `webclient-options-surface`. A root entry whose capability surface is absent SHALL NOT render as a dead functional entry. Every exploration submenu — Move, Look, Interact, Wait, each target-affordance menu, and each scripted-keyword menu — SHALL end with an enabled back row that returns to its parent menu (the root has no back row), so pointer and keyboard users backtrack through the identical router path; Escape SHALL pop exactly one level. The dock SHALL render the approved command surface — the root as one row of icon-and-label tabs carrying the shortcut guidance hint, with the open entry marked by a gold fill and, where the committed payload makes the count derivable before the frame opens, a count badge equal to that count; and each submenu in the form its content calls for, beneath a breadcrumb naming the parent and current frames with a back control that pops exactly one level. A move submenu SHALL render its exits as an outlet of cells, each carrying the exit's direction as a leading glyph together with the destination's display name; the glyph SHALL come from a fixed table of canonical direction words, an exit label outside that table SHALL render verbatim in the glyph position rather than being mapped to a guessed direction, and the destination's display name SHALL be resolved by matching the row's server-authored `destination` node against the committed `local_map` nodes, with the glyph rendered alone when that node is absent from the committed lattice. A look or interact submenu SHALL render its entries as rows carrying a decorative icon, the server-authored name, a sub-line composed only of fields the payload carries, and a trailing chevron on rows that open a deeper frame. A target-affordance submenu SHALL render a head naming the target it is scoped to above that target's affordance rows, and a submenu that carries per-item detail SHALL render a detail pane naming the focused item and its availability. The focused row SHALL be marked by a gold fill plus a leading glyph and disabled rows SHALL be dimmed but focusable, in every one of those forms. The dock SHALL keep its rendered cells matched to the keyboard router's current frame at every navigation depth, so a back row, an Escape, or a pointer click on a parent row never leaves a deeper menu's cells on screen while the router navigates the parent. Arrow keys SHALL navigate, Enter SHALL open or submit, Escape SHALL pop exactly one level, disabled entries SHALL remain focusable for their explanation but SHALL NOT submit, and held/repeated Enter and any mutation while one is in flight or awaiting its declared presentation revision SHALL be suppressed. The service dock SHALL be re-homed under the Interact/Quests/Inventory roots instead of a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only arrows and Enter to open Move, select an exit, and later open Interact and choose a scripted keyword
- **THEN** the browser submits exactly `explore.move` then `explore.talk_scripted` with the server-authored IDs, and the refreshed panels appear without a typed command

#### Scenario: The dock renders the tab bar, the breadcrumb, and the per-kind panes
- **WHEN** the exploration dock is mounted and the player opens a submenu
- **THEN** the root renders as one row of icon-and-label tabs carrying the shortcut guidance hint with the open entry in a gold fill, a breadcrumb naming the parent and current frames appears with a back control, the submenu renders in the form its content calls for with a detail pane wherever the frame carries per-item detail, the focused row carries a gold fill plus a leading glyph, and disabled rows are dimmed but focusable

#### Scenario: A move row names the direction and the destination
- **WHEN** the move submenu renders an exit whose label is a canonical direction and whose `destination` node is present in the committed `local_map`
- **THEN** the row shows that direction's glyph together with the destination node's display name — not the raw exit identifier alone — and activating it submits the unchanged `explore.move` payload

#### Scenario: A named or dynamic exit keeps its own label
- **WHEN** the move submenu renders a named door or a dynamic wilderness exit whose label is not a canonical direction, or whose `destination` node is absent from the committed lattice
- **THEN** the label renders verbatim in the glyph position, no direction is guessed, and no destination line is invented

#### Scenario: A row renders no field the payload lacks
- **WHEN** the look submenu renders a present entity
- **THEN** the row shows its display name with its `kind` as the sub-line and renders no statistics line or portrait, because the exploration payload carries neither

#### Scenario: Suggestions is a root entry only when the envelope carries one
- **WHEN** the committed `suggestions` envelope's status is `unavailable`
- **THEN** the root presents no Suggestions entry
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the root presents Suggestions and opening it pushes the suggestions frame without submitting an action

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

#### Scenario: The move frame navigates as a single-column list
- **WHEN** the player presses the horizontal arrow keys while the move frame is open
- **THEN** focus stays on the currently focused item (ArrowLeft and ArrowRight are no-ops), and ArrowUp/ArrowDown cycle through the move frame's items — the exit rows in order, then the `back` row — regardless of the pane's rendered column count

#### Scenario: Mode change tears down the exploration dock atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration dock synchronously unloads, unregisters its keyboard handlers, discards local selection and speech state, and only the combat dock owns action-dock focus

### Requirement: Exploration actions reject stale, duplicate, and tampered input without mutation
Every exploration action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` mismatch SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. After those checks, commit-time domain revalidation is authoritative: an exit, NPC, monster, keyword, or daypart that changed between render and submit is handled against current canonical state, and a tampered `exit_ref`, `current_node`, `npc_id`, `monster_id`, `keyword_id`, `speech`, `daypart`, `skill`, or `seconds` that fails current revalidation SHALL be rejected with a stable code and Traditional Chinese message with no location, time, knowledge, dialogue, quest, inventory, combat, practice progression, or memory change. A transport drop after submit SHALL NOT be auto-retried; reconnect SHALL rebuild the dock from the new-epoch full snapshot and display the uncertain-result notice.

#### Scenario: Stale revision cannot move or talk twice
- **WHEN** an older-revision `explore.move` or `explore.talk_freeform` is submitted after a newer revision is active
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without changing location, clock, or dialogue

#### Scenario: Tampered exit or NPC references perform nothing
- **WHEN** a tampered `exit_ref`/`current_node` or `npc_id` fails current domain revalidation
- **THEN** the adapter rejects before any traversal, dialogue, or time advance, and canonical state is unchanged

#### Scenario: A target that left the room rejects at commit time
- **WHEN** an NPC, monster, or object referenced by `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, or `explore.engage` was present at render but has left the actor's location (or changed type/eligibility) by submit
- **THEN** the adapter re-resolves it from the actor's current location's present contents, rejects with a stable reason before the display, dialogue, or engage API is invoked, and no memory, intent, session, or time state changes

#### Scenario: Reconnect rebuilds exploration without replaying intent
- **WHEN** the transport disconnects after sending `explore.talk_freeform` and reconnects without another action
- **THEN** the new-epoch snapshot rebuilds the dock from canonical location, knowledge, and NPC state, the uncertain-result notice is shown, and no dialogue or mutation is automatically replayed
