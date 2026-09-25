# webclient-contextual-hud Specification

## Purpose
The full-bleed cinematic stage with its anchored HUD surfaces (scene backdrop, message window,
HUD islands, action dock, command line), the committed-mode visibility matrix, the truthful scene
backdrop, the paged message window, drawer/overlay stage recessing, and the action-dock
re-chrome contract: the fixed bottom band's command region, the root tab bar with truthful count badges,
the router-derived breadcrumb, the per-kind row vocabulary, the display-only combat participant
frame, the bounded skill master-detail, and the two-step destructive confirmation.

## Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the top-left `place` and `vitals` anchors, the top-right `map` anchor, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, and
the `command-line` row — and SHALL NOT be placed inside a page-scrolling container that can push a
required surface out of view.

The top band SHALL be 48px tall at every supported viewport and SHALL carry only the brand, the top
navigation bar, the possession banner when present, the character switcher, and the connection
state; it SHALL carry no location label and no time label. The `place` anchor SHALL sit at the stage
box's top-left corner, below the top band, at a fixed height that does not depend on the label
lengths it holds, and the `vitals` anchor SHALL begin below it. The `map` anchor SHALL sit at the stage
box's top-right corner, below the top band; its content column (the minimap island, then the
objective line, then any other island this capability places there) SHALL be right-aligned to the
stage's right gutter and bounded above the bottom band.

The bottom band SHALL span the full stage width along the stage's bottom edge at one fixed height,
`clamp(260px, 27.8vh, 400px)` (300px at the 1920x1080 reference viewport), taken from a single
shared band-height token. The band's height SHALL NOT depend on its content, on the dock frame, on
the committed mode, or on any measurement: no frame, pane, line count, dialogue exchange, or mode
change SHALL grow or shrink it. The band SHALL be divided into the message region `band-message`,
covering the left two thirds of the band's width, and the command region `band-command`, covering
the remaining right third; in creation mode, where the message region is hidden, the command region
SHALL span the whole band. The band SHALL carry the reference's band chrome (the upward gradient,
the hairline top border, and the upward shadow) on the band itself, not on the content inside it.
The stage box — the region between the top band's lower edge and the bottom band's upper edge — is
where the scene is seen, and at the 1920x1080 reference viewport it SHALL be at least 65% of the
viewport's height — at least 702px of 1080; the 48px top band and the 300px bottom band leave 731px. Every surface other than the band SHALL be positioned relative to the
band-height token so that none of them overlaps the band.

The portrait anchors SHALL stand on the band: each SHALL be bottom-aligned to the band's upper edge,
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset 6% of the stage
width from its own side, and SHALL never cover the band. The `actor-left` anchor SHALL carry the
player's standing portrait — the current roster character's portrait, resolved exactly as the
stage portrait was before this requirement, with the truthful placeholder when no image exists —
in exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry no content. The
portrait anchors are non-interactive art: they SHALL carry no focusable element and SHALL NOT
intercept pointer events, and they MAY sit behind the HUD islands and the command-line row.

At 1920x1080, 1440x900, and 1280x720 no interactive stage anchor (`place`, `vitals`, `map`,
`band-message`, `band-command`, `command-line`) SHALL overlap another interactive anchor's content,
and the top band's own elements SHALL neither overlap one another nor extend into the HUD island
anchor region: a band element whose content is variable-width SHALL be bounded and truncated rather
than sized by its content. A transient popover opened from a top-band element MAY overlay the
island anchors while open, provided it does not change the band's own rendered box and closes on
Escape and on outside activation; a surface that permanently occupies vertical space SHALL NOT be
introduced into the band this way.

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1440x900
- **THEN** the scene backdrop fills the stage box, and the player portrait, the HUD islands, the bottom band, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height, or the dock frame or the narrative holds more content than its band region
- **THEN** the island stack or the band region itself is bounded and scrolls internally, and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every mode-visible surface present
- **THEN** no interactive stage anchor's rendered box intersects another interactive anchor's rendered box

#### Scenario: The top band's own elements do not collide
- **WHEN** the shell renders at 1280x720 with every top-band element present and a maximum-length character name committed
- **THEN** the band's elements render side by side without intersecting, the variable-width element is truncated within its bound, and no band element's box extends into the island anchor region

#### Scenario: A band popover overlays without displacing
- **WHEN** a transient popover is opened from a top-band element
- **THEN** the band's rendered box is unchanged, the popover renders above the island anchors, and Escape or outside activation closes it

#### Scenario: The bottom band keeps one height whatever it holds
- **WHEN** the shell renders at 1920x1080 and the player moves through the exploration root, the interaction workspace, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
- **THEN** the bottom band's rendered height is 300px (±1px) in every one of those states, and the message region's and the command region's boxes are unchanged between them

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, and in creation mode the command region spans the whole band

#### Scenario: The player portrait stands on the band
- **WHEN** the shell renders in exploration mode at 1920x1080 with a committed roster portrait for the current character
- **THEN** the `actor-left` anchor renders that portrait, its bottom edge coincides with the band's top edge, its height is `min(62vh, 680px)` (±1px), its left edge is 6% of the stage width from the stage's left edge, it holds no focusable element, and the `actor-right` anchor renders no content

#### Scenario: The portrait never outgrows the stage box
- **WHEN** the shell renders at 1280x720, where `min(62vh, 680px)` exceeds the stage box's height
- **THEN** the player portrait's height equals the stage box's height and its top edge is not above the top band's lower edge

#### Scenario: The stage box is at least 65% of the reference viewport
- **WHEN** the shell renders in exploration mode at 1920x1080
- **THEN** the top band is 48px tall, the bottom band is 300px tall (each ±1px), and the stage box between them is at least 702px tall (65% of 1080)

#### Scenario: The top band carries no location or time
- **WHEN** the shell renders in exploration mode with a committed location label and world time
- **THEN** the top band's rendered height is 48px, no element inside the top band states the location label or the world time, and the place anchor below the top band states both

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (dialogue variant) | hidden |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait | visible | visible | visible | hidden |
| action dock (band command region) | visible | visible | visible (regular exploration form) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
When a mode change, a committed revision that turns a surface's data rule false, or a collapse of the
command line hides the surface that currently holds focus, the shell SHALL move focus to the action
dock before the surface is removed, using the existing focus-restore path. A mode change into creation
SHALL also collapse the command line, so leaving creation never reveals an expanded row.

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
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the place card, message window, minimap, player standing portrait, action dock, command-line toggle, and log control all
  remain rendered, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the message window's presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

#### Scenario: The objective line shows only in exploration
- **WHEN** a non-empty committed `objectives` panel stays committed while the mode changes from exploration to combat, then to dialogue, then back to exploration
- **THEN** the objective line renders in exploration, is hidden with `display:none` in combat and in dialogue, and renders again on the return to exploration

#### Scenario: The command line starts collapsed in every playing mode
- **WHEN** the shell mounts in exploration mode, and later the committed mode changes to combat and then to dialogue without the player opening the command line
- **THEN** in each mode the command-line toggle is rendered with `aria-expanded="false"`, the command-line row is hidden with `display:none`, and the input field is outside the tab order

#### Scenario: Entering creation collapses an expanded command line
- **WHEN** the command line is expanded with focus in its field and the committed mode changes to creation, and later back to exploration
- **THEN** focus moves to the action dock before the row is hidden, and on the return to exploration the command line is collapsed

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with
cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and
labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's
gradient stage otherwise — for a missing, failed, or invalid asset, for a pending scene with no prior
image, and when the `art` panel is unavailable. A bundled decorative sample MAY accompany this
fallback only with a visible caption distinguishing it from an actual scene image, while retaining
the authoritative missing/pending/unavailable label. Samples SHALL NOT enter the art catalog or
change its status, and SHALL disappear when an actual or labelled prior scene renders.
Decorative portrait samples SHALL likewise be labelled separately from the current subject;
an available committed player-roster portrait takes precedence, and a load failure returns to
an explicitly labelled sample instead of attributing that sample to the player.
The backdrop SHALL NOT present an invented image as authoritative and
SHALL NOT present a stale image as current. The scene label, its alternative text, and any truthful
placeholder label SHALL be rendered as text outside the bitmap, so no required information exists only
inside an image. The gradient stage SHALL differ per mode (exploration, dialogue, combat) and SHALL
carry an inset vignette. The backdrop's image SHALL be cover-cropped to the stage box (from the top
band's lower edge to the bottom band's upper edge), so no part of the scene the crop keeps is hidden
behind the bottom band.

The backdrop's own floating caption elements (the truthful-placeholder card, the `目前場景圖片生成中`
pending notice, the scene label and alternative-text captions, and the full-view control) SHALL be
positioned so that none of them overlaps the bottom band, the action dock's, or the command line's
rendered content, at 1920x1080, 1440x900, and 1280x720 — extending the sibling stage requirement's
general anchor non-overlap invariant to these backdrop-internal captions, which sit outside the named
stage anchors but are absolutely positioned within the same full-bleed stage.

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped to the stage box behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

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
- **THEN** the placeholder card's rendered bounding box intersects neither the bottom band's nor the
  command line's rendered bounding box at 1920x1080, 1440x900, or 1280x720

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1920x1080, 1440x900, and 1280x720

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, at the band's fixed height — drawn with the reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. Outside the dialogue
variant, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines, and SHALL NOT present earlier responses: they remain readable in
the full-log surface. Page text SHALL be set in the serif reading face at 28px at the 1920x1080
reference size and the default prose scale, SHALL scale with the viewport height and with the
client's prose scale, and SHALL hold at most 42 CJK characters per line.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL read `▼` while the current response has further pages and `■` on its last page.
It SHALL be decorative (hidden from assistive technology), and it SHALL blink only through the
client's motion tokens, so reduced motion stops the blink. An oversize page SHALL scroll inside the
window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no head row, no unread indicator, and no jump-to-latest control. In
creation mode the window, its marker, and the `日誌` control are hidden with the message region.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and no line of the two
  earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages and the player advances once
- **THEN** the marker reads `▼` on the first page and `■` on the second, and it is absent from the
  accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

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
The surfaces placed in the stage's `vitals` and `map` anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The `vitals` anchor,
under the place card, SHALL carry the vitals, the conditions, and the compact party quickbar as sibling
islands in that fixed order, each present only while its own requirement renders it, and SHALL carry
no character head card and no portrait catalog strip. The `map` anchor SHALL carry, in this order, the
minimap island, the objective line, the combat participant frame while it is mounted, and the title
ballot menu while it is mounted, each present only while its own requirement renders it; no reference
panel and no portrait anchor content SHALL be placed in either island anchor. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the vitals, the conditions, and the party quickbar render as three separately-chromed islands in that order, each with the translucent blurred panel chrome, none of them is a single opaque column card, and no head card or portrait catalog strip is rendered

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the `vitals` stack does not intersect the place card, and neither stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders the participant frame there with no minimap and no objective line

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
The HUD SHALL show the vitals island — the vitals rows together with the conditions island beneath
them — only while at least one of these holds for the committed state: the committed mode is
`combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp)
carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries at least one
entry whose `severity` is `warning`, `harmful`, or `critical`. A condition whose `severity` is
`beneficial` or `informational` — including a passive `skill_owned` combat-modifier row — SHALL NOT
by itself make the island visible, and neither SHALL an entry with a missing or unknown `severity`.
While the island is visible its condition chips SHALL render every committed condition, whatever its
severity. Otherwise the island SHALL be hidden with `display:none`, so it leaves the accessibility tree and the
tab order and contributes no visible box. The rule SHALL be derived client-side from the committed
`status` panel and the committed mode alone: no server field, request, or timer is involved, and a
vital that is absent from the payload or carries a non-numeric field SHALL NOT count as below its
maximum. Dialogue mode SHALL follow the same rule as exploration; creation mode hides the island
through the visibility matrix; an unavailable `status` panel renders no vitals island at all.

While hidden, the island SHALL keep its trailing-bar memory, so the first committed revision that
lowers a vital from full shows the island with the trailing bar lagging from the previously committed
ratio exactly as an always-visible island would. When a committed revision turns the rule false while
focus is inside the island, focus SHALL move to the action dock before the island is hidden, through
the same focus-restore path a mode change uses.

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals island is hidden with `display:none`, is absent from the accessibility tree and the tab order, and no vitals, numerals, or low-HP marker are visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration mode carries `mp` at 40 of 60 with no condition
- **THEN** the vitals island renders with every vital's icon, label, and `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** a committed revision in exploration mode carries full vitals and one condition whose `severity` is `harmful`
- **THEN** the vitals island renders with its vitals rows and the condition chip

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** a committed revision in exploration mode carries full vitals and only conditions whose `severity` is `beneficial`, such as a passive `skill_owned` combat-modifier row
- **THEN** the vitals island stays hidden with `display:none` and none of its condition chips is visible or focusable

#### Scenario: Visible island renders every condition chip
- **WHEN** the vitals island is visible because a vital is below its maximum and the committed conditions carry one `beneficial` and one `informational` entry
- **THEN** the island renders both condition chips

#### Scenario: Combat always shows the island
- **WHEN** the committed mode is combat with every vital full and no condition
- **THEN** the vitals island renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the island is hidden at full health and the next committed revision in the same epoch lowers `hp`
- **THEN** the island renders, the hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is on a `harmful` condition chip outside combat with every vital full, and a committed revision clears that condition, leaving only `beneficial` conditions
- **THEN** focus moves to the action dock before the island is hidden, and no focus is lost to the document body

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
An empty condition list SHALL render no condition island at all — no placeholder island, no
`無條件` text — consistent with the contextual-hiding rule that an absent surface is not a dimmed or
emptied surface.

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

#### Scenario: No conditions renders no island
- **WHEN** the committed condition list is empty
- **THEN** no condition island is rendered anywhere in the HUD

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island at the top of the stage's `map` anchor, directly
below the top band and above the objective line, carrying the committed `local_map` payload's title. Where the resolved layout variant is the
coordinate lattice — which exactly the coordinate-bearing layers (`grid`, `wilderness`) select — the
island SHALL state the renderer's own axis convention as orientation marks in its header following the
redesign draft's header treatment (the letterspaced title style and the `北↑ 東→` marks the draft's
lattice header draws); on the radial graph variant it SHALL omit those marks rather than assert an axis
the presentation does not draw (a radial graph draws no axis). Those marks and the axis cross the
lattice draws are ONE claim stated twice — once in words, once as geometry — so the two SHALL travel
together: a map surface SHALL draw the axis cross only where that same surface states the axis
convention in words, and the island's marks are what license the axis its lattice draws. The island
SHALL therefore draw the axis cross through the `current` node on the coordinate lattice and SHALL draw
none on the radial graph, and a surface that states no orientation marks — the full-map surface as it
stands — SHALL draw no axis at all. The lattice's coordinate dot field and its knowledge-edge vignette
are decoration that states nothing in words and SHALL NOT be read as a position, a bearing, a distance,
or a terrain claim: the dot field pictures the coordinate cell step the lattice already claims, and the
vignette pictures the limit of what the payload knows. On a coordinate-bearing layer the island SHALL additionally state the
`current` node's own coordinates as a two-integer figure — the payload `x` and `y` exactly as
committed, with no unit, delta, or derived quantity — as the entire content of its readout line, so
the island's position statement is the drawing convention plus the current cell's world coordinates
and nothing else. The readout SHALL NOT restate the current node's place name, its visibility state,
or a movement destination: the place name belongs to the stage's place card, and a
minimap shows the current position by definition. The readout SHALL NOT be driven by hover or by
selection, and the island SHALL keep no hovered-node or selected-node state; a node's own name stays
available as its on-canvas accessible name and, for a remembered node, as visible text on the surface
its layout variant presents it on — the name drawn beside the island's edge direction marker on the
coordinate lattice, and its entry in the full-map surface's remembered list on the radial graph, where
the island draws no visible remembered-node list at all — with the untruncated name always available
to assistive technology on the island, so no remembered place is readable by sight alone. Apart from that single figure the island SHALL NOT render a bearing angle, a compass
angle, a distance, or any other coordinate figure: coordinate readouts for non-current nodes,
differences between node coordinates, and every spatial figure on the graph variant remain forbidden,
because on coordinate-bearing layers node coordinates are validated world coordinates whose only
permitted visual uses are relative-direction geometry and the current-node figure, and on every other
layer they are renderer-local layout values that carry no spatial meaning at all. The one direction
statement the island MAY make in words is the octant name an edge direction marker already draws — one
of `北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北` — and only on the island's assistive-technology
text alternative for those markers, where it names the bearing the drawing already asserts to a reader
who cannot see it; a numeric angle, a degree figure, and a distance remain forbidden everywhere.

The island SHALL NOT present any map layout control — no segmented switch, button, menu item, or other
affordance selecting between the coordinate lattice and the radial graph — on the island or on the
full-map surface: the layout is resolved once from the committed payload's `layer` in the render model
and both surfaces consume that one value, so there is nothing for a control to change. No layout choice
SHALL be persisted in a client-local preference or any storage, and nothing about layout selection SHALL
travel to the server, because no selection exists to persist.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. The island SHALL present
exactly ONE full-map affordance, and it SHALL carry no visible button chrome — no labelled control,
icon button, or other visible trigger occupies the island's header or any other part of the island,
because the island itself is the affordance. That affordance SHALL be a real `<button>` element
spanning the island's whole box, transparent and layered beneath the island's visual content so the
button element contains no focusable descendant, carrying 展開全地圖 as its accessible name and opening
the full-map surface through the platform's own Enter/Space button behaviour rather than a key handler
on a non-button element. Its focus-visible indication SHALL delineate the whole island rather than a
small region of it. Clicking anywhere on the island's non-interactive body SHALL still open the
full-map surface as a pointer convenience, provided the click did not originate in an interactive
descendant, and every activation path SHALL open the surface exactly once. The island root SHALL NOT
gain a button role or tab-stop of its own — the full-bleed button, not the root, is the keyboard path
— and `role="button"` on the island root is forbidden outright: a `role="button"` element must contain
no focusable descendant and must not flatten a composite surface into one accessible name, and the
island is a composite surface whose content the root would swallow. The full-bleed button SHALL remain
the island's only tab stop whatever its content becomes: a remembered place's presentation SHALL NOT
be a tab stop, on either layout variant, and SHALL be readable without being focusable. The minimap's
existing per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates and the resolved variant is the lattice
- **THEN** the island renders the renderer's axis orientation marks in its draft-styled header
  alongside the map title, and its readout line states the current node's two payload coordinates as
  its entire content — no place name, no visibility-state word, no destination

#### Scenario: The stated convention and the drawn axis travel together
- **WHEN** a coordinate-bearing payload renders on the island, then a coordinate-free payload renders on
  the island, then the same coordinate-bearing payload renders on the full-map surface, which states no
  orientation marks
- **THEN** the island draws the axis cross exactly where it states `北↑ 東→` and nowhere else — drawn on
  the lattice, absent on the graph, and absent on the full-map surface — so no surface ever draws an axis
  it does not name or names an axis it does not draw
- **AND** the island's coordinate dot field and knowledge-edge vignette add no word, figure, or angle to
  the island: no bearing, no distance, and no coordinate figure beyond the current node's own pair appears
  anywhere because of them

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers and then activates a non-current node on a coordinate-bearing layer
- **THEN** the readout line still states only the current node's coordinate figure, no coordinate
  figure appears for the hovered or activated node, and the island holds no hovered-node or
  selected-node state

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure rather than asserting a
  direction or position the payload does not support

#### Scenario: The layout follows the payload without any control
- **WHEN** a coordinate-bearing payload and then a coordinate-free payload are committed, with no player
  interaction beyond movement
- **THEN** the island and the full-map surface render the lattice for the first payload and the radial
  graph for the second, the map chrome exposes no layout-control element in either state, and no
  preference or storage write occurs

#### Scenario: No compass angle or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing angle, or distance appears anywhere in the island, and the only
  coordinate figure that can appear is the current node's own payload pair on a coordinate-bearing layer

#### Scenario: No control opens an unmounted surface
- **WHEN** the full-map surface is not mounted in the application
- **THEN** the island presents no full-map control, and the per-node movement submission continues to work unchanged

#### Scenario: Island body click opens the map without a second tab stop
- **WHEN** the player clicks the island's non-interactive body while the full-map surface is mounted
- **THEN** the full-map surface opens exactly once, the island root carries no button role and no
  additional tab stop, and the island's full-bleed transparent button remains the keyboard path with
  its focus restore unchanged

#### Scenario: The island's single affordance wears no visible chrome
- **WHEN** an available payload renders on the island while the full-map surface is mounted
- **THEN** exactly one full-map affordance exists, it is a `<button>` spanning the island's whole box
  with 展開全地圖 as its accessible name, no labelled or icon full-map control is rendered in the
  island's header or anywhere else in the island, and the island root carries no `role="button"`

#### Scenario: A keyboard user reaches the full map from the island
- **WHEN** a keyboard user tabs into the island and presses Enter, and repeats the run with Space
- **THEN** each press opens the full-map surface exactly once through the button element's own
  behaviour, the focus-visible indication while it is focused delineates the whole island, and closing
  the surface restores focus to that same still-present element

#### Scenario: Clicking an interactive descendant does not open the map
- **WHEN** the player activates an actionable lattice node, an edge direction marker, or the
  full-map affordance itself
- **THEN** only that control's own behavior runs — the node submits its move and no additional
  map-open is emitted, the affordance opens the map exactly once, and the marker, which carries no
  behaviour and no tab stop, lets the click fall through to the island body so the map opens exactly
  once from there

#### Scenario: A remembered place is readable on the island without a tab stop
- **WHEN** the island renders a coordinate-bearing payload carrying remembered gateways and, in turn,
  a coordinate-free payload carrying remembered rooms
- **THEN** the first draws each place's name beside its edge direction marker, the second draws no
  remembered place's name as visible text on the island and the full-map surface it opens lists each
  place's name as visible text, both islands expose every such place's untruncated name to assistive
  technology — with the marker's octant direction word on the lattice variant and no direction on the
  graph variant — and in neither case does the island offer a second tab stop beyond its full-map
  affordance

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
The action dock SHALL carry a shortcut-legend element matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook. The dock SHALL NOT carry a dialogue-mode legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`4` moves the current dock frame's focus onto the first four rows (1-indexed, rendered order)
and activates the row through the same confirm path `Enter` uses — a disabled row shows its
explanation and submits nothing, an in-flight row stays locked, and a held repeat is suppressed.
The slots address the pane's rendered rows: where a pane does not render the standard `back`
cell as a row (the exit-outlet pane), that cell takes no slot. While the narrative caption
presents the dialogue variant with at least one pick, the slots address the caption's pick rows
instead of the dock's pane rows — the caption's trailing free-dialogue and exit rows never take
a digit slot — and the dock's own rows claim no digit while that hold applies.
A digit whose row does not exist (a frame with fewer rendered rows, a caption variant with no
picks, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carries the shortcut-legend text and test hook, and no duplicate
  copy is rendered

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock tab bar renders in exploration, combat, or dialogue mode
- **THEN** the legend reads `數字鍵 1–4 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the current dock frame has at least two rows and the player presses `2` from a
  non-editable focus
- **THEN** the second row becomes the frame's focus and its action submits exactly as `Enter`
  would, once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rows than the pressed digit and the command field is
  not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue variant renders three picks over a dock root frame and the player presses
  `2` and `4` from a non-editable focus
- **THEN** the `2` press activates caption pick two through the same dispatch entry, the `4` press
  is unclaimed and falls through, and no dock row is focused or activated

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
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map`
anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the
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

#### Scenario: The frame sits in the map anchor, not on a portrait anchor
- **WHEN** a combat session commits participants at 1440x900 and 1280x720
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds no participant content, and the frame's visible box intersects neither the bottom band nor the command line

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
The client's reference surfaces SHALL render in a wide workspace bounded inside both stage edges,
below the top navigation and above the persistent command line. A fine border and charcoal
background SHALL distinguish the workspace from the stage. The existing modal drawer lifecycle
and shared motion tokens SHALL be retained over a dimmed scrim. Between its header and optional
footer, a decorative art column MAY accompany the scrolling content body; only the content body
scrolls. The head SHALL render the title in the display face at the shared workspace scale with
slight tracking, and the subtitle as the small muted line beside it. A drawer
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
SHALL carry a footer stating the client's own cast-command syntax
(`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB
protocol carries, so its presence does not depend on any panel's availability — whenever the drawer
presents the skill book itself; while the declared-practice sub-screen replaces the book body, that
footer is absent and the head title reads 修煉, because the cast syntax belongs to the book view the
sub-screen replaced.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the workspace is bounded below the navigation and above the command line over a dimmed scrim, its content body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the display face with slight tracking and the subtitle renders as the small muted line beside it

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

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer — including the 背包 · 裝備 drawer from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, and the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row — SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer. No reference drawer body SHALL render the dock's row renderer (`dock-menu`) or detail pane (`dock-detail`) in any state. Closing a reference drawer — by Escape, its close control, or the scrim — SHALL leave the router alone, popping no menu level, and SHALL restore focus to the control that opened it. Committed rows inside a reference drawer SHALL remain reachable by keyboard without a hosted router frame.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes so that a drawer's payload is no longer available, when the presentation epoch resets, or when the transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation state inside it SHALL be discarded.

#### Scenario: Opening the quest drawer from the guild clerk pushes no frame
- **WHEN** the player activates the guild clerk's `navigate` affordance row inside an open target frame
- **THEN** the 任務 drawer opens with the quest book and the guild counter, the router's current frame is still that target frame, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Opening the bag or the shop pushes no frame
- **WHEN** the player activates the top navigation's 背包 entry at the exploration root, or a merchant's shop `navigate` affordance row inside an open target frame
- **THEN** the matching drawer opens, the router's current frame is the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Keyboard reachability does not depend on a hosted list
- **WHEN** a keyboard-only player moves through the open bag drawer, or moves into a shop stock row, types a quantity within its advertised bounds, and activates its buy control
- **THEN** every committed inventory row is reachable through the focusable item tiles with the shared inspector, the shop row becomes the selected row carrying the quantity hooks and exactly one `shop.buy` is emitted with that row's `item_key` and quantity, and no parallel navigation list of those rows exists to traverse

#### Scenario: Opening the quest drawer from the top navigation pushes no frame
- **WHEN** the player activates the top navigation's 任務 entry at any dock depth
- **THEN** the dock returns to its root frame as for every top-navigation entry, the 任務 drawer opens, and the router's depth is 1 with no frame pushed by the open

#### Scenario: No drawer renders the dock's row renderer
- **WHEN** any reference drawer is open, including the quest drawer while a guild counter control or a quest-book row holds focus
- **THEN** no `dock-menu` row region and no `dock-detail` pane exists inside the drawer, and the dock itself renders exactly the router's current frame

#### Scenario: Closing a drawer pops nothing and returns focus
- **WHEN** the open 任務 drawer closes by Escape, by its close control, or by the scrim
- **THEN** the router's frame stack is exactly what it was right after the open, no action is dispatched, and focus returns to the control that opened it

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag workspace SHALL use shared chrome for the `背包 · 裝備` title, local inventory SVG icon, close control, and wallet subtitle formatted as integer copper from the committed available character panel. The wallet SHALL additionally render exactly once in the body as the single row of a `金錢` section. The available body SHALL present an `裝備` section carrying the read-only equipment doll, an `物品` section whose heading carries the shipped listing size above the bounded responsive grid, a `金錢` section carrying the same committed wallet, and a reserved non-interactive detail column driven by the existing hover/focus selection. The listing SHALL remain bounded by the server row ceiling and state that ceiling in words when reached; no shipped count SHALL claim to be the player's untruncated holdings.

Each registered row's non-null `presentation` SHALL select one local inline SVG by `icon_key`, an item-kind label, rarity label, bounded summary, and non-colour-only rarity treatment. Its tile SHALL show committed held count and a non-colour equipped marker. A null presentation SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, summary, or mechanics from item key or display name. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both inspection paths SHALL expose identical committed name, kind, rarity, count, equipped state, and summary, and the focused tile SHALL reference the stable inspector through `aria-describedby`.

Each tile SHALL follow only its committed nullable action descriptor. Inspect-only and unknown tiles SHALL dispatch nothing. Disabled tiles SHALL remain keyboard reachable, expose `aria-disabled`, and show the committed reason on activation without dispatch. Enabled usable items SHALL open a labelled, focus-trapped inventory-use confirmation; enabled equipment SHALL dispatch its toggle immediately. Selection and dialog state SHALL remain client-local and reset on panel replacement, drawer close, mode/epoch change, or transport loss. The bag SHALL NOT render or infer numeric item statistics, recovery amounts, conditions, effects, consumable flags, slots, set bonuses, comparisons, sorting, filtering, search, drag, or drop behavior, and SHALL render no static sort/filter/search pill.

The drawer SHALL remain available from its combat affordance when services v3 inventory is available. When services commits its unavailable form or inventory is absent, the bag SHALL render only the registered reason and fabricate no wallet, equipment, row, count, action, or dialog. When services inventory is available but character is unavailable, the grid SHALL remain available, the doll SHALL render its registered unavailable state, and no wallet subtitle, wallet body value, or zero balance SHALL be invented. All inspector, confirmation, and warning transitions SHALL use existing motion tokens so reduced motion makes them effectively instant.

#### Scenario: A registered actionable row preserves truthful inspection
- **WHEN** a committed registered inventory row carries presentation and an enabled action descriptor
- **THEN** its tile renders committed visual identity and inspector data, and deliberate activation follows the descriptor without deriving mechanics locally

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null and `action` null
- **THEN** its tile shows the neutral unknown state and real quantity with no inferred metadata or mutation

#### Scenario: Keyboard inspection and activation match pointer behavior
- **WHEN** keyboard and pointer users inspect and activate the same tile
- **THEN** both receive identical committed inspector data and action behavior, and the focused tile references the inspector through `aria-describedby`

#### Scenario: Eligible item use opens confirmation
- **WHEN** the player activates an enabled usable-item tile
- **THEN** the labelled confirmation dialog opens without dispatch and confirm is the only path that submits use

#### Scenario: Equipment activates directly
- **WHEN** the player activates an enabled equipment tile
- **THEN** one equipment-toggle intent is emitted without opening a confirmation

#### Scenario: Disabled item presents its reason
- **WHEN** the player activates a full-HP potion or an unequipped accessory at the five-slot cap
- **THEN** the committed reason is presented and no request is dispatched

#### Scenario: Combat bag keeps personal items reachable
- **WHEN** mode changes to active combat and services v3 commits canonical inventory
- **THEN** the combat root's client-local `背包` row opens the frameless bag without dispatch or a router frame, and personal item tiles remain reachable while guild and shop surfaces are absent

#### Scenario: The bag body retains its authoritative sections in a wide workspace
- **WHEN** the bag is available with inventory, character equipment, and wallet
- **THEN** it renders equipment, items, and money from their existing sources, with a reserved
  non-interactive item-detail column, and invents no inventory total or additional holdings

#### Scenario: Wallet renders only in the bag head and money row
- **WHEN** the bag renders with available character and inventory panels
- **THEN** the same integer copper wallet appears in the head subtitle and the single `金錢` row and nowhere else in the drawer

#### Scenario: Ceiling is stated without inventing a total
- **WHEN** the shipped inventory reaches its maximum row count
- **THEN** the bag states the listing ceiling and never labels that count as complete holdings

#### Scenario: Unavailable services fabricates nothing
- **WHEN** the services panel commits its unavailable form
- **THEN** the bag renders only the registered reason with no rows, wallet, equipment, count, heading, action, or dialog

#### Scenario: Character unavailability preserves inventory without fabricating equipment
- **WHEN** services inventory is available but the character panel is unavailable
- **THEN** the bag renders held tiles, the equipment registered unavailable reason, and no wallet subtitle, wallet value, or zero balance

#### Scenario: Reduced motion preserves action information
- **WHEN** reduced motion is active and focus, inspector, confirmation, or warning state changes
- **THEN** transitions are effectively instant while labels, reasons, focus, and committed item information remain available

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The section SHALL be introduced by the bag's small tracked section heading `裝備` carrying the right-aligned tag `真值 · 偽裝不影響`, and SHALL NOT be introduced by a standalone `裝備人偶` title. The doll SHALL lay out as the redesign's equipment row: a compact two-column square slot grid beside a 裝備描述 column that lists the committed rows grouped under their slot labels. The doll SHALL render the server's three singleton slots and one accessory summary as four named positions in the square grid. The main-hand, armor, and accessory-summary positions SHALL each render a fixed local SVG selected by its server-authored slot role; the off-hand position SHALL be the iconless position. The doll SHALL NOT select an item icon from an item key or display name. A singleton slot with no row SHALL render a visible named empty state with a dashed outline. An occupied singleton slot SHALL render its visible slot label in the grid and its committed display name in the 裝備描述 column; when the committed rows carry more than one row for a recognised singleton slot, the square position consumes only the first row and every further row for that slot SHALL render as a labelled overflow row, so no committed row is lost. The accessory summary SHALL render its visible label and committed item count, while every repeatable accessory row SHALL render in the 裝備描述 column's accessory group. Any slot key outside the recognised set SHALL render as a labelled fallback row rather than being discarded, so no row the payload sends is lost. When the committed rows carry no equipment at all the doll SHALL render only its visible empty statement.

The doll SHALL NOT render an item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item: the equipment rows carry none of those. Equipment SHALL be presented as true values that a disguise does not affect, and the section tag SHALL state exactly that.

#### Scenario: The equipment section is titled 裝備 with the true-value tag
- **WHEN** the bag renders its equipment section
- **THEN** the section heading reads `裝備` with the tag `真值 · 偽裝不影響` in the bag's shared section-heading style, and the string `裝備人偶` appears nowhere in the drawer

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its visible name with a dashed explicit empty state, and no item is invented for it

#### Scenario: An occupied singleton slot is identified without guessing its item type
- **WHEN** the committed equipment rows carry one primary-hand item
- **THEN** the square grid renders only that position's fixed slot SVG and visible slot name, the 裝備描述 column renders its committed display name under the `主手` label, and nothing is inferred about the item's icon, rarity, statistic, or comparison

#### Scenario: An occupied off-hand position renders without an item icon
- **WHEN** the committed equipment rows carry a `weapon_off` item
- **THEN** the off-hand position stays the iconless position of the binding design, rendering its visible slot label in the grid and its committed display name in the 裝備描述 column with no item icon

#### Scenario: The description column lists only committed rows
- **WHEN** the committed equipment rows carry equipment
- **THEN** the 裝備描述 column shows one labelled entry per primary row (slot label plus committed display name) — the first committed row of each recognised singleton slot and, in the accessory group, every accessory row — grouped by slot label, while duplicate and unrecognised-slot rows are rendered only by the doll's labelled fallback sections so each committed row appears exactly once, and with no committed row the column shows only the visible empty statement

#### Scenario: Duplicate singleton rows are rendered, not discarded
- **WHEN** the committed equipment rows carry more than one row for a recognised singleton slot
- **THEN** the square position shows the first row for that slot and every additional row renders as a labelled overflow row, so the duplicate committed row is never dropped

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** the accessory summary states the committed count and every accessory row renders in the description column's accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity, item icon, summary, or comparison value

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
Across every drawer, the player's wallet SHALL be rendered exactly once per opening of the inventory drawer — once in its shared header subtitle and once as the single row of its `金錢` body section, both read from the committed available panel that owns the value — and nowhere else in the drawer layer. The shop, the lore reference, the character-status drawer, and every other body element of the inventory drawer SHALL NOT render a balance of their own. A drawer whose available character panel does not carry a committed non-negative integer wallet SHALL render no balance at all rather than a zero; the `金錢` body row is additionally gated on the bag's available inventory section, because it renders only inside the bag's three-section stack and the two renderings must never disagree.

#### Scenario: One wallet per drawer-layer opening
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** the only wallet values rendered across all of them are the inventory drawer's header subtitle and its `金錢` section row, both carrying the same integer copper value, and no other drawer or body element renders a balance

#### Scenario: An unavailable panel renders no balance
- **WHEN** the character panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place

#### Scenario: A missing wallet field renders no body row
- **WHEN** the inventory section is available but the character panel's wallet is not a committed non-negative integer
- **THEN** the `金錢` section renders no balance row and the header subtitle renders no balance either, since both read the same validated character-panel figure; neither renders a zero

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

### Requirement: The command line is a collapsible row docked on the message region's top edge
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field with its send control, a hint
cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only
writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the
top navigation bar's tool group. The `command-line` anchor SHALL be one row 44px tall docked to the top
edge of the bottom band's message region: its lower edge SHALL coincide with the band's upper edge, it
SHALL extend from the left HUD island column's right edge to the message region's right edge, and it
SHALL overlay the lowest strip of the stage box, never the band and never the message text.

The command line SHALL be collapsed by default. It SHALL start collapsed on every mount of the shell,
and its expanded state SHALL be client-local and never persisted, so no stored presentation state can
open it or keep it open. While collapsed, the row SHALL be hidden with `display:none`, so the bar and
its input field leave the layout, the accessibility tree, and the tab order, while the input field stays
in the DOM with its preserved identifier and keeps any unsent draft and history-walk state. The
message region SHALL carry, at its bottom-right corner, a labelled ⌨ toggle control that reports the
row's state through `aria-expanded` and names the row through `aria-controls`. The toggle SHALL be
rendered in every mode that renders the message region, SHALL NOT cover the message text (the text's
scroll region SHALL keep its last line clear of the toggle), and SHALL NOT be affected by the committed
narrative, the dialogue variant, or the dock frame.

The command line SHALL expand, and focus SHALL move into its input field only after the row is
rendered, on exactly three paths: `/` pressed while no editable control is focused, activation of the ⌨
toggle while the row is collapsed, and the free-form dialogue borrow. It SHALL collapse, with focus
moved to the action dock before the row is hidden, on exactly two paths: Escape in the input field, and
a send the field accepts (the field clears). Activating the ⌨ toggle while the row is expanded SHALL
collapse it and leave focus on the toggle. A send the field rejects — offline, mutations locked, or a
mutation in flight — SHALL leave the row expanded with the typed text and focus in the field. Losing
focus by any other means (a pointer activation elsewhere, a drawer or overlay opening) SHALL NOT
collapse the row.

The expanded bar SHALL NOT overlap the action dock, the narrative caption, the bottom band, or any HUD
island anchor at 1920x1080, 1440x900, or 1280x720. When horizontal space is insufficient, the hint
cluster SHALL be dropped first; the input field, its send control, and the history controls SHALL
never be dropped. (The command line and its toggle are absent from the layout in creation mode, per the
visibility matrix.)

#### Scenario: The field is one action away
- **WHEN** the shell mounts in exploration mode
- **THEN** the command-line row is hidden with `display:none`, the input field is present in the DOM but outside the tab order, the ⌨ toggle is rendered at the message region's bottom-right with `aria-expanded="false"`, and pressing `/` or activating the toggle once renders the row and puts focus in the input field

#### Scenario: The expanded row keeps its geometry at the minimum viewport
- **WHEN** the command line is expanded at 1280x720 and at 1920x1080
- **THEN** the row is 44px tall (±1px), its lower edge sits on the bottom band's upper edge, its horizontal extent runs from the left HUD column's right edge to the message region's right edge, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, its send control, and the history controls are all rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first, and no input field, send control, or history control is removed

#### Scenario: Escape collapses and keeps the draft
- **WHEN** the player expands the command line with `/`, types a draft, presses Escape, and then activates the ⌨ toggle
- **THEN** Escape sends nothing, moves focus to the action dock, and hides the row, and the toggle expands the row again with the same draft in the field and focus in it

#### Scenario: A successful send collapses the line
- **WHEN** the player expands the command line, types a command, and presses Enter while the client is connected, unlocked, and has no mutation in flight
- **THEN** exactly one command is sent, the field clears, focus moves to the action dock, and the row is hidden with `display:none`

#### Scenario: A rejected send keeps the line open
- **WHEN** the player presses Enter in the expanded command line while mutations are locked or a mutation is in flight
- **THEN** the typed text stays in the field, focus stays in the field, and the row stays expanded

#### Scenario: The toggle closes the open line
- **WHEN** the command line is expanded and the player activates the ⌨ toggle with the pointer
- **THEN** the row is hidden, the toggle reports `aria-expanded="false"`, and focus is on the toggle

#### Scenario: The free-form borrow expands the line
- **WHEN** the command line is collapsed and the player activates a free-form dialogue entry (the dock's free-form row or the dialogue variant's free-dialogue row)
- **THEN** the row expands, focus moves into the input field, and no action is dispatched until the player sends

#### Scenario: No opener or chip is rendered in the bar
- **WHEN** the bar renders expanded in exploration, combat, or dialogue mode
- **THEN** no quick-word chip, letter badge, chip cluster, or overlay or drawer opener (技能系譜, 圖鑑, 稱號冊, 設定, 說明, 角色肖像圖庫) is present in the bar

#### Scenario: The expanded state is never restored from storage
- **WHEN** the player expands the command line and reloads the page
- **THEN** the reloaded shell renders the command line collapsed

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 · Tab 補全` — and
Tab completion SHALL behave as named: pressing Tab inside the input field completes the current
draft against the client's candidate set (session command history and the committed exploration panel's exit names and interact-target display names, deduplicated). With exactly one matching candidate the field SHALL hold the full completion with
the caret at its end; with several the field SHALL hold the longest common prefix and successive
Tab presses SHALL cycle the matching candidates, with Shift+Tab reversing the cycle. A draft that
matches no candidate SHALL leave the field untouched, and Tab SHALL never move focus away from the
field at all (the release path is Escape, which the dock's shortcut legend names). The completion
cycle SHALL reset when the draft text is edited manually, and a change to the committed candidate
sources SHALL drop any in-flight cycle.

The history controls SHALL be labelled controls that drive the same history-walk state the recall
keys drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command
line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and completion
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and the Tab-completion affordance, matching
  the draft wording, and both are implemented

#### Scenario: Tab completes a unique candidate
- **WHEN** the field holds a draft matching exactly one candidate and the player presses Tab
- **THEN** the field holds that candidate in full with the caret at its end, and focus stays in
  the field

#### Scenario: Tab cycles ambiguous candidates
- **WHEN** the field holds a draft matching several candidates and the player presses Tab
  repeatedly
- **THEN** the field first completes to the longest common prefix and then cycles through the
  matching candidates, with Shift+Tab reversing the cycle, and any manual edit of the draft
  resets the cycle

#### Scenario: An unmatched draft is left alone
- **WHEN** the field holds a draft that matches no candidate and the player presses Tab
- **THEN** the field text and focus are unchanged

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

Escape SHALL be resolved by a single precedence order, topmost first — a popover open inside the open
overlay, then the open overlay, then an open drawer, then the focused command field, then the dock's
current menu level — with each level consuming the key and stopping. A popover open inside an overlay
SHALL close on Escape without closing the overlay, keeping focus inside the overlay, and the next
Escape SHALL close the overlay; while no such popover is open, Escape closes the overlay as above.

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

#### Scenario: An overlay's own popover takes Escape first
- **WHEN** the full-map overlay is open with its legend popover expanded, and the player presses Escape twice
- **THEN** the first Escape closes only the popover and focus stays inside the overlay, and the second Escape closes the overlay and returns focus to the trigger that opened it

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its
actionable nodes; the island's non-interactive body MAY additionally open the same surface on pointer
click, which SHALL NOT replace or wrap the labelled control. The top navigation bar's labelled 設定
control and the 說明 control in its tool group SHALL open the settings and help surfaces, in every mode
that renders the top navigation bar, whether the command line is expanded or collapsed.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly
committed payload resolves to the other layout variant, the surface follows the resolved value with no
control of its own. It SHALL open fitted, showing the whole drawing inside its body, and SHALL offer
exactly the view affordances the full-map fit-view requirement of the local-map capability defines —
wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a
labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens
the state legend in a popover — and it SHALL name those gestures in words in its guide row. Those
affordances change only the view of the drawing: none of them SHALL change the committed payload, the
resolved layout variant, or any geometry the surface declares, and none SHALL be persisted. It SHALL
render no bearing, compass angle, distance, or coordinate figure, on any layer, and no zoom level,
scale ratio, or other figure describing the view.

The map surface's body SHALL carry the redesign draft's map-canvas framing (the radial-gradient dark
terrain background painted as pure CSS inside a rounded ink border), and SHALL NOT fabricate terrain
geometry the payload does not claim.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL name no key binding
or control the client does not implement, SHALL describe `/` and the ⌨ toggle as expanding the command
line and Escape and a successful send as collapsing it, and SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed and the command line collapsed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the top navigation bar carries a labelled 設定 control and a labelled 說明 control in its tool group that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement map, and at no point shows a map or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** its only view controls are the labelled 縮小, 放大, and 置中 buttons and the 圖例 disclosure
  button, its guide row names the wheel, `+` / `-`, and drag gestures in words, the legend appears only
  inside the 圖例 popover, and no zoom level, scale ratio, bearing, compass angle, or distance figure
  appears anywhere on the surface

#### Scenario: The map surface frames the draft canvas without invented terrain
- **WHEN** the map surface renders an available payload
- **THEN** the map body shows the radial-gradient ink background inside the rounded ink frame, and no terrain, coastline, or route geometry is drawn that the payload does not carry

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference, including `/` and the ⌨ toggle expanding the command line and Escape collapsing it, and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one

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

### Requirement: Narrative lines carry the reference's semantic classes
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of
committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with
a leading `◈` seal-colour marker contributed by the line's own class, not by invented text;
emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL
render in the serif reading face. The classes SHALL be mounted by the existing markup pipeline at
render time from committed line kinds only — the tokenizer, the player-echo divider lines, and the
box-drawing art path SHALL be unchanged, and no markup class SHALL be mounted for a kind the store
does not carry. The markup pipeline SHALL run exactly once for each retained server, system, or error
line, when the line is retained. Every surface that renders the line SHALL render from that one token
stream, never from a second tokenization or a second markup path. A player input line SHALL never
enter the pipeline. A fragment of a line that paging has split SHALL render with the same kind class,
and the same box-drawing class where it applies, as the whole line would. Only the first fragment
of a `sys` line SHALL show the leading `◈` marker.

#### Scenario: A sys line renders with the seal marker
- **WHEN** a committed narrative line of kind `sys` renders
- **THEN** the line carries the reference's sys treatment including the leading `◈` marker, and the
  marker is decorative (absent from the accessible name of any surrounding live region update that
  already names the line's text)

#### Scenario: Emphasis renders gold inside prose
- **WHEN** a committed prose line carries emphasis through the markup pipeline
- **THEN** the emphasis renders in the reference's gold accent without changing the surrounding
  prose face

#### Scenario: Unknown kinds do not gain semantic classes
- **WHEN** a committed line carries no semantic kind beyond plain output
- **THEN** it renders as plain serif prose without the sys marker

#### Scenario: Each line is tokenized once
- **WHEN** a server line is retained and is then rendered by the narrative surface and by the
  full-log surface, each more than once
- **THEN** the markup pipeline has run for that line exactly once, and both surfaces render the
  same token stream

#### Scenario: A split line's fragments keep the line's classes
- **WHEN** a `sys` line, and separately a prose line carrying emphasis, are each split into two
  fragments
- **THEN** both fragments of the `sys` line carry the sys face and colour, only the first shows the
  `◈` marker, and both fragments of the prose
  line render in the serif reading face with the emphasis still gold in whichever fragment holds it

### Requirement: The party quickbar island presents the committed party only
The `vitals` anchor SHALL carry a compact party island, beneath the vitals and conditions islands, while
the committed `party` panel is available with at least one slot in exploration, combat, or dialogue
mode, and SHALL render no party island — no header, no count, and no cell — when the panel is
unavailable, when its `slots` list is empty, or when the committed mode is creation. The island's
header SHALL read `同伴` with the slot count as `N / 4`, where `N` equals the committed slot count. Each
row of `party.slots` SHALL render one compact cell, in payload order and in one row, carrying: an avatar
showing the bound portrait only when the row's `portrait_ref` resolves through the client's art
catalog, otherwise the display name's initial letter in the reference's gold display face; beneath it
an HP hairline bar whose fill ratio is `hp_current / hp_maximum`; and an accessible name, also exposed
as the cell's tooltip, stating the display name, the HP numerals, and the row's bond stage name. When
the committed combat panel's participant rows carry a row with the same `identity`, the cell SHALL
additionally show that participant's session token (e.g. `a2`) as a visible badge on the avatar; a
companion not fighting SHALL show no token. The island SHALL render no invite cell and no padding for
missing companions: inviting and the 空位 row live in the 同伴 · 隊伍 drawer, where every row's name,
numerals, and bond stage are also visible text. Activating the island or any cell SHALL open the
同伴 · 隊伍 drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

Because the island is absent for an empty party, the character-status drawer SHALL carry one
labelled `同伴 · 隊伍` control, rendered while the committed `party` panel is available, that opens
the 同伴 · 隊伍 drawer and dispatches nothing, so that drawer stays reachable at every party size.

#### Scenario: The quickbar mirrors the committed party
- **WHEN** a snapshot commits two party slots with HP 180/220 and 144/160 and bond stages 親睦
  and 信賴
- **THEN** the island reads `同伴 2 / 4` and renders exactly two compact cells with their HP hairline
  bars, each cell's accessible name and tooltip state its display name, `180/220` or `144/160`, and
  `親睦` or `信賴`, no invite cell is rendered, and no numeric affinity appears

#### Scenario: The combat token is joined by identity
- **WHEN** the committed combat panel carries a participant row whose `identity` equals a party
  slot's `identity` with token `a2`
- **THEN** that companion's cell shows the `a2` badge on its avatar, and a party row with no matching
  participant shows no token

#### Scenario: No portrait falls back to the initial letter
- **WHEN** a party row carries `portrait_ref: null` for display name `蕾娜`
- **THEN** the avatar renders the gold initial `蕾`, not an invented image

#### Scenario: An unavailable party panel hides the island
- **WHEN** the committed `party` panel switches to the unavailable form
- **THEN** no party island is rendered anywhere in the HUD (not an emptied or dimmed island)

#### Scenario: The quickbar opens the drawer without mutating
- **WHEN** the player activates a party cell
- **THEN** the 同伴 · 隊伍 drawer opens and no `ui_action` or text command is sent

#### Scenario: An empty party renders no island
- **WHEN** the committed `party` panel is available with an empty `slots` list in exploration mode
- **THEN** no party island, header, count, or invite cell is rendered anywhere in the HUD, and nothing in the `vitals` anchor is focusable on its behalf

#### Scenario: The party drawer stays reachable with an empty party
- **WHEN** the committed party is empty and the player opens the character-status drawer and activates its `同伴 · 隊伍` control
- **THEN** the 同伴 · 隊伍 drawer opens with its 空位 row and follow rules, and no `ui_action` or text command is sent

### Requirement: The party drawer presents compbig rows and the fixed follow rules
The 同伴 · 隊伍 drawer SHALL render on the shared right-anchored drawer contract with the sub-count
`N / 4`, one compbig row per committed party slot (initial-letter/gold avatar with the same
portrait fallback, display name, bond stage line, HP bar with numerals, the joined 參戰 token
when the companion fights, and a 請其離隊 control), and one 空位 row stating the invite rule in
stage-name words — the raw affinity threshold number SHALL NOT be shown. The 空位 row's
`邀請當前 NPC…` control SHALL dispatch `explore.party_invite` with the exact existing payload
`{npc_id: <the committed invite-capable interact target's identity>, message: ""}` — the fixed
empty message, since the drawer invents no freeform invitation input — under the existing
dispatch and confirmation contract, enabled only when the committed exploration context names
an invite-capable interact target, and SHALL be disabled with its rule line as the reason
otherwise — it SHALL never fabricate a target. Activating 請其離隊 SHALL dispatch `explore.party_leave` for that identity
under the same contract. The drawer SHALL close the party section with three fixed follow-rule
statements matching the reference draft verbatim, and SHALL render no companion detail control
that has no backing read model.

#### Scenario: Rows follow the committed party
- **WHEN** the drawer is open and a party mutation commits a third companion
- **THEN** a third compbig row appears with its committed fields and the sub-count reads `3 / 4`

#### Scenario: Leaving dispatches through the confirmation contract
- **WHEN** the player activates 請其離隊 on a companion row
- **THEN** the existing confirmation flow submits `explore.party_leave` for that identity and the
  row disappears only when the corresponding commit lands

#### Scenario: The invite control is honest about its preconditions
- **WHEN** the exploration context carries no invite-capable interact target
- **THEN** 邀請當前 NPC… is disabled with the stated rule as its reason and dispatches nothing,
  and the raw invite threshold number is never shown

#### Scenario: The follow rules are the reference's three lines
- **WHEN** the drawer body is enumerated
- **THEN** the 跟隨規則 card carries the reference draft's three fixed statements and no invented
  rules

### Requirement: The objective tracker island presents the committed objectives only
The HUD SHALL carry the objective tracker as one line in the stage's `map` anchor, directly beneath
the minimap island, while the committed mode is exploration and the committed `objectives` panel is
available with a non-empty `rows` list; it SHALL be hidden with `display:none` in combat and dialogue
mode and SHALL render nothing when `rows` is empty, when the panel is unavailable, or in creation mode.
The line SHALL have one fixed row height whatever the payload holds and SHALL carry, in order: a
`目標` label; a stage box for the first row of `objectives.rows` showing a completion check when that
row's `stage_progress >= objective_quantity` and an empty box otherwise; that first row's
`objective_line`, truncated on one line with an overflow indicator while its full text stays the line's
accessible text and tooltip; a mono-gold slot carrying `stage_progress / objective_quantity` when the
first row's `objective_quantity` is greater than one and its `+reward_copper` when `objective_quantity`
is one and `reward_copper` is non-null, and carrying nothing otherwise; and, when more than one row is
committed, a mono-gold `+N` count where `N` is the number of further rows. Rows after the first, and
every row's `deadline_line`, SHALL NOT be rendered on the stage; the quest drawer presents them. The
tracker is display-only: it SHALL render no accept, abandon, turn-in, or tracking control and SHALL
dispatch no action. It SHALL present no objective prose the panel does not carry and no invented
optional or previous-stage rows.

#### Scenario: Active objectives list in payload order
- **WHEN** a snapshot commits two objective rows in exploration mode, the first with progress 2 of quantity 5 and the
  second a single-count quest with an 80-copper reward
- **THEN** the line renders `目標`, the first row's describe-seam objective line with its `2/5` tag, and
  a `+1` count, the second row's objective line and `+80` tag are not rendered on the stage, the line's
  height equals its single-row height, and no control is present

#### Scenario: A satisfied objective shows the done box
- **WHEN** the first committed row carries `stage_progress` equal to `objective_quantity`
- **THEN** the line's stage box renders the completion check

#### Scenario: An empty or unavailable objective list hides the island
- **WHEN** the committed `objectives.rows` becomes `[]` or the panel becomes unavailable
- **THEN** no objective line is rendered anywhere in the HUD

#### Scenario: The tracker dispatches nothing
- **WHEN** the player interacts with the objective line
- **THEN** no `ui_action` or text command is sent and no mutation control is present

#### Scenario: A long objective line truncates in place
- **WHEN** the first row's `objective_line` is longer than the line's width
- **THEN** the text is truncated with an overflow indicator, the line keeps its single-row height, and the full `objective_line` is the line's accessible text

### Requirement: The feed presents the dialogue variant from the committed panel
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the
message window SHALL be the ONE dialogue surface and SHALL present the reference's dialogue
variant, unpaged: a dialogue box carrying the
host's avatar (the bound portrait through the client's art catalog when the row's `portrait_ref`
resolves, otherwise the display name's initial letter in the reference's gold display face), a
gold speaker line carrying the host's `display_name` plus ` · 羈絆 <stage>` only when
`bond_stage` is non-null, and the serif reply line carrying the panel's `line` verbatim; below
the box, one numbered pick row per `dialogue.choices` entry in payload order with its mono
digit badge and bounded label, laid out in a compact row grid (at most two pick columns),
followed by a trailing free-dialogue row (`⌨` badge,
`自由對話（輸入任意話語）→ 指令列`) and, after it, a trailing exit row (`✕` badge, label
`結束對話`). The box SHALL follow the current response's lines (see `webclient-input-narrative`);
earlier responses SHALL NOT be presented and remain in the full-log surface. The exchange SHALL keep
the window's fixed box in the band's message region: when the response's lines, the box, picks, and
trailing rows exceed it they SHALL scroll inside the window's text area, with the dialogue box at the
top of that area when a new reply commits, and SHALL NOT grow the window or the band. While the
variant renders, the window SHALL show no page marker, a pointer activation on the window SHALL NOT
advance a page, and Enter and Space SHALL keep their meaning for the focused row. Activating a pick row SHALL dispatch
`explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` under the existing dispatch
contract; activating the free-dialogue row SHALL focus the borrowed command line through the
existing freeform-borrow path and SHALL dispatch nothing itself; activating the exit row SHALL
dispatch `explore.dialogue_leave` with `{npc_id: host.identity}` under the same dispatch contract
and nothing else. The variant SHALL render the
session line exactly once — the box replaces the current response's duplicate final line for that
exchange, keeping any residual text of that line, while the polite live region announces each new
committed line exactly once — and SHALL
NOT render picks the panel does not carry, reason tags, or disabled-row states. While mode is
`dialogue` but the panel is unavailable (the transient window between a clear seam and its
commit), the window SHALL fall back to its paged presentation of the current response with no
dialogue box. The dialogue variant SHALL NOT depend on any dock frame or router
descriptor: its rows derive from the committed panel alone.

#### Scenario: The dialogue box mirrors the committed panel
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, a line, and four
  keyword choices
- **THEN** the window shows the initial-letter gold avatar, the speaker line
  `灰婆婆 · 羈絆 親睦`, the reply line, four numbered pick rows, the free-dialogue row, and the
  exit row — with the reply line visible without scrolling while the picks render

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer or Enter
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that
  row's `keyword_id` is submitted through the existing dispatch contract

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates the trailing free-dialogue row
- **THEN** the command line receives focus for a freeform utterance and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates the exit row
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is
  submitted and no other action is dispatched

#### Scenario: The session line announces once
- **WHEN** a new reply commits while the dialogue variant renders
- **THEN** the reply appears once in the window and the polite live region names its text exactly
  once

#### Scenario: A transiently unavailable panel falls back plainly
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no dialogue box, picks, or exit row render and the window shows the current response's
  pages with their page marker

### Requirement: The dock keeps its regular exploration form in dialogue mode
While the committed mode is `dialogue`, the action dock SHALL render its ordinary exploration
root — the same root items, tab bar, panes, digit bindings outside the caption-retarget rule, and
router behaviour as exploration mode — derived from the committed `exploration` panel, which keeps
shipping its ordinary payload in dialogue mode. The dock SHALL NOT present a dialogue-specific
root, SHALL NOT duplicate the dialogue panel's pick rows in any pane, and SHALL NOT remove any
ordinary affordance while mode is `dialogue`. A mode switch into or out of `dialogue` SHALL
re-home the router stack to the ordinary exploration root descriptor through the existing teardown
decision point.

#### Scenario: The dock stays usable during a conversation
- **WHEN** mode commits to `dialogue` with the exploration panel's ordinary payload
- **THEN** the dock tab bar shows the ordinary exploration root entries (move/look/interact/…)
  with no `對話選項` tab and no pick-row pane anywhere

#### Scenario: Movement stays one action away
- **WHEN** the player opens the move frame while a dialogue session is live and activates an exit
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the
  session through the existing seam, and the committed mode returns to `exploration`

#### Scenario: Mode flips re-home the stack
- **WHEN** a committed snapshot switches the mode from exploration to dialogue while exploration
  submenus are open
- **THEN** the stack holds exactly the ordinary exploration root descriptor and no stale submenu
  row remains activatable

### Requirement: The skill book offers a bounded declared-practice sub-screen
The skill-book drawer SHALL offer a 修煉 affordance on each active skill row the committed
`character` panel supports, and activating it SHALL replace the book body with a practice
sub-screen inside the same drawer: the drawer title becomes 修煉, the body lists the panel's
active skills for selection, and one bounded-duration control starts the practice. The browser
SHALL compute nothing about eligibility, duration outcome, or progression: every row state comes
from the committed panel, the duration control reuses the waiting surface's bounded hours form, and
confirmation SHALL submit exactly one `explore.practice` with the selected `skill` and the
converted whole `seconds` through the shared dispatch/confirmation lock. While a submission is in
flight or its declared presentation revision is pending, the control SHALL be disabled. The
server-authored result line (success summary or rejection message) SHALL render as escaped text
inside the sub-screen and nowhere else, and closing the sub-screen SHALL restore the book body,
the original drawer title, and the book's cast-syntax footer.

#### Scenario: Practice dispatches one server-trusted intent
- **WHEN** the player opens 修煉 from an active skill row, selects the skill, enters `2` hours, and confirms
- **THEN** exactly one `ui_action` is submitted — `explore.practice` with that `skill` and `seconds: 7200` — and the drawer controls stay locked until the result revision is adopted

#### Scenario: The result line is the server's
- **WHEN** a practice result arrives
- **THEN** its Traditional Chinese summary or rejection message renders verbatim as escaped text in the sub-screen, with no client-computed progression, elapsed-time, or eligibility claim

#### Scenario: The practice screen is gated by committed data only
- **WHEN** the `character` panel is unavailable or a row carries no practice support
- **THEN** no 修煉 affordance renders for that row and no practice state is invented

#### Scenario: Closing the practice screen restores the book
- **WHEN** the player closes the practice sub-screen
- **THEN** the drawer shows the skill book again with its original title and its cast-syntax footer, and no second drawer was opened

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character
status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while
that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

Each drawer SHALL be opened either by the dock frame that owns its surface, or by a single labelled
control inside a drawer that already presents the same read model, or by a surface this capability
names elsewhere as an opener for it. No reference surface SHALL require more than two actions from
the top navigation bar or the dock's root frame to reach. Opening a drawer SHALL NOT change any dock root item, any menu frame, any
menu key, or the meaning of Escape.

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption stays in the bottom band's message region

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1440x900 and 1280x720 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the
whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed
elsewhere on the stage. Its box SHALL be the command region's box in every mode and for every frame:
no frame (the interaction workspace, the waiting frame, the combat frames, the skill master-detail,
the destructive confirmation, or an empty pane host) SHALL widen, heighten, shorten, or move it, and
no surface outside the band SHALL be positioned from the frame the dock currently carries. The
content column SHALL be laid out as a fixed-height tab bar, an optional breadcrumb line, and one
remaining region that holds the current frame's rows; that region SHALL be the surface's only
scrolling area, so no dock content is ever pushed outside the command region. A frame whose content
does not fit the region's width SHALL wrap or collapse its own columns inside the region, never
overflow it horizontally. The panel SHALL be the same single `#action-dock` element in every mode,
carrying its existing tab index, its `data-mode` attribute and its role as the surface's documented
focus target, and SHALL NOT be remounted when the mode changes.

The command region SHALL use the current charcoal-and-gold presentation, and the band that contains
it SHALL paint the reference's band chrome. Selected actions remain distinguishable by text and shape
as well as their gold or warm-red emphasis.

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1440x900 from the exploration root to the interaction workspace, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states and the band's height is unchanged

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the tab bar and the breadcrumb stay fixed, and no
  row is rendered outside the command region

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, and it is not removed and re-created

#### Scenario: The panel stays inside its region at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the command region, no dock content overflows the
  region horizontally, and the frame's confirm control is reachable by scrolling the row region
  without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element's background gradient, top border, and box-shadow are the same values
  `docs/design/elosern-redesign/index.html` draws for its dock surface, and the `#action-dock`
  content column itself paints no background, border, or shadow

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card in its `place` anchor, at the stage box's top-left corner below the
top band, while the committed mode is exploration, dialogue, or combat, and SHALL NOT render it in
creation mode. The card SHALL state the current location as its heading and the world date/time
beneath it, and SHALL be the only surface on the stage or in the top band that states either value.
The location SHALL be the best server-authored place name the client already holds, resolved in a
fixed order: the committed `local_map` panel's `current_node` label when that panel is available,
names a current node, that node is present in the panel's nodes, and its label is a non-empty string;
otherwise the committed status panel's actor location label; otherwise the card's own unavailable
placeholder `位置：--`. The world date/time SHALL be the committed world-time label, and the card's own
unavailable placeholder `時間：--` when none is committed. The card SHALL NOT compose a third string
from the two location candidates, SHALL NOT derive a name from any node or room identifier, SHALL NOT
render a raw room key while a committed panel carries the authored place name for the same room, and
SHALL render no raw mode label in place of the location.

The card SHALL wear the HUD island chrome (the translucent panel fill, the backdrop blur, the
hairline border, the shared radius and shadow, all from the shared design tokens), SHALL keep a fixed
height whatever the label lengths, and SHALL truncate a label that exceeds its width with an overflow
indicator while keeping the full label as its accessible text. It SHALL be display-only: no control,
no tab stop, and no dispatch.

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 · 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 · 12:00`, and no other stage or top-band element states either string

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode the place card is not rendered and holds no tab stop
