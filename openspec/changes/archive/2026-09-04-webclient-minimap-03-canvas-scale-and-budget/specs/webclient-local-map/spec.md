# webclient-local-map delta

## MODIFIED Requirements

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels on the full-map overlay (the minimap island mounts no state legend), SHALL allow focusing a remembered remote node to view its name/landmark without any travel action, and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

The island and the full-map overlay SHALL present the redesign draft's map visual language: every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value. On either placement's canvas the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment. The resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the geometry guarantee so the non-overlap invariant is unaffected. Node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far).

Layout SHALL be computed in the DOM-independent render model, not as a rescaling of payload coordinates into a fixed pixel box, and the model SHALL export two placements for the same committed payload: a bounded integer lattice and a radial connected-graph. The lattice placement SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on it, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts; when that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The radial placement SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas; ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates. The radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant below is constructible from the model alone; neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning. The renderer SHALL size the map canvas from the exported placement so the canvas reserves its own space **within the island's bounded height**, scaling the canvas rather than requiring the island to scroll a required surface out of view. On the island the canvas SHALL claim the island's content width rather than drawing at the placement's natural pixel size: the drawn map SHALL NOT be narrower than the island's content box merely because the payload is sparse, and the enlargement SHALL be a uniform scale of the whole canvas so every marker radius, label offset, and gutter in the geometry contract below scales together. That enlargement SHALL be bounded by an explicit maximum upscale factor, so a one-node payload cannot inflate the designed marker and label ramp; the bound SHALL be opt-in per surface, and the full-map overlay SHALL keep filling its own body width unbounded. The renderer SHALL resolve every cap it is given — a maximum width, a height budget, and the upscale bound — into a single width bound it computes itself from the canvas's own aspect ratio, `min(maxWidth, maxHeight × canvasWidth / canvasHeight, canvasWidth × maxUpscale)`, never leaving a definite width to be reconciled against a height cap by engine-specific replaced-element constraint resolution; the resulting bound SHALL be floored rather than rounded up, so honouring it can never re-cross the height budget by a sub-pixel and force the anchor's scroll fallback. The canvas's height cap SHALL be derived from the space the hud-right anchor's bounded height budget leaves after the island's remaining sections (meta line, remembered list, detail line) — not from a fixed constant — so a long remembered list no longer forces the island's `overflow-y` scroll fallback. That height budget SHALL be a fixed point of the measurement it feeds: it SHALL be measured only from geometry that does not move when the canvas resizes — the island's own position and the position of the surface bounding it from below, less a fixed clearance — and SHALL NOT be derived from any quantity the canvas's own rendered size participates in, in particular not from the rendered height of the content-sized hud-right anchor, whose height IS the island's height while the island fits. Re-measuring an already-settled island SHALL yield the same cap, so repeated observer-driven measurement passes SHALL NOT walk the canvas down toward its floor. The renderer SHALL NOT allow map content to overlap the island's title, its orientation marks, the remembered-node list, the detail line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's geometry — column pitch, row pitch, and marker sizing on the lattice, and ring radii, angular slots, and marker sizing on the radial graph — SHALL be chosen so that, at every placement the model can produce for either variant, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of any uniform scale-down applied to fit the island's bounded height (radial ring radii SHALL grow with ring member count so the angular arc between adjacent slots bounds the label footprint). A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The map-rendering logic (node/marker placement consumption, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale, by layout variant (`lattice` or `graph`), and by an explicit legend-display switch rather than duplicated: the variant SHALL be resolved once, in the render-model layer, as a pure function of the payload's `layer` — the closed coordinate-bearing set (`grid`, `wilderness`) resolves to the lattice and every other layer resolves to the graph — and both surfaces consume that one resolved value, so island and overlay can never disagree. The shared renderer SHALL render the state legend wherever its display switch is on, SHALL default the switch to on, and the minimap island SHALL pass it off so no legend element is mounted on the island for any payload while the overlay renders the payload's full legend. No map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting. Both surfaces SHALL render the resolved variant's identical in-view nodes and edges for the same committed payload, the overlay sized to its own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the hovered/selected-node detail line; both remain minimap-island-only, since selection state has no visual effect on the placement itself and the detail line's content spans both the in-view placement and the remembered list.

The full-map overlay's map surface SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a teardrop location-pin adornment anchored directly above the `current` node marker — an ornament of the real marker, not a second position claim. The overlay legend SHALL render as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone.

The island SHALL carry the payload's `title`, and its header SHALL stay a single row at every authored title length. `title` is server-authored and bounded only by the payload's 128-code-point ceiling, so the header SHALL be a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and the header's trailing control SHALL be fixed-size items that neither shrink nor wrap. No authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL occupy its anchor's full column width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length. On the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis). Node `x`/`y` carry layer-scoped semantics: on the closed coordinate-bearing set (`grid`, `wilderness`) they are validated world coordinates and MAY drive relative-direction geometry; on every other layer they are renderer-local layout values and SHALL NOT be read as direction, distance, or place. The island's detail line SHALL state the active node's coordinates as a two-integer figure — the node's payload `x` and `y` exactly as committed — whenever the payload layer is coordinate-bearing AND the active node (hovered, selected, or the current-node default) is the `current` node; it SHALL NOT state a coordinate figure for any other node, on any layer, and the full-map overlay SHALL NOT state a coordinate figure at all. No surface SHALL render a compass angle, a bearing angle, a distance, or any coordinate figure beyond the permitted current-node figure; in particular the remembered-node edge markers convey direction only and never gain a coordinate readout. The detail line's active node SHALL follow the committed payload: when a newly committed payload names a different `current_node`, or no longer carries the previously hovered/selected node, the line SHALL fall back to the payload's current node rather than resolving to nothing, so the readout describes where the player is after a move instead of a node the new payload no longer contains. When no node resolves at all, the line SHALL state nothing and SHALL render no framed container: an empty detail line SHALL paint no box and SHALL reserve no height in the island's canvas budget, rather than presenting an empty bordered widget.

`remembered` nodes SHALL be presented as a bounded, focusable list outside the coordinate canvas, retaining their non-color state indicator and their focus-only, no-travel behavior. Their payload coordinates SHALL NOT influence either exported node placement. On the lattice variant, each remembered node whose coordinates fall outside the drawn extent SHALL additionally render as an edge direction marker: the remembered-node diamond ornament (carrying the gold landmark treatment when flagged) placed where the ray from the current node through that node's **raw payload coordinate delta** crosses the canvas's marker-safe border, with the direction computed by a pure helper over the raw delta (`+y = 北`, eight octants with deterministic sector bounds) and never from rank-compressed columns or rows, since compression preserves order, not ratios. The marker SHALL convey direction only — no distance figure, angle, or coordinate readout — SHALL carry no activation of its own, SHALL be positioned deterministically so markers never overlap each other or any node marker, label, or axis, and SHALL NOT replace the remembered list, which remains the complete focusable reading path; on a surface without the list (the full-map overlay) each marker SHALL carry its place name as visible text and as its accessible name. Coordinate-free payloads SHALL render no edge direction markers. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: The island mounts no state legend
- **WHEN** an available `local_map` payload renders on both the minimap island and the full-map overlay
- **THEN** no legend element exists anywhere in the island's DOM, and the overlay renders the payload's full legend with its dot-chips and text labels

#### Scenario: Focused remembered node offers no travel action
- **WHEN** the player focuses a remembered remote node in the minimap
- **THEN** its name and landmark are shown and there is no move or travel control for it

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (marker shape, border, or text label) on the island without any legend, and the overlay legend's text labels are readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a grid-layer payload places several in-view nodes at distinct coordinates
- **THEN** each node occupies its own lattice cell, no two node markers overlap, and their relative row and column order matches the payload coordinates

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear in the bounded list rather than occupying lattice cells

#### Scenario: A remote remembered place marks the canvas edge at its true direction
- **WHEN** a coordinate-layer payload remembers a known place outside the drawn extent, e.g. due east or to the southwest
- **THEN** its remembered diamond renders on the corresponding border of the canvas, pointing along the true coordinate bearing, and no distance, angle, or coordinate figure appears with it

#### Scenario: Rank compression never skews a marker's direction
- **WHEN** an in-view span forces rank compression while a remembered remote sits at a lopsided raw delta such as (+100, +1)
- **THEN** its edge marker renders on the near-due-east border rather than on the 45° diagonal that the compressed ranks would suggest

#### Scenario: A coordinate-free payload draws no edge markers
- **WHEN** an interior or instance payload with remembered nodes renders the radial graph
- **THEN** no edge direction marker is rendered, and the remembered list remains the only presentation of those nodes

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1440x900 and at 1280x720
- **THEN** the canvas is sized within the island's bounded height, the title, orientation marks, remembered list, and detail line remain readable, no node marker or edge overprints other island content, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The island states its convention and the current coordinates
- **WHEN** the committed payload's layer is coordinate-bearing and the detail line shows the current node
- **THEN** the island states the renderer's axis orientation marks in its header, the detail line states the current node's two payload coordinates, and no compass angle, distance, or other-node coordinate figure is rendered anywhere in the island

#### Scenario: A hovered node states no coordinates
- **WHEN** the player hovers or selects a non-current node on a coordinate-bearing layer
- **THEN** the detail line states that node's label and visibility state with no coordinate figure

#### Scenario: A coordinate-free layer asserts no orientation and no coordinates
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure, and the map title and detail line render exactly as on a coordinate-bearing layer

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a schema-valid payload places in-view nodes at coordinates whose span exceeds the lattice bound
- **THEN** the model falls back to rank compression, the lattice stays within its bound, and every node is still rendered exactly once

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a grid-layer payload places two or more nodes in adjacent lattice cells (sharing a row or a column), each carrying a label at the renderer's normal truncation length
- **THEN** the rendered bounding box of each node's marker and label does not intersect the bounding box of any other node's marker or label, and the connector edge between two adjacent nodes remains visually distinguishable rather than being fully covered by their markers

#### Scenario: A densely populated lattice scales down without reintroducing overlap
- **WHEN** the in-view lattice is wide or tall enough that the island's `max-width` or `max-height` cap scales the whole SVG canvas down proportionally
- **THEN** the pre-scale geometry already satisfies the non-overlap invariant, so the uniformly scaled render remains free of marker/label collisions

#### Scenario: A sparse lattice scaled up never reintroduces overlap
- **WHEN** the fill-width rule scales the whole SVG canvas up proportionally, because the payload's natural canvas is narrower than the island's content box
- **THEN** the pre-scale geometry already satisfies the non-overlap invariant, so the uniformly scaled render remains free of marker/label collisions in the upward direction too — the scale is uniform through the viewBox, so every marker, label, and gutter offset keeps its proportion

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** the payload combines a tall in-view lattice with a long remembered-node list (up to the model's 64-node bound)
- **THEN** the canvas's height cap shrinks to the space the anchor's height budget — measured from geometry the canvas does not move — leaves after the meta line, remembered list, and detail line, so no required island content has to be scrolled out of view

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay renders the identical in-view nodes and edges the minimap island renders — in the same resolved layout variant — plus the state legend the island omits, sized to the overlay surface's own available width and height, with no marker or label collisions at that larger scale, and with no coordinate figure on the overlay surface

#### Scenario: The full-map overlay omits the remembered-node list and the detail line
- **WHEN** the full-map overlay is open with an available `local_map` payload
- **THEN** the overlay body shows only the map canvas in the resolved variant and its state legend, and does not render the minimap island's remembered-node list or hovered/selected-node detail line

#### Scenario: Draft marker ladder reads without colour
- **WHEN** the island renders a current node, a visited node, an unvisited node, and a landmark node
- **THEN** the current node is the large seal-stroked circle, the visited node is a smaller solid circle, the unvisited node is a smaller hollow circle, the landmark carries the gold treatment, and no two states share a shape

#### Scenario: Map chrome colours resolve to design tokens
- **WHEN** either map surface renders its chrome
- **THEN** every marker, edge, label, and legend colour resolves to a design token value, and the draft seal pair and label tiers match the tokens added with this change

#### Scenario: The overlay pin adorns the current marker without claiming a position
- **WHEN** the full-map overlay renders a payload with a current node
- **THEN** exactly one teardrop pin renders, anchored directly above the current node's marker, and it carries no node label or activation of its own

#### Scenario: Overlay legend chips stay text-labelled with non-colour redundancy
- **WHEN** the overlay legend renders for a payload
- **THEN** each chip pairs its colour swatch with its text label, and the remembered chip's border style differs from the visited chip's

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement for a payload whose in-view nodes are joined by edges
- **THEN** the current node sits at the centre, every other in-view node sits on the ring of its BFS exit-hop distance (edgeless in-view nodes on the outermost ring), and re-running the pass on the same payload produces identical coordinates

#### Scenario: The resolved layout preserves nodes, edges, and actions
- **WHEN** payloads on a coordinate-bearing layer and on a coordinate-free layer are committed in turn
- **THEN** each renders the resolver's variant with the same in-view nodes, edges, and per-node move actions, no marker or label overlaps in either, no compass angle or distance figure appears in either, and the map chrome exposes no layout control element at any point

#### Scenario: The orientation mark follows the resolved layout
- **WHEN** the payload's layer resolves to the graph variant (`interior`, `instance`)
- **THEN** the island renders no axis orientation mark and no coordinate figure, and on a layer resolving to the lattice (`grid`, `wilderness`) the mark renders alongside the current node's coordinate figure

#### Scenario: The island's canvas claims the island's content width
- **WHEN** a payload whose natural canvas is narrower than the island's content box renders on the island (e.g. a sparse wilderness payload drawing ~112 CSS px inside the island's 210px content box)
- **THEN** the drawn canvas fills the island's content width up to the island's own width cap, uniformly scaled, instead of drawing at its natural pixel size and leaving the map the smallest element in the island

#### Scenario: A one-node payload's fill is bounded by the upscale factor
- **WHEN** the committed payload contains a single node, whose natural canvas is 58 × 58 CSS px, and the island's maximum upscale factor is 2
- **THEN** the drawn canvas is bounded at 116px rather than stretched to the island's full content width, so the designed marker and label ramp is not inflated ~3.5×, and the bounded canvas is centred in the island

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** the island passes a 296px height budget for a canvas whose placement is 116 × 2830 CSS px
- **THEN** the renderer emits a single width bound of `296 × 116 / 2830` = 12.13px (floored, not rounded up), the rendered height equals the budget on every engine, and no engine-specific reconciliation of a definite width against a height cap can letterbox or distort the drawing

#### Scenario: The overlay is unaffected by the island's upscale bound
- **WHEN** the same committed payload renders in the full-map overlay, which declares no upscale bound
- **THEN** the overlay's canvas fills the overlay body's width unbounded, exactly as before, and only the island's canvas is subject to the upscale bound

#### Scenario: Repeated budget measurements do not ratchet the canvas down
- **WHEN** the hud-right anchor is content-sized so its rendered height equals the island's own height, and the island's height budget is re-measured on many successive observer passes
- **THEN** every pass yields the identical canvas cap, the cap never decreases by a pixel per pass, and the canvas never walks down to its 40px floor — because the budget is measured from geometry the canvas does not move, not from a quantity the canvas's rendered height participates in

#### Scenario: A long authored title never reflows the island's header
- **WHEN** the committed payload's server-authored title is long enough that the title, the orientation marks, and the header's trailing control together exceed the island's content width (e.g. `冒險者公會外街道圖` beside the axis marks and the full-map control in a 210px content box)
- **THEN** the header stays a single row: the title renders on one line truncated with an overflow indicator while its complete string stays available as the element's tooltip/accessible text, the orientation marks and the trailing control keep their full size without wrapping, and the island's card width is unchanged

#### Scenario: The readout follows the player after a move
- **WHEN** a newly committed payload replaces the rendered one with a different `current_node`, and the previously selected node is no longer carried by the payload
- **THEN** the detail line describes the new payload's current node rather than resolving to nothing, and the island shows no blank readout

#### Scenario: A readout with nothing to say draws no box
- **WHEN** no active node resolves for the island's detail line
- **THEN** the line states nothing, paints no border or box, and reserves no height in the island's canvas budget
