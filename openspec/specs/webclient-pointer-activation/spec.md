## Purpose

The dock-wide contract that every action-dock surface renders exactly the keyboard router's current menu frame, that pointer activation traverses the identical focus, disabled-explanation, and submission-gating path as the keyboard, the composite-widget focus model, the single delegated listener on the action dock, the plugin-contract keydown routing, and the pointer browser-acceptance journeys.

## Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame
Each dock that owns the action dock — exploration, character, creation, and combat — SHALL render its rows from the keyboard router's current menu frame, so the rows visible on screen are always exactly the items the router will navigate, explain, and submit. A dock SHALL re-render its rows whenever the router pushes, replaces, or pops a frame, and SHALL NOT leave a pushed frame without a rendered representation.

#### Scenario: Combat submenus become visible instead of blind
- **WHEN** the player opens Skills, a target list, a shorthand choice, or the Forfeit confirmation in combat mode
- **THEN** that frame's entries are rendered as rows in the action dock with the focused entry marked, instead of the root actions remaining on screen

#### Scenario: Popping a frame restores the parent's rows
- **WHEN** the player presses Escape from a submenu in any dock
- **THEN** exactly one level closes and the rendered rows return to the parent frame with the previously focused row marked

#### Scenario: The combat root list is the root frame's rows
- **WHEN** the combat dock is at its root frame
- **THEN** the list rows are exactly the root frame's items in the router's order with their row identities, and opening one pushes that item's frame through the ordinary confirmation path, which replaces the list with the pushed frame's rows

#### Scenario: Level indicators are derived, never held separately
- **WHEN** the router pops or replaces a frame for any reason, including a panel replacement
- **THEN** the rendered rows and the breadcrumb both re-derive from the router's frame stack in the same render, and no client-held pane or crumb state survives to contradict Escape

#### Scenario: Display-only rows stay display-only
- **WHEN** the character panel's read-only rows are rendered
- **THEN** they are focusable and update the detail pane, and no row submits an action

#### Scenario: A modal form is not required to become rows
- **WHEN** the exploration rest-duration form or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores the rendered rows for that frame

#### Scenario: The overview beneath a popover is inert
- **WHEN** a target's verb popover is open and the player clicks an exit chip of the overview visible beneath it
- **THEN** the popover closes exactly as its back row would, no `ui_action` is emitted, and the overview becomes the current frame with the target's chip focused

#### Scenario: Re-render is synchronous with the router event
- **WHEN** the router pushes, replaces, or pops a frame
- **THEN** the re-render is synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left

#### Scenario: One shared renderer defines every row
- **WHEN** rows are rendered in any dock
- **THEN** the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one shared renderer

#### Scenario: The shared renderer adapts to the frame's shape
- **WHEN** a frame's shape calls for a tab, a scene-overview chip, a verb-popover row, a suggestion card, a skill row, a target token, a scale choice, or a confirmation row
- **THEN** the same shared renderer renders the row in that visual form, chosen from the frame's own shape, and is not duplicated per form

#### Scenario: The row model preserves menu semantics
- **WHEN** the shared-renderer row model is in place
- **THEN** no menu's items, labels, order, or semantics have changed

#### Scenario: Modal forms stay outside the row model
- **WHEN** the creation dock's text and numeric fields or the exploration dock's bounded rest-duration form is open — modal forms never pushed onto the router stack
- **THEN** each keeps its existing self-contained key capture, restores the router's frame rendering when it closes, and is an exception to the row model, not a violation of it

#### Scenario: The combat root frame renders as a vertical command list
- **WHEN** the combat dock renders its root frame
- **THEN** the root frame appears as a vertical command list in the rows region carrying the same items, order, keys and row identities, and no root row stays rendered, focusable, or submittable while a deeper frame is open

#### Scenario: Level indicators come only from the router's stack
- **WHEN** any visible level indicator, including a breadcrumb, is rendered
- **THEN** it is derived from the router's frame stack and its depth, and the dock renders no navigation affordance whose state is held outside that stack

### Requirement: Pointer activation traverses the identical path as keyboard confirmation
Activating an action-dock row with the pointer SHALL move the router's focus to that row and then perform the same confirmation the keyboard performs, so both input methods share one gate. A pointer activation on an enabled row SHALL emit exactly one `ui_action` message, with the same action ID and payload the keyboard would emit. A pointer activation on a disabled row SHALL surface that row's explanation and SHALL NOT submit.

#### Scenario: Clicking a row submits exactly what Enter submits
- **WHEN** the player clicks an enabled exploration, service, creation, or combat row
- **THEN** the browser emits exactly one `ui_action` with the same action ID and payload that confirming the same row with Enter emits

#### Scenario: Clicking a disabled row explains without submitting
- **WHEN** the player clicks a row rendered as disabled
- **THEN** the row's disabled reason becomes readable in the detail pane and no `ui_action` message is emitted

#### Scenario: Clicking while locked emits nothing
- **WHEN** the player clicks an enabled mutating row while a mutation is in flight, while the client awaits a declared presentation revision, or while the offline overlay is shown
- **THEN** no message is emitted and the lock remains in effect

#### Scenario: One delegated listener survives dock re-renders
- **WHEN** a dock replaces its entire rendered subtree after a snapshot, a mode change, or a menu transition
- **THEN** clicking a newly rendered row still activates it, and no per-row listener is registered or leaked

#### Scenario: Pointer activation bypasses the held-Enter repeat guard
- **WHEN** the player activates a row with the pointer
- **THEN** the activation neither consults nor sets the held-Enter repeat guard, because that guard exists to suppress key repeat and would otherwise reject a legitimate second click on the same row

#### Scenario: Locked pointer activation is suppressed as the keyboard is
- **WHEN** a pointer activation arrives while a mutation is in flight or while the client is awaiting a declared presentation revision
- **THEN** it is suppressed exactly as the keyboard is suppressed

#### Scenario: One delegated listener on the stable dock element
- **WHEN** pointer activation is wired up
- **THEN** it is delivered by exactly one delegated listener installed on the stable action-dock element, surviving every dock re-render without per-row binding

### Requirement: The action dock is a single composite widget that cannot double-activate
The rendered rows SHALL form one composite widget: the row container SHALL carry the listbox role, be the surface's single tab stop, and name the focused row through an active-descendant association, and each row SHALL carry the option role with its selected state. Rows SHALL NOT be individually reachable by sequential keyboard navigation. Pressing the pointer on a row SHALL NOT move DOM focus off that container.

#### Scenario: Enter on a focused row emits one action, not two
- **WHEN** the player moves focus to an enabled row with the arrow keys and presses Enter
- **THEN** exactly one `ui_action` is emitted, with no additional activation from a synthesized click

#### Scenario: A double-click does not activate a replaced row
- **WHEN** the player double-clicks a row that opens a submenu
- **THEN** the submenu opens once and the second click does not activate whichever row now occupies that position

#### Scenario: A stale row cannot push a second frame
- **WHEN** a pointer activation resolves to a row that the previous activation's re-render already removed from the document
- **THEN** the activation is ignored, no additional menu frame is pushed, and one Escape still returns to the parent frame

#### Scenario: Clicking another tab returns through the router
- **WHEN** a deeper frame is open and the player clicks the tab of a different root entry
- **THEN** the router closes the open frames one level at a time back to the root, focuses that tab's row, and opens its frame with exactly one deliberate activation, emitting no unexpected `ui_action`

#### Scenario: Only one container is the listbox at a time
- **WHEN** the dock is inspected at the root frame and again at a deeper frame
- **THEN** exactly one row container carries the listbox role, the tab stop and the active-descendant reference in each case, and the other container is neither focusable by Tab nor exposed as a listbox

#### Scenario: Focus indication stays with the router
- **WHEN** the player clicks a row
- **THEN** the row container retains DOM focus, the active-descendant association names the clicked row, and the visible focus indicator is on that row

#### Scenario: Composite roles are present and machine-checkable
- **WHEN** the rendered action dock is inspected in the browser
- **THEN** the row container exposes the listbox role with a tab stop and an active-descendant reference, each row exposes the option role with its selected and disabled state, and no row is reachable by sequential keyboard navigation

#### Scenario: Exactly one container holds the listbox role
- **WHEN** the dock is at the root frame, where the root frame renders as a tab bar, and at any deeper frame
- **THEN** exactly one row container holds the role — the tab bar's container at the root frame and the rows region's container at every deeper frame — and the other is neither a tab stop nor a listbox

#### Scenario: The action-dock element forwards focus
- **WHEN** an active row container is mounted
- **THEN** the action-dock element remains the surface's documented focus target and forwards focus to the active row container, so existing focus-restoration callers need no change

#### Scenario: Only live primary pointer activations are admitted
- **WHEN** a pointer activation arrives
- **THEN** it is admitted only when it is a primary single activation and its resolved row is still part of the rendered document; a keyboard-synthesized activation, the repeated events of a multi-click, and an activation whose row belongs to a frame that has already been replaced are all ignored

#### Scenario: Ancestor-tab activation goes through the router
- **WHEN** a deeper frame is open and a pointer activates an inert ancestor tab
- **THEN** it is admitted only as router operations — closing frames one level at a time until the root frame is current, moving focus to that tab's row, then performing the ordinary confirmation — bounded by the router's own depth, never swapping the rendered rows directly, and activating the tab of the already-open root entry does nothing

#### Scenario: One deliberate activation yields one effect
- **WHEN** the keyboard confirms a focused row, or key and pointer inputs combine on rows
- **THEN** keyboard confirmation emits exactly one action, no combination of key and pointer input on the same row emits more than one action per deliberate activation, and no sequence of pointer activations pushes a menu frame more than once per deliberate activation

#### Scenario: Navigation rows obey the single-activation guarantee
- **WHEN** a navigation row — which opens a submenu rather than submitting and is therefore not covered by the in-flight mutation lock — is activated
- **THEN** the one-action-per-deliberate-activation guarantee still holds

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the focused command field owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. Field ownership SHALL be determined by whether the field
holds focus, not by whether the command line is expanded.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command field
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  focused command field owns, so no unclaimed-keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command field
- **THEN** the bridge does not claim them and history recall works

#### Scenario: A trapped surface owns its keys while it is open
- **WHEN** a full-screen overlay holds trapped focus and the player presses a navigation key
- **THEN** the overlay owns the key, the router consumes nothing behind it, and closing the
  overlay returns focus to its trigger and restores the router's ownership

#### Scenario: A collapsed command line owns no key
- **WHEN** the command line is collapsed and the action dock holds focus, and the player presses ArrowUp, then `/`, then ArrowUp
- **THEN** the first ArrowUp is claimed by the router for the dock, `/` expands the command line and moves focus into its field, and the second ArrowUp is owned by the focused field and walks the command history

#### Scenario: A field without focus owns no key
- **WHEN** a collapsed command line's hidden field cannot hold focus, or an expanded line's field has lost focus
- **THEN** the field owns no key

#### Scenario: A modal capture pre-empts the bridge and cleans up
- **WHEN** a modal capture must pre-empt the keyboard bridge — the exploration dock's bounded rest-duration entry or the creation dock's text/numeric field
- **THEN** it MAY use a capture-phase listener and SHALL remove it when its form closes

#### Scenario: A trapped surface releases ownership on close
- **WHEN** a focus-trapped surface laid over the stage — a reference drawer or a full-screen overlay — closes
- **THEN** it releases its ownership of keys and returns focus to the control that opened it

### Requirement: Pointer parity is verified in the browser without weakening keyboard-only acceptance
The managed localhost Playwright suite SHALL exercise pointer-only acceptance journeys at both acceptance viewports, asserting the exact emitted `ui_action` count and payload for each. The keyboard-only acceptance requirements SHALL NOT be weakened to accommodate pointer parity and SHALL continue to pass, so keyboard-only play is still a verified guarantee rather than a side effect.

#### Scenario: A pointer-only journey completes in Chromium
- **WHEN** a seeded actor uses only the mouse to open an exploration submenu and submit an action
- **THEN** each step emits exactly one expected `ui_action` and the panels refresh, with no key press required

#### Scenario: Keyboard-only journeys still pass unchanged
- **WHEN** the existing keyboard-only exploration, service, creation, and combat journeys run
- **THEN** they pass with the keyboard steps and assertions their own acceptance requirements define, none of which is relaxed for pointer parity

#### Scenario: Offline pointer activation emits nothing
- **WHEN** the WebSocket is interrupted and the player clicks an enabled row under the offline overlay
- **THEN** no `ui_action` crosses the wire and the overlay remains until a valid new-epoch snapshot is adopted

#### Scenario: Pointer parity runs at both acceptance viewports
- **WHEN** the pointer-only suite runs
- **THEN** it exercises the pointer only at both acceptance viewports: the 1451x790 reference viewport and 2560x1440

#### Scenario: The pointer-only journey set is enumerated
- **WHEN** the pointer-only suite exercises its journeys
- **THEN** it covers an exploration root entry and one submenu submission, a service action submitted from its reference drawer's own control, a combat root action and one combat submenu selection, a disabled row that explains without submitting, and an activation attempt while the offline overlay is shown
