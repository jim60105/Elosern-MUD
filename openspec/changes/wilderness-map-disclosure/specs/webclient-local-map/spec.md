## MODIFIED Requirements

### Requirement: local_map is a read-only version-1 presentation panel
local_map SHALL retain its exact read-only version1 field schema and canonical layer geometry; wilderness node facts SHALL require permanent reveal and hidden-location visitation before serialization.

#### Scenario: Node geometry is presentation-only, never invented
- **WHEN** a node is placed on any layer, including a gateway node shown on a layer other than its home layer; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its `x`/`y` are renderer-local presentation geometry placing it at the adjacent position of the step that reaches it (adjacency or visual-range position), not canonical world coordinates; a node's identity NEVER forces its geometry to equal its own world coordinates, and the payload NEVER invents an identity for a position

#### Scenario: Remembered nodes share the drawn layer's coordinate space
- **WHEN** a `remembered` node is emitted on a coordinate-bearing layer (`grid`, `wilderness`) — the one node kind with no step to position it; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its `x`/`y` SHALL be that node's own validated coordinates **in the layer currently being drawn** — the gateway's wilderness-side approach cell on the `wilderness` layer, the gateway's grid-side room coordinates on the `grid` layer — and SHALL NEVER be coordinates read from a different coordinate space nor a renderer-local or probed slot, because the current node and every remembered node must sit in one coordinate space for the raw-delta direction geometry to mean anything

#### Scenario: Payload field composition is exact
- **WHEN** an available payload is serialized; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `layer` SHALL be one of `grid`, `wilderness`, `instance`, or `interior`; `current_node` SHALL be a canonical node ID; `title` SHALL be a bounded localized map title; each node contains exactly `id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`, nullable `action`, and required `gateway`; each edge contains exactly `source`, `destination`, `label`, `known`, and `traversable`; and `legend` SHALL be a bounded list of text label entries

#### Scenario: The presenter leaks no live references
- **WHEN** the presenter emits any payload; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL emit no live object or filesystem reference

#### Scenario: An unrepresentable room uses the registered unavailable form
- **WHEN** the current room cannot be represented; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the presenter SHALL use the registered common unavailable form

#### Scenario: A node with no coordinate in the drawn layer is omitted, never plotted
- **WHEN** a node's identity carries no coordinate in the layer being drawn — a registered gateway whose grid-side room belongs to a different `z_map_key` than the map the `grid` layer is drawing; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the node SHALL be omitted from the payload entirely rather than plotted at a fabricated, probed, cross-space, or current-node position, and it remains fully presented on the payload of the layer it does have a coordinate in

#### Scenario: Provider-invalid wilderness directions render nothing
- **WHEN** a wilderness direction's neighbor is provider-invalid — outside the continent rectangle or an anchor footprint cell; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** that direction renders no node and no walkable edge, exactly as out-of-bounds directions render today, and the payload NEVER presents an anchor footprint cell as a walkable `wild:` node

#### Scenario: Shared bounds are exact on both validators
- **WHEN** the server and client validators check a payload, sharing the bounds unchanged; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** they enforce at most 64 `nodes`, at most 128 `edges`, at most 16 `legend` entries, node/edge/legend strings of at most 256 Unicode code points, `title` of at most 128 code points, node IDs of at most 128 characters, renderer-local `x`/`y` integers within `-10000000..10000000`, `known`/`traversable`/`current`/`anchor`/`landmark` as booleans, `visibility` as one of `current`, `visible_unvisited`, `visible_visited`, or `remembered`, and `action` as `null` or the exact `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node id>}` object

#### Scenario: Conformance is enforced on serialized size
- **WHEN** both the Python and JavaScript validators assemble a payload; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** each computes the canonical UTF-8 byte length and rejects a payload exceeding the 65,536-byte OOB envelope limit — every conforming serialized payload SHALL fit it — because the per-field ceilings are independent and a payload that maximizes every string field at once would otherwise serialize beyond the limit

#### Scenario: Worst-case serialization is pinned both ways
- **WHEN** the serialization tests run; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** one test proves a structurally maximal realistic payload fits the envelope comfortably, and a second test proves a payload at every string ceiling at once is rejected

#### Scenario: Presenter ceilings stay internal
- **WHEN** the presenter applies its own tighter internal ceilings — such as the remembered gateway cap; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** no shared bound changes, no presenter-side ceiling is mirrored in the client validator, and none alters the shared table

#### Scenario: A grid room produces a grid-layer payload
- **WHEN** the active puppet is in a `GridRoom`/`AnchorRoom` with knowledge and an adjacent traversable; any asserted wilderness destination facts are revealed and location-identity permitted
  grid exit
- **THEN** `local_map` reports `layer == "grid"`, the current node's `grid:` ID, bounded nodes and
  edges, and a before/after comparison of canonical game state is unchanged

#### Scenario: A wilderness room produces a wilderness-layer payload
- **WHEN** the active puppet is in a `TerrainRoom`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `local_map` reports `layer == "wilderness"`, the current `wild:` node, legal adjacent
  coordinates bounded by provider validity, and terrain labels, except that a registered gateway
  direction renders the resolved `grid:` gate node instead of the geometric wild cell, and a
  provider-invalid direction (out of bounds or an anchor footprint cell) renders neither node nor
  walkable edge

#### Scenario: An instance room produces a coordinate-free instance payload
- **WHEN** the active puppet is in an `InstanceRoom`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `local_map` reports `layer == "instance"` with a `room:<dbref>` current node and a small
  graph containing the current node, its origin/return, and known real Exit edges, with no `grid:` or
  `wild:` identity invented for it

#### Scenario: An ordinary interior produces an interior payload
- **WHEN** the active puppet is in a permanent interior `Room` such as the guild hall or general store; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** `local_map` reports `layer == "interior"` with a coordinate-free graph of real Exits

#### Scenario: A gateway step never renders the wild cell it replaces
- **WHEN** the puppet stands at a registered gate approach cell and the gateway direction resolves to; any asserted wilderness destination facts are revealed and location-identity permitted
  a grid node
- **THEN** no node with the geometric wild cell's `wild:` ID exists in the payload for that direction,
  and the gateway node carries the gate's `grid:` ID positioned at the adjacent cell

#### Scenario: An anchor footprint renders as absent ground, not a walkable cell
- **WHEN** the puppet stands at any wilderness cell adjacent to an anchor's derived footprint and; any asserted wilderness destination facts are revealed and location-identity permitted
  NOT on a gate approach cell (a gate approach cell faces the footprint too, but that
  footprint-facing direction is the registered gateway, which renders per the gateway rules) and
  the panel is built
- **THEN** no `wild:` node with a footprint cell's coordinate exists in the payload, the direction
  toward the footprint carries no move action, and the direction is presented exactly like today's
  out-of-bounds edge

#### Scenario: A remembered node is never plotted from a cross-coordinate-space position
- **WHEN** a payload is built on a coordinate-bearing layer while the player's knowledge contains a; any asserted wilderness destination facts are revealed and location-identity permitted
  registered gateway's node on the other side of that gateway — the gate room's `grid:` node while the
  `wilderness` layer is drawn, or the approach cell's `wild:` node while the `grid` layer is drawn
- **THEN** every `remembered` node in the payload carries the ID grammar of the layer being drawn with
  its own coordinates in that layer's space, no node carries a coordinate taken from the other space,
  and no `remembered` node is positioned at a renderer-local slot, a free-slot probe result, or the
  current node's coordinates

#### Scenario: A gateway with no coordinate in the drawn layer is omitted, not fabricated
- **WHEN** the `grid` layer draws a map while the player remembers a registered gateway whose grid-side; any asserted wilderness destination facts are revealed and location-identity permitted
  room belongs to a different `z_map_key`
- **THEN** no node for that gateway exists in the payload at all, the payload passes the exact
  validator, and the same gateway still appears on the payload of the layer whose coordinate space it
  belongs to

#### Scenario: An unrepresentable room is unavailable, not fabricated
- **WHEN** the active puppet has no location, the location cannot be represented, or the knowledge; any asserted wilderness destination facts are revealed and location-identity permitted
  record is corrupt
- **THEN** `local_map` uses the common schema-valid unavailable form with a stable reason and contains
  no invented nodes, coordinates, or edges

#### Scenario: Presenter failure remains isolated
- **WHEN** the `local_map` presenter raises while status and narrative remain healthy; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** only `local_map` becomes correlated unavailable and normal text output remains usable

#### Scenario: Every node carries exact gateway metadata
- **WHEN** any available v1 local-map node is serialized, including an instance/interior or ordinary node; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it carries `gateway`, which is null except for registered gateway nodes; a non-null value contains exactly `leads_to`, a non-empty string bounded by the existing 256-code-point node-string limit; schema_version remains 1 and no legacy omission or alias is accepted.

#### Scenario: Registered gate metadata names its far side
- **WHEN** a grid room hosting a registered gateway or a wilderness payload adjacent grid gateway is emitted; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the grid room carries the far-side wilderness region name and the wilderness-adjacent grid gateway carries the settlement name; existing coordinates, node identity, actions, visibility and registry-based gateway resolution remain unchanged.

#### Scenario: Both validators reject malformed gateway values
- **WHEN** a node omits gateway, uses a scalar/array, has missing or extra gateway fields, or has empty, whitespace-only, non-string or over-bound leads_to; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** both validators reject the available panel under their exact-field checks; null and a bounded non-empty leads_to object pass, and the normalized browser model preserves gateway unchanged.


### Requirement: Visibility states are current, visible_unvisited, visible_visited, and remembered
Each local-map node SHALL have current, visible_unvisited, visible_visited or remembered visibility; wilderness visible nodes SHALL be revealed legal neighbours, with actual visitation distinguishing visited from unvisited, while other-layer field-of-view rules remain unchanged.

#### Scenario: Remembered is layer-scoped
- **WHEN** a payload is built on any layer; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** on the coordinate-free layers (`instance`, `interior`) `remembered` SHALL mark a previously entered node outside the current field of view; on the coordinate-bearing layers (`grid`, `wilderness`) it SHALL mark **a map boundary the player has stood on** — a node outside the current field of view whose traversal takes the player onto a different map — and nothing else: a visited node that is not such a boundary SHALL NOT be emitted on those layers, so walking a region can never accumulate one indistinguishable entry per visited cell

#### Scenario: Boundaries resolve against the authored registry
- **WHEN** the presenter decides whether a visited node outside the field of view is a boundary; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL resolve against the authored wilderness entry registry (`world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY`) — the same registry the traversal code and the in-view gateway nodes read — and never against a flag in the stored knowledge record, which carries canonical identity, ticks and wilderness sight: on the `wilderness` layer a visited `wild:` node SHALL be a boundary when its coordinates equal `entry.approach_cell(gate)` for some registered entry and gate; on the `grid` layer a visited `grid:` node SHALL be a boundary when its coordinates and map key equal some registered gate's `grid_xy` and `z_map_key`
- **AND** being an `AnchorRoom`, a landmark, or a node of any other in-map significance SHALL NOT by itself make a node a boundary; a place inside the same map is not a way out of it

#### Scenario: A boundary is remembered only under its drawn-layer identity
- **WHEN** a boundary is considered for `remembered`; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL be `remembered` only when the player's stored knowledge record contains **the exact canonical node ID the drawn layer carries it as** — the approach cell's `wild:` ID on the `wilderness` layer, the gate room's `grid:` ID on the `grid` layer — and a boundary the player has never entered on the side being drawn SHALL be absent from the payload

#### Scenario: Remembered boundary labels and flags
- **WHEN** a remembered boundary is emitted; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL be labelled with the authored name of the place its traversal reaches, never with the terrain or region the boundary itself stands on: on the `wilderness` layer the entry's anchor display name from the anchor registry, and on the `grid` layer the display name of the wilderness region the gate's approach cell lies in
- **AND** remembered boundary labels within one payload SHALL be distinct; where two boundaries would carry the same far-side name, each SHALL be qualified with the canonical name of the boundary node it carries
- **AND** it SHALL carry `landmark: true`, `anchor: false`, and `action: null`

#### Scenario: Visibility keys on canonical identity
- **WHEN** visibility is resolved for any node, including a gateway node rendered on a layer other than its home layer; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL be keyed on the node's canonical identity — the same ID the resolver and the knowledge record use — so a gate the player has walked through reads `visible_visited` wherever it is drawn

#### Scenario: Unknown nodes are omitted, never hidden
- **WHEN** a node is unknown to the player's knowledge and outside the field of view; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL be omitted entirely — never sent as a hidden record

#### Scenario: The payload stays inside the envelope with in-view nodes first
- **WHEN** a payload is assembled with remembered nodes; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL remain within the OOB envelope limits, with remembered nodes bounded by most-recent `last_seen` and current/visible nodes always included first

#### Scenario: Remembered nodes are capped and ordered deterministically
- **WHEN** remembered nodes are collected; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** they SHALL be bounded by a declared presenter ceiling of at most 16 remembered nodes, and SHALL be ordered by descending most-recent `last_seen` tick then ascending canonical node ID, so the same knowledge record and world state always produce the same nodes in the same order

#### Scenario: Visited interior nodes retain their visited visibility
- **WHEN** a node inside an interior/instance local graph has been entered before; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it is `visible_visited` (or `remembered` when no longer adjacent) and carries its canonical
  room name as label

#### Scenario: A walked-through gate is visited on the far side too
- **WHEN** the player entered the wilderness through a gate and the opposite layer now draws that; any asserted wilderness destination facts are revealed and location-identity permitted
  gate's node
- **THEN** the gate node is `visible_visited` because the knowledge record contains its canonical ID

#### Scenario: Unknown nodes are absent from the payload
- **WHEN** a map adapter computes the current view for a room; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** coordinates or rooms the player has never seen and that are outside the current field of
  view are absent from `nodes` and `edges`

#### Scenario: Walked wilderness ground is not remembered
- **WHEN** the player has walked many cells of one wilderness region — enough that the old rule would; any asserted wilderness destination facts are revealed and location-identity permitted
  emit seven or more remembered cells — and none of those cells is a registered gate approach cell
- **THEN** the payload contains no `remembered` node for any of them, and in particular contains no two
  `remembered` nodes carrying the same region display name as their label

#### Scenario: A stood-on gateway is remembered from the wilderness
- **WHEN** the player has entered a registered gate's approach cell, has since moved several cells away; any asserted wilderness destination facts are revealed and location-identity permitted
  so that the cell is outside adjacency, and the wilderness payload is built
- **THEN** the payload carries exactly one `remembered` node whose ID is that approach cell's `wild:`
  ID, whose `x`/`y` are that cell's wilderness coordinates, whose label is the entry's anchor display
  name, with `landmark: true`, `anchor: false`, and `action: null`

#### Scenario: A point-shape cave entry is remembered by its own name
- **WHEN** the registry holds a one-`#` point-shape entry (cave semantics) whose anchor cell the player; any asserted wilderness destination facts are revealed and location-identity permitted
  has entered, and the player is elsewhere in the wilderness
- **THEN** the payload carries a `remembered` node at that anchor cell's coordinates labelled with the
  cave's anchor display name, resolved by exactly the same predicate as a city gate

#### Scenario: A gateway the player has never reached is absent
- **WHEN** a registered gateway exists in the registry and the player's knowledge record does not; any asserted wilderness destination facts are revealed and location-identity permitted
  contain the canonical node ID the drawn layer would carry it as
- **THEN** no node for that gateway appears in the payload in any visibility state, whatever the player
  has visited elsewhere in the same region or on the far side of that gateway

#### Scenario: A remembered gateway is named for where it leads, not what it stands on
- **WHEN** a remembered gateway is emitted on either coordinate-bearing layer; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its label is the authored name of the place on the far side of its traversal, and it is not
  the display name of the wilderness region the approach cell sits in (on the `wilderness` layer) nor
  any name derived from the node's own terrain

#### Scenario: Two gateways onto one far side stay distinguishable
- **WHEN** the payload remembers two registered gateways whose far sides carry the same authored name —; any asserted wilderness destination facts are revealed and location-identity permitted
  on the `grid` layer, the two city gates that both open onto one wilderness region; on the
  `wilderness` layer, the two gates of one anchor that share one anchor display name, since a single
  registered entry MAY carry more than one gate
- **THEN** the two nodes carry distinct labels, each qualified with the canonical name of its own
  boundary node, and no two `remembered` nodes in the payload share a label

#### Scenario: An in-map landmark is not a way out of the map
- **WHEN** the player has entered an `AnchorRoom` that is not a registered gate room, then moved beyond; any asserted wilderness destination facts are revealed and location-identity permitted
  visual range of it on the same grid map
- **THEN** that room is absent from the payload rather than emitted as a `remembered` node, and its
  `landmark` significance is unchanged wherever it is genuinely in view

#### Scenario: Coordinate-free layers keep the previously-entered meaning
- **WHEN** an instance or interior payload is built for a player who has entered other rooms of the; any asserted wilderness destination facts are revealed and location-identity permitted
  same building
- **THEN** those rooms are still emitted as `remembered` nodes with their canonical room names, exactly
  as before, because those layers assert no bearing and carry no map boundary registry

#### Scenario: Remembered nodes are bounded and deterministic
- **WHEN** the remembered set exceeds the configured cap; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the payload keeps the most-recent `last_seen` entries in deterministic order — descending
  last-seen tick then ascending node ID — never exceeds the declared remembered ceiling of 16, never
  exceeds the shared node bound, and never displaces a current or in-view node


### Requirement: The map surfaces state a place name only where it adds information
Wilderness place/region labels SHALL be emitted only for revealed cells and permitted location identities; an unrevealed or visit-gated destination SHALL disclose no place name through a map node or gateway label.

#### Scenario: The gate approach cell keeps every other field
- **WHEN** a gate approach cell is relabelled with its entry's anchor display name; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its node ID, `action`, edges, visibility, and every other field SHALL be unchanged, so the payload states a better name for the same position and never invents an identity for it

#### Scenario: Every other cell keeps its region name and labels stay non-empty
- **WHEN** an in-view cell is not a registered gate's approach cell; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL keep the region display name it carries today, and every emitted node label SHALL remain a non-empty string

#### Scenario: Duplicate region labels draw no visible text
- **WHEN** the island draws repeated wilderness region names; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: Suppression is scoped to shared region names
- **WHEN** the island draws repeated wilderness region names; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: Suppression touches no payload field
- **WHEN** label suppression is in effect; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it is a drawing rule about the set on the canvas, not a payload rule: no payload field changes, and both validators keep their existing bounds and their non-empty label rules unchanged

#### Scenario: The wilderness neighbourhood stops repeating one region name
- **WHEN** the island draws repeated wilderness region names; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** every exit label follows eight-candidate placement with truncated leader-line fallback; context labels may be omitted when no position fits. Full accessible names and marker/action identity remain unchanged.

#### Scenario: An in-view gate approach cell names the place behind it
- **WHEN** the player stands one cell from a registered gate's approach cell, so the approach cell is; any asserted wilderness destination facts are revealed and location-identity permitted
  an in-view neighbour
- **THEN** that neighbour's label is the entry's anchor display name rather than the region display
  name, its node ID is still the approach cell's `wild:` ID with its unchanged action and edge, and
  because the label differs from the current node's label the renderer draws it as visible text

#### Scenario: A cell in a different region still says so
- **WHEN** an in-view neighbour lies in a different wilderness region than the current cell; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its region display name differs from the current node's label, so the renderer draws it as
  visible text and the region change stays visible

#### Scenario: Suppressed labels never weaken the state ladder or activation
- **WHEN** a node's visible label is suppressed as a duplicate of the current node's label; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** its marker shape, landmark treatment, `data-node` identity, move action, and accessible name
  are all unchanged, and the four visibility states remain distinguishable without colour


### Requirement: Wilderness minimap nodes are actionable
Every disclosed traversable adjacent wilderness node SHALL carry its canonical explore.move descriptor; unknown or visit-gated nodes SHALL be absent while separate opaque directional controls remain usable.

#### Scenario: Adjacent wilderness node can be moved to
- **WHEN** the player opens the local map while in wilderness terrain; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** each traversable adjacent node has a move action whose destination is the canonical node, and activating it moves the player there

#### Scenario: The gate approach cell shows the gate, not terrain
- **WHEN** the player stands at a registered gate approach cell and opens the local map; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the gateway direction's node is the gate room's `grid:` node labelled with the room's name, and activating it arrives in that room

#### Scenario: Non-traversable or unreachable nodes stay inert
- **WHEN** a wilderness node is outside the traversable set (e.g. out of bounds or an anchor footprint cell); any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the node carries no move action


### Requirement: The minimap gate nodes match traversal in both directions
Permitted disclosed gateways SHALL retain their matched canonical traversal identity and action on both sides; wilderness unknown or visit-gated gateway facts SHALL be withheld before node or exit-stub serialization.

#### Scenario: The approach cell renders the gate's grid node
- **WHEN** the puppet stands at the gate's approach cell; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the gateway direction (`return_direction`) SHALL emit the gate's grid node — canonical `grid:` id, gate room label, resolver-derived visibility, and a move descriptor with that id as destination

#### Scenario: The gate room renders the approach cell's wild node
- **WHEN** the puppet stands at the gate room; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the grid layer SHALL emit that gate's approach cell's `wild:` node — canonical `wild:` id for the approach cell, the region's display name, knowledge-derived visibility, and a move descriptor whose `exit_ref` is that gate's exit and whose destination is that `wild:` id

#### Scenario: A pinning test walks every gateway both ways
- **WHEN** the pinning test runs; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL move a character through each real gateway exit in both directions and compare the committed node against the actual arrival

#### Scenario: One resolver source, never a duplicated table
- **WHEN** node identity and direction deltas are computed for these nodes; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** they SHALL come from that same single resolver source, never from a duplicated table

#### Scenario: Gate capacity is reserved before ordinary nodes
- **WHEN** registered gates compete with ordinary visible nodes; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the gate node SHALL NEVER be silently omitted: registered-gate capacity SHALL be reserved before ordinary visible nodes are collected, excess visible nodes trimmed farthest-first in deterministic order

#### Scenario: An occupied preferred slot takes the nearest free one
- **WHEN** the gate's preferred renderer-local slot is occupied; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the gate node SHALL take the nearest free slot in deterministic probe order instead of being dropped

#### Scenario: Grid-layer gate identity derives from the provisioned exit
- **WHEN** the grid layer builds a gate candidate; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the candidate's `wild:` identity and label SHALL derive from the provisioned exit's `db.gate_direction` resolved through the registry to that gate's `approach_cell`, and the candidate's slot direction SHALL be the direction of the exit connecting the gate room

#### Scenario: Identity never parses keys, aliases, or anchor cells
- **WHEN** a grid-layer gate candidate's identity is resolved; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL never come from parsing the gate exit's key or aliases (all wilderness-side gate exits share the key `荒野`, and key aliases are display affordances, not identity), and never from the entry's anchor cell as a stand-in for a per-gate approach cell

#### Scenario: The capacity trim order is part of the contract
- **WHEN** the capacity trim drops visible nodes; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL drop them in descending Chebyshev distance from the current node, then descending Y, then descending X (the current node never dropped)

#### Scenario: The slot probe order is part of the contract
- **WHEN** the slot probe searches for a free slot; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** it SHALL scan the preferred slot first when it is free and inside the payload coordinate bounds, then rings of ascending Manhattan distance from it in ascending Y-offset then ascending X-offset order, taking the first slot that is inside the coordinate bounds and free

#### Scenario: Wilderness side shows the gate room
- **WHEN** the puppet stands at a registered gate's derived approach cell and the `local_map` panel; any asserted wilderness destination facts are revealed and location-identity permitted
  is built
- **THEN** the gateway direction carries the gate room's `grid:` node with the room's name as label,
  an action whose destination equals the node id, and the geometric wild cell for that direction is
  absent from the payload

#### Scenario: Gate side shows the wilderness approach cell
- **WHEN** the puppet stands at the gate room and the `local_map` panel is built; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** a `wild:` node for that gate's approach cell exists with the region's display name, a
  move action whose `exit_ref` is that gate's exit, and activating it enters the wilderness at that
  cell

#### Scenario: Both gates of one anchor render independently on both sides
- **WHEN** the puppet stands at either approach cell of `capital_altoria`, or inside either city; any asserted wilderness destination facts are revealed and location-identity permitted
  gate room, and the panel is built
- **THEN** only that gate's node appears for that direction — the other gate is not rendered at the
  wrong side or direction — and each gate's pair (approach cell ↔ gate room) round-trips through
  activation

#### Scenario: Gate identity survives identical keys and rewritten aliases
- **WHEN** both provisioned gate exits carry the identical key `荒野` (as `sync_wilderness()`; any asserted wilderness destination facts are revealed and location-identity permitted
  creates them) with arbitrary aliases, and the grid layer is built from each gate room
- **THEN** each gate room's payload shows the `wild:` node for its OWN gate's approach cell at the
  slot of its own exit — neither room renders the other gate's approach cell, and no candidate is
  dropped to key-based deduplication

#### Scenario: Both directions agree with real traversal
- **WHEN** a test walks a character through a gateway exit into the wilderness and back through the; any asserted wilderness destination facts are revealed and location-identity permitted
  return exit, building the panel at each end, for each registered gate
- **THEN** every rendered gateway node's id and action destination equal the actual arrival node the
  traversal produced, in both directions

#### Scenario: An unregistered direction stays ordinary terrain
- **WHEN** a wilderness direction at any coordinate is not a registered gateway step and its; any asserted wilderness destination facts are revealed and location-identity permitted
  neighbor is provider-valid
- **THEN** its node is the ordinary geometric `wild:` cell with its terrain label, exactly as before

#### Scenario: A crowded gate room keeps both the neighbor and the gate
- **WHEN** a gate room has an in-range grid node occupying the gate's preferred renderer-local slot; any asserted wilderness destination facts are revealed and location-identity permitted
- **THEN** the payload contains the in-range grid node AND the gate's `wild:` node at a free probed
  slot, both with their actions, and the payload passes the exact validator

#### Scenario: Gate capacity never breaks the node bound
- **WHEN** the visible set would fill the full node cap at a room that also holds a registered gate; any asserted wilderness destination facts are revealed and location-identity permitted
  exit
- **THEN** the payload contains at most the capped number of nodes, the gate node is present, and the
  trim removes only farthest visible nodes in deterministic order



#### Scenario: Undisclosed directional target
- **WHEN** a synthetic unvisited wilderness neighbour remains outside reveal
- **THEN** it has no local-map node or identifying exit metadata, while its enabled opaque direction can still submit exit_ref/current_node without a fabricated minimap highlight
