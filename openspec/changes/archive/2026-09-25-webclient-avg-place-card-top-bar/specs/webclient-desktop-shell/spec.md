## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the bottom band's message region as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the place card, the action dock and the command line visible at 1920x1080, 1440x900, and
1280x720, and with each HUD island visible whenever its own contextual-HUD rule renders it (the vitals
island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, the party island while the party is
non-empty). The action dock, the narrative caption, and the
command line SHALL NOT be permanently closable, and the command line's input field SHALL be present and
usable without an opening action; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the top navigation bar or from the action dock's
root frame, and SHALL be closable in one action that returns focus to the control that opened it. The shell SHALL render a top navigation bar carrying
a labelled control for each navigation-presented entry of the current mode's home surface - the character
status, quest, and inventory entries - and a labelled control for the map, settings, and help surfaces;
activating a bar control SHALL open its surface in one action and SHALL NOT push a keyboard menu frame.
The bar SHALL carry no entry that names the screen the player is already on - no 探索 or 戰鬥 home
entry - because the stage itself is that screen; returning the dock to its root stays on Escape and
the dock's back controls.
The map and settings controls on the bar are additional entry points; the
map, settings and help surfaces SHALL each remain reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as its brand and the connection state in the top bar's top-meta
surface, with the connected state marked by an ok-green dot paired with a label, and SHALL show the
current location and the world date/time only in the stage's place card, resolved as the
contextual-HUD place-card requirement states - never in the top bar, and never a raw mode label in
place of location. The top bar SHALL be 48px tall. The action dock SHALL render as the approved command surface: a
panel filling the bottom band's command region (the band's right third), whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a muted-gold fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to focus the
command input). The focused row SHALL be marked by a muted-gold fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.
The stage SHALL give the narrative caption and the action dock one fixed-height bottom band - the
message region on the left two thirds and the command region on the right third - whose height comes
from one shared band-height token and never depends on the frame the dock carries, on the mode, or on
the narrative: the interaction workspace, the waiting frame, the combat frames, and an empty pane host
all render inside the same command-region box, so the narrative caption and the action dock never
overlap and neither clips the other at a supported viewport. A frame whose rows exceed the region
SHALL scroll inside the pane host while the tab bar and breadcrumb stay fixed above it. In dialogue
mode the narrative caption SHALL keep the message region's fixed box, and the host, the latest line,
the choice rows, the free-form input and the exit control SHALL all stay reachable at 1280x720 by
scrolling inside the caption, never by growing it.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the top navigation bar, the place card, every HUD island its own rule renders, the action dock, and the command line with its visible input field are present without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command without any opening action

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1440x900 or 1280x720 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at either supported viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the narrative caption, and the command line remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's root tab bar

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

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

#### Scenario: The action dock renders as a floating panel with a tab bar and a guidance hint
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one panel filling the band's command region, its root frame renders as a tab bar carrying the shortcut-key hint with the open tab in a muted-gold fill, its current frame's rows render with a shape-marked focused row and dimmed but focusable disabled rows, and a breadcrumb with a back control appears below the root frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (the interaction workspace or the waiting frame) at 1440x900 or 1280x720
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the narrative caption's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
- **THEN** the rows scroll within the pane host, the tab bar and breadcrumb remain visible and fixed above the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1280x720
- **THEN** the host identity, the latest line, every choice row, the free-form input and the exit control are all reachable by scrolling inside the caption, without document-level scrolling and without the caption or the band changing size
