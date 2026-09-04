# webclient-desktop-shell delta

## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the visual centre of the stage as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the HUD island stack, the action dock and
the command line visible at 1440x900 and 1280x720. The action dock, the narrative caption, and the
command line SHALL NOT be permanently closable, and the command line's input field SHALL be present and
usable without an opening action; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the action dock's root frame, and SHALL be
closable in one action that returns focus to the control that opened it. The map, settings and help
surfaces SHALL each be reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as
its brand and SHALL show the current location, the world date/time, and the connection state in a
top-meta surface, with the connected state marked by an ok-green dot paired with a label — never a raw
mode label in place of location. The top-meta location SHALL state the best server-authored place name
the client already holds, resolved in a fixed order: the committed `local_map` panel's `current_node`
label when that panel is available, names a current node, that node is present in the panel's nodes,
and its label is a non-empty string; otherwise the committed status panel's actor location label;
otherwise the surface's own unavailable placeholder. The shell SHALL NOT compose a third string from
the two candidates, SHALL NOT derive a name from any node or room identifier, and SHALL NOT render a
raw room key while a committed panel carries the authored place name for the same room — the raw
wilderness room key is one string for the whole continent, while the map panel names the region the
player is standing in. Neither payload contract changes: the shell chooses between two labels the
server already committed at the same revision. The action dock SHALL render as the approved command surface: a
floating panel bounded to a maximum width and centred in the stage's dock anchor, whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a seal-red fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to focus the
command input). The focused row SHALL be marked by a seal-red fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the HUD island stack, the action dock, and the command line with its visible input field are present without overlapping the narrative input path

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

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows the current location label resolved from the committed panels, the world date/time, and an ok-green "● 已連線" indicator, and no raw mode label is rendered

#### Scenario: The top-meta location names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status panel location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the top-meta location reads 西部丘陵與谷地, the raw room key is not rendered anywhere in the top-meta surface, and no composed string pairing the two appears

#### Scenario: The location falls back when the map panel cannot supply a name
- **WHEN** the `local_map` panel is absent, unavailable, or names a current node that its own nodes do not carry or that carries an empty label
- **THEN** the top-meta location states the committed status panel's actor location label, and states the surface's unavailable placeholder only when neither panel supplies a label

#### Scenario: The action dock renders as a floating panel with a tab bar and a guidance hint
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one centred floating panel in the dock anchor, its root frame renders as a tab bar carrying the shortcut-key hint with the open tab in a seal-red fill, its current frame's rows render with a shape-marked focused row and dimmed but focusable disabled rows, and a breadcrumb with a back control appears below the root frame
