# webclient-contextual-hud Specification

## Purpose
The full-bleed cinematic stage with its anchored HUD surfaces (scene backdrop, narrative caption,
HUD islands, action dock, command line), the committed-mode visibility matrix, the truthful scene
backdrop, the bounded narrative caption, drawer/overlay stage recessing, and the action-dock
re-chrome contract: the centred floating dock panel, the root tab bar with truthful count badges,
the router-derived breadcrumb, the per-kind row vocabulary, the display-only combat participant
frame, the bounded skill master-detail, and the two-step destructive confirmation.
## Requirements
### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the narrative caption card above it, the HUD islands above that, the action dock
above those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed
by named stage anchors (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`) rather than by fixed
layout columns, and SHALL NOT be placed inside a scrolling container that can push a required surface
out of view. The dock's reserved height SHALL come from the shared `--dock-h` token, and the narrative
caption and the right-hand HUD stack SHALL be positioned relative to it so they never overlap it. At
both 1440x900 and 1280x720 no stage anchor SHALL overlap another anchor's content.

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1440x900
- **THEN** the scene backdrop fills the viewport, and the narrative caption, the HUD islands, the action dock, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height
- **THEN** the island stack itself is bounded and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every mode-visible surface present
- **THEN** no stage anchor's rendered box intersects another anchor's rendered box

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | creation |
|---|---|---|---|
| narrative caption | visible | visible | hidden |
| HUD island stack (character/vitals/conditions) | visible | visible | hidden |
| minimap island | visible | **hidden** | hidden |
| action dock | visible | visible | visible (creation form) |
| command line | visible | visible | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible |

When a mode change hides the surface that currently holds focus, the shell SHALL move focus to the
action dock before the surface is removed, using the existing focus-restore path.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration
- **THEN** the minimap island renders again with the committed `local_map` payload

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides
- **THEN** focus is moved to the action dock before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the narrative caption, the HUD island stack, the minimap, and the command line are absent, and the action dock renders the creation form

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with
cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and
labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's
gradient stage otherwise — for a missing, failed, or invalid asset, for a pending scene with no prior
image, and when the `art` panel is unavailable. The backdrop SHALL NOT present an invented image and
SHALL NOT present a stale image as current. The scene label, its alternative text, and any truthful
placeholder label SHALL be rendered as text outside the bitmap, so no required information exists only
inside an image. The gradient stage SHALL differ per mode (exploration, dialogue, combat) and SHALL
carry an inset vignette.

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

#### Scenario: A missing scene degrades to the mode gradient
- **WHEN** the committed art panel carries a missing, failed, or invalid scene
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as text, and no image element carries a URL

#### Scenario: An unavailable art panel is indistinguishable from an ungenerated scene
- **WHEN** the `art` panel commits its unavailable form
- **THEN** the backdrop renders the mode gradient stage exactly as for a missing asset, with no broken image frame and no gameplay surface blocked

#### Scenario: A pending scene keeps its prior image labelled
- **WHEN** the scene is pending and a prior scene image is already rendered
- **THEN** the backdrop keeps that image visibly dimmed with the explicit `目前場景圖片生成中` label, and never presents it as the current scene

#### Scenario: The combat stage is visually distinct
- **WHEN** the committed mode is combat and no scene image is available
- **THEN** the backdrop renders the combat gradient stage, visually distinct from the exploration stage

### Requirement: The narrative is a bounded caption whose complete log is reachable in one action
The narrative SHALL render as a bounded caption card at the visual centre of the stage, constrained in
both measure and height so it never grows to fill the stage. The card SHALL carry a single labelled
control that opens a full-log surface presenting the complete retained narrative through the same
markup renderer as the caption — never a second markup path. The full-log surface SHALL be scrollable,
SHALL trap focus while open, SHALL close on Escape, and SHALL restore focus to the control that opened
it. The unread indicator, its polite live region, and its jump-to-latest behaviour SHALL remain on the
caption card and SHALL be unchanged.

#### Scenario: The caption card is bounded
- **WHEN** the narrative holds more lines than the caption card can show
- **THEN** the card scrolls internally within its bounded height and does not expand to fill the stage

#### Scenario: The complete log opens in one action
- **WHEN** the player activates the caption card's full-log control
- **THEN** the full-log surface opens showing the complete retained narrative, rendered through the same markup renderer as the caption

#### Scenario: The full-log surface returns focus on Escape
- **WHEN** the full-log surface is open and the player presses Escape
- **THEN** it closes and focus returns to the control that opened it

#### Scenario: The unread indicator is unchanged
- **WHEN** new narrative lines arrive while the caption card is scrolled away from the latest line
- **THEN** the unread indicator states its count and jump action and is announced through its polite live region exactly as before

### Requirement: An open drawer or overlay dims the stage behind it
When a drawer or a full-screen overlay is open, the shell SHALL mark the stage so the surfaces behind
the open surface are visually recessed, and SHALL clear that mark only when no drawer and no overlay
remain open. The recession SHALL be visual only: it SHALL NOT be used in place of hiding a
mode-gated surface, and it SHALL be disabled under `prefers-reduced-motion` for its transition while
the recessed state itself still applies.

#### Scenario: Opening a drawer recesses the stage
- **WHEN** a drawer or overlay opens
- **THEN** the stage behind it is visually recessed and the mark is present on the stage root

#### Scenario: The mark clears only when everything is closed
- **WHEN** two surfaces are open and one closes
- **THEN** the stage stays recessed until the last open surface closes

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces placed in the stage's `hud-left` and `hud-right` anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The left anchor SHALL
carry the character head card, the vitals, and the conditions as three sibling islands in that fixed
order. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with the `status` and `character` panels available
- **THEN** the head card, the vitals, and the conditions render as three separately-chromed islands in that order, each with the translucent blurred panel chrome, and none of them is a single opaque column card

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** the island stack's rendered box fits inside its anchor and does not intersect the action dock, the narrative caption, or the opposite anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

### Requirement: The character head card renders only backed identity
The character head card SHALL render exactly the identity the committed payloads carry: a glyph
portrait tile derived from the display name in `status.actor.name`, a numeric badge from the
`magic_level` trait row's current value, that display name, a rank line pairing the magic rank title
derived from the numeric magic level with the guild rank and merit from `character.guild`, the wallet
from `character.wallet` formatted as thousands-grouped integer copper, and an explicit disguise marker
when `status.disguise_active` is true.

The portrait tile SHALL be a glyph and SHALL NOT contain an image element: the player is never a
present focusable subject of their own exploration catalog, so no portrait asset exists for them and
none SHALL be invented. An empty or absent display name SHALL render an empty tile rather than a
substitute character.

The card SHALL NOT render a race, subrace, class, or faction line in any form — not as a value, not as
a placeholder, and not as an unknown marker — because no such field exists in the `status` or
`character` payload. The magic rank title SHALL be a pure function of the numeric magic level, derived
client-side for display only, and SHALL NOT be requested from, or invented as, a payload field. When a
disguise is active, the badge and the rank line SHALL render the **true** trait value; a displayed
disguise value SHALL NOT be substituted for it.

The head card SHALL be the client's single persistent wallet surface.

#### Scenario: The head card renders the backed identity fields
- **WHEN** the `status` and `character` panels are committed for an actor with a magic level, a guild rank and merit, and a wallet balance
- **THEN** the card shows the glyph portrait tile with the numeric magic-level badge, the display name, the derived magic rank title paired with the guild rank and merit, and the thousands-grouped wallet in copper

#### Scenario: No race, class, or faction line is rendered
- **WHEN** the head card renders for any actor
- **THEN** no race, subrace, class, or faction value, placeholder, or unknown marker appears anywhere on the card

#### Scenario: The portrait is a glyph, never an image
- **WHEN** the head card renders outside combat
- **THEN** the portrait tile contains a glyph derived from the display name and contains no image element and no asset URL

#### Scenario: An active disguise leaves the true magic level on the card
- **WHEN** a disguise is active and the `character` payload's displayed rows carry a magic-level value that differs from the true trait
- **THEN** the badge and the rank line render the true trait value, and the displayed disguise value does not replace it

#### Scenario: The wallet has one persistent surface
- **WHEN** the HUD renders with the `character` panel available
- **THEN** the wallet is present on the head card and no other persistently-visible HUD surface renders a second wallet figure

### Requirement: Vitals pair an icon, a label, and numerals with a trailing damage bar
Each of hp, mp, and sp SHALL render as one vital row carrying an icon, a Traditional Chinese label,
and the `current / maximum` numerals from `status.resources`, above a track containing a trailing bar
and a fill. The numerals SHALL render at every value, so no vital state is conveyed by the coloured
fill alone. The sp fill SHALL carry a non-colour texture distinguishing it from the hp and mp fills.

The trailing bar SHALL exist to make damage taken visible: it SHALL lag the fill when the ratio falls
and SHALL be overtaken by the fill when the ratio rises. It SHALL be decorative — hidden from the
accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already
carry on the same revision. It SHALL NOT render any value that was not a previously committed ratio of
that same gauge, SHALL NOT be interpolated or extrapolated from narrative text or an action result,
and SHALL reset to the current ratio when the epoch changes, so no trail is drawn across a reconnect.
Its motion SHALL be token-gated so the reduced-motion block disables it.

A vital at or below the client's display threshold SHALL be marked by both a recolour and an explicit
text marker, never by the recolour alone.

#### Scenario: Each vital is legible without colour
- **WHEN** the vitals island renders with the `status` panel committed
- **THEN** each of hp, mp, and sp shows an icon, a text label, and its `current / maximum` numerals, and the sp fill is distinguishable from hp and mp by texture rather than by hue

#### Scenario: Damage leaves a visible trailing bar
- **WHEN** a committed revision lowers a gauge's ratio
- **THEN** the fill moves to the new ratio and the trailing bar follows behind it, so the gap between them shows the amount lost, and the numerals show the new value immediately

#### Scenario: Healing shows no trailing bar
- **WHEN** a committed revision raises a gauge's ratio
- **THEN** the fill overtakes the trailing bar and no lagging gap is drawn

#### Scenario: The trailing bar never shows an uncommitted value
- **WHEN** the trailing bar renders at any point
- **THEN** its width corresponds to a ratio that was previously committed for that same gauge, and it is absent from the accessibility tree

#### Scenario: A reconnect does not draw a trail across epochs
- **WHEN** a new epoch's snapshot commits after a reconnect
- **THEN** the trailing bar resets to the current ratio and no gap is drawn between the pre-reconnect and post-reconnect values

#### Scenario: A low vital is marked by text as well as colour
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** the row carries both the low recolour and an explicit text marker, and the numerals continue to render

### Requirement: The low-HP presentation state is derived client-side and drives the stage hook
The client SHALL derive a low-HP presentation state from the committed `status.resources.hp` ratio
alone, against a single display-only threshold, and SHALL expose it on the stage root through the
shell's existing low-HP hook so the stage renders its red vignette and the hp fill renders its pulse.

The threshold SHALL be a presentation constant: no server field, trait, or condition expresses "low
health", and the client SHALL NOT request one, invent one on the wire, or treat the derived state as
canonical. The state SHALL NOT be load-bearing — the numerals and the low text marker SHALL convey the
same information at every value, so a viewer who perceives neither the vignette nor the pulse loses
nothing. When the `status` panel is unavailable the state SHALL be false rather than true by default.
The pulse and the vignette transition SHALL be token-gated so the reduced-motion block disables the
motion while the marker and the numerals still apply.

#### Scenario: Crossing the threshold lights the stage
- **WHEN** a committed revision takes the hp ratio to or below the display threshold
- **THEN** the stage root carries the low-HP state, the stage renders its red vignette, and the hp fill renders its pulse

#### Scenario: Recovering clears the stage state
- **WHEN** a later committed revision takes the hp ratio back above the threshold
- **THEN** the low-HP state clears and the stage returns to its ordinary vignette

#### Scenario: An unavailable status panel is not low HP
- **WHEN** the `status` panel commits its unavailable form
- **THEN** the low-HP state is false, no red vignette is rendered, and no hp value is fabricated

#### Scenario: Reduced motion keeps the information and drops the motion
- **WHEN** `prefers-reduced-motion` is set and the hp ratio is below the threshold
- **THEN** the pulse animation is disabled while the low text marker, the numerals, and the recoloured row still render

### Requirement: Condition chips carry a severity glyph, a payload duration, and a bounded overflow
Each entry in `status.conditions` SHALL render as one chip pairing a per-severity shape glyph with an
accessible name carrying the condition's label, its remaining duration when the payload supplies one,
and every derived modifier the payload provides. The five severities SHALL each map to a distinct
glyph shape, so two severities are never separated by colour alone, and the beneficial and harmful
directions SHALL be readable from the glyph itself. Because the chip is icon-only, the island SHALL
also present that label, duration, and modifier text visibly when a chip is focused or hovered, so the
information the chip moves into its accessible name stays reachable by pointer and by keyboard.

The duration badge SHALL render only when the payload carries `remaining_seconds` for that condition;
a condition without one SHALL render no badge and no substitute value. The badge SHALL show the
payload's integer verbatim and SHALL NOT be decremented, animated down, or otherwise advanced by the
client between committed revisions.

Visible chips SHALL be bounded, and the remainder SHALL be reachable in one action through an overflow
chip stating how many are hidden. The overflow surface SHALL be bounded and scrollable and SHALL close
on Escape, so no committed condition becomes unreachable at any condition count the payload permits.
An empty condition list SHALL render an explicit text statement rather than an empty island.

#### Scenario: A chip carries its label, duration, and modifiers
- **WHEN** a condition with a label, a remaining duration, and a derived modifier is committed
- **THEN** its chip renders the severity glyph and a duration badge, and its accessible name states the label, the remaining duration, and the modifier and its value

#### Scenario: Two severities are distinguishable without colour
- **WHEN** a warning condition and a harmful condition are committed together
- **THEN** their chips carry different glyph shapes and remain distinguishable with colour removed

#### Scenario: A condition without a duration renders no badge
- **WHEN** a committed condition carries no `remaining_seconds`
- **THEN** its chip renders no duration badge and no substitute value in its place

#### Scenario: The duration does not tick between revisions
- **WHEN** a chip with a duration badge is displayed and no new revision commits
- **THEN** the badge continues to show the payload's value unchanged, and the client runs no countdown

#### Scenario: Overflowing conditions stay reachable
- **WHEN** more conditions are committed than the island shows as chips
- **THEN** an overflow chip states the hidden count and reveals every remaining condition in one action, within a bounded scrollable surface that closes on Escape

#### Scenario: No conditions renders an explicit statement
- **WHEN** the committed condition list is empty
- **THEN** the island renders an explicit text statement that there are no conditions

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's right anchor, beneath the top-meta
surface, carrying the committed `local_map` payload's title. Where the payload's layer places nodes on
coordinates, the island MAY state the renderer's own axis convention as an orientation legend; where
the layer is coordinate-free, it SHALL omit that legend rather than assert one. The island SHALL NOT
render a bearing, a compass angle, or a distance in any form, because node coordinates are
renderer-local presentation geometry and not canonical world coordinates.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. The minimap's existing
per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may render the renderer's axis orientation legend alongside the map title

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation legend rather than asserting a direction the payload does not support

#### Scenario: No bearing or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing, or distance figure appears anywhere in the island

#### Scenario: No control opens an unmounted surface
- **WHEN** the full-map surface is not mounted in the application
- **THEN** the island presents no full-map control, and the per-node movement submission continues to work unchanged

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

