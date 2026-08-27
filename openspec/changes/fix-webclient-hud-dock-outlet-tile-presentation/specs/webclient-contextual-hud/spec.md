## MODIFIED Requirements

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
SHALL receive the pane's full available width. A disabled move row's server-authored explanation SHALL
remain reachable by assistive technology directly from the tile (an accessible association such as
`aria-describedby`), independent of whether any companion panel exists. The submitted move payload SHALL
be unchanged.

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
- **THEN** no detail aside or other side panel renders beside the outlet grid, and the row region occupies the pane's full available width

#### Scenario: A row renders only backed fields
- **WHEN** a look frame renders a present entity
- **THEN** the row shows the entity's display name with its kind as the sub-line, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's affordance frame
- **THEN** the pane renders a head naming that target above the target's server-authored affordance rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row is focused in any pane form, by arrow key or by pointer
- **THEN** the row keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted
