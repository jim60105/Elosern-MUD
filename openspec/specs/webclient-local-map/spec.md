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
- **THEN** `layer` SHALL be one of `grid`, `wilderness`, `instance`, or `interior`; `current_node` SHALL be a canonical node ID; `title` SHALL be a bounded localized map title; each node contains exactly `id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`, nullable `action`, and required `gateway`; each edge contains exactly `source`, `destination`, `label`, `known`, and `traversable`; and `legend` SHALL be a bounded list of text label entries

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
- **THEN** they enforce at most 64 `nodes`, at most 128 `edges`, at most 16 `legend` entries, node/edge/legend strings of at most 256 Unicode code points, `title` of at most 128 code points, node IDs of at most 128 characters, renderer-local `x`/`y` integers within `-10000000..10000000`, `known`/`traversable`/`current`/`anchor`/`landmark` as booleans, `visibility` as one of `current`, `visible_unvisited`, `visible_visited`, or `remembered`, and `action` as `null` or the exact `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node id>}` object

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
  NOT on a gate approach cell (e.g. `(856, 1080)` facing east toward `(857, 1080)`, or `(859, 1077)`
  facing north toward `(859, 1078)` — `(860, 1077)`/`(864, 1080)` face the footprint too but their
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

#### Scenario: Every node carries exact gateway metadata
- **WHEN** any available v1 local-map node is serialized, including an instance/interior or ordinary node
- **THEN** it carries `gateway`, which is null except for registered gateway nodes; a non-null value contains exactly `leads_to`, a non-empty string bounded by the existing 256-code-point node-string limit; schema_version remains 1 and no legacy omission or alias is accepted.

#### Scenario: Registered gate metadata names its far side
- **WHEN** a grid room hosting a registered gateway or a wilderness payload adjacent grid gateway is emitted
- **THEN** the grid room carries the far-side wilderness region name and the wilderness-adjacent grid gateway carries the settlement name; existing coordinates, node identity, actions, visibility and registry-based gateway resolution remain unchanged.

#### Scenario: Both validators reject malformed gateway values
- **WHEN** a node omits gateway, uses a scalar/array, has missing or extra gateway fields, or has empty, whitespace-only, non-string or over-bound leads_to
- **THEN** both validators reject the available panel under their exact-field checks; null and a bounded non-empty leads_to object pass, and the normalized browser model preserves gateway unchanged.

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
On the `wilderness` layer, an in-view `wild:` neighbour whose coordinates are a registered gate's approach cell SHALL be labelled with that entry's anchor display name — the place the gateway leads to — instead of its region's display name. On both surfaces a `visible_*` wilderness node whose label repeats the `current` node's label draws no visible text.

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
- **WHEN** either placement renders node visibility states
- **THEN** the existing current/visited/unvisited/remembered shape ladder stays non-colour-distinguishable; the island additionally draws a gate glyph for a gateway node while keeping current/visibility treatment readable. The overlay and graph glyphs remain unchanged.

#### Scenario: Each surface declares its label type steps
- **WHEN** a surface draws node labels or marker names
- **THEN** each surface SHALL declare its own node-label type size, and that size SHALL NOT resolve to drawn text larger than the surface's own smallest chrome type step, so a node label can never out-weigh the island's own title at any payload
- **AND** the island declares a 16-unit node-label step — equal to its 16px chrome step — and a 16-unit marker-name step; the full-map overlay declares 16 and 16

#### Scenario: A fitted drawing never shrinks text below its declared step
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The coordinate-field layers are inert decoration
- **WHEN** coordinate-field layers render on either surface
- **THEN** they remain pointer-inert, outside the accessibility tree and without node-marker/node-label classes, tab stops, activation or data-node identity; their colours use design tokens and encode no visibility state. Island uniform dots follow world anchors, compressed mode replaces dots with labelled distance rings, and motion follows the effective motion-level contract; overlay decoration is unchanged.

#### Scenario: The coordinate dot field states the lattice's coordinate space
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A dot never reads as a fifth node state
- **WHEN** the dot field renders beside the marker ladder
- **THEN** the dot's radius SHALL scale with the marker ladder and SHALL remain strictly and materially smaller than the smallest node marker's radius, it SHALL carry no stroke, no label, and no state class, and the state legend SHALL gain no entry for it, so the legend's four states stay closed exactly as the beyond-state note rule requires

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The axis cross follows the stated convention
- **WHEN** a surface considers drawing the axis cross
- **THEN** it SHALL draw a full-width and full-height axis line through the `current` node's drawn position ONLY where that same surface states the axis convention in words; a surface that states no orientation marks SHALL draw no axis, and the radial graph variant SHALL draw none on any surface because a graph asserts no axis
- **AND** the axis SHALL be drawn beneath every node marker — it necessarily passes through the `current` node's own marker, which is what an origin is, and that crossing SHALL NOT be read as a violation of the non-overlap invariant, whose axis clause governs the edge direction markers in the gutter band

#### Scenario: Decoration contrast is pinned in a band against the ground
- **WHEN** the dot field and the axis render against the canvas ground
- **THEN** each SHALL be present as a painted element whose resolved colour differs from the canvas ground; each SHALL keep a contrast ratio against that ground of at least 1.15:1 at every point of the canvas and at least 1.35:1 within the vignette's un-darkened inner field; and neither SHALL exceed the contrast that the connector-edge ink itself keeps against the same ground, so the coordinate decoration never reads louder than the topology it decorates
- **AND** these layers are decoration, not information: the coordinate claim they picture is carried redundantly by the node placement itself, by the header's axis orientation marks, and by the readout's coordinate figure, so no reader depends on them — but the lattice's geometry is its claim, so they SHALL NOT be invisible

#### Scenario: The render model exports two placements
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The lattice placement is bounded and rank-compresses on overflow
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The radial placement is deterministic and edge-honest
- **WHEN** the model computes the radial placement
- **THEN** it SHALL place the `current` node at the canvas centre and every other in-view node on a ring at BFS exit-hop distance from current over an UNDIRECTED adjacency built from the payload `edges` in both directions (traversable or not, since edges are topology, not passability, and ring membership SHALL NOT depend on an edge's serialization direction), with in-view nodes unreachable by any edge on the outermost ring and a current-only or entirely edgeless payload rendering the centre node alone on a fixed positive padded canvas
- **AND** ring members SHALL be ordered by first-discovery order then payload index and slotted at deterministic angles, so the same payload always yields byte-identical coordinates
- **AND** the radial geometry SHALL follow a declared footprint contract — canonical marker radii, a conservative label bounding box and its offset, a minimum ring-to-ring centre separation covering the stacked marker-plus-label extent, a per-ring minimum radius bounding the angular arc between adjacent slots, and a cumulative radius recurrence with fixed canvas padding — so the non-overlap invariant is constructible from the model alone
- **AND** neither placement SHALL infer distances or geometry the payload does not carry: a radial edge length and a lattice cell step are both presentation geometry with no world meaning

#### Scenario: Surfaces declare a fixed square canvas or a fitted view
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A fixed square canvas never magnifies
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The lattice fill grows pitch before taking margin
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The graph fill is a readable window
- **WHEN** a fixed-square graph variant fills its square
- **THEN** the fixed square window SHALL be centred on the radial placement's current node at one CSS pixel per user unit, clipping oversized radial drawings rather than shrinking their labels, and the complete graph and every full name SHALL remain reachable on the full-map surface

#### Scenario: No cap ever sizes a canvas
- **WHEN** the renderer resolves canvas dimensions
- **THEN** it SHALL accept no maximum-width or maximum-height cap and SHALL NOT resolve any cap into a width bound: no surface sizes its canvas by a cap, so there is no definite width to reconcile against a height cap and no engine-specific replaced-element constraint resolution can letterbox or distort a drawing
- **AND** the canvas's own natural size SHALL NOT be able to breach the island's square however many remembered markers it carries: the overlay's edge-marker gutter enlarges only the overlay drawing, while the island keeps its fixed 240-unit square with its markers and their whole names on the square's rim band, never a larger canvas or smaller text

#### Scenario: The island measures nothing and overlaps nothing of its own
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: No marker or label footprint ever intersects another
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The pitch is derived from what needs clearing
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The bare clearance term binds every adjacent pair
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The vertical term clears labels above markers
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The label term measures visible names in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The label term never binds on undrawn labels
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The derived pitch is a floor, bought without truncation
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The square cell keeps drawing and bearings in agreement
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

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
- **WHEN** island and overlay render the same committed coordinate-bearing payload
- **THEN** the overlay retains its existing complete lattice and the island renders its automatic projection of current and exits, small context dots that fit, and cross-layer exit-stub descriptors instead of cross-layer nodes; neither mutates the model, and graph payloads retain identical existing radial semantics. The full-map overlay has no island coordinate readout.

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
- **WHEN** a consumer reads node x/y
- **THEN** same-layer grid nodes carry metre coordinates and wilderness nodes carry kilometre-cell coordinates; cross-layer gateway slots are renderer-local offsets used for exit direction, never physical distance. Instance/interior coordinates remain layout values and are never interpreted as metric geography.

#### Scenario: The readout states the current coordinate figure and nothing else
- **WHEN** the island's readout line renders on a coordinate-bearing layer
- **THEN** it SHALL state the `current` node's coordinates as a two-integer figure — that node's payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — and SHALL state nothing else: it SHALL NOT state the current node's place name, its visibility state, a movement destination, or any other label, because the canvas already marks the current node and the shell's own location surface already names the place

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers or selects a node
- **THEN** the readout SHALL NOT be driven by pointer hover or by node selection: the island SHALL hold no hovered-node and no selected-node state, and the readout SHALL be a pure function of the committed payload, so it describes where the player is after every move without any re-seeding and cannot go stale when a payload replaces the rendered one

#### Scenario: No surface states a forbidden figure
- **WHEN** a surface renders map figures
- **THEN** the island may show its current-node coordinate figure, uniform grid-spacing caption or compressed distance-ring labels; it shows no other-node coordinate, numeric bearing or per-node distance. Remembered markers convey direction only; the overlay retains its existing figure restrictions.

#### Scenario: A coordinate-free layer resolves the readout to nothing
- **WHEN** the payload layer is coordinate-free
- **THEN** there is no coordinate figure, so the readout resolves to nothing and the empty-readout rule governs it unchanged: when the readout has nothing to state it SHALL state nothing and SHALL render no framed container, painting no box, rather than presenting an empty bordered widget; its row SHALL keep its one-line height so the island's size does not change with the layer

#### Scenario: No node's name depends on the readout
- **WHEN** the readout's label content is removed
- **THEN** every drawn node representation retains its full label as its accessible name; context omitted from the island remains reachable on the unchanged full-map surface, and an actionable cross-layer gateway stub is named `往 <leads_to> 移動`. Remembered names retain their visible edge-marker or full-map graph-list presentation and untruncated island text alternatives.

#### Scenario: The readout treatment is token-driven, not copied
- **WHEN** the island renders its readout
- **THEN** it SHALL adopt the redesign draft's closing-readout treatment as a token-driven rule rather than as a copy of the draft's declarations: it SHALL render at the island's smallest type step in the shared monospace font token, centred beneath the canvas, at a de-emphasised paper tier whose contrast against the island's panel background is at least 4.5:1, separated from the canvas by a step from the shared spacing scale, with no border, no background fill, and no padded box
- **AND** no draft hex value and no draft-canvas pixel literal SHALL be hardcoded for it

#### Scenario: The single full-map affordance is an invisible real button
- **WHEN** the island presents its full-map affordance
- **THEN** exactly one full-map affordance remains, with no visible expand-button chrome; cross-layer gateway stubs are separate focusable move buttons. The transparent full-bleed expand button remains beneath content with no focusable descendant and accessible name 展開全地圖.

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
- **WHEN** the island is rendered
- **THEN** remembered markers and their text alternatives remain inert and non-focusable; the existing full-map affordance remains, and each cross-layer gateway stub with a move action is an additional focusable button. Instance/interior behavior is unchanged.

#### Scenario: Remembered presentation follows the variant, once per surface
- **WHEN** remembered nodes are presented on a surface
- **THEN** their presentation SHALL follow the resolved layout variant, and each such node SHALL be presented exactly once on a given surface
- **AND** their payload coordinates SHALL NOT influence either exported node placement

#### Scenario: The lattice names its remembered places by edge direction marker
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Marker names stay inside the outermost gutter band
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A name's room is declared before it is drawn
- **WHEN** a surface prepares to draw marker names
- **THEN** the room a name may occupy SHALL be declared in the terms the placement helper consumes — the band depth every surface reserves, and, on a surface that draws its names OUTWARD across that band rather than along it, an outward name box — so the room is reserved before the names are drawn rather than discovered afterwards
- **AND** each name SHALL then be fitted to what that same declared geometry reserved for it, and no surface SHALL draw a name longer than the room its own declaration set aside

#### Scenario: The fit budget is measured in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Ambiguous names are dropped, never equalled
- **WHEN** a name does not fit its budget
- **THEN** it SHALL be truncated with an overflow indicator, and no surface SHALL draw two equal marker names while the payload labels behind them differ: rather than asserting that two distinct places are one place, it SHALL drop the visible name of a marker it cannot distinguish, keeping that marker's position, bearing, and state indicator
- **AND** that rule binds every surface that fits names, not only the smaller one
- **AND** a dropped or truncated visible name SHALL NOT reduce what a reader can obtain: every drawn marker's untruncated payload label SHALL remain available through the surface's assistive-technology text alternative

#### Scenario: The text alternative mirrors the drawn marker set
- **WHEN** the lattice variant's remembered markers carry no activation and are drawn inside a graphic
- **THEN** the text alternative mirrors those markers one-for-one in deterministic order with full names and octant words; it adds no remembered distance, numeric bearing or coordinates. The island scale caption and compressed ring labels are separate permitted distance information.

#### Scenario: The mirror omits nothing, invents nothing, adds no tab stop
- **WHEN** the surface derives its remembered-marker text alternative
- **THEN** it derives from the same remembered marker set and adds no tab stop; neither remembered markers nor their mirror become activatable. The island separately retains its full-map affordance and gateway exit-stub buttons.

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
- **WHEN** an island or overlay draws edges
- **THEN** connector layers are non-interactive and do not intercept activation; the coordinate-bearing island draws only labelled one-hop exit edges from current and no line to context dots. The overlay and radial graph retain their existing edge rendering; an absent endpoint yields no connector.

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
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear as named markers on the canvas border rather than occupying lattice cells

#### Scenario: A remote remembered place marks the canvas edge at its true direction, with its name
- **WHEN** a coordinate-layer payload remembers a known place outside the drawn extent, e.g. 聖潔王都 to the north-east or a cave to the south-west
- **THEN** its remembered diamond renders on the corresponding border of the canvas, pointing along the true coordinate bearing, with that place's name drawn as visible text beside it — in the marker gutter band on the overlay, and whole inside the island's square on the island (beside the diamond in the rim band, reading through it, or wrapped onto the next free inward row, never shortened) — and no distance, angle, or coordinate figure appears with it

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
- **THEN** on the overlay every marker name is rendered wholly inside the marker gutter band outside the canvas rect — the rect the coordinate-field padding grows, so the band stays outermost — so no marker name's box intersects any node marker, node label, or the drawn axis line; on the island every marker name is drawn whole inside the fixed square, clear of every diamond and every drawn node marker and, wherever the square leaves room, every drawn node label; on both surfaces no two marker names' boxes intersect each other

#### Scenario: Rank compression never skews a marker's direction
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

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
- **WHEN** the committed payload layer is coordinate-bearing
- **THEN** the island retains its axis orientation marks and current-node-only coordinate readout; its scale caption or compressed rings state the mapping separately without adding any per-node distance or numeric bearing.

#### Scenario: The readout states the coordinate figure and nothing else
- **WHEN** a wilderness payload whose current node is labelled 西部丘陵與谷地 at (60, 107) renders on the island
- **THEN** the readout line reads exactly the two-integer coordinate figure for (60, 107), it carries no place name, no 目前所在 or other visibility-state word, and no movement destination, and the place name appears instead on the shell's own location surface

#### Scenario: Hovering or activating a node never changes the readout
- **WHEN** the player hovers a non-current node, then activates one, on a coordinate-bearing layer
- **THEN** the readout line still states the current node's coordinate figure and nothing else, no coordinate figure for the hovered or activated node is rendered anywhere, and the island holds no hovered-node or selected-node state that the readout could go stale on

#### Scenario: A node's name stays reachable without the readout
- **WHEN** an in-view node's label is truncated on the island's canvas and a remembered node is presented alongside it
- **THEN** the drawn node retains its full accessible name independently of truncation; an omitted context node or cross-layer target keeps its original full name reachable on the unchanged full-map surface, while an actionable gateway stub is named `往 <leads_to> 移動`. Remembered nodes retain their visible marker or full-map graph-list names and untruncated island alternatives.

#### Scenario: A screen-reader user can still reach every remembered place
- **WHEN** a screen-reader user reads the minimap island on a wilderness payload carrying several remembered gateways, none of which is focusable and each of which is drawn inside the map graphic
- **THEN** the island exposes one text-alternative entry per drawn marker, in a deterministic order, each stating that place's untruncated authored name and its direction as one of the eight octant names, so no remembered place is reachable only by sight

#### Scenario: Replacing the list adds no tab stop and no activation
- **WHEN** a keyboard user tabs through an island carrying remembered gateways
- **THEN** remembered markers and text alternatives add no tab stop or travel action; the full-map affordance and any actionable cross-layer gateway stub retain their own behavior and do not activate each other.

#### Scenario: A coordinate-free layer asserts no orientation and no coordinates
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure, the map title renders exactly as on a coordinate-bearing layer, and the readout line — having nothing to state — states nothing and paints no box

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A densely populated lattice keeps readable collision-free geometry
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A sparse lattice scaled up never reintroduces overlap
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** a graph-variant payload combines a two-ring in-view placement with the model's maximum of remembered nodes
- **THEN** the island lays out no remembered-node list at all, its canvas is still 240 × 240 CSS px at the 1451x790 reference viewport (the canvas never depends on payload content, and the chrome factor magnifies it uniformly at every larger viewport), its title and readout row keep their places, the island's size equals its size for the same placement with no remembered node, and no required island content has to be scrolled out of view

#### Scenario: The name gutter never hands the anchor a scrollbar
- **WHEN** remembered markers enlarge the required drawing
- **THEN** the coordinate-bearing island keeps its 240-unit projection, current at (120,120), all exits within the exit ring and readable text; remembered markers keep their edge-direction presentation as smaller rim-band diamonds whose names are drawn whole inside the square, and the anchor has no scrollbar.

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

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
- **WHEN** the island renders current, visited, unvisited and gateway nodes
- **THEN** current retains its larger seal treatment, visited is solid and unvisited hollow; gateway nodes add the gate glyph, room name and `通往 <leads_to>` second line without relying on colour to identify a gateway.

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
- **WHEN** coordinate-bearing and coordinate-free payloads commit in turn
- **THEN** the island uses the automatic projection only for grid/wilderness, with exit routes and no context routes or cross-layer nodes; the overlay keeps its complete existing lattice and radial graphs remain unchanged. Actions retain their payload identity; only the island scale caption/rings add distance text and no manual island zoom or layout control is offered.

#### Scenario: The orientation mark follows the resolved layout
- **WHEN** the payload's layer resolves to the graph variant (`interior`, `instance`)
- **THEN** the island renders no axis orientation mark and no coordinate figure, and on a layer resolving to the lattice (`grid`, `wilderness`) the mark renders alongside the current node's coordinate figure

#### Scenario: The island's canvas claims its content width as coordinate margin
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The island's name band is reserved as band depth, not as an outward box
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A sparse payload reads airy rather than magnified
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The height budget is spent as an equivalent width bound
- **WHEN** a tall lattice renders on a natural mount, island and full map
- **THEN** the natural mount and overlay keep their existing lattice geometry and readable view; the island selects an automatic level or compression for current and exits in its 240-unit square, without using a height-derived width cap or shrinking text.

#### Scenario: A graph payload is cropped to its footprint and never magnified
- **WHEN** an interior graph containing one node and then a graph containing many neighbors renders on the island
- **THEN** both use a fixed 240-unit square window centered on the current node, render labels at exactly 16 CSS px at reference, and leave every full name reachable through the full map

#### Scenario: The overlay keeps its geometry and gains only the coordinate field
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

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
- **WHEN** an available local-map payload renders
- **THEN** exactly one transparent full-bleed full-map button named 展開全地圖 exists; the root has no role or tab stop and no expand icon or labelled expand control is added. Separate exit-ring gateway buttons remain visible/focusable for their move action.

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
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A field whose pitch stopped meaning one cell is rejected
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A coordinate field that went invisible fails
- **WHEN** the uniform island dot field or an existing overlay dot field and axis are measured against canvas ground
- **THEN** existing token contrast floors continue to apply to the field and axis; compressed island mode has distance rings instead of dots and does not fail for omitting dots.

#### Scenario: The dot field never reads as a fifth node state
- **WHEN** uniform dots render beside node markers
- **THEN** each dot is materially smaller than the smallest marker, with no stroke, label, state class, node identity or activation; the visibility legend is unchanged. Compressed island rings use distance text and do not imply a node visibility state.

#### Scenario: The vignette is the knowledge edge, not terrain
- **WHEN** the island's lattice renders its canvas edges
- **THEN** exactly one vignette element darkens the canvas outward as a single full-canvas gradient wash, no per-cell fill, per-region fill, or shape tracing any terrain feature is introduced anywhere, and the overlay — whose `mapcanvas` background already is its one vignette — paints no second wash

#### Scenario: The vignette never erases the far-field dots
- **WHEN** uniform island dots nearest canvas corners are measured through the vignette
- **THEN** they retain the existing contrast presence floor; compressed island mode uses rings in place of dots and the vignette cannot erase their distance information.

#### Scenario: The axis is drawn only where the convention is stated in words
- **WHEN** a coordinate-bearing payload renders on the island, which states `北↑ 東→` in its header, and in the full-map overlay, which states no orientation marks
- **THEN** the island draws a full-width and full-height axis line through the current node's drawn position beneath every node marker, and the overlay draws none — asserting no axis on a surface that names none

#### Scenario: The axis crossing the current marker is not a collision
- **WHEN** the island draws its axis through the `current` node
- **THEN** the axis passes beneath that node's own marker, which is what an origin is, the drawn edge direction markers stay wholly outside the canvas rect that contains the axis, and the non-overlap invariant that names the axis is satisfied

#### Scenario: The graph variant draws no coordinate field and no axis
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: A node label never renders larger than the surface's own chrome
- **WHEN** a sparse or crowded payload renders on the island
- **THEN** every drawn node label is exactly its declared 16-unit step at reference scale, never smaller through SVG scaling and never larger than the island's title

#### Scenario: The pitch clears exactly what the drawn label set needs
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Vertical clearance is derived even above an unlabeled marker
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The drawn cell is square so the lattice and its bearings agree
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The decoration layers stay out of the audit and the accessibility tree
- **WHEN** geometry audit and assistive technology inspect island decoration
- **THEN** dots, rings, vignette and axis add no node-marker/node-label boxes or tab stops and intercept no pointer events; distance text supplies the scale information. Remembered markers remain inert while gateway exit stubs are separate named buttons.

#### Scenario: Reduced motion and the non-colour encoding are unaffected
- **WHEN** the island renders with the reduced-motion preference active and with the colourblind override on
- **THEN** none of the three new layers animates or transitions anything, none carries a visibility state, the four-state shape ladder and its non-colour redundancy are unchanged, and every focus treatment behaves exactly as before

#### Scenario: The lattice colours resolve to existing tokens with no draft literal
- **WHEN** the coordinate field, the vignette, and the axis render on either surface
- **THEN** each layer's colour resolves to a design token already defined for the map surfaces, no new token is required, and no draft hex value and no draft-canvas pixel literal is hardcoded for any of them

#### Scenario: The island scales once with the desktop chrome factor
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: Labels are budgeted in monospace cells
- **WHEN** a coordinate-bearing sparse map is projected into the fixed HUD or full-map viewport
- **THEN** the overlay keeps its existing uniform lattice projection and view controls; the coordinate-bearing island uses its current-centred automatic uniform/compressed projection, drawing all same-layer exits, drawable context and the remembered edge-direction markers — on the island smaller diamonds on the square's rim band, each name drawn whole inside the square. Payload coordinates and action identity remain unchanged; coordinate-free graphs retain their existing layout.

#### Scenario: The fixed island consumes automatic projection
- **WHEN** a grid/wilderness payload with one-hop and two-hop nodes renders in the island
- **THEN** current is centred at (120,120) in a 240-unit square, every same-layer exit including action-null exits is drawn inside radius 88, drawable context uses small background dots without connecting lines, and context outside the canvas is omitted; no window over a minimum-pitch lattice can hide an exit.

#### Scenario: The background states scale by shape and text
- **WHEN** the island changes between uniform and compressed mode
- **THEN** uniform mode draws world-anchored dots at M/5 metres (20 units) and a spacing caption; compressed mode draws labelled distance rings using its projection and no dot field. Scale text respects the 16 px floor and is distinct from the unchanged coordinate readout.

#### Scenario: Metric fixtures exercise actual renderer exits
- **WHEN** Altoria 21-node, Ciaran 10-node, wilderness 3x3, Altoria south-gate and extreme-ratio fixture stories render
- **THEN** each metric story verifies every exit representation is inside the canvas and no two exit markers overlap; existing unit-coordinate overlay fixtures and coordinate-free stories keep their existing contracts.

#### Scenario: Labels are assigned in navigation priority
- **WHEN** island marker labels compete for space
- **THEN** eight candidate positions per marker are tried in exit, current, context priority; an exit label that fits nowhere remains drawn truncated to labelMax with a leader line, a context label that fits nowhere is omitted, and each full name remains in its accessible name. Gateway second-line labels respect the 16 px floor. Remembered edge-marker names are laid out before node labels and are always drawn whole, never truncated; a duplicate wilderness region label suppressed as information-free is not an exit label dropped for lack of room.

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
Every traversable adjacent wilderness node in the local-map payload SHALL carry an `explore.move` action
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
For every gate of every entry in the wilderness entry registry, the payload SHALL preserve the matched gateway pair on both sides, the island SHALL represent a cross-layer target by an exit stub instead of a node, and the destination SHALL always equal the node carrying it and always equal what `resolve_wilderness_destination` derives from the same registration the traversal code reads.

#### Scenario: The approach cell renders the gate's grid node
- **WHEN** the puppet stands at the gate's approach cell
- **THEN** the gateway direction (`return_direction`) SHALL emit the gate's grid node — canonical `grid:` id, gate room label, resolver-derived visibility, and a move descriptor with that id as destination

#### Scenario: The gate room renders the approach cell's wild node
- **WHEN** the puppet stands at the gate room
- **THEN** the grid layer SHALL emit that gate's approach cell's `wild:` node — canonical `wild:` id for the approach cell, the region's display name, knowledge-derived visibility, and a move descriptor whose `exit_ref` is that gate's exit and whose destination is that `wild:` id

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
- **WHEN** the puppet stands at a registered gate approach cell (e.g. `(864, 1080)` for the east
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
The wilderness presenter SHALL append one localized cell-scale note after the four visibility labels, deriving its value at build time from the owning provider constant. No consumer SHALL duplicate legend generation or its conversion. The island projection SHALL convert existing one-kilometre wilderness cell deltas to metres under that fixed coordinate-frame contract without parsing the localized legend or changing payload coordinates.

#### Scenario: The scale note is the fifth entry
- **WHEN** the scale note is appended
- **THEN** the four state labels SHALL keep their existing order and positions, so the scale note is the fifth entry

#### Scenario: Other layers keep their legend exactly as before
- **WHEN** payloads for the `grid`, `instance`, and `interior` layers are built
- **THEN** they SHALL keep their legend exactly as before (the four state labels)

#### Scenario: The extended legend stays inside the existing bounds
- **WHEN** the extended legend is validated
- **THEN** it SHALL remain within the existing bounds (at most 16 entries, 256 code points each) and SHALL pass both validators unchanged; no payload schema field is added or altered

#### Scenario: The constant is read from its owning module
- **WHEN** the presenter assembles the legend
- **THEN** it SHALL read the constant as an attribute of its owning module at legend-assembly time, never a value imported into the presenter's own namespace, so patching the provider module attribute is observed by the presenter

#### Scenario: A wilderness payload legend carries the scale note
- **WHEN** the `local_map` presenter builds an available payload for a `TerrainRoom`
- **THEN** the legend is the four state labels followed by one entry whose text contains the string form of `WILDERNESS_KM_PER_CELL`, and the payload passes the exact Python validator

#### Scenario: Non-wilderness layers are untouched
- **WHEN** the presenter builds available payloads for grid, instance, and interior rooms
- **THEN** each legend equals the four state labels exactly, with no scale note

#### Scenario: The scale note follows the single constant
- **WHEN** a test patches `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` to a different integer and rebuilds a wilderness payload
- **THEN** the scale note's kilometre figure equals the patched value, proving the note is derived from the provider constant rather than a duplicated literal

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
- **WHEN** a physical sparse map opens or its viewport changes
- **THEN** uniform fit/zoom/pan projects immutable metric coordinates; labels retain readable screen-space sizing, every node remains reachable through pan/zoom, and view state remains opening-local.

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
- **WHEN** a physical sparse map opens or its viewport changes
- **THEN** uniform fit/zoom/pan projects immutable metric coordinates; labels retain readable screen-space sizing, every node remains reachable through pan/zoom, and view state remains opening-local.

#### Scenario: A small map opens at its declared size, not magnified
- **WHEN** a physical sparse map opens or its viewport changes
- **THEN** uniform fit/zoom/pan projects immutable metric coordinates; labels retain readable screen-space sizing, every node remains reachable through pan/zoom, and view state remains opening-local.

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
- **WHEN** a coordinate-bearing island or an unchanged graph/overlay renders a large payload
- **THEN** the island automatically fits all same-layer exits at the declared text floor, may omit off-canvas context and never draws cross-layer targets as nodes; all payload nodes/actions remain in the model. The graph island retains its current-centred scale-1 window, and the unchanged full map makes every full name and remembered gateway reachable through its view controls.

#### Scenario: The derived pitch clears the drawn label set
- **WHEN** metric nodes have dense screen-space projections
- **THEN** the overlay retains its existing uniform geometry; the island uses its metric projection with bounded overlap spreading, readable labels and authoritative action identity, without changing payload coordinates.

#### Scenario: Ordinary neighbourhood is readable
- **WHEN** a three-by-three grid lattice of distinct two- and four-glyph room names with no remembered gateway renders on the island at 1451x790 and at 2560x1440
- **THEN** the title, orientation marks and readout compute to 16 CSS px at the reference viewport, the drawing's scale is 1, every drawn node label is at least 16 CSS px at the reference viewport (and at least 22.4 CSS px at 2560x1440, the same labels at the 1.4 chrome cap) and at most the island's declared 16-unit step at the reference scale, and no node marker or node label overlaps another node's marker or label

#### Scenario: Dense knowledge stays available
- **WHEN** a bounded dense payload with remembered gateways renders on island and overlay
- **THEN** the island retains its 240-unit square and text floor, draws current and every exit, omits off-canvas context and preserves remembered edge-direction markers. The model retains all payload nodes and the unchanged overlay keeps their names reachable.

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

### Requirement: The graphical grid map is independent of automatic ASCII map display

For representable grid and anchor rooms with fixed canonical inputs, changing only automatic ASCII-map display SHALL leave the complete available version-1 `local_map` payload identical. The graphical map SHALL retain its adjacent-node movement descriptors and existing navigation behavior without consuming ASCII text.

#### Scenario: Disabled text maps produce the same complete graphical payload

- **GIVEN** a representable grid or anchor room with fixed player knowledge, valid visual-range options and at least one traversable adjacent exit
- **WHEN** the production presentation registry renders `local_map` with automatic text-map display enabled and disabled, with all canonical inputs held fixed
- **THEN** both payloads are available and deeply equal, including schema version, layer, current node, title, node identities and coordinates, visibility and anchor flags, edges, legend and movement descriptors
- **AND** at least one adjacent node retains a non-null `move` descriptor identifying its real exit and canonical destination

#### Scenario: Explore look leaves the map widget input intact

- **GIVEN** the browser has an available grid-layer payload in either grid-room type and automatic ASCII output is disabled
- **WHEN** `explore.look` with `{"room": true}` succeeds and the normal presentation refresh builds `local_map` again
- **THEN** the refreshed payload is identical to the immediately preceding payload for the same canonical inputs and remains available to the existing widget
- **AND** player location, clock and knowledge remain unchanged by look and presentation
- **AND** the adjacent-node movement descriptors remain usable under the existing `explore.move` action contract

### Requirement: Metric coordinates survive authoritative transport and uniform projection
Local-map transport SHALL accept physical settlement coordinates and the wilderness frame. The full-map overlay SHALL preserve relative metric spacing under its existing uniform viewport scale, with pan and zoom; the island SHALL use automatic uniform or compressed projection with exact bearings except bounded overlap spreading; row/column rank compression SHALL be removed. Server coordinates and node/action identity SHALL remain authoritative.

#### Scenario: Unequal gaps survive real rendering
- **WHEN** nodes at (0,0), (100,0), (1000,0) and (1000,6500) pass both validators and render
- **THEN** the overlay keeps its 1:9 gap ratio under its unchanged uniform view. The island uses its exit-driven uniform/compressed mapping without changing wire coordinates or action identity; logarithmic island compression is permitted only under the approved threshold rules.

#### Scenario: Expanded bounds
- **WHEN** settlement (6500,6350) and wilderness (2699,2699) arrive over the real protocol
- **THEN** both validate; malformed noninteger/nonfinite coordinates remain rejected without guessed geometry.

#### Scenario: Visibility and remembered markers
- **WHEN** a viewport pans across remembered and unknown hidden locations
- **THEN** remembered boundary markers preserve physical orientation; unknown locations stay absent, movement descriptors retain actual traversable exits, and no action or knowledge is created by projection.

#### Scenario: Coordinate-free interiors
- **WHEN** an interior graph with no physical coordinates is shown
- **THEN** its existing graph semantics remain without invented meter positions.

### Requirement: Island projection selects a metric scale for one-hop exits
The coordinate-bearing island SHALL centre the current node at (120,120) in a 240-unit square and select its scale from same-layer one-hop exits, including locked exits. Normal placement SHALL preserve exact bearings and use the smallest fitting level in the approved ladder with R_MAX 88 and R_MIN 36.

#### Scenario: Distance inputs respect their coordinate frames
- **WHEN** a grid or wilderness model is projected
- **THEN** grid deltas are metres and wilderness cell deltas are converted to metres at the existing one-kilometre cell scale without altering the payload; exit tiers come from non-empty-labelled edges incident to current, independent of action; other same-layer in-view nodes are context and cross-layer nodes never affect scale.

#### Scenario: The full ladder and worked uniform examples
- **WHEN** positive exit distances are projected
- **THEN** the level is selected from 10,15,20,30,50,75,100,150,200,300,500,750,1000,1500,2000,3000,5000 metres per 100 units using d_max * 100 / M <= 88; Altoria plaza exits about 850–1090 m choose 1500 with radii about 57–72, and wilderness cardinal/diagonal neighbours choose 2000 with radii 50 and about 71.

#### Scenario: Hysteresis keeps at most one coarser fitting level
- **WHEN** the prior level still fits all exits and is at most one ladder step coarser than the ideal
- **THEN** it is retained; an insufficient level or one more than one step coarser is replaced by the ideal, and a changed current-node map key discards the previous level before selection.

### Requirement: Island projection compresses extreme exit distances monotonically
When the nearest uniform exit radius is below 36 or no ladder level fits the farthest exit, the island SHALL use compressed distance mapping from radius 36 to 88. Distance order and bearings SHALL remain intact except for the bounded overlap-spreading rule.

#### Scenario: Logarithmic compression and equal distances
- **WHEN** positive exit distances span d_min to d_max in compressed mode
- **THEN** r(d) = 36 + 52 * ln(d/d_min) / ln(d_max/d_min); context closer than d_min uses 36*d/d_min; equal positive exit distances use radius 66; bearings are unchanged before overlap handling.

#### Scenario: Compression boundaries
- **WHEN** an 80 m exit and a 1200 m exit are projected, or d_max exceeds 4400 m
- **THEN** compressed mode is used; a nearest radius exactly 36 remains uniform if all exits fit, and a farthest radius exactly 88 at level 5000 still fits.

### Requirement: Island projection handles sparse and coincident nodes deterministically
No-exit, zero-distance and overlapping-exit inputs SHALL produce finite deterministic positions. Context SHALL use the same mapping, with off-canvas context omitted and remembered remote nodes retaining their existing edge-direction presentation.

#### Scenario: No exits and no distance
- **WHEN** a model has no exits
- **THEN** drawable context supplies the level-selection distances; with no positive drawable distance the default level is 100, and the current-only result remains centred.

#### Scenario: Zero-distance exits
- **WHEN** exits have no defined bearing because their distance from current is zero
- **THEN** their bearings are assigned in payload order starting north and evenly spaced; their placement is finite and keeps the current marker clear, without evaluating a logarithm of zero.

#### Scenario: Overlapping exits
- **WHEN** exit marker footprints at similar radii would overlap
- **THEN** they are spread symmetrically about their mean bearing by no more than ±20 degrees; non-overlapping exits keep exact bearings and ordinary context does not receive invented routes.

### Requirement: Island projection separates gateway stubs from node scale
A cross-layer target SHALL be absent from island node placement and all distance calculations, while retaining its exit bearing, far-side label and validated move action as an exit-stub descriptor.

#### Scenario: Gate slot cannot change scale
- **WHEN** a current gateway carries a cross-layer target at a renderer-local slot and that slot offset changes
- **THEN** same-layer scale and projected node positions remain unchanged; the target yields an exit-ring stub with its bearing, `通往 <leads_to>` label and original nullable action; gateway metadata comes from the current gateway or target as available, never from invented geography.

### Requirement: Island background describes the selected distance mapping
Uniform projection SHALL return dots with 20-unit spacing anchored to integer world multiples of M/5 metres and a scale-spacing caption. Compressed projection SHALL return labelled concentric distance rings positioned by the same distance mapping, with shape and text distinguishing compression.

#### Scenario: Dot anchors follow ground
- **WHEN** the current location moves while level M is unchanged
- **THEN** each dot remains anchored to integer multiples of M/5 metres and its screen offset changes with the world-coordinate origin; the caption states that spacing, such as `格距 300 m` at M=1500.

#### Scenario: Compressed rings use real distances
- **WHEN** a compressed projection is generated
- **THEN** a bounded readable set of positive distances, such as 100 m, 300 m and 1 km when in range, receives radii from the same mapping and distance labels; no uniform dot field is returned.

### Requirement: Island gateways expose labelled accessible exit-ring controls
The island SHALL draw gateway nodes with a gate glyph, room label and second line `通往 <leads_to>`. A cross-layer target SHALL be represented only by an exit-ring arrow labelled `通往 <leads_to>`, retaining the target's nullable move action; an actionable stub SHALL be a focusable button named `往 <leads_to> 移動`.

#### Scenario: Current city gate offers wilderness travel
- **WHEN** the current city gate carries its far-side region metadata and a cross-layer target move descriptor
- **THEN** the region-labelled stub is drawn at that target bearing on the exit ring; pointer, Enter and Space each submit exactly one move using the original exit_ref and current_node, without also opening the map or inventing a destination.

#### Scenario: Wilderness offers city return without city streets
- **WHEN** a wilderness payload carries an adjacent grid gateway with settlement leads_to metadata
- **THEN** the island shows the settlement-labelled exit-ring stub, no cross-layer grid node or city streets, and no scale effect from the renderer-local gateway offset; its move arrives at the original grid destination.

#### Scenario: A locked gateway remains navigation information
- **WHEN** a gateway exit has action null
- **THEN** its exit representation and far-side label remain visible, but activation submits no move; the gateway field never grants traversal that the server withheld.

#### Scenario: Gateway stories check the full exit set
- **WHEN** metric south-gate and wilderness-return stories run
- **THEN** the story checks every same-layer exit marker and cross-layer exit-ring representation inside the canvas with no two exit markers overlapping; its focus and activation assertions preserve exact payload actions.

### Requirement: Island movement uses scale-aware effective motion
For unchanged mode and level, island movement SHALL retain its existing FLIP pan and move world-anchored dots with the drawing. A changed level or mode SHALL use a short crossfade for effective full motion and switch immediately for effective reduced or off motion. Overlay and instance/interior transitions SHALL remain unchanged.

#### Scenario: Same scale pans the ground
- **WHEN** a move commits with unchanged projection level and mode
- **THEN** the existing pan transition is used and dots move with the same drawing transform instead of staying screen-fixed; final dot anchors still match world multiples.

#### Scenario: A changed level or mode never uses equal-scale FLIP
- **WHEN** a move changes uniform level or switches between uniform and compressed mode
- **THEN** full motion uses a short crossfade under the shared motion tokens; reduced/off commit the new projection immediately, without an animated scale interpolation or lingering previous-scale frame.

#### Scenario: Real gateway journey remains usable
- **WHEN** the player walks Altoria south gate to wilderness and back in the real client
- **THEN** each settled island shows current and every available adjacent exit, valid far-side gate labels and usable return controls; the overlay still uses its existing lattice and coordinate-free layouts remain unchanged.
