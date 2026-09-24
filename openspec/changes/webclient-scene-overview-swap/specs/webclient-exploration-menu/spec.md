## ADDED Requirements

### Requirement: The exploration dock is keyboard-first and roots at the scene overview

In exploration mode the exploration dock SHALL own the action-dock surface, and its root frame SHALL
be one scene overview composed only from the validated `exploration` panel and the committed
`context_actions` `suggestions` envelope. The overview SHALL present, in this reading order:

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
server-authored affordances in payload order — scripted dialogue as 交談 opening the target's
scripted-keyword frame (finite keyword buttons), free-form dialogue borrowing the command line for
`explore.talk_freeform`, party invitation and dismissal, engage, delivery with its server-normalized
parameters, and a `navigate`-kind guild or shop entry that opens its drawer without pushing a frame —
followed by 查看, which submits `explore.look` for the target, and a back row. A target with no
mapped affordance SHALL still open a popover holding 查看 and the back row. 等待／休息 SHALL open the
three-operation waiting frame — 等待直到黎明 submitting the dawn daypart, 睡眠至完全恢復 submitting
the sleep flag, and 休息 N 小時 opening the bounded custom-hours form — with every value parsed and
validated server-side and no client-side clock derivation (the form's own hours-to-whole-seconds unit
conversion at the presentation boundary is unit entry, not clock arithmetic, as pinned by the
waiting-surface requirement); 建議 SHALL open the suggestions frame owned by `webclient-options-surface`.
Both SHALL render inside the command region in place of the overview. Every child frame — the verb
popover, the scripted-keyword frame, the waiting frame, and the suggestions frame — SHALL end with an
enabled back row returning to its parent, so pointer and keyboard users backtrack through the
identical router path; Escape SHALL pop exactly one level and SHALL restore the parent frame's
previously focused entry (the chip that opened the popover or the child frame).

When the committed location changes — a move from an exit chip, the minimap, or a typed command —
the dock SHALL return to the overview: any open popover or child frame SHALL be closed in the same
commit that publishes the new room, and no frame from the previous room SHALL remain activatable.

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
- **WHEN** a player uses only arrows and Enter to activate an exit chip, then activates a scripted dialogue host's chip, chooses 交談, and chooses a keyword
- **THEN** the browser submits exactly `explore.move` then `explore.talk_scripted` with the server-authored IDs, and the refreshed panels appear without a typed command

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

#### Scenario: 交談 keeps the scripted keyword frame
- **WHEN** the player activates 交談 in a scripted dialogue host's popover and then activates the back row of the keyword frame
- **THEN** the keyword frame opens with the host's finite keyword buttons and no `ui_action`, and the back row returns to the host's popover with 交談 focused

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
- **WHEN** focus moves to a disabled `explore.engage` row in a target's popover and the player presses Enter
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

## REMOVED Requirements

### Requirement: The exploration dock is keyboard-first and re-homes the service submenus
**Reason**: The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §7) replaces the Move / Look / Interact / Wait / Suggestions tab root with one scene overview, and the two-step interaction workspace with a verb popover. Most of this requirement's scenarios (the tab bar, the interaction workspace, the single-column move frame, backing out of the Look submenu) describe frames the player can no longer reach, so a MODIFIED block cannot keep them.
**Migration**: "The exploration dock is keyboard-first and roots at the scene overview" restates the root, the popover, the waiting and suggestions frames, the back and Escape rules, the drawer re-homing, the suppression rules, and the mode teardown. Tests annotated with the old ID re-anchor to the new one.
