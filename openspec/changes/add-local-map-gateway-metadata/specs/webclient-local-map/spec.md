# Spec Delta

## MODIFIED Requirements

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
