## Purpose

The desktop Vue SPA shell surfaces, client state reduction, keyboard focus model, command drawer, layout migration, theme, accessibility, and text fallback.

## Requirements

### Requirement: The WebClient loads a local Vue SPA desktop shell
The project WebClient SHALL load Evennia's existing transport together with a locally built,
self-contained Vue 3 single-page application. It SHALL make no remote request for a runtime UI
dependency. The application SHALL provide the required brand, narrative, scene, status, local-map,
action-dock, and command-drawer surfaces and SHALL render them as self-identifying surfaces,
never as a tab-title component strip.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, the Vite-built Vue application, the project modules, and the theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while the scene degrades to its gradient stage
- **WHEN** the shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the stage backdrop renders the mode gradient with no invented image

#### Scenario: The scene renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the stage backdrop renders the scene cover-cropped behind the HUD surfaces, with the scene label and alternative text rendered as text outside the bitmap

#### Scenario: The shell renders self-identifying surfaces without a tab strip
- **WHEN** the shell mounts
- **THEN** no tab-title chrome is rendered anywhere, every required surface is present, and each surface carries its own self-identifying content instead of a component-name tab title

#### Scenario: Each required surface names itself by its own content
- **WHEN** the shell renders the required surfaces
- **THEN** the narrative caption, status resources, map legend, scene label, dock menu, and prompt line each identify themselves through their own content

#### Scenario: The local-map surface renders its owned panel
- **WHEN** the local-map surface renders
- **THEN** it renders the `webclient-local-map` panel owned by the `map-knowledge-minimap` delivery unit

#### Scenario: The scene backdrop renders the validated panel or degrades truthfully
- **WHEN** the scene surface renders its stage backdrop
- **THEN** it renders the validated `webclient-art-panel` payload as the current scene when the panel is available, and the mode's gradient stage - never an invented image - whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable

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
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, a settings control, and the tool group, and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's scene overview

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
- **THEN** it renders as one panel filling the band's command region with one shortcut-legend strip, its exploration root renders as the scene overview and its combat root as a vertical command list with the focused row in a muted-gold fill, its current frame's rows or chips render with a shape-marked focused entry and dimmed but focusable disabled entries, and a breadcrumb with a back control appears below the root frame on every frame except a target's verb popover, which states its target in its own heading

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (a crowded scene overview, a target's verb popover, or the waiting frame) at 1451x790 or 2560x1440
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the message window's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
- **THEN** the rows scroll within the pane host, the dock's chrome (the breadcrumb and the legend strip) remains visible and fixed around the scrolling region, and the last row becomes reachable by scrolling

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
- **THEN** the surface renders in a drawer laid over the stage in the shared reference workspace, reached in at most two actions from the top navigation bar or from the action dock's scene overview

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
- **THEN** its exploration root renders as the scene overview with chip rows for exits, people, and objects, and a footer, its combat root renders as a vertical list of icon-and-label command rows with the focused entry marked by a muted-gold fill, and its remaining region renders the current frame's rows or chips

#### Scenario: The dock carries the defined shortcut legend
- **WHEN** the action dock renders
- **THEN** it carries the shortcut legend the contextual-HUD legend requirement defines

#### Scenario: Rows mark focus, absence of focus, and disablement distinctly
- **WHEN** the dock renders rows or chips
- **THEN** the focused row or chip is marked by a muted-gold fill plus a leading glyph, unfocused rows are bordered, and disabled rows are dimmed but focusable for their explanation

#### Scenario: Non-root frames show a breadcrumb and a detail pane
- **WHEN** the dock is below its root frame
- **THEN** it renders a breadcrumb naming the parent and current frames with a back control - except over a target's verb popover, whose own heading names the target once - and renders each frame's rows in the form that frame calls for: a target's verb popover over the inert overview, navigation rows, the waiting cards, suggestion cards, or the combat forms - beside a detail pane that names the focused item, its availability, and the next key action wherever the frame carries one

#### Scenario: The band height never follows its contents
- **WHEN** the dock carries the scene overview, a target's verb popover, the waiting frame, the combat frames, or an empty pane host, in any mode and under any narrative
- **THEN** all of them render inside the same command-region box whose height comes from the shared band-height token, so the message window and the action dock never overlap and neither clips the other at a supported viewport

### Requirement: Narrative output remains the authoritative text surface and is read page by page
The shell SHALL route Evennia's existing narrative and command output to the retained narrative log
without parsing it to infer panel state, and every surface that renders the log SHALL render the
portal's converted HTML stream through the `webclient-narrative-markup` allowlist pipeline rather
than inserting it as a single text node, displaying markup source to the player, or interpreting
anything outside that pipeline's allowlist.

#### Scenario: New text does not move the reader off the page
- **WHEN** the player is reading page 1 of the current response and more text of that response
  arrives
- **THEN** the page on screen is unchanged and the page marker reads `▼`

#### Scenario: Unread pages stay reachable in the complete log
- **WHEN** the player acts while pages of the previous response remain unread and then opens the
  full-log surface
- **THEN** every line of the previous response, including the unread pages' text, is present in the
  full-log surface in order

#### Scenario: Structured failure does not suppress narrative
- **WHEN** status validation and OOB initialization fail
- **THEN** ordinary text output continues to appear in the message window and the full-log surface

#### Scenario: Converted server output renders as text, not as markup source
- **WHEN** the server sends ordinary room, command, or narrator output that the portal converted to HTML
- **THEN** the message window's page and the full-log surface show the styled, line-broken prose and
  no element, attribute, or entity source characters are visible

#### Scenario: The portal converts output before sending
- **WHEN** the server sends ordinary output and the portal prepares the `text` message
- **THEN** the portal has converted it to HTML before sending, and the shell's surfaces render that converted stream through the allowlist pipeline

#### Scenario: The message window shows one page of the current response
- **WHEN** the message window renders the log
- **THEN** it presents the log one page of the current response at a time (see `webclient-contextual-hud` and `webclient-input-narrative`)

#### Scenario: The full-log surface carries the complete retained log
- **WHEN** the player opens the full-log surface, one action away
- **THEN** the complete retained log stays readable, in order and through the same pipeline

#### Scenario: No unread counter is rendered
- **WHEN** pages of the current response remain unread
- **THEN** no unread counter is rendered, the page marker states that more pages remain, and a new action flushes the unread pages to the log rather than discarding them

#### Scenario: Narrative survives every structured renderer being unavailable
- **WHEN** every structured renderer is unavailable
- **THEN** narrative output remains usable

#### Scenario: An untokenizable message degrades to literal text
- **WHEN** a message cannot be fully tokenized
- **THEN** it degrades to readable literal text rather than suppressing the log

### Requirement: Client state reduction is strict and atomic
The client state store SHALL validate protocol, transport generation, epoch, revision, mode, panel allowlist, layout version, and panel schema before publishing state to renderers. `connection_open` SHALL start a new local generation in `awaiting_initial_snapshot`, retire the prior epoch in bounded memory, clear prior panel state, and lock mutations. Only that generation's first valid full snapshot with a non-retired epoch SHALL establish active state.

#### Scenario: Malformed update changes no panel
- **WHEN** a multi-panel update contains one malformed included panel
- **THEN** the entire update is rejected and no subscriber observes partially replaced state

#### Scenario: Subscribers observe only committed state
- **WHEN** a valid snapshot or update is accepted
- **THEN** subscribed renderers receive one notification after the complete new state becomes the store baseline

#### Scenario: Same-transport epoch replacement is forbidden
- **WHEN** an active transport generation receives a valid full snapshot with an epoch different from its adopted epoch
- **THEN** the store rejects it and does not clear or replace current state

#### Scenario: Active-state stores discard stale and malformed messages
- **WHEN** an active store receives a different epoch on the same generation, an older receiver generation, a non-newer active-epoch revision, or any malformed message
- **THEN** the message is discarded

#### Scenario: Accepted panels replace completely in one commit
- **WHEN** a valid snapshot or update is applied
- **THEN** the included panels replace completely and subscribers observe no partially applied message

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the current mode's focus home SHALL own focus. Key events
SHALL be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router consumed them, rather than bound directly to the
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
- **THEN** the scene overview carries no `suggestions` chip at all
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the overview's footer carries the `suggestions` chip and activating it pushes the suggestions frame without dispatching a `ui_action`

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the client is in exploration mode on a scene overview whose first two chips are an exit
  and an interact target, and the player presses ArrowRight
- **THEN** the keyboard router's focus key is the bare overview key `target-<identity>`, not the
  legacy B2 `action-guild`-style `action-<id>`/`action-<surface>` key, and Enter on it pushes the
  target's verb popover (the dock depth becomes 2) without dispatching a `ui_action`; focus then
  lands on the popover's first row; for an exploration panel with no exits, people, or objects the
  overview's first chip is `look-room`

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces
  available and the dock renders its root
- **THEN** the scene overview carries no 角色狀態, 任務, or 背包 entry - those surfaces are opened
  from the top navigation bar - and the overview's chips keep the panel's order

#### Scenario: The router is inert while the dock is collapsed
- **WHEN** the committed mode is dialogue, focus is on the document body, and the player presses ArrowDown, Enter, Space, and Escape
- **THEN** the bridge reports each key unclaimed by the router, the router's focused key and depth are unchanged, and no request is emitted

#### Scenario: The router owns the menu and command-line keys
- **WHEN** the router handles a navigation key over a menu
- **THEN** arrow keys move within the active finite menu, Enter confirms an enabled focused item, Escape pops exactly one menu level, Space is reserved for multi-select toggles, and `/` opens the command line
- **AND** disabled entries remain focusable for their explanation but never submit

#### Scenario: The mode's focus home reclaims focus after synchronization and actions
- **WHEN** the shell reaches initial synchronization, or an action completes or is rejected with its declared presentation revision accepted
- **THEN** the current mode's focus home owns focus: the action dock, or in dialogue mode the message window's focus target, as `webclient-contextual-hud` "The command region collapses in dialogue mode and the message window spans the band" defines

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
- **THEN** the keyboard root is the scene overview frame, whose items carry the bare keys `exit-<exit_ref>` for exits, `target-<identity>` for interact targets, `entity-<identity>` and `object-<identity>` for look-only people and objects, and `look-room`, `wait`, and - whenever the committed `suggestions` envelope is not `unavailable` - `suggestions` for the footer, in the overview's reading order and navigated by its row-of-chips geometry

#### Scenario: The exploration root omits the navigation-carried entries
- **WHEN** the exploration keyboard root renders
- **THEN** it carries no `character`, `quests`, or `inventory` entry - the top navigation bar carries them as the sole keyboard-visible stop

#### Scenario: The combat root declares a single column
- **WHEN** the shell is in combat mode
- **THEN** the root declares a single column, so its vertical arrow geometry matches its rendered list order and the horizontal arrow keys are no-ops

#### Scenario: The legacy B2 key contract survives only as a gate
- **WHEN** the exploration keyboard root replaced the legacy B2 flat `context_actions` affordance list, whose items were keyed `action-<action_id>` / `action-<surface>` (e.g. `action-guild`)
- **THEN** the B2 key-derivation contract is preserved only as the isolated Node gate (`web/webclient-app/tests/action/dock_items.test.js`), not as the live exploration focus frame

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its 設定 control, one labelled group (`工具`) of icon
controls that open the client's secondary overlays and reference drawers, and SHALL NOT push a
keyboard menu frame.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 技能系譜, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
- **THEN** each activation opens its overlay, and each close returns focus to the control that opened it

#### Scenario: The codex tool opens the reference drawer
- **WHEN** the player activates the 圖鑑 control in the tool group
- **THEN** the world-codex reference drawer opens through the single open-drawer entry point, and closing it returns focus to the control

#### Scenario: The gallery tool follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, and a later revision commits the panel's unavailable form
- **THEN** the 角色肖像圖庫 control is rendered in the tool group while the panel is available, and after the unavailable form commits it is absent from the bar and the tab order

#### Scenario: The tool group is keyboard reachable
- **WHEN** the player moves focus through the top navigation bar with Tab
- **THEN** focus reaches every tool-group control in order, each exposes its label as its accessible name, and Enter on a focused control opens its surface

#### Scenario: The tool group fits the 48px bar at the minimum viewport
- **WHEN** the shell renders in exploration mode at 1451x790 with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** every tool-group control lies inside the 48px bar, and no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: The command line carries no tool opener
- **WHEN** the command line is expanded
- **THEN** it carries no 技能系譜, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control

#### Scenario: The tool group carries the five tools in order
- **WHEN** the tool group renders
- **THEN** it carries, in order, 技能系譜 for the skill lineage overlay, 圖鑑 for the world-codex reference drawer, 稱號冊 for the title-codex overlay, 角色肖像圖庫 for the portrait gallery overlay, and 說明 for the help overlay

#### Scenario: Each tool control names itself from the shared tool model
- **WHEN** a tool control renders
- **THEN** it carries an accessible name equal to its label, taken from the one tool model that also titles the header of the surface it opens, discloses that label visually in the shared tool tooltip that the stable top-navigation placement requirement defines, carries no native `title` tooltip, and is reachable by sequential keyboard navigation

#### Scenario: A tool opens through the opener-captured path
- **WHEN** the player activates a tool control with one pointer action or one Enter press
- **THEN** its surface opens through the same opener-captured path every other overlay or drawer opener uses, so closing the surface returns focus to that control

#### Scenario: The portrait gallery control follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available and later becomes unavailable
- **THEN** the 角色肖像圖庫 control renders only while the committed `gallery` panel is available

#### Scenario: The tool group renders in every bar-bearing mode
- **WHEN** the top navigation bar renders in any mode, with the command line expanded or collapsed
- **THEN** the group renders

#### Scenario: The five surfaces have exactly one opener each
- **WHEN** the rendered surfaces are inspected for openers of the five tool surfaces
- **THEN** no surface other than the tool group carries a second opener for them, and the command line carries none

#### Scenario: The tool group fits the 48px bar
- **WHEN** the shell renders at the 1451x790 reference viewport with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** the group fits the 48px bar and the navigation bar's controls do not intersect the top-meta and character-switcher cluster

### Requirement: Browser persistence is versioned and presentation-only
Local browser storage SHALL contain only a bounded wrapper with project layout version, safe dimensions/tab state, and harmless display preferences. It SHALL contain no transport generation, active or retired epoch, revision, panel payload, actor identifier, request result, command text, credential, or canonical game state.

#### Scenario: Known layout version migrates
- **WHEN** a stored project layout uses a version with a registered migration, as supplied to the store by a caller
- **THEN** the migration produces the current layout and retains only supported display preferences

#### Scenario: Unknown layout version resets safely
- **WHEN** localStorage contains an unknown version or malformed configuration
- **THEN** the shell removes or ignores it and loads the approved default with every required component

#### Scenario: Stock layout state is not imported
- **WHEN** a browser profile contains Evennia's pre-project GoldenLayout storage keys
- **THEN** the current layout version does not treat those values as canonical project layout state

#### Scenario: A version-1 wrapper resets to the current default
- **WHEN** localStorage holds a well-formed version-1 or version-2 wrapper with a stored prose scale
- **THEN** the client loads the version-3 default with every preference at its default, text speed `normal`, auto-advance off, and no stored motion level among them, and persists that version-3 wrapper

#### Scenario: An invalid motion level is dropped
- **WHEN** localStorage holds a version-3 wrapper whose `motionLevel` is not `full`, `reduced`, or `off`, beside a valid prose scale
- **THEN** the wrapper loads with no stored motion level and keeps the prose scale

#### Scenario: The current layout version carries the optional motion level
- **WHEN** the current project layout version is stated
- **THEN** it is version 3, the version that replaces the reduced-motion override with the optional motion level (`full`, `reduced`, or `off`; absent while the player has chosen none)

#### Scenario: Versions migrate only through registered migrations
- **WHEN** a project layout version needs to migrate
- **THEN** it migrates only through an explicitly registered migration, and the client registers none: versions 1 and 2 have no migration

#### Scenario: Unusable stored layouts reset to the current default
- **WHEN** stored state is malformed, oversized, missing, stock, or an unknown version, versions 1 and 2 among them
- **THEN** it resets to the current version's default while preserving required components

#### Scenario: A single invalid preference value is dropped alone
- **WHEN** a stored preference value falls outside its defined values
- **THEN** that value is dropped while the wrapper's other valid preferences are kept

### Requirement: Theme and controls remain accessible
The shell SHALL use the approved desktop palette while pairing color with labels, borders, icons,
or shapes, and SHALL use a serif face for headings, the bundled monospace face for the narrative's
message-window page text and full-log lines, and a legible UI face for the remaining controls.

#### Scenario: Keyboard focus does not depend on color alone
- **WHEN** keyboard focus moves between action controls
- **THEN** the focused control is distinguishable by a non-color visual indicator and an accessible focus state

#### Scenario: The seal-red accent never carries meaning alone
- **WHEN** a seal-red (vermilion) element is rendered
- **THEN** it is paired with a label, border, glyph, or shape, and seal-red small text on dark surfaces is not used

#### Scenario: Disabled rows expose their reason programmatically
- **WHEN** a disabled action-dock cell is rendered
- **THEN** its disabled reason is programmatically associated with the cell (for example `aria-describedby`) and is readable in the detail pane or a visually hidden description, at every navigation depth including the root

#### Scenario: Player-authored label is not executed as markup
- **WHEN** a server-authored display value in a structured panel contains HTML-like player text
- **THEN** the browser renders it as literal text and no element or script is created from it

#### Scenario: The narrative exception is bounded to one pipeline
- **WHEN** the shell's panel renderers are inspected
- **THEN** only the narrative log renders converted markup, every other renderer inserts server values as text, and no renderer uses an HTML-parsing API

#### Scenario: The approved palette is the shell's color set
- **WHEN** the shell renders its surfaces and accents
- **THEN** the palette is near-black charcoal surfaces, warm paper-gray text, a deep seal-red accent retained for its semantic roles (decisive primary action, danger affordances, selection, status markers) alongside a muted-gold navigation, focus, and emphasis accent, and an ok-green connection indicator

#### Scenario: Accessibility signals go beyond color
- **WHEN** focus, resources, disabled controls, action results, or motion are rendered
- **THEN** focus is visibly indicated, resource values include numeric text, disabled reasons are programmatically associated with controls, action results use a non-interrupting live region, and reduced-motion preference disables nonessential transitions

#### Scenario: Panel values are inserted as text only
- **WHEN** a structured presentation panel carries a server-authored value - a label, description, reason, name, or legend entry
- **THEN** it is inserted as text and never treated as markup, and no other surface renders server bytes as markup

#### Scenario: The narrative stream renders only through the allowlist pipeline
- **WHEN** the narrative transport stream renders
- **THEN** it renders only through the `webclient-narrative-markup` allowlist pipeline - the single bounded exception, whose player content the portal already escapes within its converted HTML - which constructs nodes exclusively through element and text-node constructors and degrades everything outside its allowlist to literal text

### Requirement: Connection loss locks stale controls
On WebSocket loss after a successful connection, the shell SHALL preserve the last rendered state
under a non-dismissible offline overlay and SHALL prevent all graphical mutation submission.
Reconnection SHALL request a full snapshot and remove the overlay only after a valid new-epoch
snapshot is adopted.

#### Scenario: Offline controls cannot submit
- **WHEN** the active WebSocket closes while an enabled test action is focused
- **THEN** the offline overlay appears and keyboard or mouse activation emits no mutation

#### Scenario: Reconnect waits for canonical state
- **WHEN** the socket reconnects but no valid full snapshot has arrived
- **THEN** the offline/synchronizing lock remains until the new-epoch snapshot is accepted

#### Scenario: A dropped first sync is re-requested on a bounded budget
- **WHEN** the first reconnection `ui_sync` lands before the portal re-attaches the account puppet and the snapshot is dropped
- **THEN** the client re-requests `ui_sync` on a bounded, disarming schedule, ceasing on adoption, on disconnect, or once the attempt budget is spent

#### Scenario: Extremely stale reconnections recover once
- **WHEN** the authenticated snapshot never arrives after the bounded re-request budget, so the portal has lost the browser's authenticated session
- **THEN** the client reloads the page at most once per tab session (guarded by a persistent marker) and otherwise leaves the synchronizing lock in place

#### Scenario: The overlay stays off before any successful connection
- **WHEN** a first-time visitor opens the WebClient and no connection has ever reached the active phase
- **THEN** the offline overlay remains hidden so the stock connect/create prompt underneath stays visible and usable

#### Scenario: The offline overlay outranks an open reference drawer
- **WHEN** a reference drawer (skill, inventory, shop, quest, lore, or status) is open and the WebSocket then closes
- **THEN** the offline overlay is the topmost visible surface, painted above the drawer's scrim and panel

#### Scenario: The offline overlay outranks an open full-screen overlay or full-view
- **WHEN** the map, settings, or help overlay — or the portrait/scene full-view, or the full-log overlay — is open and the WebSocket then closes
- **THEN** the offline overlay is the topmost visible surface, painted above that surface

#### Scenario: A connection loss is announced over any open surface
- **WHEN** the WebSocket closes while any surface the client can have open is displayed
- **THEN** the offline overlay renders above every other such surface - an open reference drawer, an open full-screen overlay (map/settings/help), a full-view art or scene surface, and the full-log overlay all included - so a connection loss is visibly announced regardless of what the player had open when it occurred

### Requirement: Player input lines are part of the narrative stream with a divider

The narrative log SHALL retain, in addition to server text, one input line per deliberate player
action, inserted as literal text through the same single append path as narrative output, forcing a
new line, and SHALL be styled distinctly from server output (`.inp`) wherever they render.

#### Scenario: A typed command appears with a divider
- **WHEN** the player types a command in the command line and sends it while a page of the
  previous response is on screen
- **THEN** the full-log surface shows one `.inp` line containing the raw sent text, preceded by a
  `.narrative-divider`; the message window shows no input line and presents the command's reply
  from its first page; and the text is never sent back to the server

#### Scenario: A button action appears with a divider
- **WHEN** the player submits `explore.move` via the dock or the minimap
- **THEN** the full-log surface shows one `.inp` line with its resolved command line, preceded by a
  `.narrative-divider`, with the server output that follows after it, and the message window shows
  that output as a new response

#### Scenario: The first line needs no separator
- **WHEN** a fresh log's first entry is an input line
- **THEN** the full-log surface renders it with the input style but without a preceding divider
  hairline

#### Scenario: Input lines are never executed
- **WHEN** the player re-reads the log and its input lines sit alongside server lines
- **THEN** no line is ever sent to the server, nothing is replayed, and the log content has no effect on
  game state

#### Scenario: Each deliberate action echoes as one input line
- **WHEN** the player sends a typed command or triggers a mutation through a button
- **THEN** the typed command send echoes the exact raw text the player sent, and the button-triggered mutation echoes its resolved command line (see the `webclient-input-narrative` capability)

#### Scenario: An input line heads the response it begins
- **WHEN** an input line renders among the log's responses
- **THEN** it heads the response it begins, one input event (divider and input line together) begins exactly one response, it renders in the full-log surface, and it is not one of the message window's pages

#### Scenario: Every input line is separated from its predecessor
- **WHEN** an input line follows a preceding server or input line in the full-log surface
- **THEN** a `.narrative-divider` hairline separates the two, so system prose and player actions never visually merge while re-reading, and the divider does not appear before the very first line of the log

#### Scenario: An untokenizable input line degrades to literal text
- **WHEN** the append path handles an input line the way it handles a server line that fails to tokenize
- **THEN** it degrades to literal text and never suppresses the log

### Requirement: The action dock's row region and detail panes are direct children of its pane host
The action dock's pane host SHALL lay out the active frame's focusable row region and any displayed
detail pane as direct children of that host, side by side when a detail pane is displayed. The
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
- **WHEN** the dock is at the exploration root, and then a target's verb popover opens over it
- **THEN** the scene overview component is the pane host's only child, fills its width, and renders
  no detail pane, and the popover's card renders in the dock's overlay layer while the pane host's
  children stay unchanged

#### Scenario: The dock menu adds no anonymous layout container
- **WHEN** the dock menu component renders under the pane host
- **THEN** it contributes no anonymous layout container between the host and either child; its rendered roots are the row region and, when shown, the detail pane itself

#### Scenario: The combat skill detail pane is a sibling of the row region
- **WHEN** the combat skill detail pane replaces the generic detail
- **THEN** it is a sibling of the row region under the same host, and the row region gains no wrapper for either case

#### Scenario: The scene overview is the one exception to the direct-child rule for row regions
- **WHEN** the dock renders the scene overview
- **THEN** it renders as a single component that is a direct child of the pane host and that holds its labelled chip rows and its reason strip, displays no detail pane, and fills the host's full width

#### Scenario: A verb popover renders outside the pane host
- **WHEN** a target's verb popover is open over the pane region
- **THEN** it renders in the dock's overlay layer, not inside the pane host, so the pane host's children are the same while it is open

### Requirement: The collapsible command line preserves ordinary text control and the dialogue's free-form borrow

The command line SHALL be collapsed by default and SHALL always be one entrance action away from use:
its input field SHALL become visible and focused through exactly one entrance action — `/` pressed while no
editable control is focused, activation of the ⌨ toggle, or the dialogue choice list's `⌨ 自由對話` row
borrowing the field for free-form speech to the conversation's host — and no stored layout or
presentation state SHALL be able to keep it collapsed or open it.

#### Scenario: The field is one entrance action away
- **WHEN** the shell mounts the command line in a fresh browser context
- **THEN** the input field is present in the DOM inside its wrapper but hidden and outside the tab order, the ⌨ toggle reports `aria-expanded="false"`, and after one `/` press the field is visible, focused, and can be typed into

#### Scenario: Slash focuses the field without typing a slash
- **WHEN** no editable control is focused and the player presses `/`
- **THEN** the command line expands, focus moves into the input field, and the field's content is unchanged — no literal `/` is inserted

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player opens the field with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, the command line
  collapses, and focus returns to the action dock

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player opens the field with `/`, sends a command, presses `/` again, types a second command,
  and sends it
- **THEN** both commands travel through the text input path, the field is cleared and the line collapsed
  after each, and focus is in the action dock or the field at every step without any pointer interaction

#### Scenario: Escape cancels without sending and returns to the dock
- **WHEN** the player opens the field, enters unsent text, and presses Escape
- **THEN** no text and no UI action is sent, action-dock focus is restored, the command line collapses, and the next expansion shows the same unsent text

#### Scenario: A pointer-opened field sends on Enter without a prior slash
- **WHEN** the player activates the ⌨ toggle with the pointer, types a command in the now-focused field,
  and presses Enter
- **THEN** exactly one text message is sent through the single send path, the field clears, the command
  line collapses, and focus returns to the action dock; the plugin contract reports no unhandled keydown

#### Scenario: A rejected send keeps the text and the open line
- **WHEN** the player sends an ordinary command while mutations are locked or a mutation is in flight
- **THEN** the typed text remains in the field, focus stays in the field, and the command line stays expanded

#### Scenario: Shift+Enter inserts a newline without sending
- **WHEN** the input field is focused and the player presses Shift+Enter
- **THEN** no command is sent and the text insertion point moves to a new line

#### Scenario: The history walk preserves the unsent draft
- **WHEN** the player types an unsent draft, presses ArrowUp twice to recall two prior commands, and then presses ArrowDown past the most recent entry
- **THEN** the recalled commands appear in order, the unsent draft is restored when the walk returns past its most recent entry, and no command is sent by the walk

#### Scenario: A borrowed dialogue send returns focus to the dialogue
- **WHEN** the dialogue choice list's `⌨ 自由對話` row borrows the field while the command line is collapsed,
  and the player sends the speech while the action client is unlocked and the presentation phase is active
- **THEN** the borrow expanded the command line and focused the field, exactly one `explore.talk_freeform`
  action is submitted for the host, the field clears, the command line collapses, focus is on the message
  window's page surface while the reply is awaited, and focus moves to the choice list once the reply's
  last page is fully shown

#### Scenario: A locked borrowed send keeps the speech
- **WHEN** the dialogue free row borrows the field and the player sends the speech while the action client
  is locked, and then sends again after the lock lifts
- **THEN** the first send submits no action, keeps the speech in the field with focus and the expanded
  line, and echoes no input line; the second send submits exactly one `explore.talk_freeform` for the same
  host and no ordinary text command

#### Scenario: A borrowed send outside the active phase is rejected by the field
- **WHEN** the dialogue free row borrows the field and the player sends the speech while the transport is
  connected with no mutation in flight but the presentation phase is not active (a transport reset
  awaiting its first snapshot)
- **THEN** the field does not clear, the command line stays expanded with focus in the field, no action is
  submitted, no ordinary text is sent, the speech is not lost, and the borrow stays bound to the host

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the input field
- **THEN** exactly one text message is sent regardless of how focus arrived

#### Scenario: A refused borrow ends with the conversation
- **WHEN** the dialogue free row borrows the field, a send is refused while a mutation is in flight, and
  that mutation's commit ends the conversation while the field keeps focus
- **THEN** the borrow is released, and the next send from the field travels as ordinary text with no
  `explore.talk_freeform` submitted

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player activates the dialogue free row, leaves the field without sending, and later sends an
  ordinary command through the field
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is
  submitted, and the typed text is not delivered as speech to the previously selected NPC

#### Scenario: The hidden field keeps its identity in the DOM
- **WHEN** the command line is collapsed
- **THEN** the field stays in the DOM, hidden with its row, and keeps the `#inputfield` identifier inside its `.inputfieldwrapper` wrapper in both the collapsed and the expanded state

#### Scenario: Every entrance path renders the row before focusing
- **WHEN** any entrance path expands the command line
- **THEN** the path renders the row before it moves focus, so focus never lands on a hidden field, and a field focused by any entrance path is left ready to send through the single send implementation

#### Scenario: The field sends text through one implementation
- **WHEN** the field sends
- **THEN** it sends ordinary text through Evennia's text message, preserves command history, never translates text into `ui_action`, and exactly one send implementation owns the field, so a single key press can never traverse two send paths

#### Scenario: Enter sends once and Shift+Enter breaks the line
- **WHEN** the player presses Enter without Shift while the field is focused
- **THEN** exactly one command is sent regardless of how focus arrived, while Shift+Enter inserts a newline without sending

#### Scenario: The field admits a send by the delivery predicate
- **WHEN** the player sends from the field
- **THEN** the field accepts the send by exactly the predicate that decides whether it is delivered: an ordinary text send while connected, mutations unlocked, and no mutation in flight; a borrowed free-form send while connected, mutations unlocked, the presentation phase active, and no mutation in flight - the same predicate the action dispatch path applies, so the field never accepts a borrowed send the dispatch path then refuses

#### Scenario: An accepted send clears the field and restores the focus home
- **WHEN** the field accepts a send
- **THEN** the field clears, focus moves to the current mode's focus home - the action dock; in dialogue mode the dialogue choice list while it is rendered and otherwise the message window's page surface - and the command line collapses, so the next command starts with one more entrance action

#### Scenario: History controls and completion match the arrow walk
- **WHEN** the player walks the command history with the labelled history controls, or uses Tab completion in any entrance path
- **THEN** the controls drive the same ArrowUp/ArrowDown walk without sending, and the walk and Tab completion behave identically in every entrance path

#### Scenario: Only the dialogue free row borrows the field
- **WHEN** the command line's input field is borrowed
- **THEN** the only borrower is the dialogue choice list's `⌨ 自由對話` row

#### Scenario: A successful borrowed send completes the interaction
- **WHEN** the dialogue choice list's `⌨ 自由對話` row has borrowed the field and its send succeeds
- **THEN** exactly one `explore.talk_freeform` is dispatched with the host's identity and the speech, the field clears, focus returns to the dialogue's focus home, and the command line collapses, because that interaction has completed

#### Scenario: A locked borrowed send is refused and kept bound
- **WHEN** the action client is locked (offline, awaiting the first snapshot, a presentation phase other than active, or another mutation in flight) and the borrowed field sends
- **THEN** the borrowed send does not dispatch, keeps the typed speech in the field, keeps focus in the field, keeps the command line expanded, and keeps the borrow bound to the same host, so the next send once the lock lifts is still delivered as that speech

#### Scenario: The borrow releases on every exit but an accepted or rejected send
- **WHEN** focus leaves the borrowed field for any reason other than a send the field accepted or rejected, a send is routed as ordinary text, or a committed revision ends the conversation with a committed mode other than dialogue
- **THEN** the borrowed-field reference is released, whatever holds focus, so a cancelled, abandoned, or refused dialogue interaction can never capture a later unrelated command

#### Scenario: The field works with OOB controls disabled
- **WHEN** OOB controls are disabled
- **THEN** the field remains usable

### Requirement: Top navigation retains stable tool placement while respecting mode availability
The top navigation bar SHALL lay its labelled primary controls out in one primary region in a fixed
order, each as wide as its concept's label length dictates whatever the mode, with the present
controls packed against the region's trailing edge.

#### Scenario: Combat removes unavailable entries
- **WHEN** the committed mode changes from exploration to combat at a fixed viewport of 1451x790, 1741x948, or 2560x1440
- **THEN** the 角色狀態, 任務, and 地圖 controls are absent from rendering and the tab order, the combat 背包 control stands immediately before 設定, and the left edges of the 設定 control and of the `工具` group differ from their exploration positions by at most 1px

#### Scenario: An unavailable panel leaves no placeholder
- **WHEN** the committed exploration panel reports the quest surface unavailable
- **THEN** no quest control and no placeholder renders, and the 設定 control and the `工具` group keep their positions

#### Scenario: Keyboard user identifies a tool
- **WHEN** a `工具` control receives keyboard focus by Tab
- **THEN** its label appears as a visible tooltip while focus stays on the control, and Escape hides the tooltip, keeps focus on the control, and leaves the dock's frame unchanged

#### Scenario: A second Escape reaches the dock
- **WHEN** the tooltip of the focused `工具` control has been dismissed with Escape and the player presses Escape again
- **THEN** the key reaches the dock's keyboard router exactly as it would without the tooltip

#### Scenario: A restored opener stays quiet
- **WHEN** a surface opened from a `工具` control closes and returns focus to that control
- **THEN** no tooltip appears

#### Scenario: Pointer user identifies a tool
- **WHEN** the pointer rests on a `工具` control and then moves onto its tooltip
- **THEN** the label appears as a visible tooltip and stays visible, and activating the control hides it

#### Scenario: The primary region's order is fixed
- **WHEN** the bar renders in any mode
- **THEN** the primary region's order is the character status entry (角色狀態), the quest entry (任務), the inventory entry (背包 - the exploration `inventory` entry and the combat root's `bag` entry are the same concept), the map control (地圖), and the settings control (設定), followed by the `工具` group

#### Scenario: Trailing packing keeps the settings and tool positions stable
- **WHEN** the bar renders in exploration, dialogue, and combat at a fixed viewport size
- **THEN** the region is exactly as wide as all five controls together, so the 設定 control and the `工具` group keep the same horizontal position (within 1px) in all three modes, and the space a missing entry leaves collects on the brand side

#### Scenario: An unsupplied entry leaves no placeholder
- **WHEN** the current mode or the committed panels do not supply an entry (the map control in combat, the character and quest entries in combat, an entry whose panel is unavailable)
- **THEN** it is absent from rendering, the accessibility tree, and the tab order, and is not replaced by a disabled, `aria-disabled`, `visibility: hidden`, or otherwise present placeholder

#### Scenario: Order, disabled reasons, and compact padding hold
- **WHEN** the present controls render, when a primary entry is disabled, and at viewports up to 1350px wide
- **THEN** DOM order equals visual order, a disabled primary entry keeps its disabled reason as its `title`, and the controls use compact padding
- **AND** at the 1451x790 reference viewport no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: A tool tooltip shows on hover and on Tab focus
- **WHEN** the pointer rests on an icon-only `工具` control or on the tooltip itself, or keyboard focus arrives on the control by Tab
- **THEN** the control discloses its label visually in one shared tooltip treatment, while focus returned to the control programmatically by a closing surface restoring its opener shows no tooltip

#### Scenario: The tooltip's own properties are fixed
- **WHEN** a tooltip is shown
- **THEN** its text is the control's label, it is hidden from assistive technology since the label is already the control's accessible name, it takes no focus, it hides when the control is activated, and it follows the motion level

#### Scenario: Escape dismisses a tooltip with router-safe consumption
- **WHEN** the player presses Escape while a tooltip is visible
- **THEN** the tooltip hides without moving focus; when the tooltip belongs to the focused control that Escape is consumed by the dismissal and does not also reach the dock's keyboard router, while once no tooltip shows Escape on the control reaches the router as before
- **AND** a tooltip shown by the pointer hides on any Escape without consuming it, and the next hover or Tab focus shows the tooltip again

### Requirement: Reading settings preview preferences without touching play
The settings surface SHALL offer a local reading sample: one fixed line of prose set in the message
window's page face - the bundled monospace reading face - at the page size and leading of the chosen
prose scale, above both groups of settings controls, with a replay control.

#### Scenario: Preference changes are visible locally
- **WHEN** the player changes the prose scale or the text speed
- **THEN** the sample restarts once at that preference while the live response position and narrative history remain unchanged and no action is sent

#### Scenario: Reduced motion shows the sample at once
- **WHEN** the effective motion level is `減少` or `關閉` and the player replays the sample at any text speed
- **THEN** the whole line is shown at once and the caption names the motion level as the reason

#### Scenario: Preview closes mid-type
- **WHEN** the player closes settings while the sample types
- **THEN** preview timers stop and no later preview content reaches the live reader

#### Scenario: The sample types at the message window's rate
- **WHEN** the sample plays at a chosen text speed and the effective motion level
- **THEN** it types at the rate the message window would use, shows at once for `瞬間` and whenever the effective motion level is not `完整`, and names that rule in a visible caption

#### Scenario: The sample plays once and restarts only on change or replay
- **WHEN** the settings surface opens, a preference changes, or the player replays the sample
- **THEN** it plays once on open, restarts once when the prose scale, the text speed or the motion level changes, plays again only through replay, and does not loop

#### Scenario: The sample's line never rewraps while typing
- **WHEN** the sample types
- **THEN** its whole line stays laid out so it never re-wraps or changes height mid-line, and assistive technology reads the complete line rather than a partly typed one

#### Scenario: The preview touches nothing that affects play
- **WHEN** the player updates or replays the sample
- **THEN** it appends no narrative, sends no action, does not change the live message window's page or reading position, consumes or arms no auto-advance, and does not change gameplay

#### Scenario: Closing settings stops all preview work
- **WHEN** the player closes the settings surface
- **THEN** all preview work stops

### Requirement: Settings switches preserve native accessible operation
Settings toggle controls SHALL be native checkboxes exposed as switches, named by their visible
label and described by their help line, with a checked state marked by both the knob's position and
the track's fill. Their labels and help SHALL render through the shared type tokens at or above the
16px chrome floor, they SHALL remain keyboard operable with Space, and they SHALL use the existing
preference persistence path.

#### Scenario: Keyboard toggles a preference
- **WHEN** the focused switch receives Space
- **THEN** exactly one preference change occurs and its new checked state is announced

#### Scenario: Settings cards share equal column tracks
- **WHEN** the settings surface renders its cards
- **THEN** the cards share equal column tracks while each takes its own content height
