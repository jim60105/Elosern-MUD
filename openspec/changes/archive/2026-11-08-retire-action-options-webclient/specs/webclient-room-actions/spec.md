## MODIFIED Requirements

### Requirement: The exploration screen roots at the compass, the rail, and room actions
In exploration mode the screen SHALL be composed of the exit compass and the shared readout in the command panel, the presence rail on the stage, and the room-action buttons on the place card. The command panel SHALL hold no chip row, footer, or key-hint line, and the router's exploration root frame SHALL carry no item, so the compass, the rail, and the place-card actions own their keys outside the router.

#### Scenario: The command panel holds the compass, the pill, and the readout
- **WHEN** the committed exploration panel carries exits, people, and objects
- **THEN** the command panel renders the exit compass and the readout, and no 建議 pill, chip, footer row, or `action-dock-description` element

#### Scenario: The exploration root frame is empty but resolvable
- **WHEN** the dock is at the exploration root
- **THEN** the router's current frame is the root with zero items, it does not degrade into the single disabled marker row, and no key is claimed by a root item

#### Scenario: Tab order is compass, rail, place-card actions, pill
- **WHEN** the exploration screen has focus on the compass and the player presses Tab repeatedly
- **THEN** focus moves through the rail and the place card's 查看房間 and 休息 buttons, each zone one tab stop with a visible focus ring, and the retired 建議 pill is not a tab stop

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only the keyboard to aim an exit and press Enter, then presses the digit of a scripted host's rail entry, chooses 交談 on the verb card, and presses the digit of the first dialogue choice
- **THEN** the browser submits exactly `explore.move`, then `explore.talk_open`, then `explore.talk_scripted` with the server-authored keyword ID

#### Scenario: Mode change tears down the exploration controls atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the compass, rail, place-card actions, and any open centred card unload in that commit and discard their local state

#### Scenario: Exploration panel unavailable
- **WHEN** the exploration panel is unavailable
- **THEN** the compass, rail, and place-card buttons are not rendered and the dock keeps its existing degraded root

### Requirement: The shared readout resolves its content by a fixed priority
The readout SHALL show, in priority order: a transient blocked-move flash (warn tone, about 1.6 s); whatever is aimed or hovered, among the compass aim, a rail entry, and a place-card button (`查看房間` over `重新觀察四周`, `休息` over `保持清醒等待，或入睡恢復精力`); and otherwise the idle summary `出口 N · 在場 M` in the quiet tone. Server-authored disabled reasons SHALL appear here and nowhere else in the exploration screen.

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
- **WHEN** the pointer leaves a place-card button while the compass still has an aim
- **THEN** the readout shows the compass aim

### Requirement: The controls reference documents the room actions
The controls reference SHALL list the place-card actions, the tab order across the exploration zones, and the card keys (digits, Enter, Escape). Its 休息 entry SHALL describe the two layers (first 等待 or 睡眠, then 等待直到黎明, 睡眠至完全恢復, or a duration), keep the description of the sleep handoff that follows an accepted sleep, and state that `‹` returns one layer and `✕` closes the card.

#### Scenario: The help overlay lists the exploration zones
- **WHEN** the player opens the help overlay in exploration
- **THEN** it lists the compass, rail, place-card actions, and card keys

#### Scenario: The help overlay describes the rest entry
- **WHEN** the player reads the place card's 休息 entry in the help overlay
- **THEN** it contains `打開休息卡片：先選「等待」或「睡眠」，再選等待直到黎明、睡眠至完全恢復，或指定時長。`, still describes the sleep handoff, and states the `‹` and `✕` behavior, and no help entry calls the place card button 「等待」 or lists the retired row 等待 N 小時

### Requirement: Retired exploration surfaces are gone and room actions are verified in the live client
`SceneOverview`, its footer row, the `exploration.wait` and `exploration.suggestions` router frames, the waiting-screen cards, the wait card's row list (its `wait-card-row` rows and the separate `rest-card` duration card), and the `.elosern-root` duplicates of their classes SHALL be removed, and the room actions SHALL be verified by `agent-browser` in the live client at 1451×790 and 1920×1080.

#### Scenario: No retired surface renders
- **WHEN** the exploration screen renders
- **THEN** no scene overview, footer chip, waiting-screen, or suggestions card element exists in the DOM

#### Scenario: No wait row renders at either layer
- **WHEN** the rest entry is open at its first layer or with either second-layer form
- **THEN** no `wait-card-row` or `rest-card` element exists, and the published client view carries no wait-row list

#### Scenario: Geometry at both viewports
- **WHEN** the exploration screen is shown at 1451×790 and at 1920×1080 with the place card buttons and a centred card open, including the rest entry's first layer and each second-layer form
- **THEN** the buttons fit the place card without truncating the location heading's accessible name, the compass and the readout share the command panel without overlap, and the card is centred and fully visible

## REMOVED Requirements

### Requirement: The 建議 pill opens the suggestions card
**Reason**: The AI action-suggestions surface is retired end to end: no pill opens a suggestions card, because the `suggestions` envelope that fed it no longer exists (`retire-action-options-webclient`, `retire-action-options-service`, `retire-context-actions-suggestions`).
**Migration**: None. The exploration command panel keeps the exit compass and the shared readout; the place card keeps its 查看房間 and 休息 actions.
