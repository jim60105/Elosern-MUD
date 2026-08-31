# webclient-local-map delta

## MODIFIED Requirements

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels, SHALL allow focusing a remembered remote node to view its name/landmark without any travel action, and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

The island and the full-map overlay SHALL present the redesign draft's map visual language: every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value. On the coordinate canvas the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment. The resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the pitch guarantee so the non-overlap invariant is unaffected. Node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far).

Layout SHALL be computed in the DOM-independent render model as a bounded integer lattice, not as a rescaling of payload coordinates into a fixed pixel box. The model SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on that lattice, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts. When that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The renderer SHALL size the map canvas from the exported lattice so the canvas reserves its own space **within the island's bounded height**, scaling the canvas down rather than requiring the island to scroll a required surface out of view. The canvas's height cap SHALL be derived from the space the hud-right anchor's bounded height budget leaves after the island's other sections (meta line, remembered list, legend, detail line) — not from a fixed constant — so a long remembered list no longer forces the island's `overflow-y` scroll fallback. The renderer SHALL NOT allow map content to overlap the island's title, its orientation legend, the state legend, the remembered-node list, the detail line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's column pitch, row pitch, and marker sizing SHALL be chosen so that, at every lattice size the model can produce, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of any uniform scale-down applied to fit the island's bounded height. A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The lattice-rendering logic (node/marker placement, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale rather than duplicated: the full-map overlay SHALL render the identical in-view nodes, edges, and legend entries the minimap island renders for the same committed payload, sized to the overlay surface's own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the hovered/selected-node detail line; both remain minimap-island-only, since selection state has no visual effect on the lattice itself and the detail line's content spans both the in-view lattice and the remembered list.

The full-map overlay's map surface SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a teardrop location-pin adornment anchored directly above the `current` node marker — an ornament of the real marker, not a second position claim. Both the island legend and the overlay legend SHALL render as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone.

The island SHALL carry the payload's `title`. It MAY additionally state the renderer's own axis orientation as a legend on a layer whose nodes are placed on coordinates, and SHALL omit that legend on a coordinate-free layer rather than assert a direction the payload does not support. It SHALL NOT render a bearing, a compass angle, a distance, or a coordinate figure in any form: node `x`/`y` are renderer-local presentation values — on a coordinate-bearing layer they mirror validated world coordinates, elsewhere they are layout indices — and no numeric spatial reading may be derived from them.

`remembered` nodes SHALL be presented as a bounded, focusable list outside the coordinate canvas, retaining their non-color state indicator and their focus-only, no-travel behavior. Their payload coordinates describe locations outside the current field of view and SHALL NOT influence the lattice. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: Focused remembered node offers no travel action
- **WHEN** the player focuses a remembered remote node in the minimap
- **THEN** its name and landmark are shown and there is no move or travel control for it

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (shape, border, or text label) and the
  legend text is readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no
  client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full
  resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a grid-layer payload places several in-view nodes at distinct coordinates
- **THEN** each node occupies its own lattice cell, no two node markers overlap, and their relative row and column order matches the payload coordinates

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear in the bounded list rather than on the canvas

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1440x900 and at 1280x720
- **THEN** the canvas is sized within the island's bounded height, the title, orientation legend, state legend, remembered list, and detail line remain readable, no node marker or edge overprints other island content, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The orientation legend states only the drawing convention
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may state the renderer's axis orientation as a legend, and no bearing, compass angle, distance, or coordinate figure is rendered anywhere in the island

#### Scenario: A coordinate-free layer asserts no orientation
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation legend, and the map title, legend, and detail line render exactly as on a coordinate-bearing layer

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a schema-valid payload places in-view nodes at coordinates whose span exceeds the lattice bound
- **THEN** the model falls back to rank compression, the lattice stays within its bound, and every node is still rendered exactly once

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a grid-layer payload places two or more nodes in adjacent lattice cells (sharing a row or a
  column), each carrying a label at the renderer's normal truncation length
- **THEN** the rendered bounding box of each node's marker and label does not intersect the bounding box
  of any other node's marker or label, and the connector edge between two adjacent nodes remains visually
  distinguishable rather than being fully covered by their markers

#### Scenario: A densely populated lattice scales down without reintroducing overlap
- **WHEN** the in-view lattice is wide or tall enough that the island's `max-width` or `max-height`
  cap scales the whole SVG canvas down proportionally
- **THEN** the pre-scale geometry already satisfies the non-overlap invariant, so the uniformly scaled
  render remains free of marker/label collisions

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** the payload combines a tall in-view lattice with a long remembered-node list (up to the
  model's 64-node bound)
- **THEN** the canvas's max-height cap shrinks to the space the hud-right anchor's height budget leaves
  after the meta line, remembered list, legend, and detail line, so no required island content has to
  be scrolled out of view

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and
  sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay renders the identical in-view nodes, edges, and legend entries the minimap island
  renders, sized to the overlay surface's own available width and height, with no marker or label collisions
  at that larger scale

#### Scenario: The full-map overlay omits the remembered-node list and the detail line
- **WHEN** the full-map overlay is open with an available `local_map` payload
- **THEN** the overlay body shows only the lattice canvas and its state legend, and does not render the
  minimap island's remembered-node list or hovered/selected-node detail line

#### Scenario: Draft marker ladder reads without colour
- **WHEN** the island renders a current node, a visited node, an unvisited node, and a landmark node
- **THEN** the current node is the large seal-stroked circle, the visited node is a smaller solid circle, the unvisited node is a smaller hollow circle, the landmark carries the gold treatment, and no two states share a shape

#### Scenario: Map chrome colours resolve to design tokens
- **WHEN** either map surface renders its chrome
- **THEN** every marker, edge, label, and legend colour resolves to a design token value, and the draft seal pair and label tiers match the tokens added with this change

#### Scenario: The overlay pin adorns the current marker without claiming a position
- **WHEN** the full-map overlay renders a payload with a current node
- **THEN** exactly one teardrop pin renders, anchored directly above the current node's marker, and it carries no node label or activation of its own

#### Scenario: Legend chips stay text-labelled at both scales
- **WHEN** the island legend and the overlay legend render for the same payload
- **THEN** each chip pairs its colour swatch with the same text label, and the remembered chip's border style differs from the visited chip's at both scales
