# Spec Delta

## Purpose
The presence rail shows who and what is in the room on the stage floor, so people and objects stop competing with exits and room actions in the command panel; the centred choice card carries every choice that needs a list.

## ADDED Requirements

### Requirement: The exploration dock roots at the compass and the presence rail and keeps the footer overview

In exploration mode the exploration dock SHALL own the action-dock surface, and in dialogue mode it SHALL stay mounted, hidden with the collapsed command region, with its router holding the same root. Its root pane SHALL present the exit compass in the command panel and a footer-only scene overview (查看房間, 等待／休息, and 建議), while people and objects are presented by the presence rail on the stage (`webclient-presence-rail`). The router's root frame SHALL carry only the footer items.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only the keyboard to aim an exit on the compass and press Enter, then presses the digit of a scripted dialogue host's rail entry, chooses 交談 on the verb card, and then presses the digit of the first choice the dialogue surface offers
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open` with the host's identity, then `explore.talk_scripted` with the server-authored keyword ID, and the refreshed panels appear without a typed command

#### Scenario: The exploration screen shows the compass, the rail, and the footer
- **WHEN** the committed exploration panel carries two exits, one dialogue host, and one object
- **THEN** the command panel renders the exit compass with two targets and the footer with 查看房間 and 等待／休息, and the stage renders the presence rail with the host's medallion and the object's lozenge, with no 人物 or 物件 row in the overview

#### Scenario: An empty rail renders nothing
- **WHEN** the committed exploration panel carries exits but no people and no objects
- **THEN** the overview renders the footer only and the presence rail renders no entry and no placeholder

#### Scenario: A disabled exit stays aimable with its reason
- **WHEN** the room has a locked exit and the player aims it on the compass and presses Enter
- **THEN** its target is rendered disabled, its server-authored reason is readable in the compass readout, and no `ui_action` is emitted

#### Scenario: Waiting and suggestions open child frames in the panel
- **WHEN** the player activates 等待／休息, presses Escape, activates 建議, and presses Escape
- **THEN** each opens its frame inside the command region in place of the overview, and each Escape returns to the overview with the footer chip that opened it focused

#### Scenario: Movement closes the verb card and returns the dock to the overview
- **WHEN** the verb card or the waiting frame is open and the player moves by activating a minimap node
- **THEN** the commit that publishes the new room shows the new room's overview as the dock's only frame, the verb card and standee are gone, and no medallion, card row, or waiting card from the previous room remains activatable

#### Scenario: Arrow keys step through the footer chips
- **WHEN** the footer carries three chips and focus is on the first
- **THEN** ArrowRight moves to the second chip and ArrowLeft from the first wraps to the last

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces available and the dock renders its root
- **THEN** the overview carries no 角色狀態, 任務, or 背包 entry, and those surfaces are opened from the top navigation bar

#### Scenario: Escape from a re-homed service or character sub-view leaves the exploration root clean
- **WHEN** the player opens the Character, Quests, or Inventory drawer from the top navigation while the dock is at the overview and presses Escape
- **THEN** the drawer closes without sending an action, the overview remains the dock's current frame with no sub-dock active, and no exploration frame bookkeeping is corrupted or re-rendered

#### Scenario: The overview scrolls inside the fixed panel
- **WHEN** the room carries more chips than the command region can show and the player arrows to the last chip
- **THEN** the chips wrap inside the region, the overview scrolls inside it with the focused chip in view, and the command region's box is unchanged

#### Scenario: Mode change tears down the exploration dock atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration dock synchronously unloads, unregisters its keyboard handlers, discards local selection and speech state, and only the combat dock owns action-dock focus

#### Scenario: The compass mirrors move rows in payload order
- **WHEN** the compass resolves the committed exits
- **THEN** it carries one target per `move` row, and a disabled row stays a visible disabled target carrying its server-authored reason, never omitted
- **AND** activating an enabled exit target submits the unchanged `explore.move` payload

#### Scenario: The footer carries room look, waiting, and conditional suggestions
- **WHEN** the overview renders its footer
- **THEN** it holds 查看房間 (submitting `explore.look` for the room), 等待／休息, and — whenever the suggestions envelope's status is not `unavailable` — 建議, labelled `建議 (N)` with N the number of cards the suggestions frame will list when that number is positive

#### Scenario: Navigation-carried entries are absent from the overview
- **WHEN** the overview renders
- **THEN** it carries no 移動, 查看, 互動, 角色狀態, 任務, or 背包 entry: the character status, quest, and inventory surfaces are opened from the top navigation bar, which is their sole keyboard-visible stop

#### Scenario: Chips wrap and the overview scrolls inside the command region
- **WHEN** the overview's chips exceed the fixed command region's width or height
- **THEN** chips wrap inside the region and an overview taller than the region scrolls inside it with the focused chip kept in view

#### Scenario: 等待／休息 opens the three-operation waiting frame
- **WHEN** the player activates 等待／休息
- **THEN** it opens the three-operation waiting frame — 等待直到黎明 submitting the dawn daypart, 睡眠至完全恢復 submitting the sleep flag, and 休息 N 小時 opening the bounded custom-hours form — with every value parsed and validated server-side and no client-side clock derivation (the form's own hours-to-whole-seconds unit conversion at the presentation boundary is unit entry, not clock arithmetic, as pinned by the waiting-surface requirement)

#### Scenario: 建議 opens the options-surface suggestions frame in place
- **WHEN** the player activates 建議 or 等待／休息
- **THEN** 建議 opens the suggestions frame owned by `webclient-options-surface` and both frames render inside the command region in place of the overview

#### Scenario: Every child frame backtracks through the identical router path
- **WHEN** the waiting frame or the suggestions frame is open
- **THEN** it ends with an enabled back row returning to its parent, so pointer and keyboard users backtrack through the identical router path, and Escape pops exactly one level and restores the parent frame's previously focused entry (the footer chip that opened the child frame)

#### Scenario: A committed location change closes every child frame
- **WHEN** the committed location changes — a move from the compass, the minimap, or a typed command
- **THEN** the dock returns to the overview: any open verb card or child frame is closed in the same commit that publishes the new room, and no frame from the previous room remains activatable

#### Scenario: A dialogue-mode commit collapses the dock's command region
- **WHEN** a commit changes the mode from `exploration` to `dialogue` — a conversation opened from 交談, a suggestion card, or a typed command
- **THEN** the dock returns to the overview in that commit, so no verb card or child frame stays open over the conversation, and the command region that holds the dock is then collapsed for the rest of the conversation
- **AND** while the dock is collapsed its router claims no key and submits nothing, and leaving dialogue presents that overview again

#### Scenario: Enter activates the focused entry and child frames are lists
- **WHEN** the player presses Enter on an overview entry, or navigates a child frame
- **THEN** Enter opens or submits the focused entry, and every child frame is navigated as a vertical list

#### Scenario: Disabled and in-flight entries cannot submit
- **WHEN** focus is on a disabled entry, or an action is in flight or awaiting its declared presentation revision
- **THEN** the disabled entry stays focusable for its explanation but does not submit, and held or repeated Enter and any mutation are suppressed

#### Scenario: Rendered cells always match the router's current frame
- **WHEN** a back row, an Escape, or a panel replacement changes the active frame
- **THEN** the dock keeps its rendered cells matched to the keyboard router's current frame at every depth, so no deeper frame's cells remain activatable while the router navigates the parent

#### Scenario: Service surfaces have no standalone Services root
- **WHEN** the player reaches the guild or shop surfaces
- **THEN** they are reached from the top navigation bar and from a target's `navigate` affordance instead of a standalone Services root, and the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged

### Requirement: The presence rail shows people and objects on the stage floor
In exploration mode the stage SHALL render `PresenceRail` right-aligned on the stage floor, inset left of the right-hand island column: interact targets as gold medallions, other present entities as dashed muted medallions, then a separator and objects as steel lozenges, in `ExplorationMenu.overviewMenu` order, each with a name plate. It SHALL yield to the foe line-up in combat, hide during dialogue and under a centred card, and render nothing when empty.

#### Scenario: Entries follow the overview order
- **WHEN** the room has two interact targets, one bystander, and two objects
- **THEN** the rail shows two gold medallions, one dashed muted medallion, a separator, and two lozenges, each with its name plate, in that order

#### Scenario: A medallion shows the face crop or the initial
- **WHEN** an interact target's `portrait_ref` resolves in the art catalog
- **THEN** its medallion shows the face crop through the existing face-rect data

#### Scenario: A medallion without a portrait shows the initial
- **WHEN** an interact target has no `portrait_ref` or its catalog entry is unavailable
- **THEN** its medallion shows the first character of the target's name

#### Scenario: The rail is hidden outside exploration and under a card
- **WHEN** the mode is combat or dialogue, or a centred card is open
- **THEN** the rail is not visible and takes no focus

#### Scenario: An empty room renders no rail
- **WHEN** the room has no people and no objects
- **THEN** the rail renders no element and no placeholder

### Requirement: The rail shows at most six entries and folds the rest into a count
At most six rail entries SHALL show. Beyond six, the sixth slot SHALL become `＋N`, which opens the centred card listing the remaining entries with objects marked ◇, and picking a row there SHALL activate that entry as if it had been picked on the rail.

#### Scenario: Seven entries
- **WHEN** the room has seven rail entries
- **THEN** five entries show and the sixth slot reads `＋2`

#### Scenario: Overflow pick activates the entry
- **WHEN** the player opens `＋2` and picks a listed person
- **THEN** the person's verb card opens exactly as if its medallion had been activated

### Requirement: Rail entries activate by the payload each entry already carries
An interact target SHALL open the person-focus verb card. A bystander or an object SHALL submit its existing `explore.look` payload directly. Hovering or focusing an entry SHALL lift the entry and show `<name>` over the affordance summary (`交談／公會服務`) or `查看` in the shared readout. Entries SHALL fade in and out as the panel changes.

#### Scenario: A bystander is looked at
- **WHEN** the player activates a bystander's dashed medallion
- **THEN** exactly one `explore.look` with that entity's identity is submitted, byte-identical to the former 人物 look chip

#### Scenario: An object is looked at
- **WHEN** the player activates an object's lozenge
- **THEN** exactly one `explore.look` for that object is submitted

#### Scenario: Hover explains
- **WHEN** the pointer rests on a guild clerk's medallion
- **THEN** the readout shows the clerk's name over the affordance summary

### Requirement: The rail is one keyboard composite and digits pick entries
The rail SHALL be one tab stop after the compass, with ←/→ moving between entries and Enter activating the focused entry. While no card is open, digits 1–9 SHALL activate the Nth visible rail entry from anywhere in the exploration screen except the command line and drawers, and while a card is open the card SHALL own the digits.

#### Scenario: Digit picks the Nth entry
- **WHEN** no card is open, focus is on the compass, and the player presses `2` with three rail entries
- **THEN** the second entry is activated

#### Scenario: A card owns the digits
- **WHEN** a verb card is open and the player presses `2`
- **THEN** the card's second row is activated and the rail is not

#### Scenario: Arrow keys move along the rail
- **WHEN** the rail has focus on its first entry and the player presses ArrowRight
- **THEN** focus moves to the second entry and Enter activates it

### Requirement: The person-focus verb card is client-local and replaces the verb popover
Activating an interact target SHALL open the person focus with no server request and no router frame. The rail SHALL fade out, the command panel SHALL become inert and dim to about 35% opacity, and the place card and minimap SHALL step away. The target's standee SHALL slide into the `actor-right` anchor, the message window SHALL name the target as speaker, and a centred card SHALL list the target's verbs followed by `✕ 返回`.

#### Scenario: A target without a portrait uses the dialogue silhouette
- **WHEN** the focused target has no portrait
- **THEN** the standee shows the same silhouette, initial, and 無肖像 treatment as the dialogue screen

#### Scenario: Opening is local
- **WHEN** the player activates an interact target's medallion
- **THEN** the card opens with the target's verbs in `verbMenuFor` order followed by `✕ 返回`, and no `ui_action` is emitted and no router frame is pushed

#### Scenario: The command panel is inert while focused
- **WHEN** the verb card is open
- **THEN** the command panel is `inert` at about 35% opacity and takes no focus

#### Scenario: Closing restores the opener
- **WHEN** the player presses Escape or activates `✕ 返回`
- **THEN** the standee slides out, the rail returns, and focus returns to the medallion that opened the card

### Requirement: Verb card rows submit the payloads the popover rows submitted
Each verb row SHALL submit exactly the payload the former popover row submitted: 交談 submits one `explore.talk_open`, 交易 and 公會服務 open their drawer without a frame, 戰鬥 submits `explore.engage`, 查看 submits `explore.look` for the target and closes the card, and a disabled row stays focusable with its server-authored reason and submits nothing.

#### Scenario: 交談 enters dialogue continuously
- **WHEN** the player activates 交談 on the verb card
- **THEN** exactly one `explore.talk_open` with the host's identity is submitted, and the commit that makes the mode `dialogue` shows the dialogue surface with the same standee already on stage

#### Scenario: A navigate verb opens its drawer
- **WHEN** the player activates a guild clerk's 公會服務 row
- **THEN** the quest drawer opens from the unchanged `services` payload and no router frame is pushed

#### Scenario: 戰鬥 submits engage
- **WHEN** the player activates an enabled 戰鬥 row
- **THEN** exactly one `explore.engage` with the target's identity is submitted

#### Scenario: A disabled row explains without submitting
- **WHEN** the player focuses a disabled 交談 or 戰鬥 row and presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` is emitted

#### Scenario: An affordance-less target still gets a card
- **WHEN** an interact target has no mapped affordance
- **THEN** its card holds 查看 and `✕ 返回`

#### Scenario: A generative host offers one 交談 row
- **WHEN** the card of an `LLMNPC` host opens
- **THEN** it lists one 交談 row and no free-form row

### Requirement: A departed person closes the card
If the focused person is no longer in the committed `interact` list, the card SHALL close in the same commit, the standee SHALL leave, the rail SHALL return, and the readout SHALL flash `<name> 已經離開了。`. A move that changes the committed location SHALL close the card as well.

#### Scenario: The focused person leaves
- **WHEN** the verb card is open and a commit removes that person from the room
- **THEN** the card closes in that commit and the readout flashes `<name> 已經離開了。`

### Requirement: ChoiceCard is the one centred card shell
`ChoiceCard` SHALL render the card frame, digit-badged rows, the rule before a trailing row, the active-row fill and caret, and the staggered entrance with motion-level handling, as one keyboard composite with one tab stop (ArrowUp and ArrowDown wrap, Home and End, digits 1–N, Enter and Space, Escape, `aria-activedescendant`). New consumers SHALL append a trailing `✕ 返回` row and emit `pick(key)` and `back`, and the card SHALL trap focus and return it to its opener on close.

#### Scenario: Keys and digits
- **WHEN** a card with four rows has focus and the player presses `3`, then ArrowDown, then Enter
- **THEN** the third row is picked, then the active row moves, then the active row is picked

#### Scenario: Escape emits back
- **WHEN** a card has focus and the player presses Escape
- **THEN** `back` is emitted and no `pick` is emitted

#### Scenario: Focus is trapped and restored
- **WHEN** a card opens from a rail medallion and then closes
- **THEN** Tab does not leave the card while open, and focus returns to that medallion on close

### Requirement: The dialogue screen does not change when it renders through ChoiceCard
`DialogueChoices` SHALL keep its view-model logic (picks, `⌨ 自由對話`, `↦ 移動…`, `✕ 結束對話`, and the exits view) and render through `ChoiceCard`, with no visual or behavioral change to the dialogue screen.

#### Scenario: Existing dialogue behavior is unchanged
- **WHEN** the existing dialogue choice tests run unchanged
- **THEN** they pass, including digit picks, the exits view, and the entrance behavior

### Requirement: The presence rail and verb card are verified in the live client at two viewports
The rail, the verb card, the standee handover into dialogue, and the overflow card SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080.

#### Scenario: Geometry at both viewports
- **WHEN** a room with a portrait-bearing host, a bystander, and an object is shown at 1451×790 and at 1920×1080
- **THEN** the rail sits right-aligned above the band without overlapping the right-hand island column, and the verb card is centred and fully visible

#### Scenario: Continuous handover into dialogue
- **WHEN** 交談 is activated from the verb card at both viewports
- **THEN** the standee does not leave and re-enter between the card and the dialogue surface
