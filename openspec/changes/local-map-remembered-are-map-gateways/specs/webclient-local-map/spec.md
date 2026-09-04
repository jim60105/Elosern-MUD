# webclient-local-map delta

## MODIFIED Requirements

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
  the two city gates that both open onto one wilderness region
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

## ADDED Requirements

### Requirement: The map surfaces state a place name only where it adds information
This requirement is a reviewable addition raised alongside the remembered-node redefinition and may be
struck without affecting any other requirement in this change.

The in-view neighbourhood SHALL NOT repeat one place name across every cell it draws. On the
`wilderness` layer, an in-view `wild:` neighbour whose coordinates are a registered gate's approach
cell SHALL be labelled with that entry's anchor display name — the place the gateway leads to — instead
of the display name of the region the cell lies in; its node ID, `action`, edges, visibility, and every
other field SHALL be unchanged, so the payload states a better name for the same position and never
invents an identity for it. Every other in-view cell SHALL keep the region display name it carries
today, and every emitted node label SHALL remain a non-empty string.

The shared map renderer SHALL NOT draw visible label text for an in-view node whose label string is
identical to the `current` node's label string; that node SHALL keep its full label as its accessible
name, and its marker, shape ladder, landmark treatment, and activation SHALL be unaffected. The
`current` node SHALL always draw its own label. This suppression is a drawing rule about the set on the
canvas, not a payload rule: no payload field changes, and both validators keep their existing bounds
and their non-empty label rules unchanged.

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
