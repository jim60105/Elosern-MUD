## ADDED Requirements

### Requirement: The map column holds its instrument geometry and fades hidden overflow
The `map` anchor SHALL be as wide as the right column minus 28px × S and never narrower than 282px × S, SHALL stack its surfaces 10px × S apart, and SHALL paint nothing itself. An over-tall stack SHALL scroll inside the anchor without a visible scrollbar, fading the top or bottom edge only while content lies beyond that edge. Every stage offset taken from the column's left edge SHALL derive from that same width.

#### Scenario: The column never narrows below the minimap panel
- **WHEN** the shell renders in exploration at 1280x720, at 1451x790 and at 2560x1440
- **THEN** the `map` anchor's rendered width is 282px at 1280x720 (where the right column less 28px would give 250px), the right column less 28px at 1451x790, and the right column less 28px × 1.4 at 2560x1440, each within 1px, and its right edge stays 16px × S from the stage's right edge

#### Scenario: Neighbours offset from the same width
- **WHEN** the presence rail's anchor renders at any of those viewports
- **THEN** its right edge stands 24px × S left of the `map` anchor's left edge (±1px), so a widened column never reaches under the rail

#### Scenario: The anchor paints nothing and keeps its gap
- **WHEN** the anchor holds two or more surfaces
- **THEN** the anchor's own computed background is transparent with no border and no box shadow, and consecutive surfaces are 10px × S apart (±1px)

#### Scenario: An over-tall column scrolls without a scrollbar
- **WHEN** the anchor's content is taller than its bounded height
- **THEN** the anchor still scrolls vertically and every surface stays reachable by scrolling, while the anchor's scrollbar takes no width (its offset width equals its client width) and is not drawn

#### Scenario: Only an edge with content beyond it fades
- **WHEN** the over-tall anchor is scrolled to its top, then to a middle position, then to its bottom
- **THEN** at the top only the bottom edge is masked, in the middle both edges are masked, and at the bottom only the top edge is masked; each masked edge fades over 32px × S

#### Scenario: A column that fits is not masked
- **WHEN** the anchor's content fits inside its bounded height, as the populated column does at 1451x790 and at 2560x1440
- **THEN** no edge of the anchor is masked

#### Scenario: Content changes update the fade without a scroll
- **WHEN** a surface mounts into or unmounts from the anchor, or a surface changes height, with no scroll event
- **THEN** the masked edges are recomputed for the new content height, so a column that starts to overflow gains its bottom fade and a column that comes to fit loses every fade

## MODIFIED Requirements

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces in the stage's island anchors SHALL render as separate floating HUD surfaces apart by the anchor's gap, each wearing the island chrome (translucent fill, backdrop blur, hairline border, shared radius and shadow) or the borderless instrument-panel chrome its own requirement names, never one boxed column card or an opaque `<aside>` stacked in a layout column. No reference panel and no portrait anchor content SHALL be placed in either island anchor.

#### Scenario: The vitals anchor is one dock
- **WHEN** the shell renders the stage box's lower left
- **THEN** it is the vitals dock that "The vitals dock stands at the stage's lower-left above the band" defines: it carries the condition icon row and the vitals bars as one dock, and carries neither a character head card nor a portrait catalog strip nor a party quickbar

#### Scenario: The map anchor stacks its islands in one order
- **WHEN** the shell renders the `map` anchor
- **THEN** it carries, in this order, the place card, the minimap island, the objective line, and the title ballot menu while it is mounted, each present only while its own requirement renders it

#### Scenario: The populated stack never needs anchor scrolling
- **WHEN** the shell renders at the 1451x790 reference viewport and at 2560x1440 with every island populated
- **THEN** the stack's rendered height fits within its anchor, so no required island depends on scrolling the anchor to be seen

#### Scenario: One token change reaches every island
- **WHEN** a design token changes or the reduced-motion block applies
- **THEN** every island's chrome, expressed through the shared design tokens, is reached at once

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the condition icon row and the vitals bars render as the lower-left dock's two surfaces in that order, the dock carries the translucent blurred panel chrome, no head card, place card, portrait catalog strip, or party quickbar is rendered, and the party appears only as standing portraits in the `actor-left` anchor

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at the 1451x790 reference viewport with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the place card's rendered box does not intersect the minimap island below it, and neither stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, blur, border or brass fitting, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the place card, the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders nothing in the `map` anchor

#### Scenario: The island stack carries its amendments
- **WHEN** the `place-card-relocation` and `vitals-bar-redesign` amendments apply to this requirement
- **THEN** the party quickbar is removed with this change
