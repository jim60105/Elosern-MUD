## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the island anchors `hud-left` and `hud-right`, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, and
the `command-line` row — and SHALL NOT be placed inside a page-scrolling container that can push a
required surface out of view.

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
where the scene is seen, and every surface other than the band SHALL be positioned relative to the
band-height token so that none of them overlaps the band.

The portrait anchors SHALL stand on the band: each SHALL be bottom-aligned to the band's upper edge,
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset 6% of the stage
width from its own side, and SHALL never cover the band. The `actor-left` anchor SHALL carry the
player's standing portrait — the current roster character's portrait, resolved exactly as the
stage portrait was before this requirement, with the truthful placeholder when no image exists —
in exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry no content. The
portrait anchors are non-interactive art: they SHALL carry no focusable element and SHALL NOT
intercept pointer events, and they MAY sit behind the HUD islands and the command-line row.

At 1920x1080, 1440x900, and 1280x720 no interactive stage anchor (`hud-left`, `hud-right`,
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

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| narrative caption (band message region) | visible | visible | visible (dialogue focus) | hidden |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective tracker island | visible | visible | visible | hidden |
| player standing portrait | visible | visible | visible | hidden |
| action dock (band command region) | visible | visible | visible (regular exploration form) | visible (creation form, full band width) |
| command line | visible | visible | visible | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). When a mode change, or a committed revision that turns a
surface's data rule false, hides the surface that currently holds focus, the shell SHALL move focus to
the action dock before the surface is removed, using the existing focus-restore path.

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
- **THEN** the narrative caption, the HUD island stack, the minimap, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the narrative caption, minimap, objective tracker, player standing portrait, action dock, and command line all
  remain rendered, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the narrative presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

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

### Requirement: The narrative is a bounded caption whose complete log is reachable in one action
The narrative SHALL render as a caption card that fills the bottom band's message region — the left
two thirds of the band, at the band's fixed height — so it never grows to fill the stage and never
changes size with its content, drawn with the reference's caption panel treatment: charcoal panel
fill, a hairline border, shared radius and restrained shadow. The card SHALL carry a head
row styled as the reference's caption head (small uppercase letter-spaced label): on the left, a mode
label — `敘述` while the committed mode is exploration, `戰鬥日誌` while it is combat, and `對話`
while it is dialogue — and on the right, a single labelled capsule control that opens a full-log surface presenting the complete
retained narrative through the same markup renderer as the caption — never a second markup path. The
head row SHALL be a static sibling ABOVE the card's scroll viewport, never an element inside the
scrolled content, so no narrative line can ever render between the card's border and the head row at
any scroll offset. Only the content region below the head SHALL scroll, and the band's fixed height
SHALL bound that scroll region. The
full-log surface SHALL be scrollable, SHALL trap focus while open, SHALL close on Escape, and SHALL
restore focus to the control that opened it. While the committed mode is dialogue and the
committed `dialogue` panel is available, the head label reads `對話` and the full-log capsule SHALL
NOT be rendered (the reference renders no log control in the dialogue variant); the unread
indicator, its polite live region, and its
jump-to-latest behaviour SHALL remain on the caption card beside the head label and SHALL otherwise
be unchanged.

#### Scenario: The caption card is bounded
- **WHEN** the narrative holds more lines than the caption card can show
- **THEN** the card keeps the message region's box — the band's height and two thirds of its
  width — scrolls internally, and does not expand into the stage

#### Scenario: No content renders above the head row
- **WHEN** the caption is scrolled to any offset in any mode
- **THEN** no narrative line is visible between the card's border and the head row, and the head
  row itself never scrolls out of the card

#### Scenario: The head row names the mode and owns the log control
- **WHEN** the caption renders in exploration mode and then in combat mode
- **THEN** the head label reads `敘述`, then `戰鬥日誌`, and the `完整日誌` capsule is the card's only
  full-log control

#### Scenario: The complete log opens in one action
- **WHEN** the player activates the caption card's full-log control
- **THEN** the full-log surface opens showing the complete retained narrative, rendered through the
  same markup renderer as the caption

#### Scenario: The full-log surface returns focus on Escape
- **WHEN** the full-log surface is open and the player presses Escape
- **THEN** it closes and focus returns to the control that opened it

#### Scenario: The unread indicator is unchanged
- **WHEN** new narrative lines arrive while the caption card is scrolled away from the latest line
- **THEN** the unread indicator states its count and jump action and is announced through its polite
  live region exactly as before

#### Scenario: The dialogue head reads 對話 without the log capsule
- **WHEN** the committed mode is dialogue and the `dialogue` panel is available
- **THEN** the head label reads `對話` and no `完整日誌` capsule is rendered

### Requirement: The command line is a permanently present bar in the stage's command-line anchor
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field, a hint cluster, the
command-history controls, and the overlay utility controls. The `command-line` anchor SHALL be one
row docked to the top edge of the bottom band's message region: its lower edge SHALL coincide with
the band's upper edge, it SHALL extend from the left HUD island column's right edge to the message
region's right edge, and it SHALL overlay the lowest strip of the stage box, never the band. The bar
SHALL carry no quick-word chip and
no other control that only writes a fixed command word into the field. The overlay utility controls
SHALL include a labelled 角色肖像圖庫 control that renders only while the committed `gallery` panel is
available and opens the portrait gallery overlay through the same opener-captured path the other
utility controls use, so closing the gallery returns focus to that control. In the modes this
capability's visibility matrix renders the command line (exploration and combat), the input field SHALL
be present in the DOM, visible and focusable without any opening action: there SHALL be no entry
control, no `aria-expanded` state and no closed state. No stored presentation state SHALL be able to
remove it. (The command line is intentionally absent from the layout in creation mode, per H1's
visibility matrix and design D10.)

The bar SHALL NOT overlap the action dock, the narrative caption, the bottom band, or any HUD island
anchor at 1920x1080, 1440x900, or 1280x720. When horizontal space is insufficient, the hint cluster
SHALL be dropped first; the input field, the history controls and the
utility controls SHALL never be dropped, because they are the only pointer path to their behaviour.

#### Scenario: The field is usable without an opening action
- **WHEN** the shell mounts in exploration mode
- **THEN** the command input field is present in the DOM and focusable, no entry control is rendered, and no element in the bar reports an `aria-expanded` state

#### Scenario: The bar keeps its geometry at the minimum viewport
- **WHEN** the stage renders at 1280x720 with every utility control rendered, including the gallery control
- **THEN** the bar's lower edge sits on the bottom band's upper edge, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, the history controls and the utility controls are all still rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first, and no input field, history control or utility control is removed

#### Scenario: The gallery control follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, the player activates the 角色肖像圖庫 utility control, closes the overlay, and a later revision commits the panel's unavailable form
- **THEN** the control opens the portrait gallery overlay, closing the overlay returns focus to the control, and after the unavailable form commits the control is absent from the bar and the tab order

#### Scenario: No quick-word chip is rendered
- **WHEN** the bar renders in exploration or combat mode
- **THEN** no quick-word chip, letter badge, or chip cluster is present in the bar

### Requirement: The feed presents the dialogue variant from the committed panel
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the
narrative caption SHALL be the ONE dialogue surface and SHALL present the reference's dialogue
variant: a dialogue box carrying the
host's avatar (the bound portrait through the client's art catalog when the row's `portrait_ref`
resolves, otherwise the display name's initial letter in the reference's gold display face), a
gold speaker line carrying the host's `display_name` plus ` · 羈絆 <stage>` only when
`bond_stage` is non-null, and the serif reply line carrying the panel's `line` verbatim; below
the box, one numbered pick row per `dialogue.choices` entry in payload order with its mono
digit badge and bounded label, laid out in a compact row grid (at most two pick columns),
followed by a trailing free-dialogue row (`⌨` badge,
`自由對話（輸入任意話語）→ 指令列`) and, after it, a trailing exit row (`✕` badge, label
`結束對話`). The exchange SHALL keep the caption's fixed box in the band's message region: when box,
picks, and trailing rows exceed it they SHALL scroll inside the caption's scroll region, with the
dialogue box at the top of that region when the picks first render, and SHALL NOT grow the caption
or the band. Activating a pick row SHALL dispatch
`explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` under the existing dispatch
contract; activating the free-dialogue row SHALL focus the borrowed command line through the
existing freeform-borrow path and SHALL dispatch nothing itself; activating the exit row SHALL
dispatch `explore.dialogue_leave` with `{npc_id: host.identity}` under the same dispatch contract
and nothing else. The variant SHALL render the
session line exactly once — the box replaces the caption's duplicate stream tail for that
exchange while the polite live region announces each new committed line exactly once — and SHALL
NOT render picks the panel does not carry, reason tags, or disabled-row states. While mode is
`dialogue` but the panel is unavailable (the transient window between a clear seam and its
commit), the caption SHALL fall back to its plain narrative presentation with the `對話` head
label and no dialogue box. The dialogue variant SHALL NOT depend on any dock frame or router
descriptor: its rows derive from the committed panel alone.

#### Scenario: The dialogue box mirrors the committed panel
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, a line, and four
  keyword choices
- **THEN** the caption shows the initial-letter gold avatar, the speaker line
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
- **THEN** the reply appears once in the caption and the polite live region names its text exactly
  once

#### Scenario: A transiently unavailable panel falls back plainly
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no dialogue box, picks, or exit row render and the caption shows plain narrative with
  the `對話` label

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
- **THEN** the right-hand HUD anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: The action dock renders as a floating panel in the stage's dock anchor
**Reason**: The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §5.1) replaces the floating dock panel and its frame-dependent `--dock-h` height with a fixed bottom band whose right third is the command region. The requirement's subject (a floating panel in a `dock` anchor whose height grows with the open frame) no longer exists.
**Migration**: "The action dock fills the band's command region at a fixed size" carries the persistent `#action-dock` element, the fixed tab bar / breadcrumb / single scrolling region layout, the in-region confirm reachability, and the band chrome; the band's fixed height is stated by "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces".
