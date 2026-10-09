# Spec Delta

## Purpose
Room actions (re-read the room, let time pass, ask for suggestions) sit beside the values they act on, and one readout line explains whatever the player aims at or hovers.

## ADDED Requirements

### Requirement: The exploration screen roots at the compass, the rail, and room actions
In exploration mode the screen SHALL be composed of the exit compass, the shared readout, and the 建議 pill in the command panel, the presence rail on the stage, and the room-action buttons on the place card. The command panel SHALL hold no chip row, footer, or key-hint line, and the router's exploration root frame SHALL carry no item, so the compass, the rail, and the place-card actions own their keys outside the router.

#### Scenario: The command panel holds the compass, the pill, and the readout
- **WHEN** the committed exploration panel carries exits, people, and objects
- **THEN** the command panel renders the exit compass, the readout, and the 建議 pill (while suggestions are not `unavailable`), and no chip, footer row, or `action-dock-description` element

#### Scenario: The exploration root frame is empty but resolvable
- **WHEN** the dock is at the exploration root
- **THEN** the router's current frame is the root with zero items, it does not degrade into the single disabled marker row, and no key is claimed by a root item

#### Scenario: Tab order is compass, rail, place-card actions, pill
- **WHEN** the exploration screen has focus on the compass and the player presses Tab repeatedly
- **THEN** focus moves through the rail, the place card's 查看房間 and 等待 buttons, and the 建議 pill, each zone one tab stop with a visible focus ring

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only the keyboard to aim an exit and press Enter, then presses the digit of a scripted host's rail entry, chooses 交談 on the verb card, and presses the digit of the first dialogue choice
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open`, then `explore.talk_scripted` with the server-authored keyword ID

#### Scenario: Mode change tears down the exploration controls atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the compass, rail, place-card actions, pill, and any open centred card unload in that commit and discard their local state

#### Scenario: Exploration panel unavailable
- **WHEN** the exploration panel is unavailable
- **THEN** the compass, rail, place-card buttons, and pill are not rendered and the dock keeps its existing degraded root

### Requirement: The place card carries 查看房間 and 等待 in exploration only
`PlaceCard` SHALL stay display-first and, only in exploration mode while the exploration panel is available, render a 查看房間 icon button (`aria-label="查看房間"`) beside the location heading and a 等待 button (hourglass icon plus label) beside the world time. In every other mode and state the place card SHALL render no button.

#### Scenario: Buttons appear in exploration
- **WHEN** the mode is exploration and the exploration panel is available
- **THEN** the place card renders 查看房間 beside the location and 等待 beside the time

#### Scenario: Buttons are absent elsewhere
- **WHEN** the mode is combat, dialogue, or creation, or the exploration panel is unavailable
- **THEN** the place card renders no button and no tab stop

#### Scenario: 查看房間 submits the room look
- **WHEN** the player activates 查看房間
- **THEN** exactly one `explore.look` for the room is submitted, byte-identical to the former footer chip's payload

#### Scenario: Activation respects the submission gate
- **WHEN** an action is in flight or the client awaits its declared presentation revision and the player activates 查看房間
- **THEN** nothing is submitted

### Requirement: 等待 opens the wait card through ChoiceCard
Activating 等待 SHALL open the centred `ChoiceCard` with the wait rows and a trailing `✕ 返回`, without a server request. 休息 N 小時 SHALL open the existing bounded `RestForm`, and the other rows SHALL submit the unchanged `explore.wait` payloads. The card SHALL trap focus, close on Escape or `✕ 返回` with focus returned to the 等待 button, and close on a committed location change or mode change.

#### Scenario: Opening is local and returns focus
- **WHEN** the player activates 等待 and then presses Escape
- **THEN** no `ui_action` is emitted, the card closes, and focus is on the 等待 button

#### Scenario: Wait rows submit the existing payloads
- **WHEN** the player activates 等待直到黎明
- **THEN** exactly one `explore.wait` with the `dawn` daypart is submitted and the card closes

#### Scenario: Rest opens the form
- **WHEN** the player activates 休息 N 小時
- **THEN** the existing bounded rest form opens and nothing is submitted until it is confirmed

#### Scenario: A move closes the card
- **WHEN** the wait card is open and a commit changes the location
- **THEN** the card is closed in that commit

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight or the client awaits its declared presentation revision
- **THEN** the wait rows are disabled and activating them submits nothing

### Requirement: Sleeping asks whether to enter dream collaboration first
Activating 睡眠至完全恢復 in the wait card SHALL open a modal question, 進入夢境協作？, with 是, 否, and a close control at its top right, without a server request. 是 SHALL submit one `explore.wait` with the `sleep` and `dream` flags, 否 SHALL submit one with only `sleep`, and the close control or Escape SHALL cancel the sleep and submit nothing. The wait card SHALL NOT carry a separate dream row.

#### Scenario: 是 sleeps into the dream
- **WHEN** the player activates 睡眠至完全恢復 and then 是
- **THEN** exactly one `ui_action` is submitted, `explore.wait` with `sleep: true` and `dream: true`, and the question and the wait card close

#### Scenario: 否 is a plain sleep
- **WHEN** the player activates 睡眠至完全恢復 and then 否
- **THEN** exactly one `ui_action` is submitted, `explore.wait` with `sleep: true` and no `dream` flag

#### Scenario: Closing cancels the sleep
- **WHEN** the player activates 睡眠至完全恢復 and then the close control, or presses Escape
- **THEN** no `ui_action` is emitted, the question closes, and focus returns to the wait card's 睡眠至完全恢復 row

#### Scenario: The question traps focus and honours the lock
- **WHEN** the question is open, or a mutation is in flight or awaiting revision
- **THEN** focus stays inside the question on 是, and 是 and 否 are disabled with the same reason text as the other wait rows while locked

### Requirement: The 建議 pill opens the suggestions card
The command panel SHALL render a 建議 pill at its top right whenever the committed suggestions status is not `unavailable`, labelled `建議 N` with N the number of cards the suggestions card lists when that number is positive, and the pill SHALL be absent otherwise. Activating it SHALL open the centred suggestions `ChoiceCard` locally, without a server request, with a trailing `✕ 返回`.

#### Scenario: Pill label with cards
- **WHEN** the committed suggestions are `ready` with four cards
- **THEN** the pill reads `建議 4`

#### Scenario: Pill hidden when unavailable
- **WHEN** the committed suggestions status is `unavailable`
- **THEN** no pill is rendered

#### Scenario: Opening is local
- **WHEN** the player activates the pill
- **THEN** the suggestions card opens, no `ui_action` is emitted, and Escape closes it with focus on the pill

#### Scenario: The generating state keeps the pill without a count
- **WHEN** the committed status is `generating`
- **THEN** the pill reads `建議` and the card shows the muted generating state

### Requirement: The shared readout resolves its content by a fixed priority
The readout SHALL show, in priority order: a transient blocked-move flash (warn tone, about 1.6 s); whatever is aimed or hovered, among the compass aim, a rail entry, a place-card button (`查看房間` over `重新觀察四周`, `等待` over `讓時間流逝、休息或睡眠`), and the 建議 pill; and otherwise the idle summary `出口 N · 在場 M` in the quiet tone. Server-authored disabled reasons SHALL appear here and nowhere else in the exploration screen.

#### Scenario: Flash beats everything
- **WHEN** a blocked move flashes while the pointer rests on a rail entry
- **THEN** the readout shows the flash in the warn tone and returns to the hovered entry when the flash ends

#### Scenario: Place-card buttons explain themselves
- **WHEN** the pointer rests on the 等待 button
- **THEN** the readout shows `等待` over `讓時間流逝、休息或睡眠`

#### Scenario: Idle summary
- **WHEN** nothing is aimed, hovered, or flashing
- **THEN** the readout shows `出口 N · 在場 M` in the quiet tone

#### Scenario: Leaving a source falls back to the next
- **WHEN** the pointer leaves the 建議 pill while the compass still has an aim
- **THEN** the readout shows the compass aim

### Requirement: The controls reference documents the room actions
The controls reference SHALL list the place-card actions, the 建議 pill, the tab order across the exploration zones, and the card keys (digits, Enter, Escape).

#### Scenario: The help overlay lists the exploration zones
- **WHEN** the player opens the help overlay in exploration
- **THEN** it lists the compass, rail, place-card actions, pill, and card keys

### Requirement: Retired exploration surfaces are gone and room actions are verified in the live client
`SceneOverview`, its footer row, the `exploration.wait` and `exploration.suggestions` router frames, the waiting-screen cards, and the `.elosern-root` duplicates of their classes SHALL be removed, and the room actions SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080.

#### Scenario: No retired surface renders
- **WHEN** the exploration screen renders
- **THEN** no scene overview, footer chip, waiting-screen, or suggestions pane element exists in the DOM

#### Scenario: Geometry at both viewports
- **WHEN** the exploration screen is shown at 1451×790 and at 1920×1080 with the place card buttons, the pill, and a centred card open
- **THEN** the buttons fit the place card without truncating the location heading's accessible name, the pill does not overlap the compass, and the card is centred and fully visible
