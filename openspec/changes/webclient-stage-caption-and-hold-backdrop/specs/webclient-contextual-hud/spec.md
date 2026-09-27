## MODIFIED Requirements

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The one exception is the band's command region in dialogue
mode, which animates out as "The command region collapses in dialogue mode and the message window spans
the band" defines: it leaves the accessibility tree, the tab order, and pointer hit-testing at the
commit, and is `visibility: hidden` once its slide ends. The second exception is the combat stage
hold: while a round whose publication already committed another mode still plays, as "Combat beats are
choreographed on the stage at the motion level" defines, the decorative combat veil and the foe line-up
MAY remain on the stage, outside the accessibility tree, the tab order, and pointer hit-testing, and the
scene backdrop SHALL keep presenting the combat stage (its combat gradient and, where a bundled sample
wash accompanies a degraded scene, the combat sample), until the round ends; every other surface
follows the committed mode at the commit. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait (`actor-left`) | visible | visible | visible (dimmed while the host speaks) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, at most three active foes) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage; the combat stage while a round that ended the fight still plays) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and
the message window, and the choice list, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
Each playing mode has one focus home: the action dock in exploration, combat, and creation mode, and
the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode
and the message window spans the band" defines. When a mode change, a committed revision that turns a
surface's data rule false, or a collapse of the command line hides the surface that currently holds
focus, the shell SHALL move focus to the focus home of the mode being entered or kept before the
surface is removed, using the existing focus-restore path. A mode change into creation SHALL also
collapse the command line, so leaving creation never reveals an expanded row.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the participant frame renders in the `map` anchor and the foe line-up renders in `actor-right`

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration, including by a round whose beats
  are still playing
- **THEN** the minimap island renders again with the committed `local_map` payload at the commit, and any
  held foe line-up or veil is inert and outside the accessibility tree

#### Scenario: A held round keeps the combat backdrop
- **WHEN** the committed art panel carries no usable scene image, a round that ends the fight by a flee
  commits mode `exploration` while its beats still play, and later the round ends
- **THEN** during the hold the scene backdrop keeps the combat gradient and the combat sample wash
  behind the held foe line-up and veil, and only when the hold ends does it return to the exploration
  stage, crossfading over the scene duration at `full` and switching in one frame at `off`

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including a scene-overview chip when the incoming mode is dialogue
- **THEN** focus is moved to the incoming mode's focus home before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the place card, message window, minimap, player standing portrait, command-line toggle, and log control all
  remain rendered, the dialogue host's standing portrait is rendered in `actor-right`, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock is out of the accessibility tree and the tab order together with the band's command region from the commit and is `visibility: hidden` once the region's slide ends, while the message window spans the whole band with the host's name plate, and the `#action-dock` element is not removed from the document

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
rendered content, at 1920x1080, 1440x900, and 1280x720 — extending the sibling stage requirement's
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
  command line's rendered bounding box at 1920x1080, 1440x900, or 1280x720

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1920x1080, 1440x900, and 1280x720

#### Scenario: The scene caption stands on the stage floor between the portraits
- **WHEN** the scene label, alternative text, and full-view control render with the command line expanded
  at 1920x1080, 1440x900, and 1280x720
- **THEN** their caption row's bottom edge lies at most 16px above the command-line row's top edge, the
  row is horizontally centred between the `actor-left` and `actor-right` anchor boxes (±1.5px), and each
  part lies between those boxes with no other surface painted over it

#### Scenario: The scene caption clears the foe line-up
- **WHEN** a combat snapshot commits one, two, and three active foes with the command line expanded at
  1920x1080, 1440x900, and 1280x720
- **THEN** the caption row lies between the `actor-left` anchor box and the leftmost foe's box, horizontally
  centred between them (±1.5px), with no foe painted over any of its parts

## ADDED Requirements

### Requirement: Held combat decoration never holds canonical scene identity
A terminal combat hold SHALL retain combat gradient, sample selection and veil only. It SHALL NOT freeze committed art identity or other canonical HUD state. Completion, skip, flush and epoch reset SHALL release decorative hold through the existing playback lifecycle.

#### Scenario: Terminal outcome changes scene
- **WHEN** a terminal round is playing while a newer committed art panel names another scene
- **THEN** the new scene follows the normal truthful image/pending rules beneath held combat decoration; the prior combat scene is not mislabelled current

#### Scenario: Playback is reset
- **WHEN** a held terminal round is skipped, flushed or reset on reconnect
- **THEN** combat decoration is released and no held foe/veil remains after the existing lifecycle clears it
