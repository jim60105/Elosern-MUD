## Purpose

The read-only version-1 `local_map` panel payload, the grid/anchor, wilderness, and
instance/interior layer adapters, the visibility states and legend, the bounded serialization the
server and browser validators share, and the minimap renderer that replaces the desktop-shell
placeholder.

## Requirements

### Requirement: local_map is a read-only version-1 presentation panel
The production presentation registry SHALL register panel name `local_map` at schema version 1, whose available payload SHALL contain exactly `schema_version`, `available`, `layer`, `current_node`, `title`, `nodes`, `edges`, and `legend`, with `available` true, and SHALL build it only from canonical room/map/knowledge data without mutating knowledge, traits, clock, or location.

#### Scenario: Node geometry is presentation-only, never invented
- **WHEN** a node is placed on any layer, including a gateway node shown on a layer other than its home layer
- **THEN** its `x`/`y` are renderer-local presentation geometry placing it at the adjacent position of the step that reaches it (adjacency or visual-range position), not canonical world coordinates; a node's identity NEVER forces its geometry to equal its own world coordinates, and the payload NEVER invents an identity for a position

#### Scenario: Remembered nodes share the drawn layer's coordinate space
- **WHEN** a `remembered` node is emitted on a coordinate-bearing layer (`grid`, `wilderness`) — the one node kind with no step to position it
- **THEN** its `x`/`y` SHALL be that node's own validated coordinates **in the layer currently being drawn** — the gateway's wilderness-side approach cell on the `wilderness` layer, the gateway's grid-side room coordinates on the `grid` layer — and SHALL NEVER be coordinates read from a different coordinate space nor a renderer-local or probed slot, because the current node and every remembered node must sit in one coordinate space for the raw-delta direction geometry to mean anything

#### Scenario: Payload field composition is exact
- **WHEN** an available payload is serialized
- **THEN** `layer` SHALL be one of `grid`, `wilderness`, `instance`, or `interior`; `current_node` SHALL be a canonical node ID; `title` SHALL be a bounded localized map title; each node contains exactly `id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`, and nullable `action`; each edge contains exactly `source`, `destination`, `label`, `known`, and `traversable`; and `legend` SHALL be a bounded list of text label entries

#### Scenario: The presenter leaks no live references
- **WHEN** the presenter emits any payload
- **THEN** it SHALL emit no live object or filesystem reference

#### Scenario: An unrepresentable room uses the registered unavailable form
- **WHEN** the current room cannot be represented
- **THEN** the presenter SHALL use the registered common unavailable form

#### Scenario: A node with no coordinate in the drawn layer is omitted, never plotted
- **WHEN** a node's identity carries no coordinate in the layer being drawn — a registered gateway whose grid-side room belongs to a different `z_map_key` than the map the `grid` layer is drawing
- **THEN** the node SHALL be omitted from the payload entirely rather than plotted at a fabricated, probed, cross-space, or current-node position, and it remains fully presented on the payload of the layer it does have a coordinate in

#### Scenario: Provider-invalid wilderness directions render nothing
- **WHEN** a wilderness direction's neighbor is provider-invalid — outside the continent rectangle or an anchor footprint cell
- **THEN** that direction renders no node and no walkable edge, exactly as out-of-bounds directions render today, and the payload NEVER presents an anchor footprint cell as a walkable `wild:` node

#### Scenario: Shared bounds are exact on both validators
- **WHEN** the server and client validators check a payload, sharing the bounds unchanged
- **THEN** they enforce at most 64 `nodes`, at most 128 `edges`, at most 16 `legend` entries, node/edge/legend strings of at most 256 Unicode code points, `title` of at most 128 code points, node IDs of at most 128 characters, renderer-local `x`/`y` integers within `-1024..1024`, `known`/`traversable`/`current`/`anchor`/`landmark` as booleans, `visibility` as one of `current`, `visible_unvisited`, `visible_visited`, or `remembered`, and `action` as `null` or the exact `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node id>}` object

#### Scenario: Conformance is enforced on serialized size
- **WHEN** both the Python and JavaScript validators assemble a payload
- **THEN** each computes the canonical UTF-8 byte length and rejects a payload exceeding the 65,536-byte OOB envelope limit — every conforming serialized payload SHALL fit it — because the per-field ceilings are independent and a payload that maximizes every string field at once would otherwise serialize beyond the limit

#### Scenario: Worst-case serialization is pinned both ways
- **WHEN** the serialization tests run
- **THEN** one test proves a structurally maximal realistic payload fits the envelope comfortably, and a second test proves a payload at every string ceiling at once is rejected

#### Scenario: Presenter ceilings stay internal
- **WHEN** the presenter applies its own tighter internal ceilings — such as the remembered gateway cap
- **THEN** no shared bound changes, no presenter-side ceiling is mirrored in the client validator, and none alters the shared table

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
Every node in the version-1 payload SHALL carry exactly one `visibility` value. `current` SHALL mark the player's current node. `visible_unvisited` SHALL mark a node inside the current field of view (visual range for grid, legal adjacency for wilderness, a currently visible one-hop Exit for instance/interior) that has not been entered. `visible_visited` SHALL mark a node inside the current field of view that was previously entered.

#### Scenario: Remembered is layer-scoped
- **WHEN** a payload is built on any layer
- **THEN** on the coordinate-free layers (`instance`, `interior`) `remembered` SHALL mark a previously entered node outside the current field of view; on the coordinate-bearing layers (`grid`, `wilderness`) it SHALL mark **a map boundary the player has stood on** — a node outside the current field of view whose traversal takes the player onto a different map — and nothing else: a visited node that is not such a boundary SHALL NOT be emitted on those layers, so walking a region can never accumulate one indistinguishable entry per visited cell

#### Scenario: Boundaries resolve against the authored registry
- **WHEN** the presenter decides whether a visited node outside the field of view is a boundary
- **THEN** it SHALL resolve against the authored wilderness entry registry (`world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY`) — the same registry the traversal code and the in-view gateway nodes read — and never against a flag in the stored knowledge record, which carries only node identity and ticks: on the `wilderness` layer a visited `wild:` node SHALL be a boundary when its coordinates equal `entry.approach_cell(gate)` for some registered entry and gate; on the `grid` layer a visited `grid:` node SHALL be a boundary when its coordinates and map key equal some registered gate's `grid_xy` and `z_map_key`
- **AND** being an `AnchorRoom`, a landmark, or a node of any other in-map significance SHALL NOT by itself make a node a boundary; a place inside the same map is not a way out of it

#### Scenario: A boundary is remembered only under its drawn-layer identity
- **WHEN** a boundary is considered for `remembered`
- **THEN** it SHALL be `remembered` only when the player's stored knowledge record contains **the exact canonical node ID the drawn layer carries it as** — the approach cell's `wild:` ID on the `wilderness` layer, the gate room's `grid:` ID on the `grid` layer — and a boundary the player has never entered on the side being drawn SHALL be absent from the payload

#### Scenario: Remembered boundary labels and flags
- **WHEN** a remembered boundary is emitted
- **THEN** it SHALL be labelled with the authored name of the place its traversal reaches, never with the terrain or region the boundary itself stands on: on the `wilderness` layer the entry's anchor display name from the anchor registry, and on the `grid` layer the display name of the wilderness region the gate's approach cell lies in
- **AND** remembered boundary labels within one payload SHALL be distinct; where two boundaries would carry the same far-side name, each SHALL be qualified with the canonical name of the boundary node it carries
- **AND** it SHALL carry `landmark: true`, `anchor: false`, and `action: null`

#### Scenario: Visibility keys on canonical identity
- **WHEN** visibility is resolved for any node, including a gateway node rendered on a layer other than its home layer
- **THEN** it SHALL be keyed on the node's canonical identity — the same ID the resolver and the knowledge record use — so a gate the player has walked through reads `visible_visited` wherever it is drawn

#### Scenario: Unknown nodes are omitted, never hidden
- **WHEN** a node is unknown to the player's knowledge and outside the field of view
- **THEN** it SHALL be omitted entirely — never sent as a hidden record

#### Scenario: The payload stays inside the envelope with in-view nodes first
- **WHEN** a payload is assembled with remembered nodes
- **THEN** it SHALL remain within the OOB envelope limits, with remembered nodes bounded by most-recent `last_seen` and current/visible nodes always included first

#### Scenario: Remembered nodes are capped and ordered deterministically
- **WHEN** remembered nodes are collected
- **THEN** they SHALL be bounded by a declared presenter ceiling of at most 16 remembered nodes, and SHALL be ordered by descending most-recent `last_seen` tick then ascending canonical node ID, so the same knowledge record and world state always produce the same nodes in the same order

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
On the `wilderness` layer, an in-view `wild:` neighbour whose coordinates are a registered gate's approach cell SHALL be labelled with that entry's anchor display name — the place the gateway leads to — instead of the display name of the region the cell lies in, so the in-view neighbourhood does not repeat one place name across every cell it draws.

#### Scenario: The gate approach cell keeps every other field
- **WHEN** a gate approach cell is relabelled with its entry's anchor display name
- **THEN** its node ID, `action`, edges, visibility, and every other field SHALL be unchanged, so the payload states a better name for the same position and never invents an identity for it

#### Scenario: Every other cell keeps its region name and labels stay non-empty
- **WHEN** an in-view cell is not a registered gate's approach cell
- **THEN** it SHALL keep the region display name it carries today, and every emitted node label SHALL remain a non-empty string

#### Scenario: Duplicate region labels draw no visible text
- **WHEN** a payload whose `layer` is `wilderness` is rendered and an in-view node's label string is identical to the `current` node's label string
- **THEN** the shared map renderer SHALL NOT draw visible label text for that node; that node SHALL keep its full label as its accessible name, and its marker, shape ladder, landmark treatment, and activation SHALL be unaffected
- **AND** the `current` node SHALL always draw its own label

#### Scenario: Suppression is scoped to shared region names
- **WHEN** labels are suppressed on any layer
- **THEN** the suppression is scoped to the `wilderness` layer because that layer's labels are shared region names, where a repeat is the reported defect; on `grid`, `instance`, and `interior` layers a label is an individual room name, where two distinct rooms sharing a name are still two distinct places and SHALL both draw their label

#### Scenario: Suppression touches no payload field
- **WHEN** label suppression is in effect
- **THEN** it is a drawing rule about the set on the canvas, not a payload rule: no payload field changes, and both validators keep their existing bounds and their non-empty label rules unchanged

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
A node's `action` SHALL be null unless that node is associated with a currently present, traversable `Exit` from the actor's current room, and for such a node `action` SHALL be exactly `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node id>}` where `exit_ref` is an opaque server-authored identifier and `destination` is the canonical destination node ID and equals the ID of the node carrying it.

#### Scenario: The association follows the arrival the step performs
- **WHEN** a wilderness direction or a registered wilderness gate exit — whose stored `destination` is a self-loop and never names the arrival — is associated with a node
- **THEN** the association SHALL follow the arrival the step actually performs: the associated node is the canonical node the traversal resolver derives from the step, not the exit's stored destination

#### Scenario: Remembered remote nodes offer no travel descriptor
- **WHEN** a remembered remote node is presented
- **THEN** it SHALL carry `action: null`, SHALL provide no travel descriptor, and the browser SHALL NOT be able to submit movement through a node with `action: null`

#### Scenario: The exact validator rejects malformed descriptors
- **WHEN** an `action` has an unknown `kind`, an oversized or non-ASCII `exit_ref`, or a missing/invalid `destination`
- **THEN** the exact schema validator SHALL reject it

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
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder, SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels only on the full-map overlay's legend popover (the minimap island mounts no state legend), SHALL make every `remembered` remote node's name readable without any travel action and without any activation, and SHALL omit unknown nodes.

#### Scenario: Remembered names stay readable across truncation and graphics
- **WHEN** a remembered remote node's name is not drawn as visible text on the island, wherever that visible text can be truncated, or wherever it is drawn inside a graphic
- **THEN** the name is readable as visible text on a map surface — the island's named edge marker on the lattice variant, the full-map surface's remembered list on the graph variant — and, in the cases named in the condition, as an assistive-technology text alternative on the island carrying the untruncated name

#### Scenario: Reconnect rebuilds from server-persisted knowledge
- **WHEN** the WebSocket reconnects and the new epoch's snapshot arrives
- **THEN** the component rebuilds the map from the server-persisted knowledge in that snapshot, and no client map cache is authoritative

#### Scenario: The island is a bounded constant-size HUD anchored on the stage
- **WHEN** the component renders
- **THEN** it renders as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column
- **AND** the island SHALL have a constant size that no payload changes: a single 1px hairline frame, a padding no larger than the shared spacing scale's smallest step, a single-row header, a square map canvas of 240 CSS px on each side at the 1451x790 reference scale, multiplied once by the desktop chrome factor above the reference height, and a readout row that always reserves its one line

#### Scenario: The island never sizes itself from its surroundings
- **WHEN** the island lays out at any anchor size or payload
- **THEN** the island SHALL NOT stretch to its anchor's width, SHALL NOT measure its anchor or any other surface to size itself, and SHALL NOT draw a second frame around its canvas inside its own frame

#### Scenario: The island root keeps the identifier the shell selects on
- **WHEN** the shell's mode-gated visibility rules or its focus-rescue path select the island
- **THEN** the island's root element SHALL keep the stable `local-map` component identifier both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it

#### Scenario: Map visual language comes from design tokens
- **WHEN** the island and the full-map overlay present the redesign draft's map visual language
- **THEN** every marker, edge, label, and legend colour SHALL come from a design token (including the draft seal pair and map label-tier tokens), and no component SHALL hardcode a draft hex value
- **AND** node labels SHALL use the draft label-tier tokens (current, landmark-gold, seen, far)

#### Scenario: The marker shape ladder holds at both scales
- **WHEN** either placement's canvas renders the visibility states
- **THEN** the `current` node SHALL render as a seal-deep filled circle with a seal-light stroke, strictly larger than the other on-canvas markers; `visible_visited` SHALL render as a small ink-filled circle; `visible_unvisited` SHALL render as a small hollow circle keeping the `未探索` rule; a landmark node SHALL additionally carry the gold landmark treatment
- **AND** the resulting shape ladder (large stroked circle / small solid circle / small hollow circle / out-of-canvas diamond for `remembered`) SHALL keep the states distinguishable without colour at both the island and the overlay scale, and the new marker footprints SHALL remain within the geometry guarantee so the non-overlap invariant is unaffected

#### Scenario: Each surface declares its label type steps
- **WHEN** a surface draws node labels or marker names
- **THEN** each surface SHALL declare its own node-label type size, and that size SHALL NOT resolve to drawn text larger than the surface's own smallest chrome type step, so a node label can never out-weigh the island's own title at any payload
- **AND** the island declares a 16-unit node-label step — equal to its 16px chrome step — and a 16-unit marker-name step; the full-map overlay declares 16 and 16

#### Scenario: A fitted drawing never shrinks text below its declared step
- **WHEN** a fitted drawing's uniform scale would carry a label below the surface's declared step at the reference scale
- **THEN** the drawing holds the label at the step rather than shrinking it, and pitch/footprint clearing accounts for the labels actually drawn: a fitted drawing SHALL never render a node label or marker name below its surface's declared step at the reference scale

#### Scenario: The coordinate-field layers are inert decoration
- **WHEN** the lattice variant draws the redesign draft's coordinate-field layers
- **THEN** these layers are pure decoration: each SHALL be non-interactive, SHALL be excluded from the accessibility tree, SHALL carry neither the node-marker nor the node-label component class that the geometry audit pairs every box of, SHALL introduce no tab stop, activation, or `data-node` identity, SHALL be static so the reduced-motion preference has nothing to disable, and SHALL encode no visibility state — the four-state shape ladder, its non-colour redundancy, the colourblind override, and every focus treatment SHALL be unaffected by their presence
- **AND** every colour they use SHALL resolve to a design token and no draft hex value SHALL be hardcoded for any of them

#### Scenario: The coordinate dot field states the lattice's coordinate space
- **WHEN** the lattice variant paints its coordinate dot field
- **THEN** the lattice SHALL paint one dot per coordinate cell across its whole canvas, beneath every connector edge, node marker, node label, and axis line, with horizontal and vertical dot pitch equal to the drawn column and row pitch, so one dot spacing is exactly one coordinate cell on each axis and the field states the coordinate space the lattice claims rather than a decorative texture
- **AND** the field SHALL be registered to the exported placement, so for every drawn node a dot position coincides with that node's centre
- **AND** because the field is painted beneath the markers, an occupied cell SHALL show its node marker and never a marker and a dot together

#### Scenario: A dot never reads as a fifth node state
- **WHEN** the dot field renders beside the marker ladder
- **THEN** the dot's radius SHALL scale with the marker ladder and SHALL remain strictly and materially smaller than the smallest node marker's radius, it SHALL carry no stroke, no label, and no state class, and the state legend SHALL gain no entry for it, so the legend's four states stay closed exactly as the beyond-state note rule requires

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** a map surface paints its vignette
- **THEN** each map surface SHALL paint exactly ONE vignette treatment that darkens the canvas toward its edges, and that treatment SHALL be the knowledge edge — the limit of what the payload knows — and SHALL NOT be, or be styled as, terrain: a single full-canvas gradient wash with no fabricated geometry — no per-cell fill, no per-region fill, and no drawn shape tracing any terrain feature
- **AND** the vignette SHALL NOT reduce the coordinate dot field below the presence floor at any point of the canvas, so the far-field dots it is meant to make faint stay visible rather than being erased

#### Scenario: The axis cross follows the stated convention
- **WHEN** a surface considers drawing the axis cross
- **THEN** it SHALL draw a full-width and full-height axis line through the `current` node's drawn position ONLY where that same surface states the axis convention in words; a surface that states no orientation marks SHALL draw no axis, and the radial graph variant SHALL draw none on any surface because a graph asserts no axis
- **AND** the axis SHALL be drawn beneath every node marker — it necessarily passes through the `current` node's own marker, which is what an origin is, and that crossing SHALL NOT be read as a violation of the non-overlap invariant, whose axis clause governs the edge direction markers in the gutter band

#### Scenario: Decoration contrast is pinned in a band against the ground
- **WHEN** the dot field and the axis render against the canvas ground
- **THEN** each SHALL be present as a painted element whose resolved colour differs from the canvas ground; each SHALL keep a contrast ratio against that ground of at least 1.15:1 at every point of the canvas and at least 1.35:1 within the vignette's un-darkened inner field; and neither SHALL exceed the contrast that the connector-edge ink itself keeps against the same ground, so the coordinate decoration never reads louder than the topology it decorates
- **AND** these layers are decoration, not information: the coordinate claim they picture is carried redundantly by the node placement itself, by the header's axis orientation marks, and by the readout's coordinate figure, so no reader depends on them — but the lattice's geometry is its claim, so they SHALL NOT be invisible

#### Scenario: The render model exports two placements
- **WHEN** a payload is committed
- **THEN** layout SHALL be computed in the DOM-independent render model, not as a rescaling of payload coordinates into a fixed pixel box, and the model SHALL export two placements for the same committed payload: a bounded integer lattice and a radial connected-graph
- **AND** the renderer SHALL size the map canvas from the exported placement and from the surface's own declared canvas geometry

#### Scenario: The lattice placement is bounded and rank-compresses on overflow
- **WHEN** the model computes the lattice placement
- **THEN** it SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on it, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts
- **AND** when that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement
- **THEN** it SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas
- **AND** ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates
- **AND** the radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant is constructible from the model alone
- **AND** neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning

#### Scenario: Surfaces declare a fixed square canvas or a fitted view
- **WHEN** a surface declares its canvas geometry
- **THEN** a surface MAY declare a **fixed square canvas** — the island SHALL declare one of 240 CSS px, and the full-map surface declares none — or MAY instead declare a **fitted view** — the full-map surface SHALL declare one, and the island declares none
- **AND** a fitted view SHALL show the placement's unchanged drawing — the same user-unit geometry, gutter, pitch, and type sizes the surface declares — through a uniformly scaled, translated window, and its opening fit, zoom bounds, pan, and recentre SHALL follow the full-map fit-view requirement
- **AND** a surface that declares neither SHALL draw at the placement's own size

#### Scenario: A fixed square canvas never magnifies
- **WHEN** a surface declares a fixed square canvas
- **THEN** the canvas SHALL always render at exactly that size, its drawing SHALL be laid out in a square coordinate extent whose side is the larger of the declared size and the side the drawing requires, and the drawn uniform scale SHALL therefore be the declared size divided by that side: exactly 1 whenever the drawing fits and below 1 only when it does not, and NEVER above 1 — so no payload, however sparse, can inflate the designed marker radii, label size, marker-name size, or gutter offsets above the sizes the surface declares, and no maximum-upscale bound SHALL be needed or declared
- **AND** such a surface SHALL fill its square by the pitch-before-margin and readable-window rules below, and SHALL NOT meet the fill by magnification

#### Scenario: The lattice fill grows pitch before taking margin
- **WHEN** a fixed-square lattice fills its square
- **THEN** the drawn square pitch SHALL start from the derived minimum pitch and SHALL grow, never shrink, toward the largest whole-unit pitch at which the node core — every lattice column and row plus the node-label band beneath the bottom row — fits inside the declared square less an inset: the edge-marker gutter band where the payload draws edge direction markers, and 8 CSS px on each side otherwise
- **AND** the drawn pitch SHALL NOT exceed one and a half times the surface's declared pitch, so a sparse payload's coordinate cells stay recognisable as cells
- **AND** whatever room remains after the pitch is chosen SHALL be taken as **coordinate margin**, padded symmetrically around the node core on both axes up to the square, with the edge-marker band remaining the canvas's outermost band and the padded extent between the core and that band being coordinate space that the dot field paints
- **AND** where even the derived minimum pitch does not fit, the drawing SHALL keep that minimum pitch and the square extent SHALL grow to the required side
- **AND** the island SHALL show a square window of side `canvasSize` over the drawing at scale 1, centred on the current node and clamped inside the drawing, clipped to the fixed canvas; every drawn label SHALL remain at least 16 CSS px at the reference, and the full-map surface SHALL keep the complete drawing reachable through its existing view operations

#### Scenario: The graph fill is a readable window
- **WHEN** a fixed-square graph variant fills its square
- **THEN** the fixed square window SHALL be centred on the radial placement's current node at one CSS pixel per user unit, clipping oversized radial drawings rather than shrinking their labels, and the complete graph and every full name SHALL remain reachable on the full-map surface

#### Scenario: No cap ever sizes a canvas
- **WHEN** the renderer resolves canvas dimensions
- **THEN** it SHALL accept no maximum-width or maximum-height cap and SHALL NOT resolve any cap into a width bound: no surface sizes its canvas by a cap, so there is no definite width to reconcile against a height cap and no engine-specific replaced-element constraint resolution can letterbox or distort a drawing
- **AND** the canvas's own natural size SHALL NOT be able to breach the island's square however much the edge-marker gutter grows it: the gutter enlarges the drawing's required side, which the square window absorbs as clipping, never as a larger canvas or smaller text

#### Scenario: The island measures nothing and overlaps nothing of its own
- **WHEN** the island renders map content
- **THEN** no island size, pitch, or scale SHALL be derived from a measurement of the island's anchor, of the island's other rows, or of any other surface, and the renderer SHALL NOT allow map content to overlap the island's title, its orientation marks, the readout line, or any other island content
- **AND** node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name

#### Scenario: No marker or label footprint ever intersects another
- **WHEN** the renderer chooses geometry — column pitch, row pitch, and marker sizing on the lattice, and ring radii, angular slots, and marker sizing on the radial graph
- **THEN** at every placement the model can produce for either variant, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label
- **AND** this holds independently of clipping by the island's fixed square canvas, independently of any uniform scale and translation the full-map surface's fitted view applies at any zoom level it permits, and independently of any pitch the island's fill grows beyond the derived minimum (radial ring radii SHALL grow with ring member count so the angular arc between adjacent slots bounds the label footprint)
- **AND** a connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects

#### Scenario: The pitch is derived from what needs clearing
- **WHEN** the lattice's minimum pitch is derived
- **THEN** it SHALL be **derived from what actually needs clearing at the drawn placement, not asserted as a constant**, and the derivation SHALL be constructible from the model and the drawn label set alone so the non-overlap invariant holds at every placement the model can produce; three clearance terms SHALL be honoured

#### Scenario: The bare clearance term binds every adjacent pair
- **WHEN** two lattice cells are adjacent
- **THEN** the pitch SHALL clear the widest drawn footprint of each of the two markers — including any decoration drawn over a marker, such as the actionable halo, not merely the marker shape itself — with a strictly positive gap, SHALL leave a strictly positive visible connector segment between them, and SHALL keep each node's own label box clear of its own node's widest drawn footprint

#### Scenario: The vertical term clears labels above markers
- **WHEN** an upper drawn node has a visible label and the cell directly below it contains a marker, even if that lower node has no visible label
- **THEN** the pitch SHALL reserve the label baseline, its descent, the lower marker's widest footprint and a strictly positive gap; it SHALL grow rather than allow the upper label to overprint the lower marker

#### Scenario: The label term measures visible names in monospace cells
- **WHEN** two horizontally adjacent cells BOTH draw visible label text
- **THEN** the pitch SHALL additionally clear both label boxes actually drawn side by side with a half-em gap, `(cells(a) + cells(b)) / 2 × CELL_EM × labelFont + labelFont / 2` rounded up to a whole unit, where the visible (truncated) label is measured in monospace cells at the surface's declared label type size — a code point that the bundled monospace face draws one cell wide counts as one cell, and every other code point — East Asian Wide or Fullwidth characters, and characters the face lacks, which fall back to a wider face — counts as two cells, a cell being CELL_EM, the shipped face's Latin cell advance that the font manifest publishes — and the largest such need over every adjacent labelled pair binds
- **AND** two truncated labels of `labelMax` wide glyphs plus the narrow overflow indicator therefore need `(2 × labelMax + 1) × CELL_EM × labelFont + labelFont / 2`, never less than the former worst-case term `(labelMax + 1) × labelFont + 3`, while shorter or narrower names ask only for the room they occupy

#### Scenario: The label term never binds on undrawn labels
- **WHEN** the drawn label set contains no such adjacent pair — which a payload whose neighbouring cells state no place name of their own produces
- **THEN** the label term SHALL NOT bind, and the derived minimum pitch SHALL NOT be inflated to clear labels that are not drawn

#### Scenario: The derived pitch is a floor, bought without truncation
- **WHEN** the three terms have derived the minimum pitch
- **THEN** a surface that declares a fixed square canvas MAY draw a larger pitch to fill its square, as the canvas-sizing rule states, and SHALL NEVER draw a smaller one, and the renderer SHALL NOT satisfy any term by truncating node labels more aggressively: `labelMax` is a legibility contract, and shortening it to buy pitch was rejected when the pitch was first derived

#### Scenario: The square cell keeps drawing and bearings in agreement
- **WHEN** the clearance terms apply to a drawn lattice
- **THEN** all applicable terms SHALL be satisfied by the same pitch on both axes, so a drawn lattice cell is **square**: an unequal pitch would draw a node at `(+1, +1)` along a different line than the edge direction marker for the same delta, which is computed from the raw coordinate delta, and the drawing and its bearings SHALL agree

#### Scenario: Map rendering logic is shared and variant-resolved
- **WHEN** the minimap island and the full-map overlay render a committed payload
- **THEN** the map-rendering logic (node/marker placement consumption, connector edges, and per-node labels) SHALL be shared between them, parameterized by scale and by layout variant (`lattice` or `graph`) rather than duplicated
- **AND** the variant SHALL be resolved once, in the render-model layer, as a pure function of the payload's `layer` — the closed coordinate-bearing set (`grid`, `wilderness`) resolves to the lattice and every other layer resolves to the graph — and both surfaces consume that one resolved value, so island and overlay can never disagree

#### Scenario: Only the full-map surface renders the state legend
- **WHEN** either surface renders
- **THEN** the state legend SHALL NOT be part of the shared canvas rendering: the full-map surface SHALL be the only surface that renders it, inside a legend popover it opens on request, and no legend element SHALL be mounted on the island for any payload

#### Scenario: The layout follows the data, never a setting
- **WHEN** a map surface presents its layout
- **THEN** no map surface SHALL offer a layout switch or any other means for the player to choose a layout, and no layout choice SHALL be kept as a preference or in any client-side storage: the layout follows the data the world ships, not a setting

#### Scenario: Both surfaces render the identical resolved variant
- **WHEN** island and overlay render the same committed payload
- **THEN** both surfaces SHALL render the resolved variant's identical in-view nodes and edges, the overlay's drawing shown whole through its fitted view within its own available space rather than on the minimap island's fixed small canvas, with the same non-overlap guarantee applying at every zoom level that view permits
- **AND** the full-map overlay SHALL NOT render the island's coordinate readout line, since it states no coordinate figure at all

#### Scenario: The graph variant's remembered list is overlay-only
- **WHEN** a graph-variant payload with remembered nodes renders
- **THEN** the full-map overlay SHALL render the payload's `remembered` nodes as a visible list outside its canvas — each entry pairing the remembered state's non-colour indicator with the node's full payload label as visible text, carrying no travel action, no activation, and no tab stop — and the minimap island SHALL NOT render that list in any visible form
- **AND** on the lattice variant neither surface renders a remembered-node list

#### Scenario: The overlay surface wears the draft mapcanvas treatment
- **WHEN** the full-map overlay renders its map surface
- **THEN** it SHALL be framed in the draft `mapcanvas` treatment: a dark radial-gradient background painted with pure CSS (no fabricated terrain geometry), a rounded ink border, and a thin seal-toned ring concentric with the `current` node marker, drawn inside that node's own group at 10.5 units × the marker scale — an ornament of the real marker within its reserved footprint, not a second position claim; no teardrop or other pin is drawn above or beside the marker

#### Scenario: The overlay background is its one vignette
- **WHEN** the overlay's canvas ground is painted
- **THEN** that background IS the overlay's one knowledge-edge vignette, so the overlay SHALL NOT paint a second wash over it, and the dot field's contrast against the overlay's own canvas ground SHALL satisfy the same presence band as on the island

#### Scenario: Overlay legend chips pair colour with text
- **WHEN** the overlay legend renders inside its legend popover
- **THEN** it SHALL render as draft dot-chips (a small colour chip paired with its text label); the chip border style SHALL additionally distinguish the remembered entry from the visited entry so the legend's distinctions do not rely on colour alone

#### Scenario: The header stays one row at every title length
- **WHEN** the island carries the payload's `title`, server-authored and bounded only by the payload's 128-code-point ceiling
- **THEN** its header SHALL stay a single row at every authored title length as a localization-safe container: the title SHALL be the row's only elastic item — rendered on one line, truncated with an overflow indicator when it does not fit, and keeping its complete string available as the element's own tooltip/accessible text — while the orientation marks and every other header item SHALL be fixed-size items that neither shrink nor wrap
- **AND** no authored or translated title SHALL be able to reflow the header onto a second line, and the island's card SHALL keep its constant width rather than being sized by its widest row, so neither the card's width nor the canvas's is a function of the title's length

#### Scenario: The header carries no full-map control
- **WHEN** the island's header is composed
- **THEN** it SHALL carry no full-map control of its own: the island's single full-map affordance is the full-bleed element specified below, so the header's fixed-size items are the orientation marks and nothing else unless a later change adds one

#### Scenario: Orientation marks appear only on the lattice variant
- **WHEN** the island renders a payload
- **THEN** on the lattice variant — which exactly the coordinate-bearing layers select — the island SHALL state the renderer's own axis orientation as orientation marks in its header and SHALL omit those marks otherwise rather than assert a direction or an axis the presentation does not support (a radial graph asserts no axis)

#### Scenario: Node coordinates carry layer-scoped semantics
- **WHEN** a consumer reads a node's `x`/`y`
- **THEN** on the closed coordinate-bearing set (`grid`, `wilderness`) they are validated world coordinates and MAY drive relative-direction geometry; on every other layer they are renderer-local layout values and SHALL NOT be read as direction, distance, or place

#### Scenario: The readout states the current coordinate figure and nothing else
- **WHEN** the island's readout line renders on a coordinate-bearing layer
- **THEN** it SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers or selects a node
- **THEN** the readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one

#### Scenario: No surface states a forbidden figure
- **WHEN** any surface renders figures
- **THEN** the island SHALL NOT state a coordinate figure for any node other than the `current` node, on any layer, and the full-map overlay SHALL NOT state a coordinate figure at all
- **AND** no surface SHALL render a compass angle, a bearing angle, a distance, or any coordinate figure beyond the permitted current-node figure; in particular the remembered-node edge markers convey direction only and never gain a coordinate readout

#### Scenario: A coordinate-free layer resolves the readout to nothing
- **WHEN** the payload layer is coordinate-free
- **THEN** there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box, rather than presenting an empty bordered widget; its row SHALL keep its one-line height so the island's size does not change with the layer

#### Scenario: No node's name depends on the readout
- **WHEN** the readout's label content is removed
- **THEN** no node's name becomes unreachable: each in-view node's full label SHALL remain available as its on-canvas accessible name, and a remembered node's name SHALL remain readable — as the visible text of its edge marker on the lattice variant and of its entry in the full-map surface's remembered list on the graph variant — with its untruncated form always available to assistive technology on the island

#### Scenario: The readout treatment is token-driven, not copied
- **WHEN** the island renders its readout
- **THEN** it SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box
- **AND** no draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it

#### Scenario: The single full-map affordance is an invisible real button
- **WHEN** the island presents its full-map affordance
- **THEN** it SHALL present exactly one, carrying no visible button chrome — no labelled control, icon button, or other visible trigger anywhere on the island
- **AND** the affordance SHALL be a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element itself contains no focusable descendant, carrying 展開全地圖 as its accessible name

#### Scenario: Activation runs through the platform's button behaviour
- **WHEN** the affordance is activated by pointer, by Enter, or by Space
- **THEN** it SHALL open the full-map surface through the platform's own button behaviour, and no key handler on a non-button element SHALL stand in for it

#### Scenario: The affordance is the island's tab order and focus ring
- **WHEN** a keyboard user reaches the affordance
- **THEN** it SHALL be reachable in the island's tab order without the island's root element gaining a role or a tab stop of its own, and its focus-visible indication SHALL delineate the whole island rather than a small region of it

#### Scenario: The affordance survives payloads so focus returns
- **WHEN** payloads commit while the full-map surface is open
- **THEN** the affordance element SHALL be stable across committed payloads, so the full-map surface's opener — the focused element captured when that surface opens — still exists when it closes and focus is restored to it

#### Scenario: Body clicks open the map; descendants keep their own behaviour
- **WHEN** the island's pointer convenience is exercised
- **THEN** it SHALL be unchanged: a click on the island's body SHALL open the full-map surface, a click that originates in an interactive descendant — an actionable lattice node or the affordance itself — SHALL run only that descendant's own behaviour, and every activation path SHALL open the full-map surface exactly once

#### Scenario: The island carries no other interactive descendant
- **WHEN** the island is rendered on any layout variant
- **THEN** it SHALL carry no other tab stop and no other interactive descendant: neither an edge direction marker, nor a marker name, nor an entry of either text alternative SHALL be focusable or activatable, so the affordance remains the island's single keyboard path on every layout variant

#### Scenario: Remembered presentation follows the variant, once per surface
- **WHEN** remembered nodes are presented on a surface
- **THEN** their presentation SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface
- **AND** their payload coordinates SHALL NOT influence either exported node placement

#### Scenario: The lattice names its remembered places by edge direction marker
- **WHEN** a remembered node's coordinates fall outside the drawn extent on the lattice variant
- **THEN** the named edge direction marker SHALL BE the presentation: it SHALL render as the remembered-node diamond ornament (carrying the gold landmark treatment when flagged) placed where the ray from the current node through that node's **raw payload coordinate delta** crosses the canvas's marker-safe border, with the direction computed by a pure helper over the raw delta (`+y = 北`, eight octants with deterministic sector bounds) and never from rank-compressed columns or rows, since compression preserves order, not ratios
- **AND** the marker SHALL convey direction only — no distance figure, angle, or coordinate readout — and SHALL carry no activation of its own
- **AND** the island SHALL NOT render a remembered-node list on this variant: the list is removed outright, and no surface SHALL present a remembered node both as a marker and as a list entry

#### Scenario: Marker names stay inside the outermost gutter band
- **WHEN** a surface draws edge direction markers — the island as well as the full-map overlay
- **THEN** each marker SHALL carry its place name as visible text beside it, drawn wholly inside the marker gutter band that lies outside the canvas rect containing every node marker, every node label, the coordinate dot field's registered cells, and the axis — the rect the surface's coordinate-field padding grows, so the band stays the canvas's outermost band however much margin is taken — so a marker name can never intersect a node marker, a node label, or the axis line that surface now draws
- **AND** markers and their names SHALL be positioned deterministically so that no marker overlaps another marker and no name overlaps another name

#### Scenario: A name's room is declared before it is drawn
- **WHEN** a surface prepares to draw marker names
- **THEN** the room a name may occupy SHALL be declared in the terms the placement helper consumes — the band depth every surface reserves, and, on a surface that draws its names OUTWARD across that band rather than along it, an outward name box — so the room is reserved before the names are drawn rather than discovered afterwards
- **AND** each name SHALL then be fitted to what that same declared geometry reserved for it, and no surface SHALL draw a name longer than the room its own declaration set aside

#### Scenario: The fit budget is measured in monospace cells
- **WHEN** a marker name is fitted to its room
- **THEN** the fit budget SHALL be the lesser of two terms measured in the same monospace cells (one for a code point the bundled monospace face draws one cell wide, two for every other code point, each CELL_EM of the shipped face's Latin cell advance) at the surface's declared name type size: the free span the marker holds along its own edge, and — only where that marker's name is drawn outward across the band — the declared outward name box, which SHALL be declared wide enough for `labelMax + 1` wide glyphs
- **AND** a surface that declares band depth alone, drawing its names along the band, has no outward term and is bound by its span alone
- **AND** the number that budgets the fit SHALL be the same number that sizes the drawn glyph, so a surface cannot size its text by one measure and reserve room by another

#### Scenario: Ambiguous names are dropped, never equalled
- **WHEN** a name does not fit its budget
- **THEN** it SHALL be truncated with an overflow indicator, and no surface SHALL draw two equal marker names while the payload labels behind them differ: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator
- **AND** that rule binds every surface that fits names, not only the smaller one
- **AND** a dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative

#### Scenario: The text alternative mirrors the drawn marker set
- **WHEN** the lattice variant's markers carry no activation and are drawn inside a graphic
- **THEN** the variant's complete reading path SHALL be a text alternative that mirrors the drawn marker set one entry per drawn marker, in a deterministic order, each entry stating that marker's untruncated payload label together with its direction as one of the eight octant names (`北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北`)
- **AND** naming the octant in words is permitted on that mirror; a numeric bearing, an angle, a distance, and any coordinate figure beyond the permitted current-node figure remain forbidden on every surface

#### Scenario: The mirror omits nothing, invents nothing, adds no tab stop
- **WHEN** the surface derives its text alternative
- **THEN** the mirror SHALL be derived from the same marker set the surface draws, so it can neither omit a drawn marker nor invent one, and SHALL introduce no additional tab stop: the island's tab order SHALL remain exactly its single full-map affordance, and neither the markers nor the mirror SHALL be focusable

#### Scenario: Coordinate-free payloads render no edge direction markers
- **WHEN** a coordinate-free payload renders
- **THEN** it SHALL render no edge direction markers, because a radial graph draws no canvas edge for a bearing to cross and its node `x`/`y` are renderer-local layout values

#### Scenario: The graph variant presents remembered nodes through a hidden list
- **WHEN** the graph variant renders remembered nodes on the island
- **THEN** the island SHALL present them only through an assistive-technology text alternative: a visually hidden, non-focusable list with one entry per `remembered` node in payload order, each stating that node's untruncated payload label and no direction, no distance, and no coordinate figure
- **AND** no remembered node on that variant SHALL be placed on the canvas or on its border, since a position there would assert a bearing the payload does not carry

#### Scenario: The island never shows a visible remembered list
- **WHEN** any variant renders on the island
- **THEN** the island SHALL render no visible remembered-node list, chip, or entry, so the number of places the player has visited can never change the island's size or crowd its canvas
- **AND** the visible presentation of those nodes is the full-map surface's remembered list, which the island's single full-map affordance opens in one activation, so a sighted reader without assistive technology can always read every remembered place

#### Scenario: Edges are inert connector lines
- **WHEN** a surface draws edges
- **THEN** they SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer

#### Scenario: The minimap change leaves the payload rules untouched
- **WHEN** the browser minimap renders
- **THEN** the `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged

#### Scenario: The island mounts no state legend
- **WHEN** an available `local_map` payload renders on both the minimap island and the full-map overlay
- **THEN** no legend element exists anywhere in the island's DOM, and once the reader opens the overlay's legend popover it renders the payload's full legend with its dot-chips and text labels

#### Scenario: A remembered place is readable and offers no travel action
- **WHEN** a remembered remote node is presented — as a named edge direction marker on the island's lattice variant, as a text-alternative entry on the island and a visible list entry on the full-map surface on the graph variant
- **THEN** its name and its landmark treatment are shown wherever it is drawn, its untruncated name is available to assistive technology on the island, and there is no move or travel control for it and no activation of its own on either surface

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
- **THEN** activating the island's single full-map affordance opens a readable full-map window at scale 1; its pan and focus-reveal paths reach the gateway's visible name and accessible name at 16 CSS px or more, and its declared name capacity SHALL be strictly larger, on the same payload, than the island's span capacity, so the reader can read strictly more of the name and read it whole whenever the authored label is within the overlay's capacity

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
- **WHEN** an interior or instance payload with remembered nodes renders the radial graph on the island and on the full-map surface
- **THEN** no edge direction marker is rendered and no remembered node is placed on either canvas or its border, the island renders no visible remembered-node list element and exposes one visually hidden, non-focusable text-alternative entry per remembered node stating its untruncated name, and the full-map surface renders a visible list with one entry per remembered node, each showing the node's full name with its non-colour state indicator and no travel action

#### Scenario: An interior payload's remembered rooms do not vanish with the lattice's list
- **WHEN** the player, having walked twelve rooms of a building, stands in one whose interior payload carries those rooms as `remembered`, and the island renders
- **THEN** the island's rendered size and its canvas size are exactly what they are for the same building with no remembered room, no remembered room's name is drawn as visible text on the island, every one of those rooms is named once in the island's text alternative, and activating the island's full-map affordance opens a surface that names every one of them as visible text

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1451x790 and at 1741x948, on a lattice payload with named edge markers and on a graph payload with remembered nodes
- **THEN** the canvas renders at exactly 240 × 240 CSS px (S = 1) at the reference acceptance viewport and 288 × 288 CSS px (±1) at 1741x948 (S = 1.2), the title, orientation marks, marker names, and readout line remain readable, no node marker, marker name, or edge overprints other island content, the island's rendered box is identical for both payloads, and no required island content has to be scrolled to

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
- **THEN** the in-view node's full label is still available as its on-canvas accessible name and the remembered node's name is still readable — as its marker's visible text on the lattice variant, as its full-map list entry's visible text on the graph variant, and untruncated through the island's text alternative on both — so removing the readout's label content makes no node's name unreachable

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

#### Scenario: A densely populated lattice keeps readable collision-free geometry
- **WHEN** the derived pitch of a dense lattice exceeds the island's 240px square
- **THEN** its unchanged geometry is clipped through a scale-1 window around the current node, every drawn label remains at least 16 CSS px, and the full-map view operations reach the complete drawing without marker/label collisions

#### Scenario: A sparse lattice scaled up never reintroduces overlap
- **WHEN** the payload's node core at its derived minimum pitch is smaller than the island's square, so an earlier revision of this surface would have scaled the whole SVG up to fill it
- **THEN** no scale above 1 is produced at all: the island's fill is taken first as pitch grown from the derived minimum and then as symmetric coordinate margin around the node core, never as magnification, so the drawn scale is `canvas side / side ≤ 1` and the upward direction of the non-overlap question cannot arise

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** a graph-variant payload combines a two-ring in-view placement with the model's maximum of remembered nodes
- **THEN** the island lays out no remembered-node list at all, its canvas is still 240 × 240 CSS px at the 1451x790 reference viewport (the canvas never depends on payload content, and the chrome factor magnifies it uniformly at every larger viewport), its title and readout row keep their places, the island's size equals its size for the same placement with no remembered node, and no required island content has to be scrolled out of view

#### Scenario: The name gutter never hands the anchor a scrollbar
- **WHEN** remembered markers grow the lattice's drawing beyond the fixed island canvas
- **THEN** the canvas stays 240 × 240 CSS px, its current-centered scale-1 window clips the oversized drawing, its effective text remains at least 16 CSS px, and the anchor has no scrollbar

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay retains the identical in-view nodes and edges in the same resolved layout variant, opens a readable current-centered window at scale 1 with the complete drawing reachable through pan and focus reveal, offers the state legend in its popover, has no marker or label collisions at any permitted zoom, and has no coordinate figure on the overlay surface

#### Scenario: The full-map overlay omits the remembered-node list and the readout line
- **WHEN** the full-map overlay is open with an available lattice payload carrying remembered gateways
- **THEN** the overlay body shows only its guide row, the map canvas with its view controls and legend popover control floating over the canvas's top-right corner, in the lattice variant with its named edge markers, and does not render a remembered-node list or the island's coordinate readout line

#### Scenario: The full-map overlay lists a graph payload's remembered rooms
- **WHEN** the full-map overlay is open with an available interior payload carrying remembered rooms
- **THEN** the overlay body shows its guide row, the map canvas in the graph variant with its view controls and legend popover control floating over the canvas's top-right corner, and a visible remembered list outside the canvas and below it with exactly one entry per remembered room in payload order, each pairing the remembered state's non-colour indicator with the room's full name, carrying no tab stop, no role that invites activation, and no travel action, and the body renders no coordinate readout line

#### Scenario: Draft marker ladder reads without colour
- **WHEN** the island renders a current node, a visited node, an unvisited node, and a landmark node
- **THEN** the current node is the large seal-stroked circle, the visited node is a smaller solid circle, the unvisited node is a smaller hollow circle, the landmark carries the gold treatment, and no two states share a shape

#### Scenario: Map chrome colours resolve to design tokens
- **WHEN** either map surface renders its chrome
- **THEN** every marker, edge, label, and legend colour resolves to a design token value, and the draft seal pair and label tiers match the tokens added with this change

#### Scenario: The overlay pin adorns the current marker without claiming a position
- **WHEN** the full-map overlay renders a payload with a current node
- **THEN** exactly one current-location ring renders, as a child of the current node's own group and concentric with its marker, no teardrop pin renders anywhere, and the ring carries no node label, accessible name, pointer target, or activation of its own

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
- **WHEN** a wilderness payload whose three-by-three in-view core carries no remembered gateway and no horizontally adjacent labelled pair renders on the island, where its derived minimum pitch is 40 user units
- **THEN** the drawn square pitch is 60 user units — the grown pitch reaches the 60-unit cap of one and a half times the declared pitch at the 240px square's roomier inset box (three columns, three rows, and the 14-unit label band fit 240px less its 16px inset) — so the node core spans 180 of the canvas's 240 CSS px instead of 120, the remaining room is painted as coordinate margin by the dot field registered to the 60-unit pitch, the uniform scale is exactly 1, and every marker radius and label renders at the size the island declares

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** the reported three-by-three wilderness shape renders with remembered gateways and vertically adjacent visible labels
- **THEN** the marker band reserves name depth, the square pitch satisfies the derived vertical clearance as well as horizontal clearance, and the 240px current-centered window draws labels at 16 CSS px without overlap

#### Scenario: A sparse payload reads airy rather than magnified
- **WHEN** the committed payload contains a single node and renders on the island
- **THEN** the pitch grows only to its 60-unit cap of one and a half times the declared 40-unit pitch, the rest of the 240px square is coordinate margin, so roughly three and a half coordinate cells of dot field surround one marker drawn at its designed radius with its label at the island's declared 16-unit type size — exactly 16 CSS px, the island's own 16px chrome step and never above it — and neither the marker ladder nor the label is inflated
- **AND** no maximum-upscale bound is declared for the island at all, and the island's canvas carries no width or height bound derived from a measurement

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** a two-column, sixty-four-row lattice renders on a natural mount, the island, and the full map
- **THEN** the natural mount has no inline size cap; the island clips it at scale 1 inside its 240px square; and the full map opens a readable window with pan/zoom/recentre, never an equivalent width cap or below-floor text

#### Scenario: A graph payload is cropped to its footprint and never magnified
- **WHEN** an interior graph containing one node and then a graph containing many neighbors renders on the island
- **THEN** both use a fixed 240-unit square window centered on the current node, render labels at exactly 16 CSS px at reference, and leave every full name reachable through the full map

#### Scenario: The overlay keeps its geometry and gains only the coordinate field
- **WHEN** the same committed payload renders in the full-map overlay, which declares neither a fixed square canvas nor an axis
- **THEN** the overlay's column pitch, row pitch, label truncation length and marker scale are all exactly what they were before this change, its node-label and marker-name type steps rise to the same 16-unit legibility floor the island declares, no pitch-fit or footprint crop is applied to it, its drawing is shown through its fitted view rather than stretched to the overlay body's width, it paints no second vignette over its `mapcanvas` background, and it draws no axis — the one layer it carries beyond the markers is the coordinate dot field, because the dot pitch's meaning belongs to the lattice variant rather than to a surface
- **AND** the conditional label term of the pitch derivation never binds there, because the widest truncated label (`2 × labelMax + 1` cells) plus its half-em gap at the overlay's label type size is smaller than either of its declared pitches

#### Scenario: Repeated budget measurements do not ratchet the canvas down
- **WHEN** the island re-renders across many successive payload commits and `map` anchor resizes
- **THEN** every render draws the canvas at exactly 240 × 240 CSS px at the stated reference acceptance viewport, because the island measures nothing to size itself — no anchor height, no section height, and no resize observation feeds its canvas — so no sequence of renders can walk the canvas down toward a floor

#### Scenario: The island's size never depends on the payload
- **WHEN** the island renders, in turn, a coordinate-bearing lattice payload with remembered gateways, a single-node lattice payload, and an interior graph payload carrying twelve remembered rooms
- **THEN** the island's rendered width and height are identical for every one of them and its canvas is 240 × 240 CSS px each time at the 1451x790 reference viewport

#### Scenario: A long authored title never reflows the island's header
- **WHEN** the committed payload's server-authored title is long enough that the title and the orientation marks together exceed the island's content width (e.g. `冒險者公會外街道圖` beside the axis marks in the island's reference-scale 240px content box)
- **THEN** the header stays a single row: the title renders on one line truncated with an overflow indicator while its complete string stays available as the element's tooltip/accessible text, the orientation marks keep their full size without wrapping, no full-map control occupies the row at all, and the island's card width is unchanged

#### Scenario: The readout follows the player after a move
- **WHEN** a newly committed payload replaces the rendered one with a different `current_node`
- **THEN** the readout line states the new payload's current node's coordinate figure rather than resolving to nothing or to the previous room, without any selection to re-seed, and the island shows no blank readout

#### Scenario: A readout with nothing to say draws no box
- **WHEN** the island's readout line has nothing to state
- **THEN** the line states nothing and paints no border or box, and its row keeps its one-line height so the island's size is the same as on a payload whose readout states a figure

#### Scenario: The island offers exactly one full-map affordance, with no visible button
- **WHEN** an available `local_map` payload renders on the island
- **THEN** exactly one full-map affordance exists in the island, it is a `<button>` element spanning the island's whole box with 展開全地圖 as its accessible name, no labelled control or icon button is rendered in the island's header or anywhere else in the island, and the island's root element carries no role and no tab stop of its own

#### Scenario: A keyboard user opens the full map from the island
- **WHEN** a keyboard user tabs to the island's full-map affordance and presses Enter, and then repeats the run pressing Space
- **THEN** each activation opens the full-map surface exactly once through the button element's own platform behaviour, with no key handler on a non-button element involved, and the focus-visible indication while it is focused delineates the whole island rather than a small corner of it

#### Scenario: Activating a lattice node moves instead of opening the map
- **WHEN** the player clicks an actionable in-view lattice node, its marker, an edge direction marker, or the full-map affordance itself
- **THEN** a click on the node or its marker submits that node's move and emits no map-open, a click on an edge direction marker — which carries no behaviour of its own — falls through to the island body and opens the full-map surface exactly once, a click on the affordance opens the full-map surface exactly once, and a click on the island's plain body opens the full-map surface exactly once

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
- **WHEN** the drawn pitch changes — because the payload's drawn label set moves the lattice from the field pitch to the label-cleared pitch, because the island's square fill grows the pitch beyond its derived minimum, or because a surface declares a different pitch
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
- **THEN** no coordinate dot field and no axis line is drawn anywhere on that surface, because a radial placement has no coordinate cells and asserts no axis, its markers, edges, and labels render exactly as before, and the full-map surface's legend popover lists the same entries as on a lattice payload

#### Scenario: A node label never renders larger than the surface's own chrome
- **WHEN** a sparse or crowded payload renders on the island
- **THEN** every drawn node label is exactly its declared 16-unit step at reference scale, never smaller through SVG scaling and never larger than the island's title

#### Scenario: The pitch clears exactly what the drawn label set needs
- **WHEN** a wilderness payload suppresses shared-region labels and another payload shows distinct adjacent names
- **THEN** horizontal clearance binds only for pairs of visible names, vertical clearance binds for every labeled upper node above a lower marker including an unlabeled one, and the square pitch satisfies all applicable footprint terms without more aggressive truncation

#### Scenario: Vertical clearance is derived even above an unlabeled marker
- **WHEN** visible labels occur on vertically adjacent lattice rows
- **THEN** the derived square pitch grows above the declared floor enough to keep every upper label clear of the marker beneath it, even if that marker has no label, and a fixed canvas clips rather than defeating clearance or reducing text size

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

#### Scenario: The island scales once with the desktop chrome factor
- **WHEN** the same payload renders on the island at 1451x790 and at 2560x1440
- **THEN** the canvas is 240 × 240 CSS px at 1451x790 and 336 × 336 CSS px (±1) at 2560x1440 (the 1.4 cap), the SVG's viewBox, pitch, marker radii and label sizes in user units are identical for both, and the drawing is only uniformly magnified

#### Scenario: Labels are budgeted in monospace cells
- **WHEN** two horizontally adjacent lattice cells draw the labels `霧骨渡口` and `NPC 7`, and an edge marker's name mixes CJK and ASCII
- **THEN** the pitch clears `(8 + 5) / 2 × CELL_EM × labelFont + labelFont / 2`, where `CELL_EM` is the shipped face's Latin cell advance in em, each CJK code point counting as two cells and each ASCII code point as one, and the marker name is fitted to its span and outward box by the same cell measure, so a monospace face whose wide glyphs are two Latin cells wide stays inside every reserved box

### Requirement: Adjacent traversable map nodes submit explore.move through their move descriptor
The WebClient `local-map` component SHALL make a currently traversable adjacent node with an exact `move` action descriptor actionable: activating it (click or Enter on the focused node) SHALL submit the `explore.move` UI action carrying that node's opaque `exit_ref` and the canonical `current_node` identity.

#### Scenario: Ineligible nodes stay inert or focus-only
- **WHEN** a node has `action: null`, is a remembered remote node, or its `visibility` is not a current-field-of-view state
- **THEN** it SHALL NOT submit any travel action and SHALL remain inert or focus-only exactly as before

#### Scenario: Submissions derive only from the validated payload
- **WHEN** the component submits a move
- **THEN** it SHALL derive the submitted `exit_ref` and `current_node` only from the validated `local_map` payload, SHALL NOT construct an exit reference, destination, or room identity from entity data or prose, and SHALL leave the `local_map` panel payload contract, the `未探索` unvisited-node rule, and the remembered-node no-travel rule unchanged

#### Scenario: The refreshed payload replaces the rendered minimap
- **WHEN** a submission succeeds or is rejected
- **THEN** the refreshed `local_map` payload at the newer revision SHALL replace the rendered minimap, and the component SHALL NOT keep a client-side canonical map cache

#### Scenario: The pitch fix never retargets an activation
- **WHEN** the corrected node-pitch geometry of this change is applied
- **THEN** it SHALL NOT alter which node an activation targets: the enlarged marker's clickable/focusable area SHALL remain centered on the same lattice coordinate the payload assigned it

#### Scenario: Island and overlay activate identically
- **WHEN** a lattice renders inside the minimap island or inside the full-map overlay
- **THEN** the activation behavior SHALL be identical in both, since both consume the same shared lattice-rendering logic

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
For every gate of every entry in the wilderness entry registry, the minimap SHALL present the gateway as a matched pair of edges on both sides, and the rendered destination SHALL always equal the node carrying it and always equal what `resolve_wilderness_destination` derives from the same registration the traversal code reads.

#### Scenario: The approach cell renders the gate's grid node
- **WHEN** the puppet stands at the gate's approach cell
- **THEN** the gateway direction (`return_direction`) SHALL render the gate's grid node — canonical `grid:` id, gate room label, resolver-derived visibility, and a move descriptor with that id as destination

#### Scenario: The gate room renders the approach cell's wild node
- **WHEN** the puppet stands at the gate room
- **THEN** the grid layer SHALL render that gate's approach cell's `wild:` node — canonical `wild:` id for the approach cell, the region's display name, knowledge-derived visibility, and a move descriptor whose `exit_ref` is that gate's exit and whose destination is that `wild:` id

#### Scenario: A pinning test walks every gateway both ways
- **WHEN** the pinning test runs
- **THEN** it SHALL move a character through each real gateway exit in both directions and compare the committed node against the actual arrival

#### Scenario: One resolver source, never a duplicated table
- **WHEN** node identity and direction deltas are computed for these nodes
- **THEN** they SHALL come from that same single resolver source, never from a duplicated table

#### Scenario: Gate capacity is reserved before ordinary nodes
- **WHEN** registered gates compete with ordinary visible nodes
- **THEN** the gate node SHALL NEVER be silently omitted: registered-gate capacity SHALL be reserved before ordinary visible nodes are collected, excess visible nodes trimmed farthest-first in deterministic order

#### Scenario: An occupied preferred slot takes the nearest free one
- **WHEN** the gate's preferred renderer-local slot is occupied
- **THEN** the gate node SHALL take the nearest free slot in deterministic probe order instead of being dropped

#### Scenario: Grid-layer gate identity derives from the provisioned exit
- **WHEN** the grid layer builds a gate candidate
- **THEN** the candidate's `wild:` identity and label SHALL derive from the provisioned exit's `db.gate_direction` resolved through the registry to that gate's `approach_cell`, and the candidate's slot direction SHALL be the direction of the exit connecting the gate room

#### Scenario: Identity never parses keys, aliases, or anchor cells
- **WHEN** a grid-layer gate candidate's identity is resolved
- **THEN** it SHALL never come from parsing the gate exit's key or aliases (all wilderness-side gate exits share the key `荒野`, and key aliases are display affordances, not identity), and never from the entry's anchor cell as a stand-in for a per-gate approach cell

#### Scenario: The capacity trim order is part of the contract
- **WHEN** the capacity trim drops visible nodes
- **THEN** it SHALL drop them in descending Chebyshev distance from the current node, then descending Y, then descending X (the current node never dropped)

#### Scenario: The slot probe order is part of the contract
- **WHEN** the slot probe searches for a free slot
- **THEN** it SHALL scan the preferred slot first when it is free and inside the payload coordinate bounds, then rings of ascending Manhattan distance from it in ascending Y-offset then ascending X-offset order, taking the first slot that is inside the coordinate bounds and free

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
The `local_map` presenter SHALL, for the `wilderness` layer only, append one localized scale note to the payload `legend` after the four visibility-state labels, whose text states the wilderness cell size in kilometres derived at build time from `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` — no module or client code SHALL duplicate the constant or the conversion.

#### Scenario: The scale note is the fifth entry
- **WHEN** the scale note is appended
- **THEN** the four state labels SHALL keep their existing order and positions, so the scale note is the fifth entry

#### Scenario: Other layers keep their legend exactly as before
- **WHEN** payloads for the `grid`, `instance`, and `interior` layers are built
- **THEN** they SHALL keep their legend exactly as before (the four state labels)

#### Scenario: The extended legend stays inside the existing bounds
- **WHEN** the extended legend is validated
- **THEN** it SHALL remain within the existing bounds (at most 16 entries, 256 code points each) and SHALL pass both validators unchanged — no payload schema field is added or altered

#### Scenario: The constant is read from its owning module
- **WHEN** the presenter assembles the legend
- **THEN** it SHALL read the constant as an attribute of its owning module at legend-assembly time (never a value imported into the presenter's own namespace), so patching the provider module attribute is observed by the presenter

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
The full-map surface's legend SHALL render each legend entry beyond the four visibility-state labels with a dedicated neutral info-chip treatment — design-token colors only, text as the primary carrier — and SHALL NOT style it by cycling the four state chip styles.

#### Scenario: The first four entries keep their state treatments
- **WHEN** the legend renders
- **THEN** the first four entries SHALL keep their state chip treatments and order exactly as before

#### Scenario: The legend popover remains the only legend surface
- **WHEN** any payload renders
- **THEN** the full-map surface's legend popover SHALL remain the only legend surface (the minimap island renders no legend element for any payload, and the shared canvas renderer renders none on either surface)

#### Scenario: The info chip is distinguishable without colour
- **WHEN** an info entry is shown beside state entries
- **THEN** the info entry's distinction from state entries SHALL NOT rely on colour alone

#### Scenario: The overlay shows four state chips and one info chip
- **WHEN** the full-map overlay renders a wilderness payload whose legend carries the scale note and
  the reader opens its legend popover
- **THEN** the popover's legend lists five entries, the first four keep their state chip treatments in
  the fixed order, and the fifth renders with the neutral info-chip treatment distinct from all four
  state treatments

#### Scenario: Extra entries never masquerade as visibility states
- **WHEN** a payload legend carries any entry beyond the fourth (present-day or future)
- **THEN** that entry renders with the info-chip treatment, not with any of the four state chip
  classes, and its text label is rendered in full

#### Scenario: The island still renders no legend
- **WHEN** a wilderness payload with the scale note renders on the minimap island
- **THEN** no legend element exists anywhere in the island's DOM, exactly as for every other
  payload

### Requirement: The full-map surface opens fitted to its body and offers zoom, pan, and recentre
The full-map overlay SHALL present its map through a clipped viewport that takes the overlay body's height left after its one-line guide row and, on the graph variant, its remembered list, so neither row can push the map out of the body and the body needs no scrolling to show the map.

#### Scenario: Zooming and panning never change declared geometry
- **WHEN** the map is drawn inside the viewport through a window onto the unchanged drawing
- **THEN** zooming and panning SHALL change only a uniform scale and a translation of the whole drawing, never the placement, the pitch, the edge-marker gutter, the marker radii, the label and marker-name type sizes, the name fitting, or any other geometry the surface declares, so every rule the shared renderer states about that geometry — including the non-overlap invariant — holds at every zoom level

#### Scenario: The view opens readable at scale one
- **WHEN** the overlay opens
- **THEN** the view SHALL open at one CSS pixel per user unit, so every declared 16-unit label remains at least 16 CSS px
- **AND** a drawing smaller than the viewport SHALL be centred on each non-overflowing axis, and an oversized drawing SHALL open around the current node, clamped to the drawing's edges, rather than shrinking text to show all nodes at once

#### Scenario: Zoom bounds and full reachability
- **WHEN** the reader zooms the drawing
- **THEN** the zoom level SHALL be bounded below by one and above by two CSS pixels per user unit, and the complete drawing SHALL remain reachable by the existing pan, zoom, focus-reveal and remembered-list paths without dropping topology

#### Scenario: Untouched views re-fit; touched views persist within the opening
- **WHEN** a viewport resize or moved-current payload arrives
- **THEN** while the reader has not zoomed, panned, or recentred, it SHALL recreate that default readable view
- **AND** once touched, a resize SHALL preserve the viewport's center point subject to bounds, a moved-current payload SHALL center the new current node at the reader's scale, and any other replacement SHALL only re-clamp the view

#### Scenario: No view state persists between openings
- **WHEN** the overlay closes and opens again
- **THEN** no zoom, window position or popover state SHALL persist between openings, and each opening SHALL restore the default readable view and close the legend popover

#### Scenario: Wheel and keys zoom the view
- **WHEN** the reader uses the view's zoom operations
- **THEN** a mouse wheel over the viewport SHALL zoom about the pointer, keeping the drawing point under the pointer fixed, and SHALL NOT scroll the body or the page
- **AND** the `+` key (and `=`) and the `-` key SHALL zoom in and out by a fixed step about the viewport's centre while focus is inside the overlay; a key pressed with Ctrl, Meta, or Alt SHALL be left to the browser
- **AND** labelled `放大` and `縮小` buttons in the view-control group floating over the map's top-right corner SHALL do the same

#### Scenario: Dragging pans and never activates
- **WHEN** the reader drags with the primary pointer button
- **THEN** the window SHALL move with the pointer and SHALL stop at the drawing's edges so no empty space opens beyond a canvas edge on an axis where the drawing is larger than the viewport
- **AND** a press that moves more than a small threshold is a drag: it SHALL NOT activate the node it started or ended on, so a drag never submits a move, and a press that stays within the threshold is an ordinary click, so pointer travel on an actionable node is unchanged

#### Scenario: The recentre button centres the current node
- **WHEN** the reader activates the labelled `置中` button in that view-control group
- **THEN** it SHALL centre the `current` node in the viewport at the current zoom level, clamped to the drawing's edges

#### Scenario: Inapplicable controls state unavailability without losing focus
- **WHEN** a view control's operation cannot apply — zoom in at the upper bound, zoom out at the readable bound, `置中` on a payload with no current node
- **THEN** each control SHALL be a real `<button>` with an accessible name; an inapplicable control SHALL state that it is unavailable to assistive technology and SHALL do nothing when activated, and SHALL stay focusable so focus never falls out of the overlay's focus trap

#### Scenario: The keyboard path moves and reveals
- **WHEN** a keyboard user travels the overlay
- **THEN** the path SHALL remain: every actionable node stays a tab stop in the overlay's focus order and still moves on Enter or Space, and when a node receives focus outside the visible window the view SHALL pan — at the current zoom level, only as far as needed — so that node's marker and label are visible with a margin

#### Scenario: Gestures are named and nothing animates
- **WHEN** the overlay presents its view operations
- **THEN** the guide row SHALL name the gestures in words, and no view operation SHALL animate, so the reduced-motion preference has nothing to disable and a reduced-motion reader sees exactly the same frames

#### Scenario: The legend lives in a popover off the body layout
- **WHEN** the reader opens the state legend
- **THEN** it SHALL NOT occupy the overlay body's layout; it SHALL open from a `?` disclosure button in that view-control group named 圖例, which states whether the popover is expanded; the popover SHALL float above the top-right of the map viewport, SHALL hold the payload's full legend with its dot-chips and text labels and no focusable content, and SHALL be absent from the DOM while closed

#### Scenario: The popover closes without stealing presses or the overlay
- **WHEN** the popover is open and the reader dismisses it
- **THEN** it SHALL close on a second activation of its button, on a pointer press inside the overlay outside the popover and its button — without consuming that press, so a drag or a node activation still proceeds — and on Escape
- **AND** Escape while the popover is open SHALL close only the popover and SHALL NOT close the overlay; the next Escape closes the overlay

#### Scenario: A tall map opens readable around the current node
- **WHEN** the player opens an oversized tall lattice or wilderness map with named edge markers at 1451x790
- **THEN** the current node is visible at a scale of 1, labels and marker names draw at least 16 CSS px, the overlay body has no scrollbar, and panning reaches every node and edge marker

#### Scenario: A small map opens at its declared size, not magnified
- **WHEN** the player opens the full-map overlay on a single-node payload
- **THEN** the node is centred in the viewport, its marker and label render at the overlay's declared
  sizes at one CSS pixel per user unit, and nothing is scaled above that

#### Scenario: The remembered list never pushes the map out of view
- **WHEN** the player opens the full-map overlay on an interior payload carrying sixteen remembered
  rooms
- **THEN** the remembered list renders below the viewport, the radial drawing remains reachable through the readable viewport, and the overlay body shows no scrollbar

#### Scenario: Wheel and keys zoom within bounds
- **WHEN** the reader turns the wheel forward over a node, then presses `-` repeatedly, then presses
  `+` repeatedly
- **THEN** the wheel enlarges the drawing while the node under the pointer stays under the pointer,
  `-` stops at scale 1 with readable text and the zoom-out control stating it is
  unavailable, `+` stops at two CSS pixels per user unit with the zoom-in control stating it is
  unavailable, and the page and the overlay body never scroll

#### Scenario: A drag pans and never moves the player
- **WHEN** the reader zooms in, presses the primary button on an actionable node, drags well past the
  threshold, and releases over another actionable node
- **THEN** the drawing moves with the pointer, stops at the drawing's edges, and no move is submitted;
  a subsequent press-and-release on an actionable node without movement submits that node's move
  exactly once

#### Scenario: 置中 returns to the current node
- **WHEN** the reader zooms in, pans the current node out of the viewport, and activates `置中`
- **THEN** the current node's marker is at the viewport's centre, or as near it as the drawing's edges
  allow, and the zoom level is unchanged

#### Scenario: Keyboard travel reveals the focused node
- **WHEN** a keyboard user zooms in so that an actionable node lies outside the viewport and then tabs
  to that node and presses Enter
- **THEN** the view pans at the same zoom level until the node's marker and label are inside the
  viewport, and Enter submits that node's move exactly once

#### Scenario: Travel recentres only a touched view
- **WHEN** a payload moving the current node commits once while the view is still fitted, and again
  after the reader has zoomed in; and a payload with the same current node commits while the reader
  has panned elsewhere
- **THEN** the first restores the readable current-centered default, the second centres the new current node at the reader's
  zoom level, and the third leaves the reader's window where it was

#### Scenario: The legend opens in a popover and Escape closes it first
- **WHEN** the reader opens the full-map overlay, activates the 圖例 button, presses Escape, and presses
  Escape again
- **THEN** no legend element exists before the button is activated and the map viewport's box does
  not change when the popover opens; the button states it is expanded while the popover shows the
  full legend; the first Escape closes only the popover with focus still on the 圖例 button; and the
  second Escape closes the overlay and restores focus to its opener

#### Scenario: Nothing about the view is remembered
- **WHEN** the reader zooms, pans, and opens the legend popover, closes the overlay, and opens it again
- **THEN** the overlay opens fitted with the popover closed, and no preference, client storage, store
  field, or server message carries a zoom level, a window position, or a popover state

#### Scenario: Reduced motion loses nothing
- **WHEN** the reader zooms, pans, recentres, and opens the legend with the reduced-motion preference
  active
- **THEN** every operation takes effect in the same frame as without the preference, because no view
  operation animates

### Requirement: Map chrome and ordinary node labels are legible without dropping topology
The minimap island's title, orientation marks and readout SHALL render at the shared `--text-xs` step (16 CSS px at the reference scale), which is the island's one and smallest chrome step, and the full-map overlay's guide, input hint, view controls, legend and remembered list SHALL render at 16 CSS px or more through the shared type tokens; neither surface SHALL hardcode a map chrome type size below that step.

#### Scenario: Node text keeps its declared floor at every scale
- **WHEN** the island draws node labels and marker names
- **THEN** each SHALL render at its declared 16-unit step with an effective rendered size of at least 16 CSS px at reference, and at least 22.4 CSS px at the desktop chrome cap

#### Scenario: Oversized drawings clip instead of shrinking
- **WHEN** a lattice or graph drawing exceeds the island's canvas
- **THEN** it SHALL be clipped through a current-centered scale-1 window rather than shrinking labels; all nodes and edges SHALL remain in the model, every node SHALL retain its full text alternative, and the full map SHALL make every full name and remembered gateway reachable at its readable scale floor through existing view controls

#### Scenario: The derived pitch clears the drawn label set
- **WHEN** the lattice pitch is derived
- **THEN** it SHALL satisfy horizontal and vertical footprint clearance for the actual drawn label set

#### Scenario: Ordinary neighbourhood is readable
- **WHEN** a three-by-three grid lattice of distinct two- and four-glyph room names with no remembered gateway renders on the island at 1451x790 and at 2560x1440
- **THEN** the title, orientation marks and readout compute to 16 CSS px at the reference viewport, the drawing's scale is 1, every drawn node label is at least 16 CSS px at the reference viewport (and at least 22.4 CSS px at 2560x1440, the same labels at the 1.4 chrome cap) and at most the island's declared 16-unit step at the reference scale, and no node marker or node label overlaps another node's marker or label

#### Scenario: Dense knowledge stays available
- **WHEN** a payload at the model's 64-node bound — 48 in-view nodes and 16 remembered gateways — renders on the island and then in the full-map overlay
- **THEN** the island stays a 240 × 240 CSS px canvas retaining every in-view node with its full label as its text alternative and every remembered gateway; its drawn labels are at least 16 CSS px, and the overlay makes every full name reachable at 16 CSS px or more at every permitted zoom level

### Requirement: Current map location has one unambiguous footprint
On the full-map overlay the current-location decoration SHALL be a ring concentric with the true current marker, drawn inside the current node's own group at 10.5 units × the marker scale with a hairline seal-toned stroke that does not scale with the drawing, so it can never read as another location.

#### Scenario: The ring stays clear of labels and connectors
- **WHEN** the ring renders at the fitted view
- **THEN** it SHALL stay inside the current node's footprint — its outer edge at least 1 CSS px clear of every node label box, including its own — and SHALL leave every connector incident to the current node a visible segment between the ring's outer edge and the neighbour's footprint

#### Scenario: The ring is decoration only
- **WHEN** the geometry audit or assistive technology encounters the ring
- **THEN** it SHALL be decoration only: not a node marker for the geometry audit, no accessible name, no pointer target, no activation

#### Scenario: The island adds no ornament and decoration encodes no state
- **WHEN** either surface decorates its map
- **THEN** the island draws no ornament beyond its current marker, and decorative map material — the canvas corner brackets both surfaces paint outside the drawing, the dot field and the single vignette — SHALL encode no place, terrain or visibility state

#### Scenario: Current pin meets a path
- **WHEN** the full-map overlay renders a current node with connectors to its north, east, south and west neighbours
- **THEN** exactly one current-location ring renders, its centre coincides with the current marker's centre, no teardrop pin renders, the ring's outer edge keeps at least 1 CSS px from every node label box, each of the four connectors runs from the current marker's centre and keeps a visible segment between the ring's outer edge and the neighbour's actionable halo, and the frame's corner brackets are pointer-inert

### Requirement: The shipped font manifest is the single source of the map cell measure
The client cell measure used to fit drawn map text — the Latin cell advance of the bundled monospace face, in em — SHALL have exactly one authored source: the Latin `cell_advance` (advance and units-per-em) the font importer records in the shipped code-point manifest when it pins a release of the bundled face.

#### Scenario: The generator exports, the surfaces consume
- **WHEN** the cell-table generator runs and a map surface budgets a drawn label or marker name
- **THEN** the generator SHALL export that measure into the client cell module from the manifest, and every map surface SHALL consume the exported value rather than a hand-written copy

#### Scenario: Re-pinning touches only pins and artifacts
- **WHEN** the bundled face is re-pinned to a new upstream release
- **THEN** only the importer release pin, the importer advance pin, and regenerated artifacts SHALL change; no specification, hand-written source constant, or test assertion SHALL need an edit that is not itself derived from the exported measure

#### Scenario: The exported cell measure equals the manifest
- **WHEN** the shipped code-point manifest and the client cell module are inspected together
- **THEN** the exported cell measure equals the manifest's recorded Latin advance divided by its recorded units-per-em, and the regenerated cell table and the manifest agree code point for code point

#### Scenario: A re-pinned face needs only tool pins and regenerated artifacts
- **WHEN** the bundled monospace face is re-pinned to a newer upstream release whose Latin cell advance differs
- **THEN** the importer advance pin, the regenerated slices, stylesheet, manifest, and cell module carry the new measure, every derived map-fit assertion recomputes from the exported value, and no hand-written metric constant or specification text names the old advance
