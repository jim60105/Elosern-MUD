## MODIFIED Requirements

### Requirement: The keyboard-first exploration dock roots at the scene overview and opens dialogue directly

In exploration mode the exploration dock SHALL own the action-dock surface, and in dialogue mode it SHALL
stay mounted, hidden with the collapsed command region (`webclient-contextual-hud`), with its router
holding the same root; its root pane SHALL be composed only from the validated `exploration` panel, the
committed `local_map` panel, and the committed `context_actions` `suggestions` envelope, and SHALL present
the exit compass (`webclient-exit-compass`) for movement beside a scene overview whose rows are 人物 and 物件
and the footer, in that reading order. The overview SHALL carry no 出口 row, and the router's root frame SHALL
carry no exit item.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only the keyboard to aim an exit on the compass and press Enter, then activates a scripted dialogue host's chip, chooses 交談, and then presses the digit of the first choice the dialogue surface offers
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open` with the host's identity, then `explore.talk_scripted` with the server-authored keyword ID, and the refreshed panels appear without a typed command

#### Scenario: The overview shows exits, people, and objects in one frame
- **WHEN** the committed exploration panel carries two exits, one dialogue host, and one object
- **THEN** the exits are the exit compass's two targets rather than an overview row: the dock's root pane renders the compass, and the overview beside it renders the 人物 row with the host's chip, the 物件 row with the object's chip, and the footer with 查看房間 and 等待／休息, all in one frame with no tab to switch and no 出口 row

#### Scenario: An empty row is omitted
- **WHEN** the committed exploration panel carries exits but no people and no objects
- **THEN** the overview renders the footer only, no 人物 or 物件 label or empty row is present, and the compass still renders

#### Scenario: A disabled exit stays visible with its reason
- **WHEN** the room has a locked exit and the player aims it on the compass and presses Enter
- **THEN** its target is rendered disabled, its server-authored reason is readable in the compass readout, and no `ui_action` is emitted

#### Scenario: A person chip opens the verb popover in payload order
- **WHEN** the player activates the chip of a target whose affordances are 交談, 交易, and 戰鬥 in that payload order
- **THEN** a popover naming the target opens inside the command region listing 交談, 交易, 戰鬥, 查看, and the back row in that order, no `ui_action` is emitted, and the overview beneath takes no focus or activation


#### Scenario: 查看 in the popover looks at the target
- **WHEN** the player activates 查看 in a target's popover
- **THEN** exactly one `explore.look` with that target's identity is submitted


#### Scenario: 交談 enters the conversation in one step
- **WHEN** the player activates 交談 in a dialogue host's popover
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted and no frame is pushed, and the commit that makes the mode `dialogue` shows the dialogue surface with the host's opening line and choices while the dock has returned to the overview and is hidden with the collapsed command region


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
- **WHEN** the overview has three object chips and two person chips, focus is on the third object chip, and the player presses ArrowRight, then ArrowUp
- **THEN** ArrowRight moves focus to the first footer chip, and ArrowUp moves focus to the object chip at the same position within its row, because arrow keys step through reading order and rows exactly as before the exit row left the overview

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


#### Scenario: The 出口 row mirrors move rows in payload order
- **WHEN** the exits are resolved (by the compass, which replaced the 出口 row) the committed exits
- **THEN** it carries one target per `move` row, and a disabled row stays a visible disabled target carrying its server-authored reason, never omitted
- **AND** activating an enabled exit target submits the unchanged `explore.move` payload

#### Scenario: The 人物 row pairs interact chips with look chips
- **WHEN** the overview renders the 人物 row
- **THEN** it carries one chip per `interact` target in payload order, followed by one look chip per `look.entities` descriptor that has no `interact` descriptor
- **AND** activating a target chip opens that target's verb popover and activating a look chip submits `explore.look` for it


#### Scenario: The 物件 row looks at each object
- **WHEN** the overview renders the 物件 row
- **THEN** it carries one chip per `look.objects` descriptor, whose activation submits `explore.look` for that object


#### Scenario: The footer carries room look, waiting, and conditional suggestions
- **WHEN** the overview renders its footer
- **THEN** it holds 查看房間 (submitting `explore.look` for the room), 等待／休息, and — whenever the suggestions envelope's status is not `unavailable` — 建議, labelled `建議 (N)` with N the number of cards the suggestions frame will list when that number is positive


#### Scenario: An empty row loses its label too
- **WHEN** an overview row has no chip
- **THEN** the row is omitted together with its label


#### Scenario: Navigation-carried entries are absent from the overview
- **WHEN** the overview renders
- **THEN** it carries no 移動, 查看, 互動, 角色狀態, 任務, or 背包 entry: the character status, quest, and inventory surfaces are opened from the top navigation bar, which is their sole keyboard-visible stop


#### Scenario: Chips wrap and the overview scrolls inside the command region
- **WHEN** the overview's chips exceed the fixed command region's width or height
- **THEN** chips wrap inside the region and an overview taller than the region scrolls inside it with the focused chip kept in view


#### Scenario: The verb popover is a child card over the inert overview
- **WHEN** a target chip opens its verb popover
- **THEN** the popover is one child frame of the overview, rendered as a card inside the command region over the inert overview, with a head naming the target


#### Scenario: The popover lists server-authored affordances before look and back
- **WHEN** the popover renders a target's affordances
- **THEN** it lists them in payload order — 交談, which submits exactly one `explore.talk_open` with the target's identity and no further step, party invitation and dismissal, engage, delivery with its server-normalized parameters, and a `navigate`-kind guild or shop entry that opens its drawer without pushing a frame — followed by 查看, which submits `explore.look` for the target, and a back row


#### Scenario: The popover never borrows the dialogue surface or command line
- **WHEN** a target's popover renders
- **THEN** it offers no keyword list, no free-form dialogue row, and no path that borrows the command line: a conversation's topics and free-form speech are offered only by the dialogue surface once `explore.talk_open` has opened it


#### Scenario: A disabled 交談 explains in place
- **WHEN** a target's affordance list holds a disabled 交談
- **THEN** it stays focusable with its server-authored reason and submits nothing


#### Scenario: An affordance-less target still gets a popover
- **WHEN** a target has no mapped affordance and its chip is activated
- **THEN** it still opens a popover holding 查看 and the back row


#### Scenario: 等待／休息 opens the three-operation waiting frame
- **WHEN** the player activates 等待／休息
- **THEN** it opens the three-operation waiting frame — 等待直到黎明 submitting the dawn daypart, 睡眠至完全恢復 submitting the sleep flag, and 休息 N 小時 opening the bounded custom-hours form — with every value parsed and validated server-side and no client-side clock derivation (the form's own hours-to-whole-seconds unit conversion at the presentation boundary is unit entry, not clock arithmetic, as pinned by the waiting-surface requirement)


#### Scenario: 建議 opens the options-surface suggestions frame in place
- **WHEN** the player activates 建議 or 等待／休息
- **THEN** 建議 opens the suggestions frame owned by `webclient-options-surface` and both frames render inside the command region in place of the overview


#### Scenario: Every child frame backtracks through the identical router path
- **WHEN** the verb popover, the waiting frame, or the suggestions frame is open
- **THEN** it ends with an enabled back row returning to its parent, so pointer and keyboard users backtrack through the identical router path, and Escape pops exactly one level and restores the parent frame's previously focused entry (the chip that opened the popover or the child frame)


#### Scenario: A committed location change closes every child frame
- **WHEN** the committed location changes — a move from the exit compass, the minimap, or a typed command
- **THEN** the dock returns to the overview: any open popover or child frame is closed in the same commit that publishes the new room, and no frame from the previous room remains activatable


#### Scenario: A dialogue-mode commit collapses the dock's command region
- **WHEN** a commit changes the mode from `exploration` to `dialogue` — a conversation opened from 交談, a suggestion card, or a typed command
- **THEN** the dock returns to the overview in that commit, so no popover or child frame stays open over the conversation, and the command region that holds the dock is then collapsed for the rest of the conversation
- **AND** while the dock is collapsed its router claims no key and submits nothing, and leaving dialogue presents that overview again


#### Scenario: Arrow keys walk the chip grid
- **WHEN** the player presses ArrowLeft/ArrowRight or ArrowUp/ArrowDown on the overview
- **THEN** ArrowLeft and ArrowRight move to the previous and next chip in reading order, wrapping across the whole overview
- **AND** ArrowUp and ArrowDown move to the chip at the same position in the previous or next row, clamped to that row's last chip and wrapping across rows, and are no-ops when the overview has one row


#### Scenario: Enter activates the focused entry and child frames are lists
- **WHEN** the player presses Enter on an overview entry, or navigates a child frame
- **THEN** Enter opens or submits the focused entry, and the popover and every other child frame is navigated as a vertical list


#### Scenario: Disabled and in-flight entries cannot submit
- **WHEN** focus is on a disabled entry, or an action is in flight or awaiting its declared presentation revision
- **THEN** the disabled entry stays focusable for its explanation but does not submit, and held or repeated Enter and any mutation are suppressed


#### Scenario: Rendered cells always match the router's current frame
- **WHEN** a back row, an Escape, or a panel replacement changes the active frame
- **THEN** the dock keeps its rendered cells matched to the keyboard router's current frame at every depth, so no deeper frame's cells remain activatable while the router navigates the parent


#### Scenario: Service surfaces have no standalone Services root
- **WHEN** the player reaches the guild or shop surfaces
- **THEN** they are reached from the top navigation bar and from a target's `navigate` affordance instead of a standalone Services root, and the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged

#### Scenario: Exit chips carry canonical glyphs and resolved destinations
- **WHEN** the compass aims an exit
- **THEN** the readout carries the exit's direction glyph from the fixed table of canonical direction words and, while enabled, the destination's display name resolved from the committed `local_map` nodes
- **AND** an exit label outside that table is a portal that renders verbatim with no guessed direction, and a destination absent from the committed lattice falls back to the exit's own label
