# Spec Delta

## MODIFIED Requirements

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The party window (whose tabs hold members, the bag and equipment, status, skills and lineage), the shop window, the quest board and the lore reference SHALL each render in exactly one place — its window or drawer — and SHALL NOT be present in the DOM while closed. The stage SHALL carry no permanently visible column of reference panels.

#### Scenario: Every reference surface is reachable in two actions
- **WHEN** a player seeks a reference surface from the top navigation bar or the dock's root frame
- **THEN** each drawer is opened either by the dock frame that owns its surface, or by a single labelled control inside a drawer that already presents the same read model, or by a surface this capability names elsewhere as an opener for it, and no reference surface requires more than two actions to reach

#### Scenario: Opening a drawer disturbs no dock contract
- **WHEN** a drawer opens
- **THEN** no dock root item, menu frame, menu key, or the meaning of Escape changes

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no party window, shop window, quest board or lore reference element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each reference surface and party window tab is reached in at most two actions, and the narrative caption stays in the bottom band's message region

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1451x790 and 2560x1440 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's

### Requirement: The command line is a collapsible row docked on the message region's top edge
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor, containing — in this order — a prompt chevron, the command input field with its send control, a hint cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the top navigation bar's tool group.

#### Scenario: The anchor is a 44px row on the message region's top edge
- **WHEN** the `command-line` anchor renders in any mode
- **THEN** it is one row 44px tall docked to the top edge of the bottom band's message region: its lower edge coincides with the band's upper edge, it extends from the left HUD island column's right edge to the right edge of the band's left two thirds in every mode — so in dialogue mode, where the message region spans the whole band, it stops short of the dialogue host's portrait — and it overlays the lowest strip of the stage box, never the band and never the message text

#### Scenario: The line is collapsed by default and never persisted
- **WHEN** the shell mounts, and when the player expands and reloads
- **THEN** the command line starts collapsed on every mount, its expanded state is client-local and never persisted, and no stored presentation state can open it or keep it open

#### Scenario: Collapsed hides the row but keeps the field's state
- **WHEN** the row is collapsed
- **THEN** it is hidden with `display:none`, so the bar and its input field leave the layout, the accessibility tree, and the tab order, while the input field stays in the DOM with its preserved identifier and keeps any unsent draft and history-walk state

#### Scenario: The ⌨ toggle reports the row's state
- **WHEN** the message region renders in any mode
- **THEN** it carries, at its bottom-right corner, a labelled ⌨ toggle control that reports the row's state through `aria-expanded` and names the row through `aria-controls`; the toggle is rendered in every mode that renders the message region, never covers the message text (the text's scroll region keeps its last line clear of the toggle), and is unaffected by the committed narrative, the dialogue choice list, or the dock frame

#### Scenario: Exactly three paths expand the line
- **WHEN** the player presses `/` while no editable control is focused, activates the ⌨ toggle while the row is collapsed, or borrows the line for free-form dialogue
- **THEN** the command line expands and focus moves into its input field only after the row is rendered, on exactly these three paths

#### Scenario: Exactly two paths collapse the line
- **WHEN** Escape is pressed in the input field, or a send the field accepts clears it
- **THEN** the line collapses on exactly these two paths, with focus moved to the current mode's focus home (the action dock, or in dialogue mode the dialogue choice list while it is rendered and the message window's page surface otherwise) before the row is hidden

#### Scenario: Toggle-close keeps focus; rejected sends stay open
- **WHEN** the ⌨ toggle is activated while the row is expanded, or a send is rejected — offline, mutations locked, a mutation in flight, or, for a borrowed free-form send, a presentation phase other than active
- **THEN** the toggle collapses the row and leaves focus on the toggle, and a rejected send leaves the row expanded with the typed text and focus in the field

#### Scenario: Losing focus never collapses the row
- **WHEN** the field loses focus by any other means (a pointer activation elsewhere, a drawer or overlay opening)
- **THEN** the row does not collapse

#### Scenario: The expanded bar keeps its clearances and drops only hints
- **WHEN** the bar is expanded at 1451x790 or at any larger viewport up to the chrome cap, and when horizontal space is insufficient
- **THEN** the expanded bar does not overlap the action dock, the narrative caption, the bottom band, or any HUD island anchor; the hint cluster is dropped first; and the input field, its send control, and the history controls are never dropped (the command line and its toggle are absent from the layout in creation mode, per the visibility matrix)

#### Scenario: The field is one action away
- **WHEN** the shell mounts in exploration mode
- **THEN** the command-line row is hidden with `display:none`, the input field is present in the DOM but outside the tab order, the ⌨ toggle is rendered at the message region's bottom-right with `aria-expanded="false"`, and pressing `/` or activating the toggle once renders the row and puts focus in the input field

#### Scenario: The expanded row keeps its geometry at the minimum viewport
- **WHEN** the command line is expanded at the 1451x790 reference viewport and at 2560x1440, in exploration mode and in dialogue mode
- **THEN** the row is 44px tall (±1px), its lower edge sits on the bottom band's upper edge, its horizontal extent runs from the left HUD column's right edge to the right edge of the band's left two thirds, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, its send control, and the history controls are all rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first, and no input field, send control, or history control is removed

#### Scenario: Escape collapses and keeps the draft
- **WHEN** the player expands the command line with `/`, types a draft, presses Escape, and then activates the ⌨ toggle
- **THEN** Escape sends nothing, moves focus to the action dock, and hides the row, and the toggle expands the row again with the same draft in the field and focus in it

#### Scenario: A successful send collapses the line
- **WHEN** the player expands the command line, types a command, and presses Enter while the client is connected, unlocked, and has no mutation in flight
- **THEN** exactly one command is sent, the field clears, focus moves to the action dock, and the row is hidden with `display:none`

#### Scenario: A rejected send keeps the line open
- **WHEN** the player presses Enter in the expanded command line while mutations are locked or a mutation is in flight
- **THEN** the typed text stays in the field, focus stays in the field, and the row stays expanded

#### Scenario: The toggle closes the open line
- **WHEN** the command line is expanded and the player activates the ⌨ toggle with the pointer
- **THEN** the row is hidden, the toggle reports `aria-expanded="false"`, and focus is on the toggle

#### Scenario: The free-form borrow expands the line
- **WHEN** the command line is collapsed and the player activates the dialogue choice list's `⌨ 自由對話` row
- **THEN** the row expands, focus moves into the input field, and no action is dispatched until the player sends

#### Scenario: No opener or chip is rendered in the bar
- **WHEN** the bar renders expanded in exploration, combat, or dialogue mode
- **THEN** no quick-word chip, letter badge, chip cluster, or overlay or drawer opener (信件, 圖鑑, 稱號冊, 設定, 說明, 角色肖像圖庫) is present in the bar

#### Scenario: The expanded state is never restored from storage
- **WHEN** the player expands the command line and reloads the page
- **THEN** the reloaded shell renders the command line collapsed

#### Scenario: Escape in dialogue returns to the message window
- **WHEN** the committed mode is dialogue, the player expands the command line with `/`, and presses Escape
- **THEN** nothing is sent, the row is hidden, and focus is on the dialogue's focus home — the choice list while it is shown, else the message window's page surface — never on the hidden action dock or the document body
