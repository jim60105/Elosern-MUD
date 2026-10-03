## MODIFIED Requirements

### Requirement: The place card names the current location and the world time
This requirement carries the `place-card-relocation` amendment; the visible-mode set below narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells.
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's
top-right corner directly below the top band and directly above the minimap island, while the
committed mode is exploration or combat, and SHALL NOT render it in
dialogue or creation mode. The card SHALL state the current location as its heading and the world date/time
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
numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 12px chrome
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
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode and in dialogue mode the place card is not rendered and holds no tab stop

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the heading is set one
  step below the display size the stage's island chrome uses at `--text-lg`, the time line's numerals
  are tabular lining figures in the numeral face, and the card keeps its fixed height

### Requirement: Surface visibility is gated by the committed game mode
This requirement carries the amendments from `place-card-relocation` (place card in the `map` anchor), `vitals-bar-redesign` (the vitals dock at the lower left), and `companion-portrait-lineup` (the party quickbar row removed, the portrait row naming the companion line). Dialogue mode now hides the cockpit and navigation surfaces: the place card, the minimap island, and the vitals dock are hidden while the committed mode is `dialogue`.
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
| place card (location, world time; `map` anchor, above the minimap) | visible | visible | **hidden** | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | **hidden** | hidden |
| minimap island | visible | **hidden** | **hidden** | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| controlled character and companion standing portraits (`actor-left`) | visible | visible | visible (listeners dimmed while the host speaks; the party line stays) | hidden |
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
The place card's visibility SHALL follow this matrix exactly: it is shown in exploration and combat,
hidden in dialogue and creation; hiding the `map` anchor in dialogue hides the place card with the
minimap, and the card's own visibility rule SHALL NOT claim dialogue after this change.
The vitals dock SHALL be hidden in dialogue mode through the mode gate regardless of its data rule:
a committed revision while dialogue holds — a vital dropping below its maximum, a new condition —
SHALL NOT reveal the dock, and the dock's reveal transition SHALL NOT play until the mode leaves
dialogue. The dialogue's attention surface is the message window and the name plate; the dock returns
through its normal reveal when the mode commits back to exploration or combat. The low-HP stage
vignette is not mode-gated and keeps rendering in dialogue, so a critical HP state is still conveyed
through the stage frame.
Each playing mode has one focus home: the action dock in exploration, combat, and creation mode, and
the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode
and the message window spans the band" defines. When a mode change, a committed revision that turns a
surface's data rule false, or a collapse of the command line hides the surface that currently holds
focus, the shell SHALL move focus to the focus home of the mode being entered or kept before the
surface is removed, using the existing focus-restore path. A mode change into creation SHALL also
collapse the command line, so leaving creation never reveals an expanded row.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the participant frame renders in the `map` anchor below the still-visible place card and the foe line-up renders in `actor-right`

#### Scenario: The place card stays visible through combat
- **WHEN** the committed mode changes from exploration to combat with a committed location and world time
- **THEN** the place card remains rendered above the participant frame, and returns to standing above the minimap island when the mode returns to exploration

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
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player and companion standing portraits, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the message window spans the whole band with the host's name plate, the dialogue host's standing portrait is rendered in `actor-right`, the player's front figure and the companion standing portraits remain rendered in `actor-left` dimmed as listeners, the command-line toggle and the log control remain rendered, the command line keeps its expanded or collapsed state, the action dock is out of the accessibility tree and the tab order together with the band's command region from the commit and is `visibility: hidden` once the region's slide ends, and the `#action-dock` element is not removed from the document

#### Scenario: Dialogue mode hides the cockpit and navigation islands
- **WHEN** the committed mode changes from exploration to dialogue with a committed location, a committed `local_map` panel, and a vital below its maximum
- **THEN** the place card, the minimap island, the objective line, and the vitals dock are absent from the accessibility tree and the tab order, and once each surface's exit transition has finished it is `display:none`

#### Scenario: A vital change during dialogue does not reveal the dock
- **WHEN** the committed mode is dialogue with the dock hidden and a committed revision lowers `hp` below its maximum
- **THEN** the vitals dock stays `display:none`, no reveal transition plays, and the numerals are not visible anywhere on the stage

#### Scenario: Returning from dialogue restores the hidden surfaces
- **WHEN** the committed mode changes from dialogue back to exploration with a vital below its maximum
- **THEN** the place card and the minimap island render again at the commit, and the vitals dock enters through its reveal transition because the vitals rule holds

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
