## RENAMED Requirements

- FROM: `### Requirement: The place card carries 查看房間 and 等待 in exploration only`
- TO: `### Requirement: The place card carries 查看房間 and 休息 in exploration only`

## MODIFIED Requirements

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
- **THEN** focus moves through the rail, the place card's 查看房間 and 休息 buttons, and the 建議 pill, each zone one tab stop with a visible focus ring

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only the keyboard to aim an exit and press Enter, then presses the digit of a scripted host's rail entry, chooses 交談 on the verb card, and presses the digit of the first dialogue choice
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open`, then `explore.talk_scripted` with the server-authored keyword ID

#### Scenario: Mode change tears down the exploration controls atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the compass, rail, place-card actions, pill, and any open centred card unload in that commit and discard their local state

#### Scenario: Exploration panel unavailable
- **WHEN** the exploration panel is unavailable
- **THEN** the compass, rail, place-card buttons, and pill are not rendered and the dock keeps its existing degraded root

### Requirement: The place card carries 查看房間 and 休息 in exploration only
`PlaceCard` SHALL stay display-first and, only in exploration mode while the exploration panel is available and the exploration dock is at its root frame (no sub-dock or deeper frame owning the surface), render a 查看房間 icon button (`aria-label="查看房間"`) beside the location heading and a 休息 button (hourglass icon plus label) beside the world time. In every other mode and state the place card SHALL render no button.

#### Scenario: Buttons appear in exploration
- **WHEN** the mode is exploration and the exploration panel is available
- **THEN** the place card renders 查看房間 beside the location and 休息 beside the time

#### Scenario: The 休息 button keeps its hooks
- **WHEN** the 休息 button renders
- **THEN** its visible label is 休息, it keeps the hourglass icon, `data-testid="place-card-wait"`, and the class `place-card__action--wait`, and no element on the place card is labelled 等待

#### Scenario: Buttons are absent elsewhere
- **WHEN** the mode is combat, dialogue, or creation, or the exploration panel is unavailable
- **THEN** the place card renders no button and no tab stop

#### Scenario: 查看房間 submits the room look
- **WHEN** the player activates 查看房間
- **THEN** exactly one `explore.look` for the room is submitted, byte-identical to the former footer chip's payload

#### Scenario: Activation respects the submission gate
- **WHEN** an action is in flight or the client awaits its declared presentation revision and the player activates 查看房間
- **THEN** nothing is submitted

### Requirement: The shared readout resolves its content by a fixed priority
The readout SHALL show, in priority order: a transient blocked-move flash (warn tone, about 1.6 s); whatever is aimed or hovered, among the compass aim, a rail entry, a place-card button (`查看房間` over `重新觀察四周`, `休息` over `保持清醒等待，或入睡恢復精力`), and the 建議 pill; and otherwise the idle summary `出口 N · 在場 M` in the quiet tone. Server-authored disabled reasons SHALL appear here and nowhere else in the exploration screen.

#### Scenario: Flash beats everything
- **WHEN** a blocked move flashes while the pointer rests on a rail entry
- **THEN** the readout shows the flash in the warn tone and returns to the hovered entry when the flash ends

#### Scenario: Place-card buttons explain themselves
- **WHEN** the pointer rests on the 休息 button
- **THEN** the readout shows `休息` over `保持清醒等待，或入睡恢復精力`

#### Scenario: Idle summary
- **WHEN** nothing is aimed, hovered, or flashing
- **THEN** the readout shows `出口 N · 在場 M` in the quiet tone

#### Scenario: Leaving a source falls back to the next
- **WHEN** the pointer leaves the 建議 pill while the compass still has an aim
- **THEN** the readout shows the compass aim

### Requirement: The controls reference documents the room actions
The controls reference SHALL list the place-card actions, the 建議 pill, the tab order across the exploration zones, and the card keys (digits, Enter, Escape). Its 休息 entry SHALL describe the two layers (first 等待 or 睡眠, then 等待直到黎明, 睡眠至完全恢復, or a duration), keep the description of the sleep handoff that follows an accepted sleep, and state that `‹` returns one layer and `✕` closes the card.

#### Scenario: The help overlay lists the exploration zones
- **WHEN** the player opens the help overlay in exploration
- **THEN** it lists the compass, rail, place-card actions, pill, and card keys

#### Scenario: The help overlay describes the rest entry
- **WHEN** the player reads the place card's 休息 entry in the help overlay
- **THEN** it contains `打開休息卡片：先選「等待」或「睡眠」，再選等待直到黎明、睡眠至完全恢復，或指定時長。`, still describes the sleep handoff, and states the `‹` and `✕` behavior, and no help entry calls the place card button 「等待」 or lists the retired row 等待 N 小時

### Requirement: Retired exploration surfaces are gone and room actions are verified in the live client
`SceneOverview`, its footer row, the `exploration.wait` and `exploration.suggestions` router frames, the waiting-screen cards, the wait card's row list (its `wait-card-row` rows and the separate `rest-card` duration card), and the `.elosern-root` duplicates of their classes SHALL be removed, and the room actions SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080.

#### Scenario: No retired surface renders
- **WHEN** the exploration screen renders
- **THEN** no scene overview, footer chip, waiting-screen, or suggestions pane element exists in the DOM

#### Scenario: No wait row renders at either layer
- **WHEN** the rest entry is open at its first layer or with either second-layer form
- **THEN** no `wait-card-row` or `rest-card` element exists, and the published client view carries no wait-row list

#### Scenario: Geometry at both viewports
- **WHEN** the exploration screen is shown at 1451×790 and at 1920×1080 with the place card buttons, the pill, and a centred card open, including the rest entry's first layer and each second-layer form
- **THEN** the buttons fit the place card without truncating the location heading's accessible name, the pill does not overlap the compass, and the card is centred and fully visible

## REMOVED Requirements

### Requirement: 等待 opens the wait card through ChoiceCard
**Reason**: The place card button is now 休息 and opens a two-layer entry (choice tiles, then a wait or sleep form under one shell) instead of a `ChoiceCard` with three rows and a trailing `✕ 返回`; the row-based scenarios no longer describe the surface.
**Migration**: Replaced by "休息 opens a two-layer rest entry" and "The rest entry steps back and closes with defined focus" (plus the first-layer, context, shell, wait-form, and test-hook requirements added here). Tests annotated with this requirement are re-mounted to the replacement identifiers the traceability tool generates after sync.

## ADDED Requirements

### Requirement: 休息 opens a two-layer rest entry
Activating 休息 SHALL open, without a server request, a first layer offering 等待 and 睡眠; choosing one SHALL open that mode's second-layer form. Each of the four options SHALL submit exactly its existing `explore.wait` payload, and a sent dispatch SHALL close the entry. A committed location change or mode change SHALL close the entry at either layer.

#### Scenario: Opening is local and focuses the 等待 tile
- **WHEN** the player activates 休息
- **THEN** no `ui_action` is emitted, the first layer opens, and focus is on the 等待 tile

#### Scenario: A tile opens its form with the duration input focused
- **WHEN** the player presses `1` on the first layer, or activates the 睡眠 tile with Enter
- **THEN** the 等待 form (respectively the 睡眠 form) opens in the second layer, nothing is submitted, and focus is on that form's duration input

#### Scenario: The wait options submit the existing payloads
- **WHEN** the player activates 等待直到黎明, or enters `1.5` and activates 等待此時長
- **THEN** exactly one `explore.wait` with `{daypart: "dawn"}` (respectively `{seconds: 5400}`) is submitted and the entry closes

#### Scenario: The sleep options submit the existing payloads
- **WHEN** the player activates 睡眠至完全恢復, or enters `2` and activates 以此時長入睡
- **THEN** exactly one `explore.wait` with `{sleep: true}` (respectively `{sleep: true, sleep_mode: "duration", seconds: 7200}`) is submitted, the entry closes, and the server-owned sleep handoff, dream question, and continuation surfaces follow unchanged

#### Scenario: A move closes the entry at either layer
- **WHEN** the first layer or a second-layer form is open and a commit changes the location or the mode
- **THEN** the entry is closed in that commit

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight, the client awaits its declared presentation revision, or the session is not live
- **THEN** no tile, form button, or digit submits or opens anything that submits, and the one reason `上一個行動尚未完成，請稍候。` is exposed

### Requirement: The rest entry steps back and closes with defined focus
On the second layer, `‹` or Escape SHALL return to the first layer with focus on the tile the player came from. `✕` on either layer, and Escape on the first layer, SHALL close the whole entry with focus returned to the place card's 休息 button. Neither control SHALL submit anything.

#### Scenario: The first layer closes to the 休息 button
- **WHEN** the first layer is open and the player presses Escape, or activates its `✕`
- **THEN** the entry closes, nothing is submitted, and focus is on the 休息 button

#### Scenario: Stepping back returns to the tile the player came from
- **WHEN** the 睡眠 form is open and the player activates `‹`, or presses Escape inside the form
- **THEN** the first layer is shown again with focus on the 睡眠 tile, and nothing is submitted

#### Scenario: The second layer closes to the 休息 button
- **WHEN** either second-layer form is open and the player activates its `✕`
- **THEN** the whole entry closes, nothing is submitted, and focus is on the 休息 button

### Requirement: The rest entry's first layer presents two choice tiles
The first layer SHALL be a modal dialog named 等待或睡眠 with the visible caption 度過時間, two tile buttons, `1` 等待 (hint 保持清醒，讓時間流逝) and `2` 睡眠 (hint 入睡，恢復精力), each with a line icon, and a corner `✕` labelled 關閉並回到探索 (title 關閉). It SHALL hold no inputs. Its keys SHALL be `1`/`2` to pick, arrows to move with wrap, Home/End to jump, Enter/Space to activate, and Escape to close, with Tab trapped across the `✕` and the tiles.

#### Scenario: The tiles render their labels and hints
- **WHEN** the first layer opens
- **THEN** it shows the caption 度過時間, the 等待 tile with badge `1` and hint 保持清醒，讓時間流逝, the 睡眠 tile with badge `2` and hint 入睡，恢復精力, and the corner `✕`, and its accessible name is 等待或睡眠

#### Scenario: Arrow keys move focus with wrap
- **WHEN** focus is on the 睡眠 tile and the player presses `→`, or focus is on the 等待 tile and the player presses `←` or `↑`
- **THEN** focus moves to the other tile, and Home or End moves focus to the 等待 or 睡眠 tile respectively

#### Scenario: Tab stays in the first layer
- **WHEN** the first layer is open and the player presses Tab or Shift+Tab repeatedly
- **THEN** focus cycles only among the `✕` and the two tiles

#### Scenario: Narrow anchors stack the tiles
- **WHEN** the card's anchor is narrower than `calc(320px * var(--ui-scale))`
- **THEN** the tiles stack vertically, each laid out with its icon left, text in the middle, and badge right, and they remain tile buttons rather than rows

#### Scenario: Locked tiles stay focusable and explain themselves
- **WHEN** the first layer is open while the submission gate is locked
- **THEN** both tiles carry `aria-disabled="true"`, stay focusable, are described by a `role="status"` line reading `上一個行動尚未完成，請稍候。`, and `1`, `2`, Enter, and Space open nothing

### Requirement: The choice tiles show only client-known context
Each tile SHALL show one context line when its source is committed and omit only that line when it is not: the 等待 tile `現在 HH:MM` from the clock part of the committed world-time label, and the 睡眠 tile `精力 N%（stage label）` from the committed status panel's fatigue row for the controlled body. A context line SHALL never wrap. The tiles SHALL show no value the client does not hold, such as hours until dawn or whether the place is safe.

#### Scenario: Both context lines render
- **WHEN** the committed world time is `春季 3 日 ‧ 22:40` and the controlled body's fatigue row reads 62% with the label 輕度疲勞
- **THEN** the 等待 tile reads `現在 22:40` and the 睡眠 tile reads `精力 62%（輕度疲勞）`

#### Scenario: A missing source omits only its line
- **WHEN** no world time is committed, or the status panel carries no fatigue row for the controlled body
- **THEN** the corresponding tile renders without its context line and keeps its badge, icon, label, and hint

#### Scenario: Possession reads the controlled body's row
- **WHEN** the player possesses a companion and the status panel carries the owner's row and the companion's row
- **THEN** the 睡眠 tile shows the row whose identity is the controlled body's

#### Scenario: The widest line fits on one line
- **WHEN** the fatigue row reads 100% with the label 精神充沛 at the default card width
- **THEN** `精力 100%（精神充沛）` renders on a single line

### Requirement: The rest entry's second layer shares one shell around the wait and sleep forms
The second layer SHALL be a modal dialog labelled by a visible caption naming the mode, 等待 or 睡眠, holding that mode's form and, after the form in tab order, two corner buttons: `‹` at the top left (label and title 返回上一層) and `✕` at the top right (label 關閉並回到探索, title 關閉). Tab SHALL stay within the form controls and the two corner buttons, and Escape inside the form or on a corner button SHALL step back.

#### Scenario: The wait shell
- **WHEN** the player picks 等待
- **THEN** a dialog captioned 等待 holds the wait form, then `‹` and `✕`, and Tab from the last form control reaches `‹`, then `✕`, then the first form control

#### Scenario: The sleep shell carries one caption
- **WHEN** the player picks 睡眠
- **THEN** a dialog captioned 睡眠 holds the sleep form with its 睡眠至完全恢復 button, duration input, and 以此時長入睡 button, and the text 睡眠模式 appears nowhere in the dialog

#### Scenario: Escape on a corner button steps back
- **WHEN** focus is on the second layer's `✕` and the player presses Escape
- **THEN** the first layer is shown with focus on the tile the player came from

#### Scenario: Duration inputs are centred
- **WHEN** either form renders inside the shell
- **THEN** its duration input text is centred and the form has no background or border of its own

### Requirement: The wait form mirrors the sleep form
The wait form SHALL offer a 等待直到黎明 button, then a 或指定時長（小時） number input labelled 等待時長（小時） with default `1`, the hint 最長 12 小時，可輸入小數。, and a 等待此時長 submit button. It SHALL validate exactly as the sleep form does: fractional hours convert once to whole seconds between 1 and 43200, and an invalid entry shows `請輸入有效時長，最短 1 秒、最長 12 小時。` without dispatching.

#### Scenario: A valid duration converts once
- **WHEN** the player enters `0.25` and activates 等待此時長
- **THEN** the form emits exactly 900 seconds and shows no resulting world time

#### Scenario: An invalid duration errors without dispatching
- **WHEN** the input is empty, `0`, or `13` and the player activates 等待此時長
- **THEN** the form shows `請輸入有效時長，最短 1 秒、最長 12 小時。`, nothing is submitted, and the input stays editable

#### Scenario: A locked form submits nothing
- **WHEN** the submission gate is locked while the wait form is open
- **THEN** 等待直到黎明 and 等待此時長 are disabled and Enter in the input submits nothing

### Requirement: The rest entry exposes stable test hooks
The rest entry SHALL carry these `data-testid` hooks: the first layer `wait-card` (with `data-card-kind="wait"`), each tile `wait-card-tile` with `data-tile="wait"` or `data-tile="sleep"`, the first layer's `✕` `wait-card-close`, the second-layer shell `wait-form-card` or `sleep-card`, its corners `rest-step-back` and `rest-step-close`, the wait form `wait-form` with `wait-form-dawn` on its first button, and the unchanged `sleep-form` and `sleep-form-recovery`.

#### Scenario: Hooks at each layer
- **WHEN** the rest entry is opened, then the 等待 tile is picked, then `‹` is activated and the 睡眠 tile is picked
- **THEN** the hooks `wait-card`, two `wait-card-tile` elements, and `wait-card-close` exist on the first layer; `wait-form-card`, `wait-form`, `wait-form-dawn`, `rest-step-back`, and `rest-step-close` exist on the wait layer; and `sleep-card`, `sleep-form`, `sleep-form-recovery`, `rest-step-back`, and `rest-step-close` exist on the sleep layer
