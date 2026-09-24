## MODIFIED Requirements

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
- **WHEN** the shell renders at 1920x1080 and the player moves through the exploration scene overview, a target's verb popover, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
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

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the
whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed
elsewhere on the stage. Its box SHALL be the command region's box in every mode and for every frame:
no frame (the scene overview, a target's verb popover, the waiting frame, the combat frames, the skill
master-detail, the destructive confirmation, or an empty pane host) SHALL widen, heighten, shorten, or
move it, and
no surface outside the band SHALL be positioned from the frame the dock currently carries. The
content column SHALL be laid out as fixed chrome — the combat root's tab bar in combat mode and no bar
in exploration or dialogue mode, an optional breadcrumb line, and the shortcut-legend strip at the
bottom — around one remaining region that holds the current frame's rows or chips; that region SHALL
be the surface's only scrolling area, so no dock content is ever pushed outside the command region.
A target's verb popover SHALL render as a card laid over that region's visible box, inside the command
region, and SHALL scroll inside its own card when its rows exceed it. A frame whose content
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
- **WHEN** the dock moves at 1440x900 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb popover's card lies inside the command region

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat tab bar, the breadcrumb,
  and the legend strip) stays fixed, and no row or chip is rendered outside the command region

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

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration, dialogue, and combat mode (never in creation mode), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no tab bar SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`4` moves the current dock frame's focus onto its first four entries (1-indexed, rendered order —
for the scene overview, its first four chips in reading order) and activates the entry through the
same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an
in-flight entry stays locked, and a held repeat is suppressed.
The slots address the frame's rendered entries: where a pane does not render the standard `back`
cell as a row (the exit-outlet pane), that cell takes no slot. While the message window
presents the dialogue variant with at least one pick, the slots address the window's pick rows
instead of the dock's entries — the trailing free-dialogue and exit rows never take
a digit slot — and the dock's own entries claim no digit while that hold applies.
A digit whose entry does not exist (a frame with fewer rendered entries, a dialogue variant with no
picks, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in exploration, dialogue, or combat mode, at the overview, in a child frame, or at the combat root
- **THEN** exactly one element carries the shortcut-legend text and test hook, it is the dock's
  legend strip, and no tab bar or pane renders a duplicate copy

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration, combat, or dialogue mode
- **THEN** the legend reads `數字鍵 1–4 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the scene overview's first two chips are an exit and a person, and the player presses `2`
  from a non-editable focus
- **THEN** the person chip becomes the frame's focus and its popover opens exactly as `Enter`
  would, once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue variant renders three picks over the dock's scene overview and the player presses
  `2` and `4` from a non-editable focus
- **THEN** the `2` press activates pick two through the same dispatch entry, the `4` press
  is unclaimed and falls through, and no dock chip is focused or activated

### Requirement: The dock keeps its regular exploration form in dialogue mode
While the committed mode is `dialogue`, the action dock SHALL render its ordinary exploration
root — the same scene overview, verb popover, child frames, digit bindings outside the caption-retarget
rule, and router behaviour as exploration mode — derived from the committed `exploration` panel, which keeps
shipping its ordinary payload in dialogue mode. The dock SHALL NOT present a dialogue-specific
root, SHALL NOT duplicate the dialogue panel's pick rows in the overview or any frame, and SHALL NOT remove any
ordinary affordance while mode is `dialogue`. A mode switch into or out of `dialogue` SHALL
re-home the router stack to the ordinary exploration root descriptor through the existing teardown
decision point.

#### Scenario: The dock stays usable during a conversation
- **WHEN** mode commits to `dialogue` with the exploration panel's ordinary payload
- **THEN** the dock shows the ordinary scene overview (exits, people, objects, and the footer)
  with no `對話選項` entry and no pick-row frame anywhere

#### Scenario: Movement stays one action away
- **WHEN** the player activates an exit chip in the scene overview while a dialogue session is live
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the
  session through the existing seam, and the committed mode returns to `exploration`

#### Scenario: Mode flips re-home the stack
- **WHEN** a committed snapshot switches the mode from exploration to dialogue while a verb popover
  or another exploration child frame is open
- **THEN** the stack holds exactly the ordinary exploration root descriptor and no stale submenu
  row remains activatable

## ADDED Requirements

### Requirement: The combat dock's root frame renders as an icon tab bar with a truthful skills badge
In combat mode the dock's root menu frame SHALL render as a horizontal tab bar, one tab per combat root
item, each carrying a decorative glyph and its label. The focused or open root entry's tab SHALL be
marked with the accent fill, and the marking SHALL NOT be the only indication of state. When the router
is at the combat root frame the tab bar SHALL be the surface's row container: it SHALL carry the
listbox role, be the surface's single tab stop, name the focused tab through an active-descendant
association, and carry each root item's preserved row identity attribute and row id. When a deeper
combat frame is open the tab bar SHALL become inert ancestor chrome that marks which root entry is open
and SHALL NOT be a second tab stop. No other mode SHALL render a root tab bar: the exploration and
dialogue root is the scene overview.

The 技能 tab SHALL carry a count badge equal to the number of skill descriptors the committed combat
panel lists across its categories and groups, and SHALL carry no badge when that number is zero; no
other combat tab carries a badge, and a badge SHALL NEVER be rendered from an estimate or from a value
the panel does not carry.

The combat root's focus geometry SHALL match the rendered tab order: its column count SHALL equal its
item count, so the horizontal arrow keys traverse the visible tabs and the vertical arrow keys are a
no-op on the root.

A tab's decorative glyph SHALL match the icon `docs/design/elosern-redesign/index.html` (the binding
visual reference) draws for that same tab concept, for every combat-root key the reference draws an
icon for. A key with no counterpart in the reference (a client-local entry such as the bag drawer row)
SHALL carry whatever glyph best represents it.

#### Scenario: The combat root renders as tabs and owns the listbox
- **WHEN** the dock is at the combat root frame
- **THEN** each root item renders as a tab with a glyph and its label, the tab bar carries the listbox role with a single tab stop and an active-descendant reference, and each tab carries its preserved row identity attribute

#### Scenario: A combat tab glyph matches the reference design's icon for the same concept
- **WHEN** the combat root renders the 攻擊/技能/道具/防禦/逃跑/投降 tabs
- **THEN** each tab's glyph is the same pictogram `docs/design/elosern-redesign/index.html` draws for that tab's concept

#### Scenario: The skills badge equals the committed skill count
- **WHEN** the committed combat panel lists three skill descriptors across its categories, and later a panel with none
- **THEN** the 技能 tab shows the badge `3`, then no badge at all, and no other combat tab shows a badge

#### Scenario: Combat tab focus geometry matches the rendered order
- **WHEN** the player presses the horizontal arrow keys on the combat root frame
- **THEN** focus moves through the tabs in their rendered order and wraps at the ends, and the vertical arrow keys move focus nowhere

#### Scenario: An open deeper combat frame leaves the tab bar inert
- **WHEN** a deeper combat frame is open
- **THEN** the tab bar marks which root entry is open, the deeper frame's row container is the surface's only listbox and only tab stop, and no tab is reachable by sequential keyboard navigation

#### Scenario: Exploration renders no root tab bar
- **WHEN** the dock renders in exploration or dialogue mode at any depth
- **THEN** no tab bar is rendered, and no 移動, 查看, 互動, or 建議 tab exists anywhere in the dock

## REMOVED Requirements

### Requirement: The dock's root frame renders as an icon tab bar with truthful count badges
**Reason**: The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §7) removes the exploration tab bar (`移動 / 查看 / 互動 / 等待 / 建議`) and its 互動 and 建議 count badges. The exploration root is the scene overview, and only the combat root keeps a tab bar. The requirement's scenarios name the exploration tabs and badges.
**Migration**: "The combat dock's root frame renders as an icon tab bar with a truthful skills badge" keeps the tab bar, listbox, geometry, glyph, and badge rules for the combat root. "The exploration dock is keyboard-first and roots at the scene overview" (`webclient-exploration-menu`) covers the exploration root. The 建議 count moves into the footer chip's `建議 (N)` label. Tests annotated with the old ID re-anchor to the combat requirement.
