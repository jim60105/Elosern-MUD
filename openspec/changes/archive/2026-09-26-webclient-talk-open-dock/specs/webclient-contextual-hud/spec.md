## MODIFIED Requirements

### Requirement: Dock panes render a per-kind vocabulary from backed fields only

The dock's row region SHALL render the current frame in a form chosen for what that frame contains,
using one shared row renderer for every form so the focused marker, the disabled marker and its
`（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined
in exactly one place. The forms SHALL be: exit, person, object, and footer chips for the scene
overview; the verb popover's rows under a target head; the waiting cards; suggestion cards for the
suggestions frame; and the combat forms specified elsewhere in this capability. No exploration frame
SHALL render an exit-outlet grid or a navigation-row list: exits are chips of the scene overview, and
a host's conversation topics are the dialogue surface's choices, never a dock frame.

An exit chip SHALL render the exit's direction as a leading glyph, and, while the chip is enabled, its
primary text SHALL be the destination's display name — never a repetition of the direction word or the
exit's own label once a glyph already carries that meaning. The glyph SHALL be resolved from a fixed
client-side table of canonical direction words; an exit label outside that table SHALL render verbatim
as the chip's primary text (there being no glyph to carry it) rather than being mapped to a guessed
direction. The destination's display name SHALL be resolved by matching the exit's server-authored
destination node against the committed local-map nodes; when that node is not present in the committed
lattice, an enabled canonical-direction chip SHALL fall back to its own exit label as its primary text
rather than rendering blank — but SHALL NOT render both the destination name and the exit's own label
at once. A disabled exit chip SHALL always render its own exit label as its primary text, never the
destination name, followed by the shared disabled marker. An exit chip's focused state SHALL be
conveyed by its background and border fill together and SHALL NOT additionally render a focus-only
glyph beside its persistent direction glyph. A disabled exit chip's server-authored explanation SHALL
remain reachable by assistive technology directly from the chip and SHALL be shown in the overview's
reason strip while the chip is focused. The submitted move payload SHALL be unchanged.

A chip or row SHALL render only fields the committed payload carries: its server-authored name and,
where its form has one, an optional sub-line composed of such fields. No chip or row SHALL
render a statistics line, a portrait, or any other element for which the payload has no field; where
the design draft shows such an element it SHALL be absent rather than emptied or mocked. Icons and
glyphs SHALL be decorative, SHALL be hidden from assistive technology, SHALL always accompany a real
text label, and SHALL be selected only from stable server-authored keys or the direction table — never
from free text such as a display name.

A target's verb popover SHALL render a head naming the target it is scoped to, taken from the frame's
own server-authored display name, above that target's rows.

Every row and chip in every form SHALL keep the existing disabled contract: a disabled entry SHALL
remain focusable by arrow keys and by pointer, SHALL keep its accessible disabled state and its
server-authored explanation, and SHALL submit nothing.

#### Scenario: A move row names where it goes
- **WHEN** the scene overview renders an enabled exit chip whose label is a canonical direction and whose destination node is present in the committed local map
- **THEN** the chip renders that direction's glyph together with the destination node's display name as its primary text, with no separate rendering of the exit's own direction-word label, and activating it submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** an exit chip's label is a named door or a dynamic wilderness exit rather than a canonical direction
- **THEN** the chip renders that label verbatim as its primary text and no direction is guessed for it

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** an enabled canonical-direction exit chip's destination node is absent from the committed local map
- **THEN** the chip renders its glyph together with the exit's own label as a fallback primary text, and no destination name is invented

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** a canonical-direction exit chip is disabled and its destination node is present in the committed local map
- **THEN** the chip renders its own exit label followed by the shared disabled marker as its primary text, not the destination's display name, and its server-authored explanation remains reachable by assistive technology from the chip itself

#### Scenario: A focused move row is not double-marked
- **WHEN** an exit chip carrying a direction glyph is focused
- **THEN** the chip's background and border change together to mark focus, and no additional focus-only glyph renders alongside its existing direction glyph

#### Scenario: The move frame has no companion panel
- **WHEN** the scene overview renders with any chip focused
- **THEN** no detail aside or other side panel renders beside the overview, the overview occupies the pane's full available width, and no exit-outlet grid exists anywhere in the dock

#### Scenario: A row renders only backed fields
- **WHEN** the scene overview renders a look-only chip for a present entity
- **THEN** the chip shows the entity's display name only, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's verb popover
- **THEN** the popover renders a head naming that target above the target's server-authored rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row or chip is focused in any form, by arrow key or by pointer
- **THEN** it keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

## ADDED Requirements

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
- **WHEN** a combat skill, target, or scale pane renders in the command region at the minimum supported 1280x720 viewport
- **THEN** every row lies inside the pane's right edge, the pane shows no horizontal overflow, and a long label wraps within its row

#### Scenario: Rendered width never changes the keyboard cell mapping
- **WHEN** the player presses ArrowRight in a pane whose keyboard geometry fixes two columns
- **THEN** focus reaches the row that the fixed column count places in the second column, whatever width each row renders at

## REMOVED Requirements

### Requirement: A fixed-column dock pane sizes its columns to content
**Reason**: Its content-sized track rule applied only to the nav pane, and this change deletes the nav pane with the keyword frame. The combat panes never followed the rule: they are flex forms on which the inline `repeat(n, 1fr)` template has no effect (the skill rows fill the pane, the target tokens are fixed squares, the scale chips share the width equally). Keeping the rule would direct a later implementer to change the combat layout under a logic change. How the combat panes use their width is a visual decision.
**Migration**: "A fixed-column dock pane stays inside the command region" keeps the no-overflow rule and the fixed cell mapping for the remaining fixed-column panes, without prescribing track sizing. Test annotations re-anchor to it.
