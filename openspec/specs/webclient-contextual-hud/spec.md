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

The backdrop's own floating caption elements (the truthful-placeholder card, the `目前場景圖片生成中`
pending notice, the scene label and alternative-text captions, and the full-view control) SHALL be
positioned so that none of them overlaps the action dock's or the command line's rendered content, at
both 1440x900 and 1280x720 — extending the sibling stage requirement's general anchor non-overlap
invariant to these backdrop-internal captions, which sit outside the five named stage anchors but are
absolutely positioned within the same full-bleed stage.

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

#### Scenario: The truthful-placeholder caption never intrudes on the action dock
- **WHEN** the `art` panel is unavailable or the scene is missing/failed, so the truthful-placeholder
  card renders
- **THEN** the placeholder card's rendered bounding box does not intersect the action dock's rendered
  bounding box at either 1440x900 or 1280x720

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the dock
- **THEN** each one's rendered bounding box stays above the action dock's top edge and above the command
  line, at both 1440x900 and 1280x720

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

The panel's background gradient and shadow SHALL match the values
`docs/design/elosern-redesign/index.html`
(the binding visual reference) draws for its dock surface — the panel reads as receding into shadow
toward its lower edge, not as a lit, tinted card.

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

#### Scenario: The panel's background matches the reference's shadowed gradient
- **WHEN** the dock panel renders in any mode
- **THEN** its background gradient and box-shadow are the same values `docs/design/elosern-redesign/index.html` draws for its dock surface

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

A tab's decorative glyph SHALL match the icon `docs/design/elosern-redesign/index.html` (the binding
visual reference) draws for that same tab concept, for every root or combat-root key the reference
itself draws an icon for. A key with no counterpart in the reference (a client-local entry the
reference's static draft never modelled, such as a sub-dock shortcut) SHALL carry whatever glyph best
represents it and is never required to match a reference that does not exist.

#### Scenario: The root renders as tabs and owns the listbox
- **WHEN** the dock is at its root frame
- **THEN** each root item renders as a tab with a glyph and its label, the tab bar carries the listbox role with a single tab stop and an active-descendant reference, and each tab carries its preserved row identity attribute

#### Scenario: A tab glyph matches the reference design's icon for the same concept
- **WHEN** the exploration root renders the 移動/查看/互動/建議 tabs, or the combat root renders the 攻擊/技能/道具/防禦/逃跑/投降 tabs
- **THEN** each tab's glyph is the same pictogram `docs/design/elosern-redesign/index.html` draws for that tab's concept

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

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend text naming the keyboard behaviour it actually implements.
The legend SHALL render exactly once as visible content; any additional copy kept only to satisfy a
test hook on a different element SHALL be rendered visually hidden (removed from the visual layout and
from the accessibility narration order a sighted-equivalent reading would follow) while remaining present
in the DOM and readable by its `data-testid`.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no longer
behaves as named. When a named affordance's behaviour changes (for example, a control that used to open
a surface and now only moves focus into an always-present one), the legend's wording SHALL be updated in
the same change that alters the behaviour.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carrying the shortcut-legend text is visible, and any other element carrying the same text is visually hidden

#### Scenario: The legend names the command line's real focus behaviour, not an open/close toggle
- **WHEN** the shortcut legend names the command-line-focus key
- **THEN** its wording states that the key focuses the command line, and does not state that the key opens or closes it

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
target's server-authored display name. When the keyboard router's focus is on the `back` item (the
non-rendered navigation cell of the exit outlet), the breadcrumb's back control SHALL carry a visible
focused state — a background fill and border change together (the same non-color-alone treatment
shared with every other dock row form), so the focused `back` row keeps a visible focus carrier;
activating it with the back control or with Enter SHALL pop exactly one level, restore the parent
frame's previously focused row, and dispatch no action.

#### Scenario: The breadcrumb appears only below the root
- **WHEN** the dock is at its root frame
- **THEN** no breadcrumb is rendered
- **WHEN** the player opens a submenu
- **THEN** the breadcrumb appears naming the parent frame and the current frame

#### Scenario: The back control is the Escape path
- **WHEN** the player activates the breadcrumb's back control at any depth
- **THEN** exactly one menu level closes, the parent frame's rows render with the previously focused row marked, and no `ui_action` is emitted

#### Scenario: A focused `back` row keeps a visible focus carrier
- **WHEN** keyboard focus moves onto the move frame's `back` item, which is not rendered as an outlet tile
- **THEN** the breadcrumb's back control renders a focused state (fill and border change together, not color alone), and Enter or a click on that control pops exactly one level back to the parent frame

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

A move row SHALL render the exit's direction as a leading glyph, and, while the row is enabled, its
primary text SHALL be the destination's display name — never a repetition of the direction word or the
exit's own label once a glyph already carries that meaning. The glyph SHALL be resolved from a fixed
client-side table of canonical direction words; an exit label outside that table SHALL render verbatim
as the row's primary text (there being no glyph to carry it) rather than being mapped to a guessed
direction. The destination's display name SHALL be resolved by matching the move row's server-authored
destination node against the committed local-map nodes; when that node is not present in the committed
lattice, an enabled canonical-direction row SHALL fall back to its own exit label as its primary text
rather than rendering blank — but SHALL NOT render both the destination name and the exit's own label at
once when both are available, since that repeats the glyph's meaning as text. A disabled row SHALL
always render its own exit label as its primary text, never the destination name, because the label is
this row form's only carrier of the disabled marker; the destination-name substitution above applies
only to enabled rows. A move row's focused state SHALL be conveyed by its background and border fill
together (the same non-color-alone treatment shared with every other dock row form) and SHALL NOT
additionally render a focus caret glyph when the row already carries a persistent direction glyph — a
second, focus-only glyph on top of one already shown is not an additional signal. The move frame SHALL
render no companion detail panel or side surface: the outlet tile is self-contained, and the row region
SHALL receive the pane's full available width, with the exit outlet laid out as a width-adaptive
`repeat(auto-fit, minmax(min(150px, 100%), 1fr))` grid whose `1fr` tracks the tiles stretch to fill (no
content-width cap on the tile). A disabled move row's server-authored explanation SHALL remain reachable
by assistive technology directly from the tile (an accessible association such as `aria-describedby`),
independent of whether any companion panel exists. The submitted move payload SHALL be unchanged.

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
- **WHEN** the move frame renders an enabled exit whose label is a canonical direction and whose destination node is present in the committed local map
- **THEN** the row renders that direction's glyph together with the destination node's display name as the row's primary text, with no separate rendering of the exit's own direction-word label, and activating it submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** a move row's label is a named door or a dynamic wilderness exit rather than a canonical direction
- **THEN** the row renders that label verbatim as its primary text and no direction is guessed for it

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** an enabled canonical-direction move row's destination node is absent from the committed local map
- **THEN** the row renders its glyph together with the exit's own label as a fallback primary text, and no destination name is invented

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** a canonical-direction move row is disabled and its destination node is present in the committed local map
- **THEN** the row renders its own exit label (carrying the server's disabled suffix) as its primary text, not the destination's display name, and its server-authored explanation remains reachable by assistive technology from the row itself

#### Scenario: A focused move row is not double-marked
- **WHEN** a move row carrying a direction glyph is focused
- **THEN** the row's background and border change together to mark focus, and no additional focus-only glyph renders alongside the row's existing direction glyph

#### Scenario: The move frame has no companion panel
- **WHEN** the move frame renders with any row focused
- **THEN** no detail aside or other side panel renders beside the outlet grid, the row region occupies the pane's full available width, and the `auto-fit` grid fills the remaining horizontal space (each column at least 150px wide, or the pane's own width when the pane is narrower)

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

### Requirement: Reference surfaces render in a right-anchored drawer with one modal contract
The client's reference surfaces SHALL render inside a drawer anchored to the right edge of the stage,
spanning the full stage height, bounded to a width that never exceeds the viewport, drawn on the solid
panel background with a left border so it reads as a surface laid over the stage rather than a region
of it. The drawer SHALL enter and leave by a horizontal slide expressed through the shared motion
tokens, over a blurred scrim that covers the whole stage. Its header, its scrolling body and its
optional footer SHALL be one column, and the body SHALL be the drawer's only scrolling region. A drawer
MAY declare one leading head icon (a decorative, `aria-hidden` glyph rendered before its title); a
drawer that declares none renders its title with no icon, unchanged. The drawer's close control SHALL
carry an accessible name (e.g. an `aria-label`) but MAY be rendered icon-only, with no visible text
node — "labelled" in this requirement means an accessible name, not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a
subtitle stating its owner's active and passive skill counts (`主動 {n} · 被動 {m}`, computed from that
same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is
empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer
SHALL always carry a footer stating the client's own cast-command syntax
(`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB
protocol carries, so its presence does not depend on any panel's availability.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the drawer slides in against the right edge for the full stage height over a blurred scrim, its body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

#### Scenario: The close control is icon-only but keeps its accessible name
- **WHEN** a reference drawer's close control renders
- **THEN** it carries no visible text node, renders a decorative close glyph, and exposes the same accessible name (e.g. `aria-label="關閉"`) an assistive technology would have read from the previous visible text

#### Scenario: The skill-book drawer states its skill counts and cast syntax
- **WHEN** the skill-book drawer opens with the `character` panel available
- **THEN** its head carries a leading skill glyph and a `主動 {n} · 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once (not duplicated inside the body), and its footer states the client's `/cast` syntax as static copy

### Requirement: The reference surfaces have no permanently visible home and are reached from the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character
status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while
that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

Each drawer SHALL be opened either by the dock frame that owns its surface, or by a single labelled
control inside a drawer that already presents the same read model, or by a surface this capability
names elsewhere as an opener for it. No reference surface SHALL require more than two actions from the
dock's root frame to reach. Opening a drawer SHALL NOT change any dock root item, any menu frame, any
menu key, or the meaning of Escape.

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption remains the visual centre of the stage

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1440x900 and 1280x720 with every drawer closed
- **THEN** the right-hand HUD anchor renders no reference panel, contributes no visible box and no tab stop, and no stage anchor's rendered box intersects another's

### Requirement: A drawer hosting a dock frame renders that frame rather than a second navigation model
When the keyboard router's current frame belongs to a surface that a drawer presents, that drawer
SHALL be open and SHALL render that frame's rows through the same shared row renderer the dock uses,
beside the surface's own presentation. The client SHALL NOT maintain a second frame stack, a second
focus model, or a second set of menu keys for a drawer.

Closing the drawer SHALL pop exactly one menu level, and leaving that surface by any path SHALL close
the drawer, so no state exists in which such a frame is current while its drawer is closed. A drawer
that presents no router frame SHALL open and close without touching the frame stack at all.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes
so that a drawer's payload is no longer available, when the presentation epoch resets, or when the
transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation
state inside it SHALL be discarded.

#### Scenario: A hosted frame renders inside its drawer
- **WHEN** the player opens a service surface whose frame the router pushes
- **THEN** the matching drawer opens, that frame's rows render inside it through the shared row renderer with the focused row marked and disabled rows focusable, and the dock renders no duplicate copy of those rows

#### Scenario: Escape from a hosted frame pops exactly one level
- **WHEN** a drawer is hosting a router frame and the player presses Escape
- **THEN** exactly one menu level closes, the drawer closes with it, focus returns to the opener, and no action is dispatched

#### Scenario: A drawer with no frame leaves the router alone
- **WHEN** the player opens the character-status drawer, which pushes no menu frame
- **THEN** the router's frame stack is unchanged, and closing the drawer pops nothing

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag drawer SHALL use the shared drawer chrome for the `背包 · 裝備` title, local `inventory` SVG icon, close control, and a wallet subtitle formatted as integer copper from the committed available `character` panel. It SHALL render that wallet in no other body location. Its available body SHALL begin with the read-only equipment doll built from the committed `character` panel's equipment rows, followed by the committed `services` panel's inventory rows — each row's display name, held count and whether it is equipped — and nothing else. The listing SHALL be bounded by the server's row ceiling; when it holds that many rows the drawer SHALL state the ceiling in words. The shipped row count SHALL NOT be presented as a count of the player's untruncated holdings, because the panel's inventory total is that same shipped count and carries no information about what was truncated.

The bag SHALL NOT render an item rarity, a per-item statistics line, a comparison tooltip, or a numeric item mechanic in this change. It SHALL NOT render a use, consume or equip control, because the panel advertises no such action. When the `services` panel commits its unavailable form, or when its inventory section is absent, the bag SHALL render only the registry-owned reason and SHALL fabricate no wallet, equipment slot, row or count. When services are available but the character panel is unavailable, the held-item listing remains available, the doll renders its registered unavailable state, and the drawer header renders no balance.

#### Scenario: The bag lists what the payload carries
- **WHEN** the committed `services` panel carries inventory rows and the committed character panel is available
- **THEN** each row renders its display name, its held count and an equipped marker where the row is equipped, the body begins with the true equipment doll, and no rarity, statistic or tooltip is rendered for it

#### Scenario: The inventory drawer owns the equipment and wallet context
- **WHEN** the inventory drawer opens with available services and character panels
- **THEN** its shared header shows the local bag symbol and thousands-grouped character wallet, its body contains the equipment doll, and the character-status drawer contains neither a wallet figure nor equipment doll

#### Scenario: The ceiling is stated, the total is not invented
- **WHEN** the inventory listing holds the server's maximum number of rows
- **THEN** the drawer states that the listing is bounded at that maximum, and it never renders a figure claiming to be the player's complete holdings

#### Scenario: No use or equip control appears
- **WHEN** the bag renders a held item, whether equipped or not
- **THEN** it offers no use, consume or equip control, matching the panel's action set

#### Scenario: An unavailable services panel fabricates nothing
- **WHEN** the `services` panel commits its unavailable form
- **THEN** the bag renders only the registry-owned reason message, with no rows, wallet, equipment slot or count

#### Scenario: Character unavailability does not fabricate a balance or equipment
- **WHEN** the services inventory is available and the character panel is unavailable
- **THEN** the bag renders its held rows, renders the equipment section's registered unavailable reason, and shows no wallet subtitle or zero balance

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each
of which carries a slot, an item key and a display name and nothing more. The doll SHALL present the
server's singleton slots as named positions that render an explicit empty state when no row occupies
them, SHALL group the repeatable accessory rows together, and SHALL render any slot key outside the
recognised set as a labelled row rather than discarding it, so no row the payload sends is lost.

The doll SHALL NOT render a statistics line, an attack or defence value, a rarity, or a comparison
against another item: the equipment rows carry none of those. Equipment SHALL be presented as true
values that a disguise does not affect.

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its name with an explicit empty state, and no item is invented for it

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** every accessory row renders in the accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity or comparison value

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode; each condition SHALL pair a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value. Equipment and wallet presentation belong exclusively to the inventory drawer and SHALL NOT render in character status.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values. A displayed value SHALL NEVER replace a true trait row.

The character-status drawer SHALL preserve the 親密狀態 disclosure section added by the archived intimate-status change: when the committed `character` panel's `intimate` field is present the drawer renders its collapsed-by-default disclosure widget immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and this change SHALL NOT remove, move or restyle it. When `intimate` is `null` or the `character` panel is unavailable, the section is absent from the DOM, exactly as the merged main spec requires. This change removes only the equipment and wallet sections.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, intimate status, persona) SHALL carry a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its own bordered card tile in a two-column grid rather than a plain text row, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; no value not already present in the committed payload (such as an effective-vs-base delta) SHALL be invented to fill the tile. The condition roster SHALL render as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD. These presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, guild and persona sections with the registry-owned reason without a wallet or equipment placeholder

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate section is preserved in place
- **WHEN** the character-status drawer renders with the `character` panel available and its `intimate` field present
- **THEN** the drawer renders the 親密狀態 disclosure collapsed by default immediately after the 偽裝 section and before the 背景 section, and this change leaves it unchanged

#### Scenario: Every section states what it is
- **WHEN** the character-status drawer renders any of its sections
- **THEN** each section carries a labelled small-caps heading naming it, matching the heading treatment used elsewhere in the HUD

#### Scenario: Vitals, traits, and guild counters render as card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their rows
- **THEN** each row renders as its own bordered tile inside a two-column grid, showing only the label and the value already present in the committed payload, with no invented delta or base-vs-effective figure

#### Scenario: The condition roster renders as coloured pill badges
- **WHEN** the condition roster renders one or more committed conditions
- **THEN** each condition renders as a rounded pill carrying its label, its visible severity word, its severity glyph, and its duration/modifier text — with no content dropped relative to today's rendering — coloured by the same severity-to-colour mapping the capped status-island chips use, and the pills wrap onto additional lines rather than clipping or scrolling horizontally

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered in exactly one place — the inventory drawer's shared header — and SHALL be read from the committed available character panel that owns it. The shop, the lore reference, the inventory body, and the character-status drawer SHALL NOT render a balance of their own. A drawer that cannot read the wallet from an available character panel SHALL render no balance at all rather than a zero.

#### Scenario: One wallet across the whole drawer layer
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** exactly one wallet value is rendered across all of them, in the inventory drawer header

#### Scenario: An unavailable panel renders no balance
- **WHEN** the character panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place

### Requirement: Mutations issued from a drawer keep the dispatch and confirmation contract
Every affordance inside a drawer SHALL emit exactly the server-authored action identifier and payload
its descriptor carries, through the client's single dispatch entry, and SHALL be governed by the same
in-flight, epoch and revision gates as the same action issued from the dock. A disabled affordance
SHALL remain readable for its server-authored reason and SHALL submit nothing. While mutations are
locked — a submission in flight, an unaccepted revision, or a lost transport — every drawer affordance
SHALL be locked with them.

A destructive service action issued from a drawer SHALL sit behind an explicit confirmation step that
names what it does, with a cancel path that submits nothing. A quantity form inside a drawer SHALL
keep the server-advertised minimum and maximum and SHALL NOT permit a value outside them.

#### Scenario: A drawer affordance dispatches the exact server intent
- **WHEN** the player activates an enabled affordance inside a drawer
- **THEN** exactly one action is emitted carrying the descriptor's own action identifier and payload, through the same dispatch entry the dock uses

#### Scenario: Abandoning a quest from a drawer requires confirmation
- **WHEN** the player activates the abandon affordance on an active quest inside the quest drawer
- **THEN** a confirmation step renders naming the quest and what abandoning does, no mutation is sent, and cancelling returns without submitting

#### Scenario: A locked client locks the drawers
- **WHEN** a submission is in flight, its revision is unaccepted, or the transport is lost
- **THEN** every affordance inside every drawer is locked and emits nothing

#### Scenario: A quantity form keeps the server's bounds
- **WHEN** the player raises a quantity inside a drawer past the server-advertised maximum
- **THEN** the value is clamped to that maximum and no request can authorise a larger quantity

### Requirement: The command line is a permanently present bar in the stage's command-line anchor
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — the mode's quick-word chips, a prompt chevron, the command input field, a
hint cluster, the command-history controls, and the overlay utility controls. In the modes this
capability's visibility matrix renders the command line (exploration and combat), the input field SHALL
be present in the DOM, visible and focusable without any opening action: there SHALL be no entry
control, no `aria-expanded` state and no closed state. No stored presentation state SHALL be able to
remove it. (The command line is intentionally absent from the layout in creation mode, per H1's
visibility matrix and design D10.)

The bar SHALL NOT overlap the action dock, the narrative caption or any HUD anchor at 1440x900 or
1280x720. When horizontal space is insufficient, the hint cluster SHALL be dropped first and the
quick-word chips SHALL scroll within their own cluster; the input field, the history controls and the
utility controls SHALL never be dropped, because they are the only pointer path to their behaviour.

#### Scenario: The field is usable without an opening action
- **WHEN** the shell mounts in exploration mode
- **THEN** the command input field is present in the DOM and focusable, no entry control is rendered, and no element in the bar reports an `aria-expanded` state

#### Scenario: The bar keeps its geometry at the minimum viewport
- **WHEN** the stage renders at 1280x720 with the full quick-word chip set
- **THEN** the bar's rendered box intersects no other stage anchor's box, and the input field, the history controls and the utility controls are all still rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first and the chip cluster scrolls within itself, and no input field, history control or utility control is removed

### Requirement: Quick-word chips prepare a command without submitting it
The command line SHALL render quick-word chips for the committed mode. Activating a chip SHALL write
its command text into the input field and move focus to the field, and SHALL NOT submit: a prepared
command SHALL still travel through the field's single send implementation, so exactly one send path
exists.

Each chip's visible label SHALL be the literal command verb it inserts, and every chip SHALL insert a
verb the server's installed command set actually accepts — a chip SHALL NOT offer a verb the parser
would reject. Each chip SHALL carry a decorative icon beside its text label, drawn from this client's
stable glyph vocabulary (the same table the action dock's tab bar and pane rows draw from); the icon
SHALL be hidden from assistive technology and SHALL NOT appear without its accompanying text label.
Chips SHALL carry no key-mnemonic badge unless this client binds that key. Chips that do not apply to
the committed mode SHALL be removed with `display:none` so they leave the accessibility tree and the tab
order, never dimmed.

#### Scenario: A chip prepares, it does not send
- **WHEN** the player activates a quick-word chip
- **THEN** the chip's command text plus a trailing space is written into the input field, focus moves to the field, and no text message and no `ui_action` is sent

#### Scenario: The chip set follows the mode
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the exploration-only chips are hidden with `display:none` so they leave the accessibility tree and the tab order (never dimmed, and still present in the DOM), and the combat chip set renders in their place

#### Scenario: No chip offers a verb the game does not have
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip's inserted text is a command key or alias the server installs, and no chip advertises a key mnemonic that this client does not bind

#### Scenario: Every chip carries a decorative icon paired with its label
- **WHEN** the rendered chip set is enumerated in any mode
- **THEN** every chip renders an `aria-hidden` icon alongside its visible text label, and no chip renders an icon without that label

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys, and SHALL NOT state a completion affordance, because the client implements none.

The history controls SHALL be labelled controls that drive the same history-walk state the recall keys
drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command line
SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and nothing else
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and states no completion affordance

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is preserved across the walk, and neither submits

### Requirement: A full-screen overlay is one focus-trapped surface, and only one is open at a time
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying a header naming
the surface and a labelled close control, with its body as its only scrolling region. The surface is fixed
from the stage's 46px command-line height (`top:46px; left:0; right:0; bottom:0`), so the command line
stays visible and usable underneath it. While an overlay
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It
SHALL close on Escape and on activation of its close control, and both paths SHALL restore focus to the
control that opened it. It SHALL use the shared focus trap the client already owns rather than a second
implementation.

At most one overlay SHALL be open at any time; opening a second SHALL close the first, and the opener
recorded for the replacement is the control that opened it, so closing restores focus to the most recent
trigger, never to the trigger of the closed overlay. An overlay and a
reference drawer SHALL NOT be open together: opening either SHALL close the other, so at most one
focus-trapped surface exists at any moment. An open overlay SHALL register itself as an open surface so
the stage recession this capability already requires applies without a second mechanism.

Escape SHALL be resolved by a single precedence order, topmost first — the open overlay, then an open
drawer, then the focused command field, then the dock's current menu level — with each level consuming
the key and stopping.

A mode change into creation, a presentation-epoch reset and a loss of the transport SHALL each close
every open overlay. The mode-driven character-creation surface SHALL NOT be part of this single-open
stack, because it is not opened by the player and a utility control must never dismiss it.

#### Scenario: An overlay opens, traps focus, and returns it
- **WHEN** the player activates an overlay trigger, cycles focus forward past the overlay's last control and backward past its first, and then presses Escape
- **THEN** focus stays inside the overlay in both directions, the overlay closes on Escape, and focus returns to the trigger that opened it

#### Scenario: Only one overlay is open at a time
- **WHEN** an overlay is open and the player activates a different overlay's trigger
- **THEN** the first overlay closes as the second opens, and exactly one overlay is present

#### Scenario: An overlay and a drawer are never open together
- **WHEN** a reference drawer is open and the player activates an overlay trigger
- **THEN** the drawer closes as the overlay opens, and exactly one focus-trapped surface is present

#### Scenario: Escape resolves at exactly one level
- **WHEN** an overlay is open above a focused command field and a dock frame at depth two, and the player presses Escape once
- **THEN** the overlay closes, focus returns to its trigger, the command field's content is untouched, and the dock's menu depth is unchanged

#### Scenario: Closing the last overlay clears the recession
- **WHEN** the open overlay closes and no drawer remains open
- **THEN** the stage's recession mark is cleared

#### Scenario: A creation transition closes the overlays
- **WHEN** the committed mode changes to creation while an overlay is open
- **THEN** that overlay closes, focus is routed to the action dock, and the character-creation surface is not itself treated as one of the single-open overlays

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its lattice rather than as a wrapper around its
actionable nodes. The command line's utility controls SHALL open the settings and help surfaces.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale lattice or a stale reason on screen. It SHALL
present no zoom or pan affordance and SHALL NOT advertise one. It SHALL render no bearing, compass angle
or distance figure, because node coordinates are renderer-local presentation geometry.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model, the quick-word chips and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the command line carries labelled controls that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement lattice, and at no point shows a lattice or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** no zoom or pan control, hint or legend entry is present, and no bearing, compass angle or distance figure appears

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps, selectable from the settings surface,
whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply
to narrative and dialogue prose only — the narrative caption's lines, the complete-log surface's lines
and the prompt line — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at either supported viewport.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied to the
document's presentation tokens immediately and persisted through the client's versioned,
presentation-only browser store as a harmless display preference, SHALL be re-applied at load, and SHALL
be reset to its default — fully applied, never half-applied — whenever that store resets. The
reduced-motion setting SHALL act as an override over the operating system's reduced-motion preference,
which SHALL continue to apply when no override is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the narrative caption's lines, the complete-log surface's lines and the prompt line render larger, every HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale is re-applied after the reload, and after the reset every setting is applied at its default with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no reduced-motion override is stored and the operating system requests reduced motion
- **THEN** non-essential transitions are disabled; and when the player then sets the override off, the client honours the override

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

### Requirement: A fixed-column-count dock pane sizes its columns to content, never stretching to fill the panel

When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count SHALL govern only which cell each row occupies, never the rendered width of a column. A column's rendered width SHALL fit the natural size of the tile or row content placed in it; a pane whose rows are fewer or narrower than the panel's available width SHALL leave the remaining width empty rather than stretching every column to consume it. When the pane's available width is narrower than the combined natural content width of the fixed columns, the columns SHALL compress (each track can shrink toward zero) rather than overflow the pane horizontally. This SHALL hold regardless of how many columns the keyboard geometry fixes, and changing a column's rendered width SHALL NOT change which row occupies which cell. The exit-outlet pane (the move frame) SHALL be exempt from the fixed-column rule: its row region SHALL be laid out with the width-adaptive `repeat(auto-fit, minmax(min(150px, 100%), 1fr))` grid, the column count SHALL follow the pane's available width, and the tiles SHALL stretch with their `1fr` tracks (no content-width cap) so the row region receives the pane's full available width. The track floor SHALL shrink to the pane's own width (`100%`) when the pane is narrower than 150px, so the outlet never overflows a very narrow pane. When the exit count exceeds the pane's rendered column count and the final row is partial, the last exit tile SHALL span the remaining columns of that row so no horizontal space is left blank. The move frame's keyboard geometry SHALL be a single-column list, so the arrow-key cell mapping SHALL NOT depend on the pane's rendered column count.

#### Scenario: A short exit list fills the pane width
- **WHEN** the move frame renders one or two exits in a pane whose available width could fit many 150px columns
- **THEN** the `auto-fit` grid collapses the empty tracks, the rendered tiles each occupy their full-width tracks, and no horizontal space in the pane is left empty
- **WHEN** the move frame renders four or more exits in a pane whose available width fits N columns of at least 150px
- **THEN** the outlet grid renders N columns, each tile stretches with its track, and no horizontal space in the pane is left empty

#### Scenario: A very narrow pane does not overflow
- **WHEN** the pane's available width is narrower than 150px
- **THEN** the track floor shrinks to the pane's width (the `min(150px, 100%)` floor), a single full-width track renders the exits without horizontal overflow, and the tiles fill the available space

#### Scenario: Column-count-driven layout never invents equal-width stretching
- **WHEN** a fixed-column dock pane (a nav or combat pane) applies a fixed column count for its keyboard geometry
- **THEN** no column in that pane stretches a narrower row's content to an equal share of the panel's width, and the exit-outlet pane is the exempted width-adaptive exception

#### Scenario: A narrow pane compresses the fixed columns instead of overflowing
- **WHEN** the pane's available width (e.g. the minimum supported 1280x720 viewport) is narrower than the combined natural width of the fixed columns
- **THEN** the columns compress to fit the pane without horizontal overflow, and each tile or row wraps long content within its width

#### Scenario: The move frame navigates as a single-column list
- **WHEN** the player presses ArrowUp or ArrowDown inside the move frame
- **THEN** focus cycles through the move frame's items — the exit rows in order, then the `back` row — ArrowLeft and ArrowRight are no-ops, and the keyboard cell mapping does not depend on the pane's rendered column count

