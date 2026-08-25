## ADDED Requirements

### Requirement: The action dock renders as a floating panel in the stage's dock anchor
The action dock SHALL render inside the stage's `dock` anchor as one floating panel bounded to a
maximum width and horizontally centred, drawn with the stage's panel gradient, a hairline top border
and an upward shadow so it reads as a surface floating above the scene rather than a full-width page
row. Its height SHALL come from the shared `--dock-h` token and SHALL NOT grow with its content. The
panel SHALL be laid out as a fixed-height tab bar, an optional breadcrumb line, and one remaining
region that holds the current frame's rows; that region SHALL be the panel's only scrolling area, so
no dock content is ever pushed outside the anchor. The panel SHALL be the same single `#action-dock`
element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the
surface's documented focus target, and SHALL NOT be remounted when the mode changes.

#### Scenario: The dock is one centred floating panel
- **WHEN** the shell renders at 1440x900 in exploration mode
- **THEN** the dock renders as a single centred panel inside the dock anchor with a bounded maximum width, a top border and an upward shadow, and its height equals the shared dock-height token

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the panel's row region can display
- **THEN** the row region scrolls internally, the tab bar and the breadcrumb stay fixed, and no row is rendered outside the dock anchor

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute switches to the new mode, and it is not removed and re-created

#### Scenario: The panel stays inside its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock panel's rendered box stays within the dock anchor, and the frame's confirm control is reachable by scrolling the row region without being clipped

### Requirement: The dock's root frame renders as an icon tab bar with truthful count badges
The current dock surface's root menu frame SHALL render as a horizontal tab bar, one tab per root
item, each carrying a decorative glyph and its server-authored text label. The open root entry's tab
SHALL be marked with the accent fill, and the marking SHALL NOT be the only indication of state. When
the router is at the root frame the tab bar SHALL be the surface's row container: it SHALL carry the
listbox role, be the surface's single tab stop, name the focused tab through an active-descendant
association, and carry each root item's preserved row identity attribute and row id. When a deeper
frame is open the tab bar SHALL become inert ancestor chrome that marks which root entry is open and
SHALL NOT be a second tab stop.

A tab SHALL carry a count badge only when the number of rows its frame will contain is derivable
from the committed payload before that frame is opened; the badge SHALL equal that count exactly. A
tab whose count is zero or not derivable SHALL carry no badge. A badge SHALL NEVER be rendered from
an estimate, from a value the panel does not carry, or for rows the frame will not list.

The root menu's focus geometry SHALL match the rendered tab order: the root frame's column count
SHALL equal its item count, so the horizontal arrow keys traverse the visible tabs and the vertical
arrow keys are a no-op on the root.

#### Scenario: The root renders as tabs and owns the listbox
- **WHEN** the dock is at its root frame
- **THEN** each root item renders as a tab with a glyph and its label, the tab bar carries the listbox role with a single tab stop and an active-descendant reference, and each tab carries its preserved row identity attribute

#### Scenario: Badges equal a real count
- **WHEN** the committed exploration panel carries two interact targets and the committed suggestions payload carries four ready cards
- **THEN** the interact tab shows the badge `2`, the suggestions tab shows the badge `4`, and the look and move tabs show no badge

#### Scenario: A zero or unknowable count shows no badge
- **WHEN** a tab's frame would contain no rows, or its row count cannot be derived from the committed payload
- **THEN** that tab renders no badge at all rather than a zero or a placeholder

#### Scenario: Tab focus geometry matches the rendered order
- **WHEN** the player presses the horizontal arrow keys on the root frame
- **THEN** focus moves through the tabs in their rendered order and wraps at the ends, and the vertical arrow keys move focus nowhere

#### Scenario: An open deeper frame leaves the tab bar inert
- **WHEN** a deeper frame is open
- **THEN** the tab bar marks which root entry is open, the deeper frame's row container is the surface's only listbox and only tab stop, and no tab is reachable by sequential keyboard navigation

### Requirement: A breadcrumb derived from the router names the player's position at depth
The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root
frame, and SHALL hide it entirely at the root frame. The breadcrumb SHALL name the parent frame and
the current frame, with the current frame visually distinguished, and SHALL carry a back control.
Activating the back control SHALL perform exactly the same operation the Escape key performs — it
SHALL pop exactly one menu level and SHALL NOT dispatch any action.

The breadcrumb's contents and its visibility SHALL be derived from the keyboard router's own frame
stack and depth, published through the committed view in the same pass as the frame's rows. The
client SHALL NOT maintain a second navigation state — no local pane selection, no locally accumulated
crumb stack — so the breadcrumb can never disagree with what Escape will do. A frame's breadcrumb
label SHALL come from the frame itself; for a frame scoped to one target, that label SHALL be the
target's server-authored display name.

#### Scenario: The breadcrumb appears only below the root
- **WHEN** the dock is at its root frame
- **THEN** no breadcrumb is rendered
- **WHEN** the player opens a submenu
- **THEN** the breadcrumb appears naming the parent frame and the current frame

#### Scenario: The back control is the Escape path
- **WHEN** the player activates the breadcrumb's back control at any depth
- **THEN** exactly one menu level closes, the parent frame's rows render with the previously focused row marked, and no `ui_action` is emitted

#### Scenario: The breadcrumb tracks a target frame's own name
- **WHEN** the player opens an interact target's affordance frame
- **THEN** the breadcrumb's current segment is that target's server-authored display name

#### Scenario: The breadcrumb cannot drift from the router
- **WHEN** a panel replacement pops or replaces the current frame
- **THEN** the breadcrumb's depth and labels match the router's frame stack in the same render, with no interval in which they describe a frame the router has already left

### Requirement: Dock panes render a per-kind vocabulary from backed fields only
The dock's row region SHALL render the current frame in a form chosen for what that frame contains,
using one shared row renderer for every form so the focused marker, the disabled marker and its
`（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined
in exactly one place. The forms SHALL be: an exit outlet for a move frame, navigation rows for a
target or object list, affordance rows under a target head for a target-affordance frame, suggestion
cards for the suggestions frame, and the combat forms specified elsewhere in this capability.

A move row SHALL render the exit's direction as a leading glyph together with the destination's
display name. The glyph SHALL be resolved from a fixed client-side table of canonical direction words;
an exit label outside that table SHALL render verbatim in the glyph position rather than being mapped
to a guessed direction. The destination's display name SHALL be resolved by matching the move row's
server-authored destination node against the committed local-map nodes; when that node is not present
in the committed lattice the row SHALL render the glyph alone with no destination line. The submitted
move payload SHALL be unchanged.

A navigation row SHALL render a decorative icon, the row's server-authored name, an optional sub-line
and, when the row opens a deeper frame, a trailing affordance chevron. A sub-line SHALL contain only
fields the committed payload carries. No row SHALL render a statistics line, a portrait, or any other
element for which the payload has no field; where the design draft shows such an element it SHALL be
absent rather than emptied or mocked. Icons SHALL be decorative, SHALL be hidden from assistive
technology, SHALL always accompany a real text label, and SHALL be selected only from stable
server-authored keys — never from free text such as a display name.

A target-affordance frame SHALL render a head naming the target it is scoped to, taken from the
frame's own server-authored display name, above that target's affordance rows.

Every row in every form SHALL keep the existing disabled contract: a disabled row SHALL remain
focusable by arrow keys and by pointer, SHALL keep its accessible disabled state and its
server-authored explanation, and SHALL submit nothing.

#### Scenario: A move row names where it goes
- **WHEN** the move frame renders an exit whose label is a canonical direction and whose destination node is present in the committed local map
- **THEN** the row renders that direction's glyph together with the destination node's display name, and activating it submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** a move row's label is a named door or a dynamic wilderness exit rather than a canonical direction
- **THEN** the row renders that label verbatim in the glyph position and no direction is guessed for it

#### Scenario: An unknown destination renders no destination line
- **WHEN** a move row's destination node is absent from the committed local map
- **THEN** the row renders its glyph alone with no destination line and no invented name

#### Scenario: A row renders only backed fields
- **WHEN** a look frame renders a present entity
- **THEN** the row shows the entity's display name with its kind as the sub-line, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's affordance frame
- **THEN** the pane renders a head naming that target above the target's server-authored affordance rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row is focused in any pane form, by arrow key or by pointer
- **THEN** the row keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame in the HUD island area, grouped into the
player's side and the opposing side using the committed participants' server-authored team values, in
the presenter's order. Each participant SHALL render its session token, its display name, its current
and maximum hit points as numerals, and its state; a non-active state SHALL be conveyed by an explicit
text marker in addition to any colour. The frame SHALL NOT invent a field the participant descriptor
does not carry.

Each participant's portrait SHALL be resolved only by looking its server-authored portrait reference
up in the committed art panel's portrait catalog: a resolvable entry SHALL render that entry, an
entry that resolves to a placeholder SHALL render the placeholder card, and a null reference or an
unavailable art panel SHALL render no portrait at all. The client SHALL NOT construct a portrait
subject key or URL. While the participant frame is mounted it SHALL be the sole presenter of the
portrait catalog, so no separate portrait strip is rendered alongside it.

The participant frame SHALL be display-only: it SHALL NOT be a row container, SHALL NOT be part of
the dock's composite widget, and SHALL NOT be a second tab stop. Target selection happens in the
dock's target frame.

#### Scenario: Both sides render from the payload
- **WHEN** a combat session commits participants on both teams
- **THEN** the frame renders the player's side and the opposing side in presenter order, each participant showing its token, display name, current and maximum hit points, and state

#### Scenario: A non-active participant is marked in text
- **WHEN** a participant's state is fled, knocked out or defeated
- **THEN** the frame renders an explicit text marker for that state alongside any colour treatment

#### Scenario: A portrait comes only from the catalog
- **WHEN** a participant carries a portrait reference present in the committed portrait catalog
- **THEN** the frame renders that catalog entry, and when the reference is null or the art panel is unavailable it renders no portrait and constructs no URL

#### Scenario: The frame does not compete for focus
- **WHEN** the participant frame is mounted during combat
- **THEN** it is not reachable by sequential keyboard navigation, the dock's active row container remains the surface's only listbox, and no portrait strip is rendered outside the frame

### Requirement: Combat skills are chosen through a bounded master-detail
In combat, opening Skills SHALL present the committed skill categories as a bounded frame of category
entries, each carrying its server-authored label and the count of its own skill descriptors. Opening a
category SHALL present that category's sub-groups as a frame when the category carries more than one
sub-group, and SHALL open the skill frame directly when it carries exactly one — so no menu level ever
offers a single choice. The skill frame SHALL list that group's descriptors in the server's order,
each row carrying the skill's label and its resource cost, beside a detail region naming the focused
skill, its description, its cost, its target requirement and, when it is unavailable, its
server-authored reason.

Category, group and skill ordering SHALL be exactly the committed panel's order at every level. The
frames SHALL NOT reorder, filter or merge the server's grouping, and SHALL NOT render any badge or
field the skill descriptor does not carry. The subsequent power-scale step and target step SHALL be
unchanged in behaviour and payload: the scale frame SHALL render each advertised scale with its
server-computed cost in ascending order, and the target frame SHALL render the valid participants as
selectable tokens distinguishing the player's side from the opposing side, preserving the existing
multi-select marker. Every submitted cast payload SHALL be byte-identical to the payload the same
choices produce today.

The focused row SHALL be scrolled into view within the bounded row region on every frame render and
every focus change, so arrow navigation never leaves the focused row off-screen.

#### Scenario: Skills opens categories, not one flat list
- **WHEN** the player opens Skills in combat
- **THEN** the dock renders one row per committed skill category, each with its label and its own descriptor count, in the panel's order

#### Scenario: A single-group category skips a pointless level
- **WHEN** the player opens a category whose committed payload carries exactly one sub-group
- **THEN** the skill frame opens directly, and Escape from it returns to the category frame

#### Scenario: A multi-group category presents its groups
- **WHEN** the player opens a category whose committed payload carries more than one sub-group
- **THEN** the dock renders one row per sub-group in the panel's order, and opening one lists that group's skills

#### Scenario: The detail region names the focused skill
- **WHEN** a skill row is focused, including a disabled one
- **THEN** the detail region names that skill, its description, its cost and its target requirement, and for a disabled skill its server-authored reason, while the row stays focusable and submits nothing

#### Scenario: The cast payload is unchanged
- **WHEN** the player reaches a target through the category and group frames and confirms
- **THEN** the emitted cast payload is byte-identical to the payload the same skill, scale and target produce before this change

#### Scenario: The focused row is never off-screen
- **WHEN** the player arrows through a skill list longer than the bounded row region
- **THEN** the row region scrolls so the focused row is visible after every focus change

### Requirement: Destructive combat confirmation renders as an explicit two-step panel
The Forfeit entry SHALL open a confirmation frame rather than submitting, and that frame SHALL render
as an explicit warning panel stating what forfeiting does, with a cancel row and a confirm row. Only
the confirm row SHALL submit, and it SHALL carry the current session identifier exactly as it does
today. Escape or the breadcrumb's back control SHALL leave the confirmation without submitting and
without ending the session.

#### Scenario: Opening Forfeit submits nothing
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, and no mutation is sent

#### Scenario: Leaving the confirmation is safe
- **WHEN** the player presses Escape or activates the breadcrumb's back control on the confirmation frame
- **THEN** exactly one level closes, no mutation is sent, and the combat session is unchanged

#### Scenario: Confirming carries the session identifier
- **WHEN** the player activates the confirm row
- **THEN** exactly one forfeit action is emitted carrying the current session identifier
