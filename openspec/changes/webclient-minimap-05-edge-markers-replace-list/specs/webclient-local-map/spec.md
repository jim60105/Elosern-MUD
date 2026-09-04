# webclient-local-map delta

## MODIFIED Requirements

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels on the full-map overlay (the minimap island mounts no state legend), SHALL make every `remembered` remote node's name readable without any travel action and without any activation — as visible text on the surface that draws it and, wherever that visible text can be truncated or is drawn inside a graphic, as an assistive-technology text alternative carrying the untruncated name — and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

The island and the full-map overlay SHALL present the redesign draft's map visual language: every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value. On either placement's canvas the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment. The resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the geometry guarantee so the non-overlap invariant is unaffected. Node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far).

Layout SHALL be computed in the DOM-independent render model, not as a rescaling of payload coordinates into a fixed pixel box, and the model SHALL export two placements for the same committed payload: a bounded integer lattice and a radial connected-graph. The lattice placement SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on it, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts; when that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The radial placement SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas; ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates. The radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant below is constructible from the model alone; neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning. The renderer SHALL size the map canvas from the exported placement so the canvas reserves its own space **within the island's bounded height**, scaling the canvas rather than requiring the island to scroll a required surface out of view. On the island the canvas SHALL claim the island's content width rather than drawing at the placement's natural pixel size: the drawn map SHALL NOT be narrower than the island's content box merely because the payload is sparse, and the enlargement SHALL be a uniform scale of the whole canvas so every marker radius, label offset, and gutter in the geometry contract below scales together. That enlargement SHALL be bounded by an explicit maximum upscale factor, so a one-node payload cannot inflate the designed marker and label ramp; the bound SHALL be opt-in per surface, and the full-map overlay SHALL keep filling its own body width unbounded. The renderer SHALL resolve every cap it is given — a maximum width, a height budget, and the upscale bound — into a single width bound it computes itself from the canvas's own aspect ratio, `min(maxWidth, maxHeight × canvasWidth / canvasHeight, canvasWidth × maxUpscale)`, never leaving a definite width to be reconciled against a height cap by engine-specific replaced-element constraint resolution; the resulting bound SHALL be floored rather than rounded up, so honouring it can never re-cross the height budget by a sub-pixel and force the anchor's scroll fallback. The canvas's height cap SHALL be derived from the space the hud-right anchor's bounded height budget leaves after the island's remaining laid-out sections — not from a fixed constant, and not from a fixed section list — so no other island content can force the island's `overflow-y` scroll fallback. Those sections are the meta line, the canvas, and at most one of the graph-variant remembered list and the coordinate readout line, since a payload whose layer resolves to the lattice renders no remembered list and a payload whose layer resolves to the graph states no coordinate figure; the separating-gap count SHALL be derived from the sections actually laid out rather than from a constant, so a section that renders nothing costs the canvas neither its own height nor a gap. The canvas's own natural size SHALL NOT be able to breach that cap however much the edge-marker gutter grows it: the gutter enlarges the canvas's natural width and height by the same amount, so the single width bound above resolves to a rendered height that is at most the height cap in every case. That height budget SHALL be a fixed point of the measurement it feeds: it SHALL be measured only from geometry that does not move when the canvas resizes — the island's own position and the position of the surface bounding it from below, less a fixed clearance — and SHALL NOT be derived from any quantity the canvas's own rendered size participates in, in particular not from the rendered height of the content-sized hud-right anchor, whose height IS the island's height while the island fits. Re-measuring an already-settled island SHALL yield the same cap, so repeated observer-driven measurement passes SHALL NOT walk the canvas down toward its floor. The renderer SHALL NOT allow map content to overlap the island's title, its orientation marks, the graph-variant remembered-node list, the readout line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's geometry — column pitch, row pitch, and marker sizing on the lattice, and ring radii, angular slots, and marker sizing on the radial graph — SHALL be chosen so that, at every placement the model can produce for either variant, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of any uniform scale-down applied to fit the island's bounded height (radial ring radii SHALL grow with ring member count so the angular arc between adjacent slots bounds the label footprint). A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The map-rendering logic (node/marker placement consumption, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale, by layout variant (`lattice` or `graph`), and by an explicit legend-display switch rather than duplicated: the variant SHALL be resolved once, in the render-model layer, as a pure function of the payload's `layer` — the closed coordinate-bearing set (`grid`, `wilderness`) resolves to the lattice and every other layer resolves to the graph — and both surfaces consume that one resolved value, so island and overlay can never disagree. The shared renderer SHALL render the state legend wherever its display switch is on, SHALL default the switch to on, and the minimap island SHALL pass it off so no legend element is mounted on the island for any payload while the overlay renders the payload's full legend. No map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting. Both surfaces SHALL render the resolved variant's identical in-view nodes and edges for the same committed payload, the overlay sized to its own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the island's coordinate readout line; both remain minimap-island-only, since the overlay is sized to its own surface and states no coordinate figure at all, and the list is in any case an island-side, graph-variant-only presentation.

The full-map overlay's map surface SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a teardrop location-pin adornment anchored directly above the `current` node marker — an ornament of the real marker, not a second position claim. The overlay legend SHALL render as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone.

The island SHALL carry the payload's `title`, and its header SHALL stay a single row at every authored title length. `title` is server-authored and bounded only by the payload's 128-code-point ceiling, so the header SHALL be a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and every other header item SHALL be fixed-size items that neither shrink nor wrap. The header SHALL carry no full-map control of its own: the island's single full-map affordance is the full-bleed element specified below, so the header's fixed-size items are the orientation marks and nothing else unless a later change adds one. No authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL occupy its anchor's full column width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length. On the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis). Node `x`/`y` carry layer-scoped semantics: on the closed coordinate-bearing set (`grid`, `wilderness`) they are validated world coordinates and MAY drive relative-direction geometry; on every other layer they are renderer-local layout values and SHALL NOT be read as direction, distance, or place. The island's readout line SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — whenever the payload layer is coordinate-bearing, and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place. The readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one. The island SHALL NOT state a coordinate figure for any node other than the `current` node, on any layer, and the full-map overlay SHALL NOT state a coordinate figure at all. No surface SHALL render a compass angle, a bearing angle, a distance, or any coordinate figure beyond the permitted current-node figure; in particular the remembered-node edge markers convey direction only and never gain a coordinate readout. On a coordinate-free layer there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box and reserving no height in the island's canvas budget, rather than presenting an empty bordered widget. Removing the readout's label content SHALL NOT make any node's name unreachable: each in-view node's full label SHALL remain available as its on-canvas accessible name, and a remembered node's name SHALL remain readable — as the visible text of its edge marker on the lattice variant and of its list entry on the graph variant — with its untruncated form always available to assistive technology.

The island's readout SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box. No draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it.

The island SHALL present exactly one full-map affordance, and that affordance SHALL carry no visible button chrome — no labelled control, icon button, or other visible trigger anywhere on the island. The affordance SHALL be a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element itself contains no focusable descendant, carrying 展開全地圖 as its accessible name. Activating it by pointer, by Enter, or by Space SHALL open the full-map surface through the platform's own button behaviour; no key handler on a non-button element SHALL stand in for it. The affordance SHALL be reachable in the island's tab order without the island's root element gaining a role or a tab stop of its own, and its focus-visible indication SHALL delineate the whole island rather than a small region of it. The affordance element SHALL be stable across committed payloads, so the full-map surface's opener — the focused element captured when that surface opens — still exists when it closes and focus is restored to it. The island's existing pointer convenience SHALL be unchanged: a click on the island's body SHALL open the full-map surface, a click that originates in an interactive descendant — an actionable lattice node or the affordance itself — SHALL run only that descendant's own behaviour, and every activation path SHALL open the full-map surface exactly once. The island SHALL carry no other tab stop and no other interactive descendant: neither an edge direction marker, nor a marker name, nor a graph-variant remembered-list entry SHALL be focusable or activatable, so the affordance remains the island's single keyboard path on every layout variant.

The presentation of `remembered` nodes SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface. Their payload coordinates SHALL NOT influence either exported node placement.

On the lattice variant, the named edge direction marker SHALL BE the presentation: each remembered node whose coordinates fall outside the drawn extent SHALL render as the remembered-node diamond ornament (carrying the gold landmark treatment when flagged) placed where the ray from the current node through that node's **raw payload coordinate delta** crosses the canvas's marker-safe border, with the direction computed by a pure helper over the raw delta (`+y = 北`, eight octants with deterministic sector bounds) and never from rank-compressed columns or rows, since compression preserves order, not ratios. The marker SHALL convey direction only — no distance figure, angle, or coordinate readout — and SHALL carry no activation of its own. The island SHALL NOT render a remembered-node list on this variant: the list is removed outright, and no surface SHALL present a remembered node both as a marker and as a list entry.

On every surface that draws edge direction markers — the island as well as the full-map overlay — each marker SHALL carry its place name as visible text beside it. The name SHALL be drawn wholly inside the marker gutter band that lies outside the canvas rect containing every node marker, every node label, and the axis, so a marker name can never intersect a node marker, a node label, or the axis. Markers and their names SHALL be positioned deterministically so that no marker overlaps another marker and no name overlaps another name; each name SHALL be fitted to the free span its own marker holds along its edge, and the surface's reserved band SHALL be declared in the geometry the placement helper consumes so the band is reserved before the names are drawn rather than discovered afterwards. Where a name does not fit its span it SHALL be truncated with an overflow indicator, and **the surface SHALL NOT draw two equal marker names while the payload labels behind them differ**: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator. A dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative.

Because the markers carry no activation and are drawn inside a graphic, the lattice variant's complete reading path SHALL be a text alternative that mirrors the drawn marker set one entry per drawn marker, in a deterministic order, each entry stating that marker's untruncated payload label together with its direction as one of the eight octant names (`北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北`). Naming the octant in words is permitted on that mirror; a numeric bearing, an angle, a distance, and any coordinate figure beyond the permitted current-node figure remain forbidden on every surface. The mirror SHALL be derived from the same marker set the surface draws, so it can neither omit a drawn marker nor invent one, and SHALL introduce no additional tab stop: the island's tab order SHALL remain exactly its single full-map affordance, and neither the markers nor the mirror SHALL be focusable.

Coordinate-free payloads SHALL render no edge direction markers, because a radial graph draws no canvas edge for a bearing to cross and its node `x`/`y` are renderer-local layout values. On the graph variant, therefore, the island SHALL retain the bounded remembered-node list outside the canvas — each entry keeping its non-color state indicator and its place name as visible text, carrying no travel action, no activation, and no tab stop — so a remembered node on an `interior` or `instance` payload keeps a presentation instead of disappearing from the surface entirely. No remembered node on that variant SHALL be placed on the canvas or on its border, since a position there would assert a bearing the payload does not carry. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: The island mounts no state legend
- **WHEN** an available `local_map` payload renders on both the minimap island and the full-map overlay
- **THEN** no legend element exists anywhere in the island's DOM, and the overlay renders the payload's full legend with its dot-chips and text labels

#### Scenario: A remembered place is readable and offers no travel action
- **WHEN** a remembered remote node is presented on the minimap — as an edge direction marker on the lattice variant, as a list entry on the graph variant
- **THEN** its name and its landmark treatment are shown, its untruncated name is available to assistive technology, and there is no move or travel control for it and no activation of its own

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (marker shape, border, or text label) on the island without any legend — the remembered state by its diamond ornament on the canvas border, named beside it — and the overlay legend's text labels are readable

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
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear as named markers on the canvas border rather than occupying lattice cells

#### Scenario: A remote remembered place marks the canvas edge at its true direction, with its name
- **WHEN** a coordinate-layer payload remembers a known place outside the drawn extent, e.g. 聖潔王都 to the north-east or a cave to the south-west
- **THEN** its remembered diamond renders on the corresponding border of the canvas, pointing along the true coordinate bearing, with that place's name drawn as visible text beside it in the marker gutter band, and no distance, angle, or coordinate figure appears with it

#### Scenario: The island presents each remembered place once, with no list beneath the map
- **WHEN** a wilderness payload carrying remembered gateways renders on the minimap island
- **THEN** no remembered-node list element exists anywhere in the island's DOM, each remembered gateway is drawn exactly once as a named edge direction marker, and no remembered place is presented both as a marker and as a list entry

#### Scenario: A lone gateway on an edge carries its whole authored name
- **WHEN** exactly one remembered gateway's bearing leaves through a given canvas edge and its authored label is the disambiguated form 西部丘陵與谷地（南門）
- **THEN** that marker's visible name is the complete label rather than a four-glyph node-label truncation, because the name is fitted to the free span its own marker holds along that edge

#### Scenario: A truncation that would make two places look alike is refused
- **WHEN** two remembered gateways whose payload labels differ only in a trailing qualifier — 西部丘陵與谷地（南門） and 西部丘陵與谷地（北門） — crowd one canvas edge so tightly that neither name can be drawn distinctly in its span
- **THEN** the surface does not draw the same string twice: each name it does draw is distinct from every other drawn marker name, any marker it cannot distinguish keeps its diamond, its bearing, and its landmark treatment with its visible name omitted, and both untruncated labels remain available to assistive technology

#### Scenario: A name the island cannot show is still reachable without assistive technology
- **WHEN** the island omits or truncates a marker's visible name — the fit-to-span rule shortened it, or the ambiguity rule dropped it — and the reader is a sighted keyboard-only user with no assistive technology running, so neither the visually-hidden mirror nor a hover tooltip on the `pointer-events: none` marker layer can serve them
- **THEN** activating the island's single full-map affordance opens the full-map overlay, which renders every remembered gateway's name as visible text and as the marker's accessible name at the overlay's own larger scale, where the island's span constraints do not apply — so no remembered place's identity is reachable only through assistive technology

#### Scenario: Marker names never collide with each other, a node label, or the axis
- **WHEN** a lattice payload places remembered markers on several canvas edges, including two on one edge, while the drawn lattice carries in-view node labels at the renderer's truncation length and the canvas draws its axis
- **THEN** every marker name is rendered wholly inside the marker gutter band outside the canvas rect, so no marker name's box intersects any node marker, node label, or axis line, and no two marker names' boxes intersect each other

#### Scenario: Rank compression never skews a marker's direction
- **WHEN** an in-view span forces rank compression while a remembered remote sits at a lopsided raw delta such as (+100, +1)
- **THEN** its edge marker renders on the near-due-east border rather than on the 45° diagonal that the compressed ranks would suggest

#### Scenario: A coordinate-free payload draws no edge markers and still presents its remembered nodes
- **WHEN** an interior or instance payload with remembered nodes renders the radial graph
- **THEN** no edge direction marker is rendered and no remembered node is placed on the canvas or its border, and the island's bounded remembered list is present on this variant and is the presentation of those nodes, each entry showing the node's name with its non-colour state indicator and no travel action

#### Scenario: An interior payload's remembered rooms do not vanish with the lattice's list
- **WHEN** the player, having walked several rooms of a building, stands in one whose interior payload carries those rooms as `remembered`, and the island renders
- **THEN** every one of those remembered rooms is still presented on the island by name, and none is silently dropped because the coordinate variant no longer renders a list

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1440x900 and at 1280x720
- **THEN** the canvas is sized within the island's bounded height, the title, orientation marks, marker names, and whichever of the graph-variant remembered list and the readout line the payload lays out remain readable, no node marker, marker name, or edge overprints other island content, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The island states its convention and the current coordinates
- **WHEN** the committed payload's layer is coordinate-bearing
- **THEN** the island states the renderer's axis orientation marks in its header, the readout line states the current node's two payload coordinates as its entire content, and no compass angle, distance, or other-node coordinate figure is rendered anywhere in the island

#### Scenario: The readout states the coordinate figure and nothing else
- **WHEN** a wilderness payload whose current node is labelled 西部丘陵與谷地 at (60, 107) renders on the island
- **THEN** the readout line reads exactly the two-integer coordinate figure for (60, 107), it carries no place name, no 目前所在 or other visibility-state word, and no movement destination, and the place name appears instead on the shell's own location surface

#### Scenario: Hovering or activating a node never changes the readout
- **WHEN** the player hovers a non-current node, then activates one, on a coordinate-bearing layer
- **THEN** the readout line still states the current node's coordinate figure and nothing else, no coordinate figure for the hovered or activated node is rendered anywhere, and the island holds no hovered-node or selected-node state that the readout could go stale on

#### Scenario: A node's name stays reachable without the readout
- **WHEN** an in-view node's label is truncated on the island's canvas and a remembered node is presented alongside it
- **THEN** the in-view node's full label is still available as its on-canvas accessible name and the remembered node's name is still readable — as its marker's visible text on the lattice variant, as its entry's visible text on the graph variant, and untruncated through the surface's text alternative — so removing the readout's label content makes no node's name unreachable

#### Scenario: A screen-reader user can still reach every remembered place
- **WHEN** a screen-reader user reads the minimap island on a wilderness payload carrying several remembered gateways, none of which is focusable and each of which is drawn inside the map graphic
- **THEN** the island exposes one text-alternative entry per drawn marker, in a deterministic order, each stating that place's untruncated authored name and its direction as one of the eight octant names, so no remembered place is reachable only by sight

#### Scenario: Replacing the list adds no tab stop and no activation
- **WHEN** a keyboard user tabs through the island on a payload carrying the maximum number of remembered gateways
- **THEN** the island still offers exactly one tab stop — its full-map affordance — neither an edge direction marker nor the text alternative is focusable, and activating anything on the island still opens only the full-map surface or submits only a lattice node's own move

#### Scenario: A coordinate-free layer asserts no orientation and no coordinates
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure, the map title renders exactly as on a coordinate-bearing layer, and the readout line — having nothing to state — states nothing and paints no box

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
- **WHEN** a graph-variant payload combines a tall in-view placement with a long remembered-node list (up to the model's 64-node bound)
- **THEN** the canvas's height cap shrinks to the space the anchor's height budget — measured from geometry the canvas does not move — leaves after the meta line and that list, counting only the sections actually laid out and one gap per gap between them, so no required island content has to be scrolled out of view

#### Scenario: The name gutter never hands the anchor a scrollbar
- **WHEN** a lattice payload's remembered markers crowd one canvas edge so the model grows the marker gutter, enlarging the canvas's natural width and height well beyond the placement's own size
- **THEN** the island's rendered canvas height is still at most the measured height cap — the width bound resolves the enlarged aspect ratio rather than being reconciled against the cap afterwards — the island's total height stays within the anchor's budget, the hud-right anchor shows no scrollbar, and re-measuring the settled island yields the same cap

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay renders the identical in-view nodes and edges the minimap island renders — in the same resolved layout variant — plus the state legend the island omits, sized to the overlay surface's own available width and height, with no marker or label collisions at that larger scale, and with no coordinate figure on the overlay surface

#### Scenario: The full-map overlay omits the remembered-node list and the readout line
- **WHEN** the full-map overlay is open with an available `local_map` payload
- **THEN** the overlay body shows only the map canvas in the resolved variant and its state legend, and does not render the minimap island's remembered-node list or its coordinate readout line

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

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** the reported wilderness shape renders on the island with named edge markers — a three-column by three-row in-view lattice whose natural canvas is 174 × 146 user units at the island's marker geometry
- **THEN** the island's declared name geometry reserves only the band's depth, so the marker gutter grows from 26.46 to 44.46 user units rather than to the 83.46 that an outward, edge-perpendicular name box of the overlay's width would demand, the drawn lattice keeps 136 of its 158 CSS px instead of collapsing to 105 CSS px — which is narrower than the 112 CSS px the island was reported as broken at — and each marker name renders at the island's own smallest legible type step rather than at the 6.6 CSS px the outward box would leave it

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
- **WHEN** the committed payload's server-authored title is long enough that the title and the orientation marks together exceed the island's content width (e.g. `冒險者公會外街道圖` beside the axis marks in a 210px content box)
- **THEN** the header stays a single row: the title renders on one line truncated with an overflow indicator while its complete string stays available as the element's tooltip/accessible text, the orientation marks keep their full size without wrapping, no full-map control occupies the row at all, and the island's card width is unchanged

#### Scenario: The readout follows the player after a move
- **WHEN** a newly committed payload replaces the rendered one with a different `current_node`
- **THEN** the readout line states the new payload's current node's coordinate figure rather than resolving to nothing or to the previous room, without any selection to re-seed, and the island shows no blank readout

#### Scenario: A readout with nothing to say draws no box
- **WHEN** the island's readout line has nothing to state
- **THEN** the line states nothing, paints no border or box, and reserves no height in the island's canvas budget

#### Scenario: The island offers exactly one full-map affordance, with no visible button
- **WHEN** an available `local_map` payload renders on the island
- **THEN** exactly one full-map affordance exists in the island, it is a `<button>` element spanning the island's whole box with 展開全地圖 as its accessible name, no labelled control or icon button is rendered in the island's header or anywhere else in the island, and the island's root element carries no role and no tab stop of its own

#### Scenario: A keyboard user opens the full map from the island
- **WHEN** a keyboard user tabs to the island's full-map affordance and presses Enter, and then repeats the run pressing Space
- **THEN** each activation opens the full-map surface exactly once through the button element's own platform behaviour, with no key handler on a non-button element involved, and the focus-visible indication while it is focused delineates the whole island rather than a small corner of it

#### Scenario: Activating a lattice node moves instead of opening the map
- **WHEN** the player clicks an actionable in-view lattice node, its marker, an edge direction marker, a graph-variant remembered entry, or the full-map affordance itself
- **THEN** a click on the node or its marker submits that node's move and emits no map-open, a click on an edge direction marker or on a remembered entry — neither of which carries any behaviour of its own — falls through to the island body and opens the full-map surface exactly once, a click on the affordance opens the full-map surface exactly once, and a click on the island's plain body opens the full-map surface exactly once

#### Scenario: Closing the full map returns focus to the island affordance
- **WHEN** the player opens the full-map surface from the island and then closes it
- **THEN** the element captured as the opener is the island's full-map affordance, that element still exists after the payload commits that arrived while the surface was open, and focus is restored to it

#### Scenario: The readout renders in the draft's token-driven treatment
- **WHEN** the island renders its coordinate readout
- **THEN** the line is centred beneath the canvas at the island's smallest type step in the shared monospace font token, its colour resolves to a design token whose contrast against the island's panel background is at least 4.5:1, it draws no border, background fill, or padded box, and no draft hex value or draft-canvas pixel literal is hardcoded for it
