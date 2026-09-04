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
position. A `remembered` node on a coordinate-bearing layer (`grid`, `wilderness`) is the one node kind
that has no step to position it, so its `x`/`y` SHALL be that node's own validated coordinates **in the
layer currently being drawn** — the gateway's wilderness-side approach cell on the `wilderness` layer,
the gateway's grid-side room coordinates on the `grid` layer — and SHALL NEVER be coordinates read from
a different coordinate space nor a renderer-local or probed slot, because the current node and every
remembered node must sit in one coordinate space for the raw-delta direction geometry to mean anything.
A node whose identity carries no coordinate in the layer being drawn — a registered gateway whose
grid-side room belongs to a different `z_map_key` than the map the `grid` layer is drawing — SHALL be
omitted from the payload entirely rather than plotted at a fabricated, probed, cross-space, or
current-node position; it remains fully presented on the payload of the layer it does have a
coordinate in. `edges` SHALL be a bounded list where each edge contains exactly `source`, `destination`,
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
at once is rejected. The presenter MAY apply its own tighter internal ceilings — such as the remembered
gateway cap — without changing any shared bound; no presenter-side ceiling is mirrored in the client
validator and none alters this table.

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

#### Scenario: A remembered node is never plotted from a cross-coordinate-space position
- **WHEN** a payload is built on a coordinate-bearing layer while the player's knowledge contains a
  registered gateway's node on the other side of that gateway — the gate room's `grid:` node while the
  `wilderness` layer is drawn, or the approach cell's `wild:` node while the `grid` layer is drawn
- **THEN** every `remembered` node in the payload carries the ID grammar of the layer being drawn with
  its own coordinates in that layer's space, no node carries a coordinate taken from the other space,
  and no `remembered` node is positioned at a renderer-local slot, a free-slot probe result, or the
  current node's coordinates

#### Scenario: A gateway with no coordinate in the drawn layer is omitted, not fabricated
- **WHEN** the `grid` layer draws a map while the player remembers a registered gateway whose grid-side
  room belongs to a different `z_map_key`
- **THEN** no node for that gateway exists in the payload at all, the payload passes the exact
  validator, and the same gateway still appears on the payload of the layer whose coordinate space it
  belongs to

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
field of view that was previously entered.

`remembered` is layer-scoped. On the coordinate-free layers (`instance`, `interior`) it SHALL mark a
previously entered node outside the current field of view. On the coordinate-bearing layers (`grid`,
`wilderness`) it SHALL mark **a map boundary the player has stood on** — a node outside the current
field of view whose traversal takes the player onto a different map — and nothing else: a visited node
that is not such a boundary SHALL NOT be emitted on those layers, so walking a region can never
accumulate one indistinguishable entry per visited cell.

A boundary SHALL be resolved at presentation time against the authored wilderness entry registry
(`world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY`) — the same registry the traversal code and
the in-view gateway nodes read — and never against a flag in the stored knowledge record, which carries
only node identity and ticks. On the `wilderness` layer a visited `wild:` node SHALL be a boundary when
its coordinates equal `entry.approach_cell(gate)` for some registered entry and gate; on the `grid`
layer a visited `grid:` node SHALL be a boundary when its coordinates and map key equal some registered
gate's `grid_xy` and `z_map_key`. Being an `AnchorRoom`, a landmark, or a node of any other in-map
significance SHALL NOT by itself make a node a boundary; a place inside the same map is not a way out
of it.

A boundary SHALL be `remembered` only when the player's stored knowledge record contains **the exact
canonical node ID the drawn layer carries it as** — the approach cell's `wild:` ID on the `wilderness`
layer, the gate room's `grid:` ID on the `grid` layer. A boundary the player has never entered on the
side being drawn SHALL be absent from the payload.

A remembered boundary SHALL be labelled with the authored name of the place its traversal reaches,
never with the terrain or region the boundary itself stands on: on the `wilderness` layer the entry's
anchor display name from the anchor registry, and on the `grid` layer the display name of the
wilderness region the gate's approach cell lies in. Remembered boundary labels within one payload SHALL
be distinct; where two boundaries would carry the same far-side name, each SHALL be qualified with the
canonical name of the boundary node it carries. A remembered boundary SHALL carry `landmark: true`,
`anchor: false`, and `action: null`.

Visibility SHALL be keyed on the node's canonical identity — the same ID
the resolver and the knowledge record use — including for a gateway node rendered on a layer other
than its home layer, so a gate the player has walked through reads `visible_visited` wherever it is
drawn. Unknown nodes SHALL be omitted entirely — never sent as hidden records. The payload SHALL
remain within the OOB envelope limits, with remembered nodes bounded by most-recent `last_seen` and
current/visible nodes always included first. Remembered nodes SHALL additionally be bounded by a
declared presenter ceiling of at most 16 remembered nodes, and SHALL be ordered by descending
most-recent `last_seen` tick then ascending canonical node ID, so the same knowledge record and world
state always produce the same nodes in the same order.

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

#### Scenario: Walked wilderness ground is not remembered
- **WHEN** the player has walked many cells of one wilderness region — enough that the old rule would
  emit seven or more remembered cells — and none of those cells is a registered gate approach cell
- **THEN** the payload contains no `remembered` node for any of them, and in particular contains no two
  `remembered` nodes carrying the same region display name as their label

#### Scenario: A stood-on gateway is remembered from the wilderness
- **WHEN** the player has entered a registered gate's approach cell, has since moved several cells away
  so that the cell is outside adjacency, and the wilderness payload is built
- **THEN** the payload carries exactly one `remembered` node whose ID is that approach cell's `wild:`
  ID, whose `x`/`y` are that cell's wilderness coordinates, whose label is the entry's anchor display
  name, with `landmark: true`, `anchor: false`, and `action: null`

#### Scenario: A point-shape cave entry is remembered by its own name
- **WHEN** the registry holds a one-`#` point-shape entry (cave semantics) whose anchor cell the player
  has entered, and the player is elsewhere in the wilderness
- **THEN** the payload carries a `remembered` node at that anchor cell's coordinates labelled with the
  cave's anchor display name, resolved by exactly the same predicate as a city gate

#### Scenario: A gateway the player has never reached is absent
- **WHEN** a registered gateway exists in the registry and the player's knowledge record does not
  contain the canonical node ID the drawn layer would carry it as
- **THEN** no node for that gateway appears in the payload in any visibility state, whatever the player
  has visited elsewhere in the same region or on the far side of that gateway

#### Scenario: A remembered gateway is named for where it leads, not what it stands on
- **WHEN** a remembered gateway is emitted on either coordinate-bearing layer
- **THEN** its label is the authored name of the place on the far side of its traversal, and it is not
  the display name of the wilderness region the approach cell sits in (on the `wilderness` layer) nor
  any name derived from the node's own terrain

#### Scenario: Two gateways onto one far side stay distinguishable
- **WHEN** the payload remembers two registered gateways whose far sides carry the same authored name —
  on the `grid` layer, the two city gates that both open onto one wilderness region; on the
  `wilderness` layer, the two gates of one anchor that share one anchor display name, since a single
  registered entry MAY carry more than one gate
- **THEN** the two nodes carry distinct labels, each qualified with the canonical name of its own
  boundary node, and no two `remembered` nodes in the payload share a label

#### Scenario: An in-map landmark is not a way out of the map
- **WHEN** the player has entered an `AnchorRoom` that is not a registered gate room, then moved beyond
  visual range of it on the same grid map
- **THEN** that room is absent from the payload rather than emitted as a `remembered` node, and its
  `landmark` significance is unchanged wherever it is genuinely in view

#### Scenario: Coordinate-free layers keep the previously-entered meaning
- **WHEN** an instance or interior payload is built for a player who has entered other rooms of the
  same building
- **THEN** those rooms are still emitted as `remembered` nodes with their canonical room names, exactly
  as before, because those layers assert no bearing and carry no map boundary registry

#### Scenario: Remembered nodes are bounded and deterministic
- **WHEN** the remembered set exceeds the configured cap
- **THEN** the payload keeps the most-recent `last_seen` entries in deterministic order — descending
  last-seen tick then ascending node ID — never exceeds the declared remembered ceiling of 16, never
  exceeds the shared node bound, and never displaces a current or in-view node

### Requirement: The map surfaces state a place name only where it adds information
The in-view neighbourhood SHALL NOT repeat one place name across every cell it draws. On the
`wilderness` layer, an in-view `wild:` neighbour whose coordinates are a registered gate's approach
cell SHALL be labelled with that entry's anchor display name — the place the gateway leads to — instead
of the display name of the region the cell lies in; its node ID, `action`, edges, visibility, and every
other field SHALL be unchanged, so the payload states a better name for the same position and never
invents an identity for it. Every other in-view cell SHALL keep the region display name it carries
today, and every emitted node label SHALL remain a non-empty string.

On a payload whose `layer` is `wilderness`, the shared map renderer SHALL NOT draw visible label text
for an in-view node whose label string is identical to the `current` node's label string; that node
SHALL keep its full label as its accessible name, and its marker, shape ladder, landmark treatment, and
activation SHALL be unaffected. The `current` node SHALL always draw its own label. The suppression is
scoped to the `wilderness` layer because that layer's labels are shared region names, where a repeat is
the reported defect; on `grid`, `instance`, and `interior` layers a label is an individual room name,
where two distinct rooms sharing a name are still two distinct places and SHALL both draw their label.
This suppression is a drawing rule about the set on the canvas, not a payload rule: no payload field
changes, and both validators keep their existing bounds and their non-empty label rules unchanged.

#### Scenario: The wilderness neighbourhood stops repeating one region name
- **WHEN** the island renders a wilderness payload whose current cell and all eight in-view neighbours
  lie in one region
- **THEN** exactly one visible label is drawn — the current node's — and the eight neighbours draw no
  visible label text while each keeps its full label as its accessible name

#### Scenario: An in-view gate approach cell names the place behind it
- **WHEN** the player stands one cell from a registered gate's approach cell, so the approach cell is
  an in-view neighbour
- **THEN** that neighbour's label is the entry's anchor display name rather than the region display
  name, its node ID is still the approach cell's `wild:` ID with its unchanged action and edge, and
  because the label differs from the current node's label the renderer draws it as visible text

#### Scenario: A cell in a different region still says so
- **WHEN** an in-view neighbour lies in a different wilderness region than the current cell
- **THEN** its region display name differs from the current node's label, so the renderer draws it as
  visible text and the region change stays visible

#### Scenario: Suppressed labels never weaken the state ladder or activation
- **WHEN** a node's visible label is suppressed as a duplicate of the current node's label
- **THEN** its marker shape, landmark treatment, `data-node` identity, move action, and accessible name
  are all unchanged, and the four visibility states remain distinguishable without colour

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
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels on the full-map overlay (the minimap island mounts no state legend), SHALL make every `remembered` remote node's name readable without any travel action and without any activation — as visible text on the surface that draws it and, wherever that visible text can be truncated or is drawn inside a graphic, as an assistive-technology text alternative carrying the untruncated name — and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

The island and the full-map overlay SHALL present the redesign draft's map visual language: every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value. On either placement's canvas the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment. The resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the geometry guarantee so the non-overlap invariant is unaffected. Node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far). Each surface SHALL declare its own node-label type size, and that size SHALL keep the draft's label-to-canvas type proportion (the draft draws its lattice labels at 4.44% of its canvas width) and SHALL NOT resolve to drawn text larger than the surface's own smallest chrome type step, so a node label can never out-weigh the island's own title at any payload.

The lattice variant SHALL additionally draw the redesign draft's coordinate-field layers, which are pure decoration: each SHALL be non-interactive, SHALL be excluded from the accessibility tree, SHALL carry neither the node-marker nor the node-label component class that the geometry audit pairs every box of, SHALL introduce no tab stop, activation, or `data-node` identity, SHALL be static so the reduced-motion preference has nothing to disable, and SHALL encode no visibility state — the four-state shape ladder, its non-colour redundancy, the colourblind override, and every focus treatment SHALL be unaffected by their presence. Every colour they use SHALL resolve to a design token and no draft hex value SHALL be hardcoded for any of them. The three layers are:

1. **The coordinate dot field.** The lattice SHALL paint one dot per coordinate cell across its whole canvas, beneath every connector edge, node marker, node label, and axis line. The field's horizontal and vertical dot pitch SHALL equal the drawn column and row pitch, so one dot spacing is exactly one coordinate cell on each axis and the field states the coordinate space the lattice claims rather than a decorative texture; the field SHALL be registered to the exported placement, so for every drawn node a dot position coincides with that node's centre. Because the field is painted beneath the markers, an occupied cell SHALL show its node marker and never a marker and a dot together. The dot SHALL NOT read as a fifth node state: its radius SHALL scale with the marker ladder and SHALL remain strictly and materially smaller than the smallest node marker's radius, it SHALL carry no stroke, no label, and no state class, and the state legend SHALL gain no entry for it, so the legend's four states stay closed exactly as the beyond-state note rule requires.
2. **The knowledge-edge vignette.** Each map surface SHALL paint exactly ONE vignette treatment that darkens the canvas toward its edges, and that treatment SHALL be the knowledge edge — the limit of what the payload knows — and SHALL NOT be, or be styled as, terrain. It SHALL be a single full-canvas gradient wash with no fabricated geometry: no per-cell fill, no per-region fill, and no drawn shape tracing any terrain feature. The vignette SHALL NOT reduce the coordinate dot field below the presence floor below at any point of the canvas, so the far-field dots it is meant to make faint stay visible rather than being erased.
3. **The axis cross.** A surface SHALL draw a full-width and full-height axis line through the `current` node's drawn position ONLY where that same surface states the axis convention in words; a surface that states no orientation marks SHALL draw no axis, and the radial graph variant SHALL draw none on any surface because a graph asserts no axis. The axis SHALL be drawn beneath every node marker — it necessarily passes through the `current` node's own marker, which is what an origin is, and that crossing SHALL NOT be read as a violation of the non-overlap invariant, whose axis clause governs the edge direction markers in the gutter band.

The dot field's and the axis's presence and contrast SHALL be pinned as a band against the canvas ground, so neither an invisible layer nor one that out-shouts the drawing can ship. Each SHALL be present as a painted element whose resolved colour differs from the canvas ground; each SHALL keep a contrast ratio against that ground of at least 1.15:1 at every point of the canvas and at least 1.35:1 within the vignette's un-darkened inner field; and neither SHALL exceed the contrast that the connector-edge ink itself keeps against the same ground, so the coordinate decoration never reads louder than the topology it decorates. These layers are decoration, not information: the coordinate claim they picture is carried redundantly by the node placement itself, by the header's axis orientation marks, and by the readout's coordinate figure, so no reader depends on them — but the lattice's geometry is its claim, so they SHALL NOT be invisible.

Layout SHALL be computed in the DOM-independent render model, not as a rescaling of payload coordinates into a fixed pixel box, and the model SHALL export two placements for the same committed payload: a bounded integer lattice and a radial connected-graph. The lattice placement SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on it, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts; when that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The radial placement SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas; ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates. The radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant below is constructible from the model alone; neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning. The renderer SHALL size the map canvas from the exported placement and from the surface's own declared coordinate field, so the canvas reserves its own space **within the island's bounded height**, scaling the canvas rather than requiring the island to scroll a required surface out of view. On the island the canvas SHALL claim the island's content width rather than drawing at the placement's natural pixel size: the drawn map SHALL NOT be narrower than the island's content box merely because the payload is sparse. On a surface that declares a coordinate field, that claim SHALL be met by **coordinate margin, never by magnification**: the canvas's drawn extent SHALL be padded symmetrically around the node core, at the surface's designed pitch, up to the surface's own width cap, with the edge-marker band remaining the canvas's outermost band and the padded extent between the core and that band being coordinate space that the dot field paints. The uniform scale of such a surface's canvas SHALL therefore be exactly 1 whenever the drawing fits its caps and below 1 only when it does not, and SHALL NEVER exceed 1 — so no payload, however sparse, can inflate the designed marker radii, label size, or gutter offsets above the sizes the surface declares. Padding the extent SHALL NOT reduce the uniform scale below what the unpadded extent would have achieved: the margin taken on each axis SHALL be bounded by what that axis's own cap affords, so a payload whose height cap already binds takes no vertical margin at all. No maximum-upscale bound SHALL be needed or declared for such a surface, since there is no magnification left to bound. The renderer SHALL resolve every cap it is given — a maximum width and a height budget — into a single width bound it computes itself from the canvas's own aspect ratio, `min(maxWidth, maxHeight × canvasWidth / canvasHeight)`, never leaving a definite width to be reconciled against a height cap by engine-specific replaced-element constraint resolution; the resulting bound SHALL be floored rather than rounded up, so honouring it can never re-cross the height budget by a sub-pixel and force the anchor's scroll fallback. The canvas's height cap SHALL be derived from the space the hud-right anchor's bounded height budget leaves after the island's remaining laid-out sections — not from a fixed constant, and not from a fixed section list — so no other island content can force the island's `overflow-y` scroll fallback. Those sections are the meta line, the canvas, and at most one of the graph-variant remembered list and the coordinate readout line, since a payload whose layer resolves to the lattice renders no remembered list and a payload whose layer resolves to the graph states no coordinate figure; the separating-gap count SHALL be derived from the sections actually laid out rather than from a constant, so a section that renders nothing costs the canvas neither its own height nor a gap. The canvas's own natural size SHALL NOT be able to breach that cap however much the edge-marker gutter grows it: the gutter enlarges the canvas's natural width and height by the same amount, so the single width bound above resolves to a rendered height that is at most the height cap in every case. That height budget SHALL be a fixed point of the measurement it feeds: it SHALL be measured only from geometry that does not move when the canvas resizes — the island's own position and the position of the surface bounding it from below, less a fixed clearance — and SHALL NOT be derived from any quantity the canvas's own rendered size participates in, in particular not from the rendered height of the content-sized hud-right anchor, whose height IS the island's height while the island fits. Re-measuring an already-settled island SHALL yield the same cap, so repeated observer-driven measurement passes SHALL NOT walk the canvas down toward its floor. The renderer SHALL NOT allow map content to overlap the island's title, its orientation marks, the graph-variant remembered-node list, the readout line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's geometry — column pitch, row pitch, and marker sizing on the lattice, and ring radii, angular slots, and marker sizing on the radial graph — SHALL be chosen so that, at every placement the model can produce for either variant, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of any uniform scale-down applied to fit the island's bounded height (radial ring radii SHALL grow with ring member count so the angular arc between adjacent slots bounds the label footprint). A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The lattice's pitch SHALL be **derived from what actually needs clearing at the drawn placement, not asserted as a constant**, and the derivation SHALL be constructible from the model and the drawn label set alone so the invariant above holds at every placement the model can produce. Two clearance terms SHALL be honoured. The **bare term** applies to every adjacent pair: the pitch SHALL clear the widest drawn footprint of each of the two markers — including any decoration drawn over a marker, such as the actionable halo, not merely the marker shape itself — with a strictly positive gap, SHALL leave a strictly positive visible connector segment between them, and SHALL keep each node's own label box clear both of its own node's widest drawn footprint and of the widest drawn footprint of the node in the row beneath it. The **label term** applies only where two horizontally adjacent cells BOTH draw visible label text: there the pitch SHALL additionally clear both truncated label boxes side by side with a strictly positive gap, the worst case being `(labelMax + 1)` full-width glyphs at the surface's declared label type size. Where the drawn label set contains no such adjacent pair — which a payload whose neighbouring cells state no place name of their own produces — the label term SHALL NOT bind, and the pitch SHALL NOT be inflated to clear labels that are not drawn. The renderer SHALL NOT satisfy either term by truncating node labels more aggressively: `labelMax` is a legibility contract, and shortening it to buy pitch was rejected when the pitch was first derived. Both terms SHALL be satisfied by the same pitch on both axes, so a drawn lattice cell is **square**: an unequal pitch would draw a node at `(+1, +1)` along a different line than the edge direction marker for the same delta, which is computed from the raw coordinate delta, and the drawing and its bearings SHALL agree.

The map-rendering logic (node/marker placement consumption, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale, by layout variant (`lattice` or `graph`), and by an explicit legend-display switch rather than duplicated: the variant SHALL be resolved once, in the render-model layer, as a pure function of the payload's `layer` — the closed coordinate-bearing set (`grid`, `wilderness`) resolves to the lattice and every other layer resolves to the graph — and both surfaces consume that one resolved value, so island and overlay can never disagree. The shared renderer SHALL render the state legend wherever its display switch is on, SHALL default the switch to on, and the minimap island SHALL pass it off so no legend element is mounted on the island for any payload while the overlay renders the payload's full legend. No map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting. Both surfaces SHALL render the resolved variant's identical in-view nodes and edges for the same committed payload, the overlay sized to its own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the island's coordinate readout line; both remain minimap-island-only, since the overlay is sized to its own surface and states no coordinate figure at all, and the list is in any case an island-side, graph-variant-only presentation.

The full-map overlay's map surface SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a teardrop location-pin adornment anchored directly above the `current` node marker — an ornament of the real marker, not a second position claim. That background IS the overlay's one knowledge-edge vignette, so the overlay SHALL NOT paint a second wash over it, and the dot field's contrast against the overlay's own canvas ground SHALL satisfy the same presence band as on the island. The overlay legend SHALL render as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone.

The island SHALL carry the payload's `title`, and its header SHALL stay a single row at every authored title length. `title` is server-authored and bounded only by the payload's 128-code-point ceiling, so the header SHALL be a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and every other header item SHALL be fixed-size items that neither shrink nor wrap. The header SHALL carry no full-map control of its own: the island's single full-map affordance is the full-bleed element specified below, so the header's fixed-size items are the orientation marks and nothing else unless a later change adds one. No authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL occupy its anchor's full column width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length. On the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis). Node `x`/`y` carry layer-scoped semantics: on the closed coordinate-bearing set (`grid`, `wilderness`) they are validated world coordinates and MAY drive relative-direction geometry; on every other layer they are renderer-local layout values and SHALL NOT be read as direction, distance, or place. The island's readout line SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — whenever the payload layer is coordinate-bearing, and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place. The readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one. The island SHALL NOT state a coordinate figure for any node other than the `current` node, on any layer, and the full-map overlay SHALL NOT state a coordinate figure at all. No surface SHALL render a compass angle, a bearing angle, a distance, or any coordinate figure beyond the permitted current-node figure; in particular the remembered-node edge markers convey direction only and never gain a coordinate readout. On a coordinate-free layer there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box and reserving no height in the island's canvas budget, rather than presenting an empty bordered widget. Removing the readout's label content SHALL NOT make any node's name unreachable: each in-view node's full label SHALL remain available as its on-canvas accessible name, and a remembered node's name SHALL remain readable — as the visible text of its edge marker on the lattice variant and of its list entry on the graph variant — with its untruncated form always available to assistive technology.

The island's readout SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box. No draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it.

The island SHALL present exactly one full-map affordance, and that affordance SHALL carry no visible button chrome — no labelled control, icon button, or other visible trigger anywhere on the island. The affordance SHALL be a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element itself contains no focusable descendant, carrying 展開全地圖 as its accessible name. Activating it by pointer, by Enter, or by Space SHALL open the full-map surface through the platform's own button behaviour; no key handler on a non-button element SHALL stand in for it. The affordance SHALL be reachable in the island's tab order without the island's root element gaining a role or a tab stop of its own, and its focus-visible indication SHALL delineate the whole island rather than a small region of it. The affordance element SHALL be stable across committed payloads, so the full-map surface's opener — the focused element captured when that surface opens — still exists when it closes and focus is restored to it. The island's existing pointer convenience SHALL be unchanged: a click on the island's body SHALL open the full-map surface, a click that originates in an interactive descendant — an actionable lattice node or the affordance itself — SHALL run only that descendant's own behaviour, and every activation path SHALL open the full-map surface exactly once. The island SHALL carry no other tab stop and no other interactive descendant: neither an edge direction marker, nor a marker name, nor a graph-variant remembered-list entry SHALL be focusable or activatable, so the affordance remains the island's single keyboard path on every layout variant.

The presentation of `remembered` nodes SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface. Their payload coordinates SHALL NOT influence either exported node placement.

On the lattice variant, the named edge direction marker SHALL BE the presentation: each remembered node whose coordinates fall outside the drawn extent SHALL render as the remembered-node diamond ornament (carrying the gold landmark treatment when flagged) placed where the ray from the current node through that node's **raw payload coordinate delta** crosses the canvas's marker-safe border, with the direction computed by a pure helper over the raw delta (`+y = 北`, eight octants with deterministic sector bounds) and never from rank-compressed columns or rows, since compression preserves order, not ratios. The marker SHALL convey direction only — no distance figure, angle, or coordinate readout — and SHALL carry no activation of its own. The island SHALL NOT render a remembered-node list on this variant: the list is removed outright, and no surface SHALL present a remembered node both as a marker and as a list entry.

On every surface that draws edge direction markers — the island as well as the full-map overlay — each marker SHALL carry its place name as visible text beside it. The name SHALL be drawn wholly inside the marker gutter band that lies outside the canvas rect containing every node marker, every node label, the coordinate dot field's registered cells, and the axis — the rect the surface's coordinate-field padding grows, so the band stays the canvas's outermost band however much margin is taken — so a marker name can never intersect a node marker, a node label, or the axis line that surface now draws. Markers and their names SHALL be positioned deterministically so that no marker overlaps another marker and no name overlaps another name. The room a name may occupy SHALL be declared in the terms the placement helper consumes — the band depth every surface reserves, and, on a surface that draws its names OUTWARD across that band rather than along it, an outward name box — so the room is reserved before the names are drawn rather than discovered afterwards. **Each name SHALL then be fitted to what that same declared geometry reserved for it, and no surface SHALL draw a name longer than the room its own declaration set aside.** The fit budget SHALL be the lesser of two terms measured at the surface's declared name type size: the free span the marker holds along its own edge, and — only where that marker's name is drawn outward across the band — the declared outward name box. A surface that declares band depth alone, drawing its names along the band, has no outward term and is bound by its span alone. The number that budgets the fit SHALL be the same number that sizes the drawn glyph, so a surface cannot size its text by one measure and reserve room by another. Where a name does not fit that budget it SHALL be truncated with an overflow indicator, and **no surface SHALL draw two equal marker names while the payload labels behind them differ**: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator. That rule binds every surface that fits names, not only the smaller one. A dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative.

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

#### Scenario: Bounding the outward box leaves the island's own fitting untouched
- **WHEN** the island fits the marker names for a payload, declaring band depth only and no outward name box
- **THEN** its budget, its drawn names, and its marker geometry are exactly what they were before the outward term existed, because a term a surface does not declare cannot bind it

#### Scenario: A truncation that would make two places look alike is refused
- **WHEN** two remembered gateways whose payload labels differ only in a trailing qualifier — 西部丘陵與谷地（南門） and 西部丘陵與谷地（北門） — crowd one canvas edge so tightly that neither name can be drawn distinctly in its span
- **THEN** the surface does not draw the same string twice: each name it does draw is distinct from every other drawn marker name, any marker it cannot distinguish keeps its diamond, its bearing, and its landmark treatment with its visible name omitted, and both untruncated labels remain available to assistive technology

#### Scenario: A name the island cannot show is still reachable without assistive technology
- **WHEN** the island omits or truncates a marker's visible name — the fit-to-span rule shortened it, or the ambiguity rule dropped it — and the reader is a sighted keyboard-only user with no assistive technology running, so neither the visually-hidden mirror nor a hover tooltip on the `pointer-events: none` marker layer can serve them
- **THEN** activating the island's single full-map affordance opens the full-map overlay, which draws that gateway's name as visible text and as the marker's accessible name at the overlay's own larger scale and its own declared name capacity — a capacity that SHALL be strictly larger, on the same payload, than the capacity the island's span allows — so that reader always reads strictly more of the name on the overlay than the island could show, and reads it whole whenever the authored label is within the overlay's capacity

#### Scenario: The disclosure chain ends at the largest surface's declared capacity
- **WHEN** an authored gateway label is longer than the declared name capacity of the surface with the largest one, so even that surface must fit it
- **THEN** that surface draws the fitted name with its overflow indicator and carries the untruncated label as the marker's accessible name, and it SHALL NOT instead draw the name past its reserved box: a name that overruns its box overprints the canvas rect — the node markers, the node labels and the axis the invariant above protects — or its neighbouring marker's name, so it discloses nothing, and the bounded name with its overflow indicator is the surface's final visible answer

#### Scenario: A drawn marker name never exceeds the room its surface reserved
- **WHEN** the full-map overlay draws an edge direction marker whose authored payload label is longer than the outward name box that surface declared to the placement helper — the box the helper used to size the marker band and the along-edge slots
- **THEN** the drawn name is fitted to that declared capacity with an overflow indicator rather than drawn at full length past the reserved box, so the geometry the helper reserved and the text the renderer draws agree on every surface instead of only on the island

#### Scenario: The binding term follows how the surface draws its names
- **WHEN** one surface draws its marker names outward across the band while another draws them along the band, and both fit the same authored label
- **THEN** the outward-drawing surface's budget is bounded by its declared outward name box as well as by its along-edge span, the along-drawing surface's budget is bounded by its span alone because it declares no outward box, and neither surface's drawn name exceeds the room its own declaration reserved

#### Scenario: A crowded overlay edge keeps its names apart
- **WHEN** several remembered gateways carrying long authored labels leave through one canvas edge of the full-map overlay, enough that the placement helper's along-edge slots reach their floor
- **THEN** each name is fitted to its own slot, no two drawn marker-name boxes intersect, and no name box leaves the marker band for the canvas rect

#### Scenario: Marker names never collide with each other, a node label, or the axis
- **WHEN** a lattice payload places remembered markers on several canvas edges, including two on one edge, while the drawn lattice carries in-view node labels at the renderer's truncation length and the island draws the axis cross that the invariant names
- **THEN** every marker name is rendered wholly inside the marker gutter band outside the canvas rect — the rect the coordinate-field padding grows, so the band stays outermost — so no marker name's box intersects any node marker, node label, or the drawn axis line, and no two marker names' boxes intersect each other

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
- **WHEN** the payload's natural canvas is narrower than the island's content box, so an earlier revision of this surface would have scaled the whole SVG up to fill it
- **THEN** no scale above 1 is produced at all: the island's fill is taken as symmetric coordinate margin around the node core rather than as magnification, so the drawn scale is `min(maxWidth / W, maxHeight / H) ≤ 1` and the upward direction of the non-overlap question cannot arise

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

#### Scenario: The island's canvas claims its content width as coordinate margin
- **WHEN** a payload whose node core is narrower than the island's content box renders on the island (e.g. a sparse wilderness payload whose core is 120 user units inside the island's 206-unit width cap)
- **THEN** the drawn canvas fills the island's content width up to that cap by padding its coordinate extent symmetrically around the node core at the designed pitch — the dot field painting the padding — the marker band stays the canvas's outermost band, the uniform scale is exactly 1, and every marker radius and label renders at the size the island declares rather than being enlarged to fill the card

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** the reported wilderness shape renders on the island with named edge markers — a three-column by three-row in-view lattice whose node core is 120 × 134 user units at the island's square 40-unit pitch
- **THEN** the island's declared name geometry reserves only the band's depth, so the marker gutter is 44.46 user units rather than the 83.46 that an outward, edge-perpendicular name box of the overlay's width would demand, the drawn node core keeps 118.3 of the 120 CSS px it would occupy with no names at all instead of collapsing to 86.2 CSS px, and each marker name renders at the island's own smallest legible type step rather than at the size the outward box would leave it

#### Scenario: A sparse payload reads airy rather than magnified
- **WHEN** the committed payload contains a single node, whose node core is one 40-unit cell, and it renders on the island
- **THEN** the canvas fills the island's 206-unit width cap as coordinate margin, so roughly five coordinate cells of dot field surround one marker drawn at its designed radius with its label at the island's declared 9-unit type size — at most 9 CSS px, below the island's own 10px chrome step — and neither the marker ladder nor the label is inflated, where the superseded bounded-upscale rule drew the same payload with a 22 CSS px label
- **AND** no maximum-upscale bound is declared for the island at all, and the renderer's single width bound carries no upscale term

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** the island passes a 296px height budget for a two-column, sixty-four-row placement whose canvas is 206 × 2574 user units at the island's square 40-unit pitch
- **THEN** the renderer emits a single width bound of `296 × 206 / 2574` = 23.68px (floored, not rounded up) from the two-term formula, the rendered height equals the budget on every engine, no engine-specific reconciliation of a definite width against a height cap can letterbox or distort the drawing, and the payload takes no vertical coordinate margin at all because its height cap already binds — so the padding cannot cost the drawing any scale

#### Scenario: The overlay keeps its geometry and gains only the coordinate field
- **WHEN** the same committed payload renders in the full-map overlay, which declares neither the coordinate-field padding nor an axis
- **THEN** the overlay's column pitch, row pitch, label truncation length, marker scale, label type size, and width cap are all exactly what they were before this change, its canvas fills the overlay body's width as before, it paints no second vignette over its `mapcanvas` background, and it draws no axis — the one layer it gains is the coordinate dot field, because the dot pitch's meaning belongs to the lattice variant rather than to a surface
- **AND** the conditional label term of the pitch derivation never binds there, because `(labelMax + 1)` glyphs at the overlay's label type size is smaller than either of its declared pitches

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

#### Scenario: The coordinate field draws one dot per cell, registered to the placement
- **WHEN** a wilderness payload renders the lattice on the island and in the full-map overlay
- **THEN** each surface paints a coordinate dot field across its whole canvas whose horizontal dot spacing equals that surface's drawn column pitch and whose vertical spacing equals its drawn row pitch, and for every drawn node a dot position coincides exactly with that node's centre, so one dot spacing is one coordinate cell and the field is registered to the exported placement rather than being an unregistered texture

#### Scenario: A field whose pitch stopped meaning one cell is rejected
- **WHEN** the drawn pitch changes — because the payload's drawn label set moves the lattice from the field pitch to the label-cleared pitch, or because a surface declares a different pitch
- **THEN** the dot field's spacing changes with it on both axes and stays registered to the node centres, so no rendering exists in which the dot spacing and the coordinate cell step differ

#### Scenario: A coordinate field that went invisible fails
- **WHEN** the island's lattice renders and the resolved colours of the dot field and the axis are measured against the canvas ground
- **THEN** each layer exists as a painted element whose resolved colour differs from the ground, each keeps a contrast ratio of at least 1.15:1 at every point of the canvas and at least 1.35:1 in the vignette's un-darkened inner field, and neither exceeds the contrast the connector-edge ink keeps against the same ground — so a layer shipped at zero opacity, at the ground colour, or louder than the topology all fail

#### Scenario: The dot field never reads as a fifth node state
- **WHEN** the island and the overlay render a payload carrying current, visited, unvisited, and landmark nodes over the coordinate field
- **THEN** every dot is materially smaller in radius than the smallest node marker, carries no stroke, no label, no state class, no `data-node` identity, and no activation, an occupied cell shows its node marker with no dot drawn over or beside it, the state legend gains no entry for the field, and the four visibility states remain distinguishable without colour exactly as before

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** the island's lattice renders its canvas edges
- **THEN** exactly one vignette element darkens the canvas outward as a single full-canvas gradient wash, no per-cell fill, per-region fill, or shape tracing any terrain feature is introduced anywhere, and the overlay — whose `mapcanvas` background already is its one vignette — paints no second wash

#### Scenario: The vignette never erases the far-field dots
- **WHEN** the payload renders on the island and the dots nearest the canvas corners are measured through the vignette
- **THEN** those dots still clear the presence floor against the darkened ground there, so the layer that makes the far field faint does not delete it, and an outer vignette opacity strong enough to take them below the floor is not permitted

#### Scenario: The axis is drawn only where the convention is stated in words
- **WHEN** a coordinate-bearing payload renders on the island, which states `北↑ 東→` in its header, and in the full-map overlay, which states no orientation marks
- **THEN** the island draws a full-width and full-height axis line through the current node's drawn position beneath every node marker, and the overlay draws none — asserting no axis on a surface that names none

#### Scenario: The axis crossing the current marker is not a collision
- **WHEN** the island draws its axis through the `current` node
- **THEN** the axis passes beneath that node's own marker, which is what an origin is, the drawn edge direction markers stay wholly outside the canvas rect that contains the axis, and the non-overlap invariant that names the axis is satisfied

#### Scenario: The graph variant draws no coordinate field and no axis
- **WHEN** an interior or instance payload renders the radial graph on either surface
- **THEN** no coordinate dot field and no axis line is drawn anywhere on that surface, because a radial placement has no coordinate cells and asserts no axis, and its markers, edges, labels, and legend render exactly as before

#### Scenario: A node label never renders larger than the surface's own chrome
- **WHEN** the island renders, in turn, the reported three-by-three wilderness payload and a single-node payload
- **THEN** the drawn node label is at most the island's declared 9-unit type size — 8.87 CSS px and 9.00 CSS px respectively, both below the island's own 10px chrome step and both at or above the 8.62 CSS px the superseded geometry drew — and no payload produces a node label drawn larger than the island's title

#### Scenario: The pitch clears exactly what the drawn label set needs
- **WHEN** a wilderness payload whose neighbouring cells state no place name of their own renders on the island, and then a payload in which two horizontally adjacent cells both draw visible label text renders
- **THEN** the first is drawn at the pitch the bare clearance term requires — the two markers' widest drawn footprints, a visible connector segment, and each label box clear of its own node and of the row beneath it — while the second raises the pitch so both truncated label boxes clear side by side, and in both renderings every marker/marker, marker/label, and label/label pair keeps the geometry audit's minimum gap with `labelMax` unchanged

#### Scenario: The drawn cell is square so the lattice and its bearings agree
- **WHEN** a lattice payload places a node one cell east and one cell north of the current node while a remembered gateway sits at the same raw coordinate delta
- **THEN** the node is drawn along the same line the edge direction marker's raw-delta ray follows, because the drawn column and row pitch are equal, and the dot field's cells are square on that surface

#### Scenario: The decoration layers stay out of the audit and the accessibility tree
- **WHEN** the browser geometry audit collects every node-marker box and every node-label box on the island's canvas, and a screen reader reads the island
- **THEN** the dot field, the vignette, and the axis contribute no box to either collection because they carry neither component class, they intercept no pointer event, they add no tab stop and no accessible name, and the island still exposes exactly one tab stop — its full-map affordance

#### Scenario: Reduced motion and the non-colour encoding are unaffected
- **WHEN** the island renders with the reduced-motion preference active and with the colourblind override on
- **THEN** none of the three new layers animates or transitions anything, none carries a visibility state, the four-state shape ladder and its non-colour redundancy are unchanged, and every focus treatment behaves exactly as before

#### Scenario: The lattice colours resolve to existing tokens with no draft literal
- **WHEN** the coordinate field, the vignette, and the axis render on either surface
- **THEN** each layer's colour resolves to a design token already defined for the map surfaces, no new token is required, and no draft hex value and no draft-canvas pixel literal is hardcoded for any of them

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

