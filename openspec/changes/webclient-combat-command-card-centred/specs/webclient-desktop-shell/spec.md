## MODIFIED Requirements

### Requirement: The action dock's row region and detail panes are direct children of its pane host
The action dock's pane host SHALL lay out the active frame's focusable row region and any displayed
detail pane as direct children of that host: side by side when a detail pane is displayed in the band's command region, and stacked with the detail pane as a strip below the row region inside the combat command card. The exploration root is the explicit exception, composing a compass beside a right column containing the 建議 pill and the readout. The
action dock's pane host SHALL be the only host of the dock's row region: no reference drawer body
renders it.

#### Scenario: A frame with a detail pane pairs direct children under the host
- **WHEN** the active dock frame shows a detail pane with the rows (a generic
  detail frame or the combat skill frame with its dedicated detail)
- **THEN** the focusable row region and the visible detail pane are siblings
  whose parent is the pane host, no intermediate layout element wraps either
  of them, and the pair renders side by side in the band's command region and
  stacked, the detail pane as a strip below the row region, in the combat command card

#### Scenario: A frame without a detail pane renders the row region directly
- **WHEN** the active dock frame renders without a detail pane (any full-width
  frame)
- **THEN** the focusable row region is the pane host's only dock-menu child and
  fills the host's full width, with no wrapper element rendered

#### Scenario: A reference drawer body never hosts the row region
- **WHEN** any reference drawer is open in exploration or combat mode
- **THEN** the page contains no dock-menu row region and no dock detail pane
  outside the action dock's pane host

#### Scenario: The scene overview is the host's only child
- **WHEN** the exploration root renders and a person's verb card opens over the stage
- **THEN** the pane host carries the compass and its right column, whose pill and readout remain mounted and inert with the command panel beneath the card; the card renders in the stage's `choices` anchor, outside the action dock, and no detail pane renders

#### Scenario: The dock menu adds no anonymous layout container
- **WHEN** the dock menu component renders under the pane host
- **THEN** it contributes no anonymous layout container between the host and either child; its rendered roots are the row region and, when shown, the detail pane itself

#### Scenario: The combat skill detail pane is a sibling of the row region
- **WHEN** the combat skill detail pane replaces the generic detail
- **THEN** it is a sibling of the row region under the same host, and the row region gains no wrapper for either case

#### Scenario: The scene overview is the one exception to the direct-child rule for row regions
- **WHEN** the exploration root renders
- **THEN** the compass is beside a right column holding the 建議 pill at its top and the shared readout at its bottom; the column renders no chip row and no reason strip, no detail pane renders, and the root fills the unchanged pane host

#### Scenario: A verb popover renders outside the pane host
- **WHEN** a person's verb card is open over the stage
- **THEN** it renders in the stage's `choices` anchor, not inside the action dock or its pane host, so the pane host's children are the same while it is open

### Requirement: Required desktop surfaces remain visible and usable
The stage SHALL give the message window and the action dock one fixed-height bottom band whose
height comes from one shared band-height token: the narrative occupies the band's message region as
the bounded message window on the left two thirds, the action dock fills the band's command region
on the right third, in combat mode the action dock stands as the centred combat command card over the
stage while the message window spans the whole band and the command region collapses, and in dialogue
mode the message window spans the whole band while the command region collapses.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1451x790
- **THEN** the message window, the brand, the top-meta surface, the top navigation bar with its tool group, the place card, every HUD island its own rule renders, the action dock, and the command-line toggle are present without overlapping the narrative input path, and one `/` press renders the command line with its input field focused

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 2560x1440
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command after exactly one opening action (`/` or the ⌨ toggle)

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1451x790 or 2560x1440 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at the 1451x790 reference viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the message window, and the command-line toggle remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport with the command line collapsed
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, a settings control, and the tool group, and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the action dock

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the message window's page can display
- **THEN** the player reaches the complete retained log in one action through the window's `日誌` control

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows an ok-green "● 已連線" indicator and no location or time, the place card shows the current location label resolved from the committed panels and the world date/time, and no raw mode label is rendered

#### Scenario: The top-meta location names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status panel location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the place card's location reads 西部丘陵與谷地, the raw room key is rendered neither in the place card nor anywhere in the top bar, and no composed string pairing the two appears

#### Scenario: The location falls back when the map panel cannot supply a name
- **WHEN** the `local_map` panel is absent, unavailable, or names a current node that its own nodes do not carry or that carries an empty label
- **THEN** the place card's location states the committed status panel's actor location label, and states the card's unavailable placeholder only when neither panel supplies a label

#### Scenario: The action dock fills the command region with its mode's root and one legend
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one panel — filling the band's command region outside combat, and as the combat command card centred over the stage in combat — with a shortcut-legend strip only outside exploration and creation, its exploration root renders as the exit compass beside the 建議 pill and the shared readout (people and objects stand on the stage's presence rail, and the room actions on the place card) and its combat root as a vertical command list with the focused row in a muted-gold fill, its current frame's rows or chips render with a shape-marked focused entry and dimmed but focusable disabled entries, and a breadcrumb with a back control appears below the root frame on every frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (a deep combat frame), or a person's verb card, the wait card, or the suggestions card is open over the stage, at 1451x790 or 2560x1440
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region or, in combat, inside the combat command card, the message window's box is unchanged within the mode, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the height of the command region or, in combat, of the combat command card
- **THEN** the rows scroll within the pane host, the dock's chrome (the breadcrumb and the mode-appropriate legend strip) remains visible and fixed around the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1451x790
- **THEN** the message window spans the whole band and carries the host's name plate and the paged line, the command region is not rendered, and once the line is fully shown every choice row, the free-dialogue row, the move row and the exit row are reachable in the choice list centred over the stage, never inside the message window, without document-level scrolling and without the window or the band changing size

#### Scenario: Required surfaces stay visible through the supported viewport range
- **WHEN** the shell renders at 1451x790 or any larger viewport up to the chrome factor's cap
- **THEN** the brand, the top-meta pill, the place card, the action dock (in every playing mode except dialogue, where the command region collapses) and the command-line toggle are visible

#### Scenario: Each HUD island follows its own contextual-HUD rule
- **WHEN** the shell renders the HUD islands
- **THEN** each island is visible whenever its own contextual-HUD rule renders it: the vitals island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, and the party island while the party is non-empty

#### Scenario: The dock and the message window are never permanently closable
- **WHEN** the player closes surfaces in any mode
- **THEN** the action dock and the message window remain part of the layout, and the dock's collapse in dialogue mode lasts exactly as long as the committed mode is `dialogue`

#### Scenario: The command line is never permanently closable
- **WHEN** the shell renders any mode that renders the command line
- **THEN** the command line is collapsed by default and its input field is reachable in exactly one action - `/` outside an editable control, or the ⌨ toggle - while every other surface MAY be opened on demand and closed

#### Scenario: A reference surface opens in the shared drawer within two actions
- **WHEN** the player reaches for the skill book, the bag and equipment, the shop, the quest board, the lore reference, or the character status
- **THEN** the surface renders in a drawer laid over the stage in the shared reference workspace, reached in at most two actions from the top navigation bar or from a person's verb card

#### Scenario: The top navigation bar carries the mode's entry points
- **WHEN** the shell renders the top navigation bar
- **THEN** it carries a labelled control for each navigation-presented entry of the current mode's home surface - the character status, quest, and inventory entries - a labelled control for the map and settings surfaces, and the tool group that the top-navigation tool-group requirement defines, which carries the help control, and activating a bar control opens its surface in one action without pushing a keyboard menu frame

#### Scenario: The bar names no screen the player is already on
- **WHEN** the bar renders in exploration or combat
- **THEN** it carries no entry that names the screen the player is already on - no 探索 or 戰鬥 home entry - because the stage itself is that screen, and returning the dock to its root stays on Escape and the dock's back controls

#### Scenario: The map control stands beside the minimap's own entry point
- **WHEN** the bar renders while the minimap also offers its own control
- **THEN** the bar's map control is an additional entry point beside the minimap's own control

#### Scenario: The foundation claims desktop only
- **WHEN** the shell's acceptance scope is stated
- **THEN** the foundation targets desktop only and claims no mobile acceptance

#### Scenario: The top bar is 48px tall
- **WHEN** the shell renders the top bar
- **THEN** the top bar is 48px tall

#### Scenario: The dock renders its mode's root form
- **WHEN** the action dock renders its root in exploration or combat
- **THEN** its exploration root renders as the exit compass on the left and the 建議 pill and the shared readout in the right column (people and objects stand on the stage's presence rail, and the room actions on the place card), its combat root renders as a vertical list of icon-and-label command rows with the focused entry marked by a muted-gold fill, and its remaining region renders the current frame's rows or chips

#### Scenario: The dock carries the defined shortcut legend
- **WHEN** the action dock renders
- **THEN** it carries the shortcut legend only in the modes the contextual-HUD legend requirement defines; exploration renders no permanent key-hint element

#### Scenario: Rows mark focus, absence of focus, and disablement distinctly
- **WHEN** the dock renders rows or chips
- **THEN** the focused row or chip is marked by a muted-gold fill plus a leading glyph, unfocused rows are bordered, and disabled rows are dimmed but focusable for their explanation

#### Scenario: Non-root frames show a breadcrumb and a detail pane
- **WHEN** the dock is below its root frame
- **THEN** it renders a breadcrumb naming the parent and current frames with a back control and renders each frame's rows in the form that frame calls for: navigation rows or the combat forms - with a detail pane (beside the rows in the band, below them in the combat command card) that names the focused item, its availability, and the next key action wherever the frame carries one

#### Scenario: The band height never follows its contents
- **WHEN** the dock carries the exploration root (with or without a person's verb card or a room card open over the stage), the combat frames, or an empty pane host, in any mode and under any narrative
- **THEN** outside combat all of them render inside the same command-region box whose height comes from the shared band-height token, in combat every frame renders inside the combat command card's fixed box above the band, so the message window and the action dock never overlap and neither clips the other at a supported viewport
