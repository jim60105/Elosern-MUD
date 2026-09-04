## Purpose

The read-only version-1 `local_map` panel payload, the grid/anchor, wilderness, and
instance/interior layer adapters, the visibility states and legend, the bounded serialization the
server and browser validators share, and the minimap renderer that replaces the desktop-shell
placeholder.
## Requirements
### Requirement: local_map is a read-only version-1 presentation panel
The production presentation registry SHALL register panel name `local_map` at schema version 1. Its
available payload SHALL contain exactly `schema_version`, `available`, `layer`, `current_node`,
`title`, `nodes`, `edges`, and `legend`; `available` SHALL be true. `layer` SHALL be one of `grid`,
`wilderness`, `instance`, or `interior`; `current_node` SHALL be a canonical node ID; `title` SHALL be
a bounded localized map title. `nodes` SHALL be a bounded list where each node contains exactly
`id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`, and nullable `action`; node
`x`/`y` are renderer-local presentation geometry, not canonical world coordinates: they place a node in
the current view (adjacency or visual-range position), and a node's identity NEVER forces its geometry
to equal its own world coordinates — a gateway node shown on a layer other than its home layer keeps
the adjacent position of the step that reaches it, and the payload NEVER invents an identity for a
position. `edges` SHALL be a bounded list where each edge contains exactly `source`, `destination`,
`label`, `known`, and `traversable`. `legend` SHALL be a bounded list of text label entries. The
presenter SHALL build the payload only from canonical room/map/knowledge data, SHALL emit no live
object or filesystem reference, SHALL NOT mutate knowledge, traits, clock, or location, and SHALL use
the registered common unavailable form when the current room cannot be represented. On the
wilderness layer, a direction whose neighbor is provider-invalid — outside the continent rectangle or
an anchor footprint cell — SHALL render no node and no walkable edge for that direction, exactly as
out-of-bounds directions render today; the payload NEVER presents an anchor footprint cell as a
walkable `wild:` node.

The exact bounds, shared unchanged by the server and client validators, SHALL be: at most 64 `nodes`,
at most 128 `edges`, at most 16 `legend` entries, node/edge/legend strings of at most 256 Unicode code
points, `title` of at most 128 code points, node IDs of at most 128 characters, renderer-local `x`/`y`
integers within `-1024..1024`, `known`/`traversable`/`current`/`anchor`/`landmark` as booleans,
`visibility` as one of `current`, `visible_unvisited`, `visible_visited`, or `remembered`, and `action`
as `null` or the exact `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node
id>}` object. Every conforming serialized payload SHALL fit within the 65,536-byte OOB envelope limit.
Conformance is enforced on serialized size: both the Python and JavaScript validators compute the
canonical UTF-8 byte length of the assembled payload and reject a payload that exceeds the envelope,
because the per-field ceilings are independent and a payload that maximizes every string field at once
would otherwise serialize beyond the limit. A worst-case serialization test proves a structurally
maximal realistic payload fits comfortably, and a second test proves a payload at every string ceiling
at once is rejected.

#### Scenario: A grid room produces a grid-layer payload
- **WHEN** the active puppet is in a `GridRoom`/`AnchorRoom` with knowledge and an adjacent traversable
  grid exit
- **THEN** `local_map` reports `layer == "grid"`, the current node's `grid:` ID, bounded nodes and
  edges, and a before/after comparison of canonical game state is unchanged

#### Scenario: A wilderness room produces a wilderness-layer payload
- **WHEN** the active puppet is in a `TerrainRoom`
- **THEN** `local_map` reports `layer == "wilderness"`, the current `wild:` node, legal adjacent
  coordinates bounded by provider validity, and terrain labels, except that a registered gateway
  direction renders the resolved `grid:` gate node instead of the geometric wild cell, and a
  provider-invalid direction (out of bounds or an anchor footprint cell) renders neither node nor
  walkable edge

#### Scenario: An instance room produces a coordinate-free instance payload
- **WHEN** the active puppet is in an `InstanceRoom`
- **THEN** `local_map` reports `layer == "instance"` with a `room:<dbref>` current node and a small
  graph containing the current node, its origin/return, and known real Exit edges, with no `grid:` or
  `wild:` identity invented for it

#### Scenario: An ordinary interior produces an interior payload
- **WHEN** the active puppet is in a permanent interior `Room` such as the guild hall or general store
- **THEN** `local_map` reports `layer == "interior"` with a coordinate-free graph of real Exits

#### Scenario: A gateway step never renders the wild cell it replaces
- **WHEN** the puppet stands at a registered gate approach cell and the gateway direction resolves to
  a grid node
- **THEN** no node with the geometric wild cell's `wild:` ID exists in the payload for that direction,
  and the gateway node carries the gate's `grid:` ID positioned at the adjacent cell

#### Scenario: An anchor footprint renders as absent ground, not a walkable cell
- **WHEN** the puppet stands at any wilderness cell adjacent to the `capital_altoria` footprint and
  NOT on a gate approach cell (e.g. `(57, 100)` facing east toward `(58, 100)`, or `(59, 97)`
  facing north toward `(59, 98)` — `(60, 97)`/`(60, 103)` face the footprint too but their
  footprint-facing direction is the registered gateway, which renders per the gateway rules) and
  the panel is built
- **THEN** no `wild:` node with a footprint cell's coordinate exists in the payload, the direction
  toward the footprint carries no move action, and the direction is presented exactly like today's
  out-of-bounds edge

#### Scenario: An unrepresentable room is unavailable, not fabricated
- **WHEN** the active puppet has no location, the location cannot be represented, or the knowledge
  record is corrupt
- **THEN** `local_map` uses the common schema-valid unavailable form with a stable reason and contains
  no invented nodes, coordinates, or edges

#### Scenario: Presenter failure remains isolated
- **WHEN** the `local_map` presenter raises while status and narrative remain healthy
- **THEN** only `local_map` becomes correlated unavailable and normal text output remains usable

### Requirement: Visibility states are current, visible_unvisited, visible_visited, and remembered
Every node in the version-1 payload SHALL carry exactly one `visibility` value. `current` SHALL mark
the player's current node. `visible_unvisited` SHALL mark a node inside the current field of view
(visual range for grid, legal adjacency for wilderness, a currently visible one-hop Exit for
instance/interior) that has not been entered. `visible_visited` SHALL mark a node inside the current
field of view that was previously entered. `remembered` SHALL mark a previously entered node outside
the current field of view. Visibility SHALL be keyed on the node's canonical identity — the same ID
the resolver and the knowledge record use — including for a gateway node rendered on a layer other
than its home layer, so a gate the player has walked through reads `visible_visited` wherever it is
drawn. Unknown nodes SHALL be omitted entirely — never sent as hidden records. The payload SHALL
remain within the OOB envelope limits, with remembered nodes bounded by most-recent `last_seen` and
current/visible nodes always included first.

#### Scenario: Visited interior nodes retain their visited visibility
- **WHEN** a node inside an interior/instance local graph has been entered before
- **THEN** it is `visible_visited` (or `remembered` when no longer adjacent) and carries its canonical
  room name as label

#### Scenario: A walked-through gate is visited on the far side too
- **WHEN** the player entered the wilderness through a gate and the opposite layer now draws that
  gate's node
- **THEN** the gate node is `visible_visited` because the knowledge record contains its canonical ID

#### Scenario: Unknown nodes are absent from the payload
- **WHEN** a map adapter computes the current view for a room
- **THEN** coordinates or rooms the player has never seen and that are outside the current field of
  view are absent from `nodes` and `edges`

#### Scenario: Remembered nodes are bounded and deterministic
- **WHEN** the remembered set exceeds the configured cap
- **THEN** the payload keeps the most-recent `last_seen` entries in deterministic order and never
  exceeds the bound

### Requirement: Only currently traversable Exits receive movement descriptors
A node's `action` SHALL be null unless that node is associated with a currently present, traversable
`Exit` from the actor's current room. The association SHALL follow the arrival the step actually
performs: for a wilderness direction and for a registered wilderness gate exit — whose stored
`destination` is a self-loop and never names the arrival — the associated node is the canonical node
the traversal resolver derives from the step, not the exit's stored destination. For such a node,
`action` SHALL be exactly `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node
id>}` where `exit_ref` is an opaque server-authored identifier and `destination` is the canonical
destination node ID and equals the ID of the node carrying it. Remembered remote nodes SHALL carry
`action: null` and SHALL provide no travel descriptor. The browser SHALL NOT be able to submit
movement through a node with `action: null`, and an `action` with an unknown `kind`, an oversized or
non-ASCII `exit_ref`, or a missing/invalid `destination` SHALL be rejected by the exact schema
validator.

#### Scenario: Adjacent traversable exits carry a movement descriptor
- **WHEN** the current room has a traversable exit leading to an adjacent node
- **THEN** that destination node's `action` is the exact `move` object and identifies the opaque exit
  reference and destination node

#### Scenario: A gateway exit names the arrival node, not its self-loop
- **WHEN** the current room holds a traversable gateway exit whose stored destination is itself (the
  wilderness gate pair)
- **THEN** the node the step reaches carries that exit's move descriptor whose destination equals the
  resolver's arrival node ID

#### Scenario: Remembered remote nodes carry no travel action
- **WHEN** a remembered node outside the current field of view is inspected
- **THEN** its `action` is null and it cannot submit any travel action

#### Scenario: Malformed movement descriptors are rejected
- **WHEN** a payload contains an action with an unknown `kind`, an `exit_ref` outside 1..64 ASCII
  characters, or a non-canonical or missing `destination`
- **THEN** the exact schema validator rejects the panel and the minimap renderer disables only itself
  with the single-sync recovery path

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

### Requirement: Adjacent traversable map nodes submit explore.move through their move descriptor
The WebClient `local-map` component SHALL make a currently traversable adjacent node with an exact `move` action descriptor actionable: activating it (click or Enter on the focused node) SHALL submit the `explore.move` UI action carrying that node's opaque `exit_ref` and the canonical `current_node` identity. A node with `action: null`, a remembered remote node, or a node whose `visibility` is not a current-field-of-view state SHALL NOT submit any travel action and SHALL remain inert or focus-only exactly as before. The component SHALL derive the submitted `exit_ref` and `current_node` only from the validated `local_map` payload, SHALL NOT construct an exit reference, destination, or room identity from entity data or prose, and SHALL leave the `local_map` panel payload contract, the `未探索` unvisited-node rule, and the remembered-node no-travel rule unchanged. On a successful or rejected submission the refreshed `local_map` payload at the newer revision SHALL replace the rendered minimap; the component SHALL NOT keep a client-side canonical map cache. The corrected node-pitch geometry (this change) SHALL NOT alter which node an activation targets: the enlarged marker's clickable/focusable area SHALL remain centered on the same lattice coordinate the payload assigned it. This activation behavior SHALL be identical whether the lattice renders inside the minimap island or inside the full-map overlay, since both consume the same shared lattice-rendering logic.

#### Scenario: Activating an adjacent traversable node submits explore.move
- **WHEN** the player focuses an adjacent traversable node whose `action` is the exact `move` object and confirms it
- **THEN** the browser submits exactly one `explore.move` envelope with that node's `exit_ref` and the panel's `current_node`, and the refreshed `local_map` payload replaces the rendered map

#### Scenario: A remembered remote node still offers no travel action
- **WHEN** the player focuses a remembered remote node (which carries `action: null`)
- **THEN** its name/landmark is shown and no `explore.move` or other travel submission is possible, matching the pre-existing rule

#### Scenario: A map node never invents a destination
- **WHEN** a node's `action` is missing, malformed, or not the exact `move` object, or the payload is rejected by its validator
- **THEN** no travel action is submitted, only the minimap renderer disables itself with the single-sync recovery path, and narrative and text input remain usable

#### Scenario: The wider marker geometry still targets the correct node
- **WHEN** the player activates a node marker after the pitch/sizing fix has been applied
- **THEN** the `explore.move` submission carries the same node's `exit_ref` and destination as before the
  fix, unaffected by the marker's new visual size or position within its (now larger) cell

#### Scenario: Move submission works identically from the full-map overlay
- **WHEN** the player activates a traversable adjacent node while the full-map overlay is open
- **THEN** the browser submits exactly one `explore.move` envelope — the same submission the minimap island
  produces for the same payload, since both surfaces share the same lattice-rendering logic

### Requirement: Wilderness minimap nodes are actionable
Every traversable adjacent wilderness node in the local map SHALL carry an `explore.move` action
descriptor with the canonical destination node, matching the grid/interior layers' behavior. Where a
direction is a registered gateway step, the node it renders IS the resolved `grid:` gate node — its
id, label (the gate room's canonical name), landmark flags, and action destination all identify that
gate node, and no geometric `wild:` cell stands in for it.

#### Scenario: Adjacent wilderness node can be moved to
- **WHEN** the player opens the local map while in wilderness terrain
- **THEN** each traversable adjacent node has a move action whose destination is the canonical node, and activating it moves the player there

#### Scenario: The gate approach cell shows the gate, not terrain
- **WHEN** the player stands at a registered gate approach cell and opens the local map
- **THEN** the gateway direction's node is the gate room's `grid:` node labelled with the room's name, and activating it arrives in that room

#### Scenario: Non-traversable or unreachable nodes stay inert
- **WHEN** a wilderness node is outside the traversable set (e.g. out of bounds or an anchor footprint cell)
- **THEN** the node carries no move action

### Requirement: The minimap gate nodes match traversal in both directions
For every gate of every entry in the wilderness entry registry, the minimap SHALL present the gateway
as a matched pair of edges on both sides: standing at the gate's approach cell, the gateway direction
(`return_direction`) SHALL render the gate's grid node (canonical `grid:` id, gate room label,
resolver-derived visibility, move descriptor with that id as destination); standing at the gate room,
the grid layer SHALL render that gate's approach cell's `wild:` node (canonical `wild:` id for the
approach cell, the region's display name, knowledge-derived visibility, move descriptor whose
`exit_ref` is that gate's exit and whose destination is that `wild:` id). The rendered destination
SHALL always equal the node carrying it, SHALL always equal what `resolve_wilderness_destination`
derives from the same registration the traversal code reads, and a pinning test SHALL move a
character through each real gateway exit in both directions and compare the committed node against
the actual arrival. Node identity and direction deltas for these nodes SHALL come from that same
single resolver source, never from a duplicated table. The gate node SHALL NEVER be silently
omitted: registered-gate capacity SHALL be reserved before ordinary visible nodes are collected
(excess visible nodes trimmed farthest-first in deterministic order), and when the gate's preferred
renderer-local slot is occupied the gate node SHALL take the nearest free slot in deterministic probe
order instead of being dropped.
On the grid layer specifically, the gate candidate's `wild:` identity and label SHALL derive from
the provisioned exit's `db.gate_direction` resolved through the registry to that gate's
`approach_cell`, and the candidate's slot direction SHALL be the direction of the exit connecting
the gate room — never from parsing the gate exit's key or aliases (all wilderness-side gate exits
share the key `荒野`, and key aliases are display affordances, not identity), and never from the
entry's anchor cell as a stand-in for a per-gate approach cell.

Both deterministic orders are part of this contract: the capacity trim SHALL drop visible nodes in
descending Chebyshev distance from the current node, then descending Y, then descending X (the current
node never dropped), and the slot probe SHALL scan the preferred slot first when it is free and inside
the payload coordinate bounds, then rings of ascending Manhattan distance from it in ascending Y-offset
then ascending X-offset order, taking the first slot that is inside the coordinate bounds and free.

#### Scenario: Wilderness side shows the gate room
- **WHEN** the puppet stands at a registered gate approach cell (e.g. `(60, 103)` for the north
  gate) and the `local_map` panel is built
- **THEN** the gateway direction carries the gate room's `grid:` node with the room's name as label,
  an action whose destination equals the node id, and the geometric wild cell for that direction is
  absent from the payload

#### Scenario: Gate side shows the wilderness approach cell
- **WHEN** the puppet stands at the gate room and the `local_map` panel is built
- **THEN** a `wild:` node for that gate's approach cell exists with the region's display name, a
  move action whose `exit_ref` is that gate's exit, and activating it enters the wilderness at that
  cell

#### Scenario: Both gates of one anchor render independently on both sides
- **WHEN** the puppet stands at either approach cell of `capital_altoria`, or inside either city
  gate room, and the panel is built
- **THEN** only that gate's node appears for that direction — the other gate is not rendered at the
  wrong side or direction — and each gate's pair (approach cell ↔ gate room) round-trips through
  activation

#### Scenario: Gate identity survives identical keys and rewritten aliases
- **WHEN** both provisioned gate exits carry the identical key `荒野` (as `sync_wilderness()`
  creates them) with arbitrary aliases, and the grid layer is built from each gate room
- **THEN** each gate room's payload shows the `wild:` node for its OWN gate's approach cell at the
  slot of its own exit — neither room renders the other gate's approach cell, and no candidate is
  dropped to key-based deduplication

#### Scenario: Both directions agree with real traversal
- **WHEN** a test walks a character through a gateway exit into the wilderness and back through the
  return exit, building the panel at each end, for each registered gate
- **THEN** every rendered gateway node's id and action destination equal the actual arrival node the
  traversal produced, in both directions

#### Scenario: An unregistered direction stays ordinary terrain
- **WHEN** a wilderness direction at any coordinate is not a registered gateway step and its
  neighbor is provider-valid
- **THEN** its node is the ordinary geometric `wild:` cell with its terrain label, exactly as before

#### Scenario: A crowded gate room keeps both the neighbor and the gate
- **WHEN** a gate room has an in-range grid node occupying the gate's preferred renderer-local slot
- **THEN** the payload contains the in-range grid node AND the gate's `wild:` node at a free probed
  slot, both with their actions, and the payload passes the exact validator

#### Scenario: Gate capacity never breaks the node bound
- **WHEN** the visible set would fill the full node cap at a room that also holds a registered gate
  exit
- **THEN** the payload contains at most the capped number of nodes, the gate node is present, and the
  trim removes only farthest visible nodes in deterministic order

### Requirement: The wilderness payload legend states the cell scale from the provider constant
The `local_map` presenter SHALL, for the `wilderness` layer only, append one localized scale note
to the payload `legend` after the four visibility-state labels, whose text states the wilderness
cell size in kilometres derived at build time from
`world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` — no module or client code SHALL
duplicate the constant or the conversion. The four state labels SHALL keep their existing order
and positions, so the scale note is the fifth entry. Payloads for the `grid`, `instance`, and
`interior` layers SHALL keep their legend exactly as before (the four state labels). The extended
legend SHALL remain within the existing bounds (at most 16 entries, 256 code points each) and
SHALL pass both validators unchanged — no payload schema field is added or altered.
The presenter SHALL read the constant as an attribute of its owning module at legend-assembly
time (never a value imported into the presenter's own namespace), so patching the provider
module attribute is observed by the presenter.

#### Scenario: A wilderness payload legend carries the scale note
- **WHEN** the `local_map` presenter builds an available payload for a `TerrainRoom`
- **THEN** the legend is the four state labels followed by one entry whose text contains the
  string form of `WILDERNESS_KM_PER_CELL` (e.g. `每格約 10 公里`), and the payload passes the
  exact Python validator

#### Scenario: Non-wilderness layers are untouched
- **WHEN** the presenter builds available payloads for grid, instance, and interior rooms
- **THEN** each legend equals the four state labels exactly, with no scale note

#### Scenario: The scale note follows the single constant
- **WHEN** a test patches `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` to a
  different integer and rebuilds a wilderness payload
- **THEN** the scale note's kilometre figure equals the patched value, proving the note is
  derived from the provider constant rather than a duplicated literal

### Requirement: The legend renders beyond-state entries as neutral info chips
The shared map renderer SHALL render each legend entry beyond the four visibility-state labels
with a dedicated neutral info-chip treatment — design-token colors only, text as the primary
carrier — and SHALL NOT style it by cycling the four state chip styles. The first four entries
SHALL keep their state chip treatments and order exactly as before, the overlay SHALL remain the
only legend surface (the minimap island renders no legend element for any payload), and the
info entry's distinction from state entries SHALL NOT rely on colour alone.

#### Scenario: The overlay shows four state chips and one info chip
- **WHEN** the full-map overlay renders a wilderness payload whose legend carries the scale note
- **THEN** the legend lists five entries, the first four keep their state chip treatments in the
  fixed order, and the fifth renders with the neutral info-chip treatment distinct from all four
  state treatments

#### Scenario: Extra entries never masquerade as visibility states
- **WHEN** a payload legend carries any entry beyond the fourth (present-day or future)
- **THEN** that entry renders with the info-chip treatment, not with any of the four state chip
  classes, and its text label is rendered in full

#### Scenario: The island still renders no legend
- **WHEN** a wilderness payload with the scale note renders on the minimap island
- **THEN** no legend element exists anywhere in the island's DOM, exactly as for every other
  payload

