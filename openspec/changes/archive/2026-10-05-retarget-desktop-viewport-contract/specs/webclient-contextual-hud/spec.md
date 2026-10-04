## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
This requirement carries the `place-card-relocation` and `vitals-bar-redesign` amendments; the party-line wording below replaces the solo-portrait wording of the `actor-left` anchor.
Fixed CSS-pixel chrome dimensions in this requirement are reference dimensions at viewports up to 790px tall or 1451px wide, the 1451x790 reference viewport. Above both, chrome dimensions scale once under the desktop proportional-scaling contract; viewport-relative band/prose/portrait dimensions are not multiplied again. The named acceptance-size non-overlap rules remain.
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the lower-left `vitals` anchor, the top-right `map` anchor, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, the dialogue `choices` anchor, and
the `command-line` row — and SHALL NOT be placed inside a page-scrolling container that can push a
required surface out of view. The stage SHALL carry no separate `place` anchor: the place card is an
island of the `map` anchor.

The top band SHALL be 48px tall at every supported viewport and SHALL carry only the brand, the top
navigation bar, the possession banner when present, the character switcher, and the connection
state; it SHALL carry no location label and no time label. The `vitals` anchor is the stage's lower-left vitals dock that "The vitals dock stands at the stage's lower-left above the band"
defines: bottom-anchored on the band's upper edge in the left gutter, at the left column's fixed width that does not depend on the
content it holds. The `map` anchor SHALL sit at the stage
box's top-right corner, below the top band; its content column (the place card, then the
minimap island, then the objective line, then any other island this capability places there) SHALL be right-aligned to the
stage's right gutter and bounded above the bottom band.

The bottom band SHALL span the full stage width along the stage's bottom edge at one fixed height,
`clamp(190px, 27.85vh, 400px)` with its two px bounds multiplied once by the desktop chrome factor (220px at the 1451x790 reference viewport, 401px at 2560x1440), taken from a single
shared band-height token. The band's height SHALL NOT depend on its content, on the dock frame, on
the committed mode, or on any measurement: no frame, pane, line count, dialogue exchange, or mode
change SHALL grow or shrink it. The band SHALL be divided into the message region `band-message`,
covering the left two thirds of the band's width, and the command region `band-command`, covering
the remaining right third; in creation mode, where the message region is hidden, the command region
SHALL span the whole band, and in dialogue mode, where the command region is collapsed, the message
region SHALL span the whole band. The band SHALL carry the reference's band chrome (the upward gradient,
the hairline top border, and the upward shadow) on the band itself, not on the content inside it.
The stage box — the region between the top band's lower edge and the bottom band's upper edge — is
where the scene is seen, and at the 1451x790 reference viewport it SHALL be at least 65% of the
viewport's height — at least 513.5px of 790; the 48px top band and the 220px bottom band leave 522px. Every surface other than the band SHALL be positioned relative to the
band-height token so that none of them overlaps the band.

The portrait anchors SHALL stand on the band: each SHALL be bottom-aligned to the band's upper edge,
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset at least 6% of the
stage width from its own side, and SHALL never cover the band. Where 6% would place the figure's face
(the anchor's horizontal centre) under the island column on its side — the vitals stack on
the left, the place card and the minimap card on the right — the inset SHALL grow just enough to clear that column; at
the 1451x790 reference viewport both insets take their column-clearance value and only that value
acts as a floor where no column reaches the portrait's face height. The `actor-left` anchor SHALL carry the
controlled character's stage actor — the current roster character's portrait, or the possessed
companion's while the possession banner is available — with the committed party's companion stage
actors lined up behind it as "Companion standing portraits line up behind the controlled character in
the actor-left anchor" defines, each with the truthful placeholder when no image exists, in
exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry the dialogue host's stage
actor while the committed mode is `dialogue`, the committed `dialogue` panel is available, and its host identity does not already join to a committed party or controlled lineup figure, SHALL carry
the foe line-up that "Foes stand opposite the player during combat" defines while the committed mode is
`combat` and at least one foe is active, or while a round that ended the fight still plays as "Combat
beats are choreographed on the stage at the motion level" defines, and SHALL carry no content in every
other state. The foe
line-up MAY extend leftward beyond the `actor-right` anchor's own box, within the bounds that
requirement sets, and SHALL NOT cross the stage's horizontal centre, which the companion line-up's
figures also never cross. Every stage actor follows "Stage actors present the player and the dialogue host with
a speaking state". The portrait anchors are non-interactive art: they SHALL carry no
focusable element and SHALL NOT intercept pointer events, and they MAY sit behind the HUD islands, the
`choices` anchor, and the command-line row.

The `choices` anchor SHALL render only in dialogue mode. It SHALL be horizontally centred on the stage
box, at most `min(560px, 40%)` of the stage width wide, above the portrait anchors, and its content
SHALL be vertically centred in, and bounded by, the part of the stage box between the top band and the
scene caption row that stands on the command-line row, so it never meets the scene caption or the
expanded command line; when its content is taller
than that span allows it SHALL scroll internally, and it SHALL NOT grow into the top band, the
command-line row, or the bottom band.

At 1451x790, and at every larger viewport up to the chrome factor's cap, no interactive stage anchor (`vitals`, `map`,
`band-message`, `band-command`, `choices`, `command-line`) SHALL overlap another interactive anchor's content,
and the top band's own elements SHALL neither overlap one another nor extend into the HUD island
anchor region: a band element whose content is variable-width SHALL be bounded and truncated rather
than sized by its content. A transient popover opened from a top-band element MAY overlay the
island anchors while open, provided it does not change the band's own rendered box and closes on
Escape and on outside activation; a surface that permanently occupies vertical space SHALL NOT be
introduced into the band this way.

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1451x790
- **THEN** the scene backdrop fills the stage box, and the player portrait, the HUD islands, the bottom band, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height, or the dock frame or the narrative holds more content than its band region
- **THEN** the island stack or the band region itself is bounded and scrolls internally, and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at the 1451x790 reference viewport with every mode-visible surface present
- **THEN** no interactive stage anchor's rendered box intersects another interactive anchor's rendered box

#### Scenario: The top band's own elements do not collide
- **WHEN** the shell renders at the 1451x790 reference viewport with every top-band element present and a maximum-length character name committed
- **THEN** the band's elements render side by side without intersecting, the variable-width element is truncated within its bound, and no band element's box extends into the island anchor region

#### Scenario: A band popover overlays without displacing
- **WHEN** a transient popover is opened from a top-band element
- **THEN** the band's rendered box is unchanged, the popover renders above the island anchors, and Escape or outside activation closes it

#### Scenario: The bottom band keeps one height whatever it holds
- **WHEN** the shell renders at 1451x790 and the player moves through the exploration scene overview, a target's verb popover, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
- **THEN** the bottom band's rendered height is 220px (±1px) in every one of those states, the message region's and the command region's boxes are unchanged between the exploration and combat states, and in the dialogue state the message region spans the band's whole width at the same height

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, in creation mode the command region spans the whole band, and in dialogue mode the message region spans the whole band while the command region is not rendered

#### Scenario: The player portrait stands on the band
- **WHEN** the shell renders in exploration mode at 1451x790 with a committed roster portrait for the current character
- **THEN** the `actor-left` anchor renders that portrait frontmost, its bottom edge coincides with the band's top edge, its height is `min(62vh, 680px)` (±1px) — its left-edge inset is the value its anchor rule derives, never below 6% of the stage width, it holds no focusable element, and the `actor-right` anchor renders no content

#### Scenario: The portrait never outgrows the stage box
- **WHEN** the shell renders in a window short enough that `min(62vh, 680px)` exceeds the stage box's height
- **THEN** the player portrait's height equals the stage box's height and its top edge is not above the top band's lower edge

#### Scenario: The stage box is at least 65% of the reference viewport
- **WHEN** the shell renders in exploration mode at 1451x790
- **THEN** the top band is 48px tall, the bottom band is 220px tall (each ±1px), and the stage box between them is at least 513.5px tall (65% of 790)

#### Scenario: The top band carries no location or time
- **WHEN** the shell renders in exploration mode with a committed location label and world time
- **THEN** the top band's rendered height is 48px, no element inside the top band states the location label or the world time, and the place card in the `map` anchor below the top band states both

#### Scenario: The left column carries no place card
- **WHEN** the shell renders in exploration mode with a committed location and world time
- **THEN** no place card renders anywhere in the stage's left column, and the `vitals` anchor's box is not offset by any place card's height

#### Scenario: The dialogue host stands opposite the player
- **WHEN** the committed mode changes from exploration to dialogue at 1451x790 with an available `dialogue` panel whose host is not already in the party lineup
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is inset by its anchor rule's clearance value (never below 6% of the stage width), its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1451x790 and at 2560x1440
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the leftmost edge of the right-hand island column — the place card and the minimap card, which share that column's width — and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1451x790 and at 2560x1440 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `vitals`, `map`, band, or command-line anchor, and every row is reachable

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines — or, while the
current response carries a combat round the client presents, as that round's beat pages followed by the
response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and
SHALL NOT present earlier responses: they remain readable in the full-log surface. The one exception is the clear
transition: when a new response replaces the previous one, the previous page MAY remain only as an
opaque layer over the new page that fades out within the clear duration of the client's motion level
(at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility
tree and pointer hit-testing from the moment the new response starts. Page text SHALL be set in the bundled
monospace reading face — the same Jim Mono TC family the monospace type role ships — at
18px at the 1451x790 reference size and the default prose scale, SHALL scale once with the
desktop chrome factor and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line in every mode, including the whole-band width of dialogue mode.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing and while a combat round plays by itself. When rendered, it SHALL read `▼` while the current response has further pages and
`■` on its last page. It SHALL be decorative (hidden from assistive technology), and it SHALL blink
only through the client's motion tokens, so reduced motion stops the blink. An oversize page SHALL
scroll inside the window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no unread indicator and no jump-to-latest control, and no head row
other than the dialogue name plate. In creation mode the window, its marker, and the `日誌` control are
hidden with the message region.

While the committed mode is `dialogue` and the committed `dialogue` panel is available, the window SHALL
carry a name plate above its text area, naming the host with the panel's `display_name` plus
` ‧ 羈絆 <stage>` only when `bond_stage` is non-null; the window's text area below the plate SHALL
present the current response's pages — the session line as the narrative delivered it, paged and typed
like any response, with no separate reply box, no rows, no avatar, and no text removed or rewritten
from the narrative lines. The window SHALL carry no choice, free-dialogue, or exit row: those are the
dialogue choice list's. While mode is `dialogue` but the panel is unavailable (the transient window
between a clear seam and its commit), the window SHALL render no name plate. The window SHALL make known
to the shell, from its own reader state and never from narrative prose, whether the current response's
last page is on screen, fully shown, with no pending action mark — the moment the dialogue choice list
waits for.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1451x790 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 18px (±0.5px) in the bundled monospace reading face and no rendered text line holds more
  than 42 CJK characters in either mode

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages, page 1 types to its end, and the player advances
  once and page 2 types to its end
- **THEN** no marker renders while either page is typing, the marker reads `▼` once page 1 is fully
  shown and `■` once page 2 is fully shown, and it is absent from the accessibility tree

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

#### Scenario: The dialogue line is paged under the name plate
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1451x790
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 ‧ 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode `dialogue` commits with `bond_stage` `null`
- **THEN** the name plate reads the host's `display_name` alone and carries no `羈絆` text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps — `A−` 16px, `A` 18px, and
`A+` 20px at the 1451x790 reference scale, multiplied once by the desktop chrome factor —
selectable from the settings surface, whose current step is marked by an indicator that does not
rely on colour alone. `A−` is the reading floor: at the reference scale it renders the prose the
client shows at exactly 16 CSS px, and no step renders it smaller. The scale SHALL apply
to narrative and dialogue prose only — the message window's page text, the complete-log surface's lines,
the prompt line and the settings surface's reading sample, which previews the page text — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at the reference viewport or any larger one.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied
immediately to the presentation it governs — the document's presentation tokens for the prose scale,
the motion level, the text-to-HTML toggle and the colourblind palette, and the message window for the
reading preferences and the motion level — and SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference. Each setting SHALL be re-applied at
load, and SHALL be reset to its default — fully applied, never half-applied — whenever that store
resets. A stored prose-scale value that matches none of the re-stepped values SHALL load as the
default `A` step rather than as a clamped legacy multiplier. The motion level SHALL follow "The motion level is a client-local preference that governs every
client animation": a stored level overrides the operating system's reduced-motion preference, which
SHALL continue to apply while no level is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines, the prompt line and the settings surface's reading sample render at 20px at the reference scale, every other HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1451x790

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, the text speed, and the motion level, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale, text speed, and motion level are re-applied after the reload, and after the reset every setting is applied at its default, the motion level following the operating system again, with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no motion level is stored and the operating system requests reduced motion
- **THEN** the effective motion level is `reduced`, so looping and travelling motion stops and message pages appear in full at once; and when the player then selects `完整`, the client honours that stored level over the operating system

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

### Requirement: The place card names the current location and the world time
This requirement carries the `place-card-relocation` amendment; the visible-mode set below narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells.
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's
top-right corner directly below the top band and directly above the minimap island, while the
committed mode is exploration or combat, and SHALL NOT render it in
creation mode or settled dialogue mode. During live dialogue entry it MAY retain only the inert exit
paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility
tree and tab order from commit, and SHALL become `display:none` when the anchor's fade ends.
The card SHALL state the current location as its heading and the world date/time
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
hairline border, the shared radius and shadow, all from the shared design tokens), SHALL span the same
content-column width as the minimap island beneath it, SHALL keep a fixed
height whatever the label lengths, and SHALL truncate a label that exceeds its width with an overflow
indicator while keeping the full label as its accessible text. It SHALL be display-only: no control,
no tab stop, and no dispatch.

The card SHALL set its two values on two levels: the location heading in the serif face at the
`--text-lg` step, then a quiet decorative gold rule, hidden from assistive technology, then the
world-time line. The world-time line SHALL carry no leading separator glyph or rule before its first
value, SHALL use the
numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 16px chrome
floor), and SHALL render the committed world-time label (or its placeholder) verbatim, with every
date and time value intact: all time values SHALL remain server-authored, and the card SHALL NOT
reformat, abbreviate, or derive them. The heading, the rule, and the time line SHALL fit the card's
fixed height.

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 ‧ 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 ‧ 12:00`, and no other stage or top-band element states either string

#### Scenario: The card heads the map column
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the place card is the first island of the `map` anchor, its rendered width equals the minimap island's rendered width, and the stage renders no place card in its left column

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation, and later dialogue
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode and in settled dialogue mode the place card is not rendered and holds no tab stop; during live dialogue entry only its inert exit paint may remain until the map anchor's fade ends

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the heading is set one
  step below the display size the stage's island chrome uses at `--text-lg`, the time line's numerals
  are tabular lining figures in the numeral face, and the card keeps its fixed height

### Requirement: CJK reading furniture follows the measured prose column
Prose SHALL have readable CJK line and paragraph spacing while preserving exact narrative content, the contracted reference font size, sentence-safe paging and map alignment. Page text SHALL use a line height of 1.5 times its font size and SHALL separate consecutive narrative lines by a gap of about half a line. Any CJK spacing treatment SHALL be presentation only (the rendered text content is unchanged) and SHALL NOT apply to box-drawing map lines, whose whitespace and alignment stay exact. Page measurement SHALL match displayed typography, so no page line is clipped at any viewport or prose scale. The page marker SHALL end at the prose column's right edge, or as close to it as the control strip's own controls allow, and SHALL stay inside the control strip. The dialogue name plate's underline SHALL start at the name's left edge. The message window's reading rule SHALL show only while the page surface holds keyboard focus. Decorative motion SHALL stop at the reduced and off motion levels.

#### Scenario: Resize preserves complete narrative
- **WHEN** mixed CJK and Latin prose is paged, then the viewport or reader scale changes
- **THEN** all content remains reachable without clipped lines, and the marker stays within the reserved strip at the prose edge, clear of the `日誌` control

#### Scenario: Maps preserve whitespace
- **WHEN** a response contains an ASCII map between prose blocks
- **THEN** the map retains its indentation and alignment while prose receives spacing treatment

#### Scenario: The marker follows the dialogue column
- **WHEN** a dialogue page is fully shown at 1451x790
- **THEN** the marker's right edge lies within a few pixels of the left-aligned prose column's right edge, far from the band's right end

#### Scenario: Reduced motion keeps the marker still
- **WHEN** the motion level is reduced or off while a page marker is shown
- **THEN** the marker neither bobs nor fades

### Requirement: Narrative lines carry the reference's semantic classes
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of
committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with
a leading `◈` seal-colour marker contributed by the line's own class, not by invented text;
emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL
render in the bundled monospace reading face, the face the message window's page text uses. The classes SHALL be mounted by the existing markup pipeline at
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
- **THEN** it renders as plain prose in the monospace reading face without the sys marker

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
  line render in the monospace reading face with the emphasis still gold in whichever fragment holds it

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with
cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and
labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's
gradient stage otherwise — for a missing, failed, or invalid asset, for a pending scene with no prior
image, and when the `art` panel is unavailable. A bundled decorative sample MAY accompany this
fallback only with a visible caption distinguishing it from an actual scene image, while retaining
the authoritative missing/pending/unavailable label; the sample caption and that label SHALL share one
status badge, so the stage shows at most one status badge at a time, and the badge SHALL NOT show a
raw placeholder kind code or an error-styled (dashed seal-red) frame. Samples SHALL NOT enter the art catalog or
change its status, and SHALL disappear when an actual or labelled prior scene renders.
Decorative portrait samples SHALL likewise be labelled separately from the current subject;
an available committed player-roster portrait takes precedence, and a load failure returns to
an explicitly labelled sample instead of attributing that sample to the player.
While the combat hold of "Surface visibility is gated by the committed game mode" is playing, the
backdrop MAY keep presenting the combat gradient stage (and the combat sample wash where a degraded
scene carries one), yet it SHALL NOT hold the pre-terminal scene's identity: a newer committed scene
image, pending state, or truthful degradation follows the rules above beneath the held decoration at
its commit, and the scene caption row names the newly committed scene, never the held combat one.
The backdrop SHALL NOT present an invented image as authoritative and
SHALL NOT present a stale image as current. The scene label, its alternative text, and any truthful
placeholder label SHALL be rendered as text outside the bitmap, so no required information exists only
inside an image. The gradient stage SHALL differ per mode (exploration, dialogue, combat) and SHALL
carry an inset vignette. The backdrop's image SHALL be cover-cropped to the stage box (from the top
band's lower edge to the bottom band's upper edge), so no part of the scene the crop keeps is hidden
behind the bottom band.

The backdrop's own floating caption elements (the status badge, the `目前場景圖片生成中`
pending notice, the scene label and alternative-text captions, and the full-view control) SHALL be
positioned so that none of them overlaps the bottom band, the action dock's, or the command line's
rendered content, at 1451x790 and at every larger viewport up to the chrome cap — extending the sibling stage requirement's
general anchor non-overlap invariant to these backdrop-internal captions, which sit outside the named
stage anchors but are absolutely positioned within the same full-bleed stage.
The scene caption row SHALL render only while an actual scene image is on the stage — a `done` scene
image, or the dimmed prior image of a pending scene — and SHALL NOT render for a missing, failed,
invalid, or unavailable scene, whose truthful label the status badge already states. Within the row the
alternative text SHALL be omitted when it is identical to the scene label, and the full-view control
SHALL be an icon button whose accessible name is `開啟場景全圖`.
The scene label, the alternative text, the pending notice, and the full-view control SHALL render as
one caption row on the stage box's lower edge, standing just above the command-line row docked on the
band's top edge, and centred in the open stage between the `actor-left` and `actor-right` anchor boxes —
or, while the foe line-up stands in combat, between the `actor-left` anchor box and the line-up's
leftmost foe, until a leaving line-up has faded — so no portrait anchor (which paints above the
backdrop), no foe, and no other HUD surface covers any part of it in any mode. The alternative text SHALL
give way before the scene label when the row is too narrow for both. The row SHALL stay one line tall: a label or alternative text longer than the row SHALL end
in an ellipsis on screen while its full text stays in the DOM, and the dialogue choice list SHALL stop
above the row.

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped to the stage box behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

#### Scenario: A missing scene degrades to the mode gradient
- **WHEN** the committed art panel carries a missing, failed, or invalid scene
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as text, and no image element carries a URL

#### Scenario: A degraded scene shows one status badge and no caption row
- **WHEN** the `art` panel is unavailable, or the scene is missing, and the bundled sample wash renders
- **THEN** exactly one status badge renders, stating both the sample caption and the truthful
  placeholder label, without a raw kind code, and no scene caption row, scene label, alternative text,
  or full-view control renders

#### Scenario: An alternative text equal to the label is not repeated
- **WHEN** a `done` scene's alternative text is identical to its label
- **THEN** the caption row renders the label once and no alternative-text element

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
- **WHEN** the `art` panel is unavailable or the scene is missing/failed, so the status badge
  renders
- **THEN** the status badge's rendered bounding box intersects neither the bottom band's nor the
  command line's rendered bounding box at 1451x790 or at any larger viewport up to the chrome cap

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1451x790 and at every larger viewport up to the chrome cap

#### Scenario: The scene caption stands on the stage floor between the portraits
- **WHEN** the scene label, alternative text, and full-view control render with the command line expanded
  at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** their caption row's bottom edge lies at most 16px above the command-line row's top edge, the
  row is horizontally centred between the `actor-left` and `actor-right` anchor boxes (±1.5px), and each
  part lies between those boxes with no other surface painted over it

#### Scenario: The scene caption clears the foe line-up
- **WHEN** a combat snapshot commits one, two, and three active foes with the command line expanded at
  1451x790 and at every larger viewport up to the chrome cap
- **THEN** the caption row lies between the `actor-left` anchor box and the leftmost foe's box, horizontally
  centred between them (±1.5px), with no foe painted over any of its parts

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
This requirement carries the `place-card-relocation` and `vitals-bar-redesign` amendments; the party quickbar is removed with this change.
The surfaces placed in the stage's island anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The `vitals` anchor, at the
stage box's lower left, is the vitals dock that "The vitals dock stands at the stage's lower-left above the band"
defines: it carries the condition icon row and the vitals bars as one dock, and SHALL carry
neither a character head card nor a portrait catalog strip nor a party quickbar. The `map` anchor SHALL carry, in this order, the
place card, the
minimap island, the objective line, the combat participant frame while it is mounted, and the title
ballot menu while it is mounted, each present only while its own requirement renders it; no reference
panel and no portrait anchor content SHALL be placed in either island anchor. The stack's rendered height SHALL fit within its anchor at the 1451x790 reference viewport and at 2560x1440 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the condition icon row and the vitals bars render as the lower-left dock's two surfaces in that order, the dock carries the translucent blurred panel chrome, no head card, place card, portrait catalog strip, or party quickbar is rendered, and the party appears only as standing portraits in the `actor-left` anchor

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at the 1451x790 reference viewport with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the place card's rendered box does not intersect the minimap island below it, and neither stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the place card, the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders the place card above the participant frame there with no minimap and no objective line

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map`
anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the
player's side and the opposing side using the committed participants' server-authored team values, in
the presenter's order. Each participant SHALL render its session token, its display name, its current
and maximum hit points as numerals — the current value being, while a combat round plays, the displayed
value that `webclient-combat-menu` "A combat round plays beat by beat" defines — and its state; a non-active state SHALL be conveyed by an explicit
text marker in addition to any colour. The frame SHALL NOT invent a field the participant descriptor
does not carry. The frame SHALL list every participant of both sides, including the foes the foe line-up
does not stand on the stage, and it SHALL remain the only surface that states participant tokens, hit
points, and states: the foe line-up in `actor-right` carries decorative portraits, names, non-colour
acting/target cues and hit-point gauges without numerals. A display name longer than the frame's width SHALL end in an
ellipsis on screen while its full text stays in the DOM, and the frame's rows SHALL be compact enough
that a frame of six participants ends above the foe line-up's gauges at 1451x790 and 2560x1440; at both acceptance sizes its visible content SHALL NOT cover a standing foe head.

Each participant's portrait SHALL be resolved only by looking its server-authored portrait reference
up in the committed art panel's portrait catalog: a resolvable entry SHALL render that entry, an
entry that resolves to a placeholder SHALL render a compact initial with its truthful availability state accessible outside the bitmap; an entry whose image URL fails to load SHALL render a compact initial with a localized load-failure state accessible outside the bitmap; and a null reference or an
unavailable art panel SHALL render no portrait at all. The client SHALL NOT construct a portrait
subject key or URL. While the participant frame is mounted, the frame and the stage actors SHALL be the
only presenters of the portrait catalog, so no separate portrait strip is rendered alongside them.

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

#### Scenario: A catalog portrait fails to load
- **WHEN** a catalog entry has an image URL that fails to load
- **THEN** the frame replaces the bitmap with the participant's initial and an accessible `肖像載入失敗` state, without changing its token or numeric HP

#### Scenario: The frame does not compete for focus
- **WHEN** the participant frame is mounted during combat
- **THEN** it is not reachable by sequential keyboard navigation, the dock's active row container remains the surface's only listbox, and no portrait strip is rendered outside the frame and the stage actors

#### Scenario: The frame sits in the map anchor, not on a portrait anchor
- **WHEN** a combat session commits participants at 1451x790 and 2560x1440
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds only the foe line-up's stage actors and gauges and no frame row, token, or hit-point numeral, and the frame's visible box intersects neither the bottom band nor the command line

### Requirement: Foes stand opposite the player during combat
While the committed mode is `combat`, the `actor-right` anchor SHALL carry a foe line-up: one stage actor
for each committed combat participant whose team is the opposing side and whose state is active, in the
presenter's order, at most three. Foes beyond the third SHALL NOT stand on the stage; the participant
frame lists them, and no "+N" count is drawn. Party members other than the player SHALL NOT stand on the
stage; the player alone stands in `actor-left`. When no foe is active the line-up SHALL render nothing.

The line-up SHALL be a depth-staged row that grows leftward. The first foe SHALL stand in front, nearest
the stage's right edge, and each later foe SHALL stand behind the one before it: further toward the
stage's centre, overlapping that foe and drawn behind it, smaller, and standing a little higher (up-stage)
than it. With one, two, or three foes shown, the foes' heights SHALL be, front to back, 100%; 90% and 78%;
or 80%, 70%, and 61% of the player's stage actor's height, and every later foe SHALL show 46% of its width
past the foe in front of it. The front foe SHALL stand on the band's upper edge, and each foe behind SHALL
stand 3.5% of the portrait anchor's height higher than the one in front of it. The row's right inset SHALL
be the portrait anchor's right inset, grown just enough that the front foe's horizontal centre (its face)
lies at least 24px left of the participant frame's column, within the `map` anchor in combat.
At 1451x790 and at every larger viewport up to the chrome cap, no foe's stage actor SHALL cross the stage's vertical centre line or
intersect the player's stage actor.

Each foe's stage actor SHALL expose that participant's portrait reference as a data attribute for tests
and for the beat presentation. Each foe SHALL show its display name above its decorative hit-point gauge
and distinguish acting or focused-target presentation with a non-colour cue. Names SHALL ellipsize within
their plate while retaining full DOM text. Each gauge SHALL be a slim track centred
under the figure on the scene caption's baseline, above the command-line row, filled to that foe's current
hit points (the displayed value while a combat round plays) over its maximum, with a trailing bar that follows a drop after the vitals' trail delay so
the damage shows as a gap. The line-up is decorative art: it SHALL be hidden from assistive technology,
SHALL carry no focusable element, SHALL NOT intercept pointer events, and SHALL NOT state tokens, hit-point
numerals, or participant states, which remain the participant frame's.

While a combat round plays by itself, the line-up SHALL stand the foes that were active before the round,
in the presenter's order, and a foe SHALL leave it only when its own defeat beat plays; when the round
ends, by itself or because the player ended it, the line-up SHALL stand the committed active foes.

A live change of the committed mode into `combat` SHALL bring the line-up in: after half the flash's
duration it SHALL fade in over the actor duration of the client's motion level (350ms at `full`) while
each foe slides in from the right, the front foe furthest. A live change out of `combat` SHALL fade it out
while the foes drift a step to the right. Within combat, a foe that leaves the active set SHALL fade out
where it stands, a foe that joins SHALL slide and fade in, and the remaining foes SHALL glide to their new
places and sizes. Every leaving copy SHALL be out of reach as "A leaving element is out of reach while it
animates out" requires. Mounting the client in combat, a reload, and a reconnect SHALL play no entrance.
At `reduced` the line-up SHALL only fade, within 150ms, and nothing in it SHALL move or glide; at `off`
every change SHALL render its final state in the commit's frame. No change SHALL scroll the stage or any
element that contains it.

#### Scenario: One foe stands opposite the player
- **WHEN** a combat snapshot commits one active foe with a catalog portrait at 1451x790
- **THEN** `actor-right` renders one foe stage actor with that image, its bottom edge on the band's top
  edge, its height equal to the player's stage actor's height (±1px), its horizontal centre at least 24px
  left of the participant frame's left edge, a gauge and name under it, and no focusable element

#### Scenario: Three foes stand in depth toward the centre
- **WHEN** a combat snapshot commits three active foes at 1451x790 and at 2560x1440
- **THEN** three foe stage actors render in presenter order at 80%, 70%, and 61% of the player's height
  (±1px), each later one further left, higher, and behind the one before it, and none crosses the stage's
  centre line or intersects the player's stage actor

#### Scenario: Foes beyond three stay in the participant frame
- **WHEN** a combat snapshot commits five active foes
- **THEN** the line-up shows the first three in presenter order, and the participant frame lists all five
  foes with their tokens and hit points

#### Scenario: The gauge follows the committed hit points
- **WHEN** a committed update lowers an active foe's `hp_current`
- **THEN** that foe's gauge fill shrinks to the new ratio, its trailing bar follows after the trail delay,
  and neither the gauge nor the line-up states an HP numeral

#### Scenario: Only active foes stand on the stage
- **WHEN** a committed update that carries no playable round changes the first of two foes to defeated,
  and later a playing round defeats the other foe
- **THEN** the first foe's stage actor fades out at the commit and is inert while it leaves, the other
  foe glides to the front place, the second foe stays on the stage until its defeat beat plays, and the
  participant frame still lists both defeated foes with their text markers

#### Scenario: A missing portrait shows the truthful placeholder
- **WHEN** an active foe's portrait reference is `null`, and another's names no catalog entry
- **THEN** both foes' stage actors show the display name's initial and the display name, and neither
  renders an image or a constructed URL

#### Scenario: Entering combat brings the foes in
- **WHEN** the effective level is `full` and a committed revision changes the mode from exploration to
  combat with two active foes
- **THEN** the line-up fades in over 350ms while its foes slide in from the right, and after a later change
  back to exploration it fades out and is inert while it leaves, and at no frame does any stage ancestor
  scroll horizontally

#### Scenario: A reload in combat plays no entrance
- **WHEN** the client reloads or reconnects while the committed mode is combat
- **THEN** the line-up renders in its final state with no running transition

#### Scenario: Reduced and off keep the foes still
- **WHEN** the effective level is `reduced`, and later `off`, and the mode enters and leaves combat
- **THEN** at `reduced` the line-up only fades within 150ms and never moves, and at `off` it is present
  or absent in the commit's frame

### Requirement: The command line is a collapsible row docked on the message region's top edge
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field with its send control, a hint
cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only
writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the
top navigation bar's tool group. The `command-line` anchor SHALL be one row 44px tall docked to the top
edge of the bottom band's message region: its lower edge SHALL coincide with the band's upper edge, it
SHALL extend from the left HUD island column's right edge to the right edge of the band's left two
thirds in every mode — so in dialogue mode, where the message region spans the whole band, it stops
short of the dialogue host's portrait — and it SHALL overlay the lowest strip of the stage box, never
the band and never the message text.

The command line SHALL be collapsed by default. It SHALL start collapsed on every mount of the shell,
and its expanded state SHALL be client-local and never persisted, so no stored presentation state can
open it or keep it open. While collapsed, the row SHALL be hidden with `display:none`, so the bar and
its input field leave the layout, the accessibility tree, and the tab order, while the input field stays
in the DOM with its preserved identifier and keeps any unsent draft and history-walk state. The
message region SHALL carry, at its bottom-right corner, a labelled ⌨ toggle control that reports the
row's state through `aria-expanded` and names the row through `aria-controls`. The toggle SHALL be
rendered in every mode that renders the message region, SHALL NOT cover the message text (the text's
scroll region SHALL keep its last line clear of the toggle), and SHALL NOT be affected by the committed
narrative, the dialogue choice list, or the dock frame.

The command line SHALL expand, and focus SHALL move into its input field only after the row is
rendered, on exactly three paths: `/` pressed while no editable control is focused, activation of the ⌨
toggle while the row is collapsed, and the free-form dialogue borrow. It SHALL collapse, with focus
moved to the current mode's focus home (the action dock, or in dialogue mode the dialogue choice list
while it is rendered and the message window's page surface otherwise) before the row is hidden, on exactly two paths: Escape in the input field, and
a send the field accepts (the field clears). Activating the ⌨ toggle while the row is expanded SHALL
collapse it and leave focus on the toggle. A send the field rejects — offline, mutations locked, a
mutation in flight, or, for a borrowed free-form send, a presentation phase other than active — SHALL
leave the row expanded with the typed text and focus in the field. Losing
focus by any other means (a pointer activation elsewhere, a drawer or overlay opening) SHALL NOT
collapse the row.

The expanded bar SHALL NOT overlap the action dock, the narrative caption, the bottom band, or any HUD
island anchor at 1451x790 or at any larger viewport up to the chrome cap. When horizontal space is insufficient, the hint
cluster SHALL be dropped first; the input field, its send control, and the history controls SHALL
never be dropped. (The command line and its toggle are absent from the layout in creation mode, per the
visibility matrix.)

#### Scenario: The field is one action away
- **WHEN** the shell mounts in exploration mode
- **THEN** the command-line row is hidden with `display:none`, the input field is present in the DOM but outside the tab order, the ⌨ toggle is rendered at the message region's bottom-right with `aria-expanded="false"`, and pressing `/` or activating the toggle once renders the row and puts focus in the input field

#### Scenario: The expanded row keeps its geometry at the minimum viewport
- **WHEN** the command line is expanded at the 1451x790 reference viewport and at 2560x1440, in exploration mode and in dialogue mode
- **THEN** the row is 44px tall (±1px), its lower edge sits on the bottom band's upper edge, its horizontal extent runs from the left HUD column's right edge to the right edge of the band's left two thirds, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, its send control, and the history controls are all rendered

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
- **WHEN** the command line is collapsed and the player activates the dialogue choice list's `⌨ 自由對話` row
- **THEN** the row expands, focus moves into the input field, and no action is dispatched until the player sends

#### Scenario: No opener or chip is rendered in the bar
- **WHEN** the bar renders expanded in exploration, combat, or dialogue mode
- **THEN** no quick-word chip, letter badge, chip cluster, or overlay or drawer opener (技能系譜, 圖鑑, 稱號冊, 設定, 說明, 角色肖像圖庫) is present in the bar

#### Scenario: The expanded state is never restored from storage
- **WHEN** the player expands the command line and reloads the page
- **THEN** the reloaded shell renders the command line collapsed

#### Scenario: Escape in dialogue returns to the message window
- **WHEN** the committed mode is dialogue, the player expands the command line with `/`, and presses Escape
- **THEN** nothing is sent, the row is hidden, and focus is on the dialogue's focus home — the choice list while it is shown, else the message window's page surface — never on the hidden action dock or the document body

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the
whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed
elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation
mode and for every frame: no frame (the scene overview, a target's verb popover, the waiting frame, the
combat frames, the skill master-detail, the destructive confirmation, or an empty pane host) SHALL
widen, heighten, shorten, or move it, and
no surface outside the band SHALL be positioned from the frame the dock currently carries. In dialogue
mode the command region is collapsed and the dock SHALL be hidden with `display:none` together with it,
as "The command region collapses in dialogue mode and the message window spans the band" states; it
SHALL NOT be rendered anywhere else in that mode. The
content column SHALL be laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar
in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the
bottom — around one remaining region that holds the current frame's rows or chips; that region SHALL
be the surface's only scrolling area, so no dock content is ever pushed outside the command region.
A target's verb popover SHALL render as a card laid over that region's visible box, inside the command
region, and SHALL scroll inside its own card when its rows exceed it. A frame whose content
does not fit the region's width SHALL wrap or collapse its own columns inside the region, never
overflow it horizontally. The panel SHALL be the same single `#action-dock` element in every mode,
carrying its existing tab index, its `data-mode` attribute and its role as the documented focus home
of every mode except dialogue, and SHALL NOT be remounted when the mode changes, including a change
into or out of dialogue.

The command region SHALL use the current charcoal-and-gold presentation, and the band that contains
it SHALL paint the reference's band chrome. Selected actions remain distinguishable by text and shape
as well as their gold or warm-red emphasis.

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1451x790 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb popover's card lies inside the command region

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the legend strip) stays fixed, and no row or chip is rendered outside the command region

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

### Requirement: A fixed-column dock pane stays inside the command region
When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count
SHALL govern only which cell each row occupies. This requirement SHALL NOT prescribe how wide a column
or row renders: each pane form (the combat skill list, the target tokens, the scale chips) lays out its
rows with its own styles, and whether a form fills the pane's width or leaves width empty is a visual
decision of that form. Whatever the form, every row SHALL render inside the pane's box without
horizontal overflow: when the pane's available width is narrower than the rows' natural width, the rows
SHALL wrap or compress, and long content SHALL wrap within its row. Changing a row's rendered width
SHALL NOT change which row occupies which cell. The scene overview is not a fixed-column pane (its chips
wrap by width under the section geometry the exploration dock requirement defines).

#### Scenario: A narrow command region keeps every row inside the pane
- **WHEN** a combat skill, target, or scale pane renders in the command region at the 1451x790 reference viewport
- **THEN** every row lies inside the pane's right edge, the pane shows no horizontal overflow, and a long label wraps within its row

#### Scenario: Rendered width never changes the keyboard cell mapping
- **WHEN** the player presses ArrowRight in a pane whose keyboard geometry fixes two columns
- **THEN** focus reaches the row that the fixed column count places in the second column, whatever width each row renders at

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed and the
message region SHALL span the band's whole width at the band's fixed height from the commit's frame. The
collapsed region and the action dock inside it SHALL leave the accessibility tree, the tab order, and
pointer hit-testing from the commit's frame; the region SHALL then slide out to the right and fade over
the panel duration of the client's motion level, drawn over the widened message region, and SHALL be
`visibility: hidden` once that slide ends, so it contributes nothing visible. Leaving dialogue SHALL
bring the region back into reach in the commit's frame and slide it back in from the right. At
`reduced` the region only fades, within 150ms, and at `off` it hides and returns in the commit's
frame. The dock SHALL stay the same mounted `#action-dock` element, its router SHALL keep the exploration scene overview as its only frame (the reset on entering
dialogue that `webclient-exploration-menu` defines), and leaving dialogue SHALL show that overview
again with no remount. The dialogue SHALL NOT present any dock frame, and no exploration affordance
SHALL be removed from the committed `exploration` panel: movement stays reachable through the minimap
and the conversation's own controls.

In dialogue mode the shell's focus home SHALL be the dialogue choice list while it is rendered, and
otherwise the message window's page surface. Every path that returns
focus to the focus home — the command line's Escape and accepted send, the mode-change rescue, and the
return after a completed or rejected action — SHALL land there, never on the hidden dock and never on
the document body. On entering dialogue, focus held inside the command region SHALL move to the
message window's page surface before the region is hidden. On leaving dialogue for exploration, focus
held inside the message region, inside the `choices` anchor, or on the document body SHALL move to the
action dock once the region is rendered again.

While the mode is `dialogue`, the keyboard router SHALL claim only `/` (the command-line opener); every
other key SHALL be unclaimed by the dock router, so no key moves the hidden dock's focus, pushes or pops
a frame, or activates a hidden entry. The keys the dialogue choice list handles never reach the router,
and Enter and Space on the focused page surface keep their reading meaning.

#### Scenario: Entering dialogue collapses the command region
- **WHEN** the player activates 交談 in a host's verb popover at 1451x790 and the commit makes the mode `dialogue`
- **THEN** from the commit's frame the band's command region and the `#action-dock` element are out of the accessibility tree and the tab order, the message region spans the band's whole width at 220px (±1px) height, the region is `visibility: hidden` once its slide ends, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

#### Scenario: Leaving dialogue restores the overview without a remount
- **WHEN** the player activates the exit row and the commit returns the mode to `exploration`
- **THEN** the same `#action-dock` element is back in the accessibility tree in the commit's frame, slides back into the command region at the scene overview with no popover open, and focus is on the action dock

#### Scenario: Keys never drive the hidden dock
- **WHEN** the mode is dialogue, focus is on the document body, and the player presses ArrowRight, Enter, and Escape
- **THEN** none of the keys is claimed by the dock router, the router's focused key and depth are unchanged, and no `ui_action` is emitted

#### Scenario: Slash still opens the command line in dialogue
- **WHEN** the mode is dialogue, no editable control is focused, and the player presses `/`
- **THEN** the command line expands and focus moves into its input field with no literal `/` inserted

#### Scenario: Movement stays reachable during a conversation
- **WHEN** a dialogue session is live and the player activates an adjacent minimap node
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the session through the existing seam, the committed mode returns to `exploration`, and the command region renders the new room's overview

### Requirement: Mode changes transition at the motion level
The stage SHALL animate live mode changes, taking every duration, delay, and distance from the client's
motion tokens, so they follow the effective motion level of "The motion level is a client-local
preference that governs every client animation":
- **Exploration → dialogue:** the command region slides out to the right over the panel duration (250ms
  at `full`) while the message window spans the band from the commit's frame. The dialogue host's stage
  actor slides in from the right and fades in over the actor duration (350ms at `full`). The name plate
  fades in. The greeting pages and types as `webclient-input-narrative` defines.
- **Dialogue → exploration:** the reverse. The host's stage actor slides out to the right and fades, the
  name plate fades out, the message window returns to two thirds of the band in the commit's frame, and
  the command region slides back in.
- **Exploration → combat:** a white flash lasting the flash duration (120ms at `full`) plays once over
  the stage and under every island, the combat veil fades in, and the command region's content flips
  to the combat root.
- **Combat → exploration:** the veil fades out and the command region's content flips back. No flash
  plays.
- **Dialogue choices:** each row of the dialogue choice list fades in and rises into place, delayed by
  the stagger step (40ms at `full`) times its position, and the list's card fades in. Rows swapped in by
  `↦ 移動…` or by its return stagger the same way.

Only a live mode change animates: mounting the client, reconnecting, and a resync that commits the same
mode SHALL play none of these transitions. Every leaving element SHALL be out of reach as "A leaving
element is out of reach while it animates out" requires. No transition SHALL delay a committed value or
the player's input beyond its own duration: the choice list takes focus and handles keys and pointer from
its first frame, and the dock is focusable from the first frame of its return. A mode change SHALL NOT
scroll the stage or any element that contains it: a surface that slides past the stage's edge SHALL be
clipped without widening any ancestor's scrollable area, and no focus move during a mode change SHALL
scroll an ancestor toward its target, so the stage never shifts sideways. The flash, the veil, and
the flip SHALL be decorative, absent from the accessibility tree, and SHALL never intercept a pointer.
At `reduced`, the slides, the flip's rotation, and the rise SHALL NOT move anything, the fades SHALL last
at most 150ms, the flash SHALL NOT be visible, and the stagger SHALL be zero. At `off`, every mode change
SHALL render its final state in the commit's frame.

#### Scenario: Entering dialogue slides the panel out and the host in
- **WHEN** the effective level is `full` at 1451x790 and the player opens a conversation
- **THEN** in the commit's frame the message region is the band's full width and the command region is
  inert, the command region's computed transition runs 250ms toward a translated, transparent state and
  ends `visibility: hidden`, the host's stage actor enters from the right with a 350ms fade, and the name
  plate fades in

#### Scenario: Leaving dialogue reverses the transition
- **WHEN** the effective level is `full` and the player activates `✕ 結束對話`
- **THEN** the host's stage actor leaves toward the right and is inert while it leaves, the message
  region returns to two thirds of the band in the commit's frame, the command region is in reach at
  once and slides back in, and focus is on the action dock

#### Scenario: No stage ancestor scrolls horizontally during a mode change
- **WHEN** the effective level is `full` and focus is on the action dock while the player enters and
  leaves dialogue, then enters and leaves combat
- **THEN** in every frame of every transition the stage, each element that contains it, and the
  document keep a horizontal scroll offset of zero and a scrollable width no larger than their visible
  width, and the dock takes focus on the return without moving the stage

#### Scenario: Entering combat flashes, fades the veil, and flips the panel
- **WHEN** the effective level is `full` and a committed revision changes the mode from exploration to
  combat
- **THEN** the flash layer plays one 120ms animation, the combat veil's opacity transitions from zero,
  the command region's content plays the flip toward the combat root, and none of them is in the
  accessibility tree or receives a click

#### Scenario: Leaving combat plays no flash
- **WHEN** the effective level is `full` and the mode changes from combat to exploration
- **THEN** the veil fades out and the command region's content flips back, and the flash layer plays
  no animation

#### Scenario: Choice rows stagger in without delaying input
- **WHEN** the effective level is `full` and the dialogue choice list appears with five rows
- **THEN** row N's entrance is delayed by 40ms × N, the list holds focus in its first frame, and a digit
  pressed before the last row has finished entering activates that row

#### Scenario: A reconnect replays nothing
- **WHEN** the client reconnects while the committed mode is combat or dialogue
- **THEN** no flash, flip, slide, or stagger plays, and every surface renders its final state

#### Scenario: Reduced keeps short fades and drops every movement
- **WHEN** the effective level is `reduced` and the player enters and leaves dialogue, then enters combat
- **THEN** the command region, the host, the name plate, the veil, and the choice rows only fade, each
  within 150ms, no slide, rotation, or rise moves anything, no flash is visible, and the rows appear
  together

#### Scenario: Off renders every mode change at once
- **WHEN** the effective level is `off` and the mode changes into and out of dialogue and combat
- **THEN** in the commit's frame each surface holds its final state: the command region hidden or
  shown, the host present or absent, the veil at its final opacity, the flash invisible, and every
  choice row fully shown

### Requirement: Standing portraits retain contours and truthful grounded fallbacks
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Missing artwork SHALL use a standing silhouette with the subject name and truthful availability state, without inventing generation or a URL. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at the 1451x790 reference viewport
- **THEN** the silhouette identity and state are not occluded by vitals or the command line and all HUD controls remain reachable

### Requirement: The vitals dock stands at the stage's lower-left above the band
The stage SHALL render the vitals surfaces — the condition icon row and the vitals bars — as one bottom-anchored dock in the `vitals` anchor: a left-gutter column standing on the bottom band's upper edge, inset from the stage's left edge by the stage gutter, a quarter of the viewport's width wide (a viewport-relative width, not multiplied by the chrome factor), and at whatever compact height its content takes. The dock SHALL NOT be top-anchored and SHALL NOT claim the stage's upper-left corner: at the top of the left column the stage shows only the standing portrait line. The condition icon row SHALL be the dock's topmost content, directly above the bars. The dock SHALL be bounded above the band and SHALL scroll internally rather than grow past the band's edge. The dock MAY overlap the lowest strip of the `actor-left` standing portraits (the party line's feet); the portraits keep their full standing height and the dock paints above them. The dock SHALL NOT read as a rectangular box: its ground is the shared panel ink with the backdrop blur, feathered out towards its right and top edges so the scene reads through them, and it is mounted on a hairline brass spine down its left side capped by the band's lozenge ornament, with a hairline brass crown fading out along its top; it carries no full border and no square corners. Every island chrome the dock carries SHALL come from the shared design tokens. The command-line row docked on the same band edge SHALL begin past the dock's right edge, so the two never intersect. Until `companion-portrait-lineup` removes it, the interim party quickbar island stands in the `vitals` anchor between the dock and the band.

#### Scenario: The dock stands on the band's edge
- **WHEN** the shell renders in exploration mode with the vitals dock visible at 1451x790
- **THEN** the `vitals` anchor's bottom edge coincides with the bottom band's top edge (the dock's own bottom edge does too whenever no interim party quickbar stands below it), the dock's left edge sits at the stage's left gutter and its width is a quarter of the viewport's width (±1.5px), its rendered height is the compact height of the icon row, the readout, and the three lines, and the stage's upper-left corner holds no vitals surface

#### Scenario: The dock covers only the portraits' lowest strip
- **WHEN** the dock is visible and the player's standing portrait renders at 1451x790 and at 2560x1440
- **THEN** the overlap of the two rendered boxes reaches no higher than the portrait's lowest quarter, the portrait's face and torso are fully visible, and neither box moves the other

#### Scenario: The dock stays bounded at the minimum viewport
- **WHEN** the shell renders at 1451x790 with the dock visible and conditions overflowing the row
- **THEN** the dock's box stays inside the left gutter between the top band and the band's top edge, its content scrolls within that bound, and it intersects no other interactive anchor's content

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row. Each companion portrait SHALL resolve from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved. Each figure SHALL reuse the existing StageActor rendering and remain non-interactive decorative art: no focusable element, no pointer events.

Every figure, including the controlled character, SHALL have the same full anchor size and ground line: no progressively smaller scale, lift ramp or depth dimming. Horizontal overlap SHALL compress as necessary to keep the row inside the stage's left half at 1451x790, 1741x948 and 2560x1440, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half. In dialogue the group SHALL compress overlap to clear the choice list without resizing figures. Zero companions SHALL render the existing solo portrait at its standard anchor position. The anchor SHALL have `overflow: visible`; the vitals dock MAY cover the lowest strip of feet, never face or torso.

The lineup SHALL be visible in exploration, combat and dialogue, hidden in creation. Companions SHALL use the existing StageActor listener dim unless their committed dialogue host identity is the active host speaker in dialogue mode. That speaking companion SHALL temporarily receive z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes. Speaking focus SHALL change only dim and z, never position, lift or size, and SHALL remain correct at off/reduced motion. The controlled figure SHALL retain its existing speaking and beat behavior. No figure box SHALL cross the stage's horizontal centre; the foe lineup is unchanged.

#### Scenario: A two-companion party renders a three-figure group
- **WHEN** the committed `party` panel carries two resolved-portrait slots at 1451x790 in exploration mode
- **THEN** three equally sized figures share a ground line, the player is rightmost with highest baseline z, the companions overlap leftward in party order, no box crosses the horizontal centre and no figure is focusable

#### Scenario: A zero-companion party renders only the player
- **WHEN** the committed `party` panel is available with an empty `slots` list
- **THEN** the `actor-left` anchor renders the player's solo portrait at the standard standing position, byte-stable with the solo layout before this change

#### Scenario: A companion with no portrait shows the initial letter
- **WHEN** a party slot carries `portrait_ref: null` for display name `蕾娜`
- **THEN** that figure renders the initial `蕾` through the stage actor's truthful placeholder, with no invented image or constructed URL

#### Scenario: The full party fits the left half at every viewport
- **WHEN** the committed party carries four slots and the shell renders at 1451x790 and at 2560x1440
- **THEN** all five equally sized figures render with compressed horizontal overlap inside the left half; in exploration/combat each face is at least partially visible, and in dialogue a speaking companion is brought above the overlapping listeners without moving its slot

#### Scenario: A speaking companion rises temporarily without moving
- **WHEN** the committed dialogue host is a companion and the existing speaker signal changes from player to host and back
- **THEN** that companion changes from dim baseline z to lit highest z and back, preserving its exact geometry; possession swaps, lineup changes and off motion cannot retain stale speaking z

#### Scenario: The companion line and the foe line-up do not overlap
- **WHEN** the committed mode is combat with two companions and three active foes at 1451x790
- **THEN** no companion figure's rendered box intersects any foe figure's rendered box

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
- **WHEN** the stage renders at 1451x790 and 2560x1440 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's
