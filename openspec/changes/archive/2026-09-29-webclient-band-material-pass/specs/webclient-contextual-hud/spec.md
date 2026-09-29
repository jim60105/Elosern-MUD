## ADDED Requirements

### Requirement: The bottom band separates material and focus without obscuring controls
The fixed bottom band SHALL provide a continuous ink-and-gold reading surface with a decorative stage seam and aligned message-control and shortcut rows. Page text, command rows and popovers SHALL never paint over these reserved controls. Only the active control SHALL carry the strongest focus treatment; the command field SHALL expose one clear focus frame.

#### Scenario: Popover text is isolated
- **WHEN** a verb popover opens over populated scene chips
- **THEN** no chip text shows through it, the target heading is stated once, and background chips cannot activate

#### Scenario: Dense command content is bounded
- **WHEN** a frame contains more rows than fit
- **THEN** its own row region scrolls while the legend and message controls remain visible on one baseline

#### Scenario: Motion is reduced
- **WHEN** the player changes command frames with reduced motion or off
- **THEN** reduced uses no 3D rotation or wipe and off commits immediately without losing focus

## MODIFIED Requirements

### Requirement: A breadcrumb derived from the router names the player's position at depth

The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root
frame, and SHALL hide it entirely at the root frame. The one exception is a target's verb popover
(the scene overview's person-target frame): the popover's own heading already names the target, so
while that frame is current the breadcrumb SHALL NOT render and the target SHALL be stated exactly
once; the popover's `back` row, Escape, and a pointer press outside the popover card remain its back
paths. Every other submenu keeps the breadcrumb. The breadcrumb SHALL name the parent frame and
the current frame, with the current frame visually distinguished, and SHALL carry a back control.
Activating the back control SHALL perform exactly the same operation the Escape key performs — it
SHALL pop exactly one menu level and SHALL NOT dispatch any action.

The breadcrumb's contents and its visibility SHALL be derived from the keyboard router's own frame
stack and depth, published through the committed view in the same pass as the frame's rows. The
client SHALL NOT maintain a second navigation state — no local pane selection, no locally accumulated
crumb stack — so the breadcrumb can never disagree with what Escape will do. A frame's breadcrumb
label SHALL come from the frame itself; for a frame scoped to one target, that label SHALL be the
target's server-authored display name. Every frame's `back` item SHALL render as a row of that frame, so
a focused `back` item carries the same focused treatment as any other row (a background fill and
border change together); the breadcrumb's back control SHALL carry no focus state of its own that
mirrors the router's focus. Activating the back row with Enter or the pointer, or activating the
breadcrumb's back control, SHALL pop exactly one level, restore the parent frame's previously
focused entry, and dispatch no action.

#### Scenario: The breadcrumb appears only below the root
- **WHEN** the dock is at its root frame
- **THEN** no breadcrumb is rendered
- **WHEN** the player opens a submenu
- **THEN** the breadcrumb appears naming the parent frame and the current frame

#### Scenario: The back control is the Escape path
- **WHEN** the player activates the breadcrumb's back control at any depth
- **THEN** exactly one menu level closes, the parent frame's rows render with the previously focused row marked, and no `ui_action` is emitted

#### Scenario: A focused `back` row keeps a visible focus carrier
- **WHEN** keyboard focus moves onto the suggestions frame's `back` item
- **THEN** that `back` item is rendered as a row carrying the focused state (fill and border change together, not color alone), the breadcrumb's back control carries no focused state, and Enter on the row or a click on the breadcrumb control pops exactly one level back to the parent frame
- **WHEN** keyboard focus moves onto a verb popover's `back` item
- **THEN** that `back` item carries the same focused row treatment, and Enter or a click on the row pops exactly one level back to the scene overview

#### Scenario: The breadcrumb tracks a target frame's own name
- **WHEN** the player opens a frame scoped to one target other than the verb popover
- **THEN** the breadcrumb's current segment is that target's server-authored display name
- **WHEN** the player opens an interact target's verb popover from the scene overview
- **THEN** the popover's heading is that target's server-authored display name, no breadcrumb is rendered, and the target's name appears once in the command region

#### Scenario: The breadcrumb cannot drift from the router
- **WHEN** a panel replacement pops or replaces the current frame
- **THEN** the breadcrumb's depth and labels match the router's frame stack in the same render, with no interval in which they describe a frame the router has already left
