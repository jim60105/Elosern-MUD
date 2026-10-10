## MODIFIED Requirements

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the scrolling region, in combat mode (never in creation mode, and never visibly in dialogue mode, where the strip is hidden with the collapsed command region). The legend SHALL render exactly once as visible content and SHALL be the only element carrying the legend's test hook; no root command list or pane SHALL carry a second copy.

#### Scenario: The legend matches the reference dock hint
- **WHEN** the legend strip renders
- **THEN** it matches `docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text `數字鍵 1–9 ‧ ` followed by an `<kbd>` element naming `Enter` and the verb `執行`, the separator `‧`, and an `<kbd>` element naming `Esc` and the verb `返回`; the legend renders with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border); and the dock carries no dialogue-mode legend variant

#### Scenario: The legend never lies
- **WHEN** a key, gesture, or affordance is named in the legend, or when a named affordance's behaviour changes
- **THEN** the legend names no key, gesture, or affordance this client does not implement or that no longer behaves as named, and advertises no implemented affordance the reference's legend does not name; when a named affordance's behaviour changes (for example, a control that used to open a surface and now only moves focus into an always-present one), the legend's wording is updated in the same change that alters the behaviour

#### Scenario: Digits pick and confirm the frame's first nine entries
- **WHEN** the dock owns keyboard focus (the key target is not editable) and the player presses `1`–`9`
- **THEN** the press moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order — for the scene overview, its first nine chips in reading order: people, then objects, then the footer; exits belong to the separate compass; a frame's `back` row takes the slot of its rendered position) and activates the entry through the same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an in-flight entry stays locked, and a held repeat is suppressed; the slots address the frame's rendered entries, disabled ones included

#### Scenario: Digits outside the dock's claim fall through
- **WHEN** dialogue mode holds — or a digit's entry does not exist (a frame with fewer rendered entries, dialogue mode, or the pre-session empty stack)
- **THEN** in dialogue mode neither the dock's entries nor the keyboard router claims any digit: the digits `1`–`N` belong to the dialogue choice list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage after the line is fully read" defines; and an unclaimed digit falls through to the text / command-history path

#### Scenario: The legend renders once
- **WHEN** the dock renders in combat mode and later changes to exploration or dialogue
- **THEN** combat carries exactly one legend strip and no duplicate; exploration renders no legend element and dialogue keeps its strip hidden with the command region

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in combat mode
- **THEN** the legend reads `數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the scene overview holds two person chips and one object chip beside a compass with three exit targets, and the player presses `2`, then after Escape presses `3`
- **THEN** `2` opens the second person's popover once and `3` submits the object's `explore.look` once; compass targets occupy no digit slot

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue choice list shows four picks with focus on the list, the command region is
  collapsed, and the player presses `4` and `5`
- **THEN** the `4` press activates pick four through the same dispatch entry, the `5` press is handled
  by neither the list nor the keyboard router and falls through, and the hidden dock's focus and frame
  are unchanged

### Requirement: Dock panes render a per-kind vocabulary from backed fields only

The dock's row region SHALL render the current frame in a form chosen for what that frame contains, using one shared row renderer for every form so the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place.

#### Scenario: The form set is fixed
- **WHEN** the row region selects a form
- **THEN** the forms are: person, object, and footer chips for the scene overview beside the exit compass; the verb popover's rows under a target head; the waiting cards; suggestion cards for the suggestions frame; and the combat forms specified elsewhere in this capability

#### Scenario: Exploration frames never regress to grids or nav lists
- **WHEN** any exploration frame renders
- **THEN** it renders no exit-outlet grid and no navigation-row list: exits are targets of the separate compass, and a host's conversation topics are the dialogue surface's choices, never a dock frame

#### Scenario: An enabled exit chip names direction by glyph and destination by text
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: Direction glyphs come only from the canonical table
- **WHEN** an exit label falls outside the fixed client-side table of canonical direction words
- **THEN** the glyph is resolved from that table, and an out-of-table label renders verbatim as the chip's primary text (there being no glyph to carry it) rather than being mapped to a guessed direction

#### Scenario: An unknown destination falls back without doubling labels
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: A disabled exit chip keeps its own label and marker
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: Exit chip focus and disabled reasons stay honest
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: Chips and rows render only backed fields
- **WHEN** any chip or row renders
- **THEN** it renders only fields the committed payload carries: its server-authored name and, where its form has one, an optional sub-line composed of such fields; none renders a statistics line, a portrait, or any other element for which the payload has no field — where the design draft shows such an element it is absent rather than emptied or mocked

#### Scenario: Icons are decorative and key-selected
- **WHEN** a chip or row shows an icon or glyph
- **THEN** it is decorative, hidden from assistive technology, always accompanies a real text label, and is selected only from stable server-authored keys or the direction table — never from free text such as a display name

#### Scenario: The verb popover heads with its target
- **WHEN** a target's verb popover renders
- **THEN** it renders a head naming the target it is scoped to, taken from the frame's own server-authored display name, above that target's rows

#### Scenario: The disabled contract holds in every form
- **WHEN** a disabled entry renders in any row or chip form
- **THEN** it keeps the existing disabled contract: it remains focusable by arrow keys and by pointer, keeps its accessible disabled state and its server-authored explanation, and submits nothing

#### Scenario: A move row names where it goes
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: A focused move row is not double-marked
- **WHEN** the compass resolves or aims the committed exit described by this scenario
- **THEN** the compass target and shared readout follow `webclient-exit-compass`: map bearing precedes canonical direction fallback, other exits become portals, enabled destinations use committed node names with exit-label fallback, disabled targets stay aimable and expose the unchanged server reason without submitting, and activation uses the unchanged move payload

#### Scenario: The move frame has no companion panel
- **WHEN** the exploration root renders with any overview chip focused
- **THEN** the compass occupies the left side and the shared readout and overview occupy the right column; no exit-outlet grid or detail aside renders

#### Scenario: A row renders only backed fields
- **WHEN** the scene overview renders a look-only chip for a present entity
- **THEN** the chip shows the entity's display name only, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's verb popover
- **THEN** the popover renders a head naming that target above the target's server-authored rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row or chip is focused in any form, by arrow key or by pointer
- **THEN** it keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation mode and for every frame, and no surface outside the band SHALL be positioned from the frame the dock currently carries.

#### Scenario: No frame moves or resizes the dock
- **WHEN** the dock carries the scene overview, a target's verb popover, the waiting frame, the combat frames, the skill master-detail, the destructive confirmation, or an empty pane host
- **THEN** no frame widens, heightens, shortens, or moves its box

#### Scenario: Dialogue hides the dock with the region
- **WHEN** the committed mode is dialogue
- **THEN** the command region is collapsed and the dock is hidden with `display:none` together with it, as "The command region collapses in dialogue mode and the message window spans the band" states; it is not rendered anywhere else in that mode

#### Scenario: Fixed chrome surrounds one scrolling region
- **WHEN** the dock's content column lays out
- **THEN** it is laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the bottom in combat only — around one remaining region that holds the current frame's rows or chips, and that region is the surface's only scrolling area, so no dock content is ever pushed outside the command region

#### Scenario: Popovers and wide frames stay inside the region
- **WHEN** a target's verb popover renders, or a frame's content does not fit the region's width
- **THEN** the popover renders as a card laid over the region's visible box, inside the command region, scrolling inside its own card when its rows exceed it, and the wide frame wraps or collapses its own columns inside the region, never overflowing it horizontally

#### Scenario: One dock element persists across every mode
- **WHEN** the committed mode changes, including into or out of dialogue
- **THEN** the panel is the same single `#action-dock` element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the documented focus forwarding target, with the compass owning exploration-root focus and the active row container owning other dock frames, and it is not remounted

#### Scenario: The presentation stays readable beyond colour
- **WHEN** the command region and its band render
- **THEN** the command region uses the current charcoal-and-gold presentation, the band that contains it paints the reference's band chrome, and selected actions remain distinguishable by text and shape as well as their gold or warm-red emphasis

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1451x790 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb popover's card lies inside the command region

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the combat-only legend strip) stays fixed, and no row or chip is rendered outside the command region

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, dialogue, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, it is hidden with `display:none` exactly while the mode is dialogue, and
  it is not removed and re-created

#### Scenario: The panel stays inside its region at the minimum viewport
- **WHEN** the shell renders at 1451x790 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the command region, no dock content overflows the
  region horizontally, and the frame's confirm control is reachable by scrolling the row region
  without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element paints a background gradient and a box-shadow, its top edge is the
  seam's fine gold line drawn by the band's own decoration, and the `#action-dock` content column
  itself paints no background, border, or shadow

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed and the message region SHALL span the band's whole width at the band's fixed height from the commit's frame. The collapsed region and the action dock inside it SHALL leave the accessibility tree, the tab order, and pointer hit-testing from the commit's frame.

#### Scenario: The region slides out and back with the motion level
- **WHEN** the mode enters dialogue, and later leaves it, at each motion level
- **THEN** the region slides out to the right and fades over the panel duration of the client's motion level, drawn over the widened message region, and is `visibility: hidden` once that slide ends, contributing nothing visible; leaving dialogue brings it back into reach in the commit's frame and slides it back in from the right; at `reduced` it only fades, within 150ms, and at `off` it hides and returns in the commit's frame

#### Scenario: The dock survives dialogue unmounted-free
- **WHEN** the mode enters and leaves dialogue
- **THEN** the dock stays the same mounted `#action-dock` element, its router keeps the exploration scene overview as its only frame (the reset on entering dialogue that `webclient-exploration-menu` defines), leaving dialogue shows that overview again with no remount, dialogue presents no dock frame, and no exploration affordance is removed from the committed `exploration` panel: movement stays reachable through the minimap and the conversation's own controls

#### Scenario: Dialogue's focus home is the choice list or the page surface
- **WHEN** the mode is dialogue
- **THEN** the shell's focus home is the dialogue choice list while it is rendered and otherwise the message window's page surface, and every path that returns focus to the focus home — the command line's Escape and accepted send, the mode-change rescue, and the return after a completed or rejected action — lands there, never on the hidden dock and never on the document body

#### Scenario: Mode boundaries move focus deliberately
- **WHEN** the mode enters dialogue with focus held inside the command region, or leaves dialogue for exploration with focus held inside the message region, inside the `choices` anchor, or on the document body
- **THEN** on entering, focus moves to the message window's page surface before the region is hidden; on leaving, focus moves to the exit compass once the region is rendered again

#### Scenario: The router claims only the slash in dialogue
- **WHEN** the mode is `dialogue`
- **THEN** the keyboard router claims only `/` (the command-line opener); every other key is unclaimed by the dock router, so no key moves the hidden dock's focus, pushes or pops a frame, or activates a hidden entry; the keys the dialogue choice list handles never reach the router, and Enter and Space on the focused page surface keep their reading meaning

#### Scenario: Entering dialogue collapses the command region
- **WHEN** the player activates 交談 in a host's verb popover at 1451x790 and the commit makes the mode `dialogue`
- **THEN** from the commit's frame the band's command region and the `#action-dock` element are out of the accessibility tree and the tab order, the message region spans the band's whole width at 220px (±1px) height, the region is `visibility: hidden` once its slide ends, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

#### Scenario: Leaving dialogue restores the overview without a remount
- **WHEN** the player activates the exit row and the commit returns the mode to `exploration`
- **THEN** the same `#action-dock` element is back in the accessibility tree in the commit's frame, slides back into the command region at the scene overview with no popover open, and focus is on the exit compass

#### Scenario: Keys never drive the hidden dock
- **WHEN** the mode is dialogue, focus is on the document body, and the player presses ArrowRight, Enter, and Escape
- **THEN** none of the keys is claimed by the dock router, the router's focused key and depth are unchanged, and no `ui_action` is emitted

#### Scenario: Slash still opens the command line in dialogue
- **WHEN** the mode is dialogue, no editable control is focused, and the player presses `/`
- **THEN** the command line expands and focus moves into its input field with no literal `/` inserted

#### Scenario: Movement stays reachable during a conversation
- **WHEN** a dialogue session is live and the player activates an adjacent minimap node
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the session through the existing seam, the committed mode returns to `exploration`, and the command region renders the new room's overview

### Requirement: Dialogue choices appear centred over the stage after the line is fully read
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the client SHALL present the conversation's choices as one choice list in the stage's `choices` anchor, and nowhere else. The list SHALL render only while the message window reports that the current response's last page is on screen, fully shown, with no pending action mark, and while no action the player dispatched is in flight.

#### Scenario: Any unread or in-flight moment hides the list
- **WHEN** a page is still typing, a further page is not yet read, or a pick or free-form speech awaits its reply
- **THEN** the list is not rendered

#### Scenario: The rows follow the payload exactly
- **WHEN** the choice list renders
- **THEN** its rows are, in order: one pick row per `dialogue.choices` entry in payload order, each carrying the digit badge of its 1-based position and its bounded label; a `⌨ 自由對話` row; a `↦ 移動…` row; and a `✕ 結束對話` row — and it renders no row the panel does not back, no reason tag, and no disabled pick

#### Scenario: Picks and exits dispatch their exact intents
- **WHEN** the player activates a pick row, or an enabled exit row
- **THEN** a pick dispatches `explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` through the single dispatch entry, and an enabled exit row dispatches the unchanged `explore.move` payload of its committed move row

#### Scenario: The free-form and exit rows dispatch nothing themselves
- **WHEN** the player activates `⌨ 自由對話`, or `✕ 結束對話`
- **THEN** `⌨ 自由對話` expands the command line and focuses its field through the free-form borrow path, bound to the host, and dispatches nothing itself; `✕ 結束對話` dispatches `explore.dialogue_leave` with `{npc_id: host.identity}` and nothing else

#### Scenario: The move row borrows the scene overview's exits
- **WHEN** the player activates `↦ 移動…`
- **THEN** it dispatches nothing and replaces the choices with dedicated committed `moveItems` rows from the store view, independent of the router root, in payload order, carrying their direction glyphs, enabled destination names, disabled markers and unchanged server reasons, followed by a back row

#### Scenario: The exit rows return to the choices
- **WHEN** Escape or the back row is activated in the exit rows, or the committed room has no exits
- **THEN** the choice rows return with the `↦ 移動…` row focused, and a room without exits still shows the back row alone

#### Scenario: One composite, one tab stop, full keyboard
- **WHEN** the choice list holds focus
- **THEN** it is one keyboard composite and one tab stop: DOM focus rests on the list container, which names its focused row through an active-descendant reference; ArrowUp and ArrowDown move to the previous and next row, wrapping; Home and End move to the first and last row; Enter and Space activate the focused row; while the choice rows are shown, digit `1`–`N` activates pick N directly; and a held key's auto-repeat does not activate

#### Scenario: The active row is shown by shape and fill
- **WHEN** the list holds focus on its rows, including a disabled exit row
- **THEN** the active row is shown by shape and fill — a leading `▸` and the dock's muted-gold fill — never by colour alone, and an active disabled exit row keeps a quiet treatment that promises no action

#### Scenario: Handled keys stop at the list
- **WHEN** the list handles a key, and when `/` or an unhandled key is pressed
- **THEN** every key the list handles is consumed by it and does not reach the keyboard router or the page surface, while `/` and every key the list does not handle passes on unchanged

#### Scenario: Focus arrives, leaves, and never dangles
- **WHEN** the list appears while focus is on the message window, inside the message region, or on the document body, and when an activation is about to dispatch
- **THEN** focus moves to the list with its first row focused, and before an activation dispatches focus moves to the message window's page surface, so the list's removal never leaves focus on a removed element or the document body; a pointer activation of a row focuses that row and activates it through the same path as Enter

#### Scenario: Activations obey the dispatch lock once each
- **WHEN** a mutation is in flight or awaiting its declared presentation revision, and when key and pointer input combine
- **THEN** every activation is suppressed exactly like a dock entry, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The list derives only from committed panels
- **WHEN** the list's rows and presence are computed
- **THEN** rows derive from the committed `dialogue` and `exploration` panels alone and depend on no dock frame or router descriptor, and presence derives from the window's reader state and the dispatch state, never from narrative prose

#### Scenario: The choices wait for the last page
- **WHEN** a greeting of two pages commits with three choices at the `normal` text speed
- **THEN** no choice list is rendered while page 1 types, after it is fully shown, or while page 2 types, and the list renders in the `choices` anchor with focus on its first row once page 2 is fully shown

#### Scenario: The rows follow the committed panel
- **WHEN** the list renders for a panel with three choices
- **THEN** it shows pick rows badged `1`, `2`, `3` with the panel's labels in payload order, then `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`, and nothing else

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer, Enter, or the `2` key
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that row's `keyword_id` is submitted, the list is removed while the request is in flight, focus is on the message window's page surface, and the list returns once the reply's last page is fully shown

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates `⌨ 自由對話`
- **THEN** the command line expands with focus in its field for a freeform utterance to the host, and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates `✕ 結束對話`
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is submitted and no other action is dispatched

#### Scenario: Move swaps in the exits and Escape returns
- **WHEN** the room has two exits, one locked, and the player activates `↦ 移動…`, focuses the locked exit and presses Enter, then presses Escape
- **THEN** the list shows the two exit rows with their direction glyphs and the back row, the locked row shows its reason and nothing is submitted, and Escape returns to the choice rows with `↦ 移動…` focused

#### Scenario: A move from the list leaves the conversation
- **WHEN** the player activates `↦ 移動…` and then an enabled exit row
- **THEN** exactly one `explore.move` request with the committed move row's unchanged payload is submitted, the movement settlement clears the session through the existing seam, and the committed mode returns to `exploration` with the dock at the new room's overview

#### Scenario: The list is one tab stop and keeps its keys
- **WHEN** the list has focus and the player presses Tab, then Shift+Tab back, then ArrowDown twice and Enter
- **THEN** Tab leaves the list in one step, the list is reached again in one step, the arrows move the active-descendant reference, Enter activates the focused row once, and the keyboard router saw none of those arrow or Enter keys

#### Scenario: The choices never show beside unread text
- **WHEN** a reply's first page is on screen and further lines of the same response arrive
- **THEN** the list stays unrendered until the response's last page is fully shown

