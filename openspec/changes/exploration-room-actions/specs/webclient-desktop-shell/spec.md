## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The stage SHALL give the message window and the action dock one fixed-height bottom band whose
height comes from one shared band-height token: the narrative occupies the band's message region as
the bounded message window on the left two thirds, the action dock fills the band's command region
on the right third, and in dialogue mode the message window spans the whole band while the command
region collapses.

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
- **THEN** it renders as one panel filling the band's command region with a shortcut-legend strip only outside exploration and creation, its exploration root renders as the exit compass beside the 建議 pill and the shared readout (people and objects stand on the stage's presence rail, and the room actions on the place card) and its combat root as a vertical command list with the focused row in a muted-gold fill, its current frame's rows or chips render with a shape-marked focused entry and dimmed but focusable disabled entries, and a breadcrumb with a back control appears below the root frame on every frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (a deep combat frame), or a person's verb card, the wait card, or the suggestions card is open over the stage, at 1451x790 or 2560x1440
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the message window's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
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
- **THEN** it renders a breadcrumb naming the parent and current frames with a back control and renders each frame's rows in the form that frame calls for: navigation rows or the combat forms - beside a detail pane that names the focused item, its availability, and the next key action wherever the frame carries one

#### Scenario: The band height never follows its contents
- **WHEN** the dock carries the exploration root (with or without a person's verb card or a room card open over the stage), the combat frames, or an empty pane host, in any mode and under any narrative
- **THEN** all of them render inside the same command-region box whose height comes from the shared band-height token, so the message window and the action dock never overlap and neither clips the other at a supported viewport

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the current mode's focus home SHALL own focus. Key events
SHALL be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router or focused compass consumed them, rather than bound directly to the
document.

#### Scenario: Keyboard navigation and backtracking are deterministic
- **WHEN** the player navigates a test menu with arrows, enters a submenu, and presses Escape
- **THEN** focus follows the menu geometry, exactly one menu level closes, and the prior
  focused item is restored

#### Scenario: Disabled item explains without submitting
- **WHEN** focus moves to a disabled item and the player presses Enter or clicks it
- **THEN** its explanation remains readable and no `ui_action` message is sent

#### Scenario: Repeated Enter submits once
- **WHEN** Enter key repeat fires while a proof action is being submitted
- **THEN** the browser emits one request and keeps mutation controls locked until resolution

#### Scenario: Key dispatch goes through the bridge contract
- **WHEN** the player presses a navigation key over the action dock
- **THEN** the public keyboard bridge claims it (the router consumed the key or the focused
  command field owns it), the bridge reports no unclaimed keydown, and keys the router does not
  consume still reach the text and command-history path

#### Scenario: Slash focuses the command field from the action dock
- **WHEN** the action dock holds focus, the command line is collapsed, and the player presses `/`
- **THEN** the command line expands, focus moves into the command input field, and no literal `/` is inserted
- **WHEN** the field then holds focus and the player presses Escape
- **THEN** nothing is sent, action-dock focus is restored, and the command line collapses

#### Scenario: A slash typed in an editable control is text
- **WHEN** an editable control (the command field, a creation form, or a rest form) is
  focused and the player presses `/`
- **THEN** a literal `/` is typed into that control and the router claims nothing, so text such as
  `whisper /ooc` remains fully typeable

#### Scenario: The suggestions root entry appears only when the envelope carries one
- **WHEN** the committed `suggestions` envelope's status is `unavailable`
- **THEN** the command panel carries no 建議 pill at all
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the command panel carries the 建議 pill and activating it opens the client-local suggestions card without dispatching a `ui_action` and without pushing a router frame

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the exploration root renders beside the compass and the presence rail
- **THEN** the router's exploration root carries no item; an interact target is the rail's `target-<identity>` entry, outside the router, whose Enter opens its client-local verb card without submitting and without pushing a router frame; exits, rail entries, the place card's room actions, and the 建議 pill are not router items

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces
  available and the dock renders its root
- **THEN** the action dock carries no 角色狀態, 任務, or 背包 entry - those surfaces are opened
  from the top navigation bar

#### Scenario: The router is inert while the dock is collapsed
- **WHEN** the committed mode is dialogue, focus is on the document body, and the player presses ArrowDown, Enter, Space, and Escape
- **THEN** the bridge reports each key unclaimed by the router, the router's focused key and depth are unchanged, and no request is emitted

#### Scenario: The router owns the menu and command-line keys
- **WHEN** the router handles a navigation key over a menu
- **THEN** arrow keys move within the active finite menu, Enter confirms an enabled focused item, Escape pops exactly one menu level, Space is reserved for multi-select toggles, and `/` opens the command line
- **AND** disabled entries remain focusable for their explanation but never submit

#### Scenario: The mode's focus home reclaims focus after synchronization and actions
- **WHEN** the shell reaches initial synchronization, or an action completes or is rejected with its declared presentation revision accepted
- **THEN** the current mode's focus home owns focus: the exit compass at the exploration root, the active dock row container in other dock frames, or in dialogue mode the message window's focus target, as `webclient-contextual-hud` "The command region collapses in dialogue mode and the message window spans the band" defines

#### Scenario: Slash expands the line and focuses the field without typing itself
- **WHEN** `/` opens the command line from the focus home
- **THEN** a collapsed line expands, in either state focus moves into the input field once the field is rendered, and no literal `/` is inserted into it

#### Scenario: Escape from the command field returns to the focus home
- **WHEN** the command field holds focus and the player presses Escape
- **THEN** nothing is sent, focus returns to the current mode's focus home, and the command line collapses

#### Scenario: Dialogue claims only slash and the choice list keeps its own keys
- **WHEN** the committed mode is `dialogue`
- **THEN** the router claims only `/`; arrows, Enter, Space, Escape, and digits are unclaimed by it, so the hidden dock is never navigated or activated, and the dialogue choice list handles its own keys before they reach the bridge

#### Scenario: Pointer activation follows the Enter path
- **WHEN** the player activates a rendered row with the pointer
- **THEN** the activation is admitted and traverses the identical focus, disabled-explanation, and submission-gating path as Enter, as specified by `webclient-pointer-activation`

#### Scenario: Repeat and in-flight submissions are suppressed
- **WHEN** Enter is held or repeated, or a mutation submission occurs while one is in flight or awaiting its declared presentation revision
- **THEN** the submission is suppressed, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The exploration root carries the bare overview keys
- **WHEN** the shell is in exploration mode
- **THEN** the keyboard root is the exploration root frame, an empty menu: the room actions are the place card's 查看房間 and 等待 buttons and the 建議 pill (present whenever the committed `suggestions` envelope is not `unavailable`), each its own tab stop outside the router; exits are independent compass targets with no router key, and interact targets, look-only people, and objects are the presence rail's `target-<identity>`, `entity-<identity>`, and `object-<identity>` entries, also outside the router

#### Scenario: The exploration root omits the navigation-carried entries
- **WHEN** the exploration keyboard root renders
- **THEN** it carries no `character`, `quests`, or `inventory` entry - the top navigation bar carries them as the sole keyboard-visible stop

#### Scenario: The combat root declares a single column
- **WHEN** the shell is in combat mode
- **THEN** the root declares a single column, so its vertical arrow geometry matches its rendered list order and the horizontal arrow keys are no-ops

#### Scenario: The legacy B2 key contract survives only as a gate
- **WHEN** the exploration keyboard root replaced the legacy B2 flat `context_actions` affordance list, whose items were keyed `action-<action_id>` / `action-<surface>` (e.g. `action-guild`)
- **THEN** the B2 key-derivation contract is preserved only as the isolated Node gate (`web/webclient-app/tests/action/dock_items.test.js`), not as the live exploration focus frame

### Requirement: The action dock's row region and detail panes are direct children of its pane host
The action dock's pane host SHALL lay out the active frame's focusable row region and any displayed
detail pane as direct children of that host, side by side when a detail pane is displayed. The exploration root is the explicit exception, composing a compass beside a right column containing the 建議 pill and the readout. The
action dock's pane host SHALL be the only host of the dock's row region: no reference drawer body
renders it.

#### Scenario: A frame with a detail pane pairs direct children under the host
- **WHEN** the active dock frame shows a detail pane beside the rows (a generic
  detail frame or the combat skill frame with its dedicated detail)
- **THEN** the focusable row region and the visible detail pane are siblings
  whose parent is the pane host, no intermediate layout element wraps either
  of them, and the pair renders side by side

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
