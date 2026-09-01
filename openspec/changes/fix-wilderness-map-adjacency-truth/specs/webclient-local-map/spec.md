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
position. `edges` SHALL be a bounded list where each edge contains exactly `source`, `destination`,
`label`, `known`, and `traversable`. `legend` SHALL be a bounded list of text label entries. The
presenter SHALL build the payload only from canonical room/map/knowledge data, SHALL emit no live
object or filesystem reference, SHALL NOT mutate knowledge, traits, clock, or location, and SHALL use
the registered common unavailable form when the current room cannot be represented.

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
  coordinates bounded by the provider, and terrain labels, except that a registered gateway direction
  renders the resolved `grid:` gate node instead of the geometric wild cell

#### Scenario: An instance room produces a coordinate-free instance payload
- **WHEN** the active puppet is in an `InstanceRoom`
- **THEN** `local_map` reports `layer == "instance"` with a `room:<dbref>` current node and a small
  graph containing the current node, its origin/return, and known real Exit edges, with no `grid:` or
  `wild:` identity invented for it

#### Scenario: An ordinary interior produces an interior payload
- **WHEN** the active puppet is in a permanent interior `Room` such as the guild hall or general store
- **THEN** `local_map` reports `layer == "interior"` with a coordinate-free graph of real Exits

#### Scenario: A gateway step never renders the wild cell it replaces
- **WHEN** the puppet stands at a registered wilderness entry coordinate and the gateway direction
  resolves to a grid node
- **THEN** no node with the geometric wild cell's `wild:` ID exists in the payload for that direction,
  and the gateway node carries the gate's `grid:` ID positioned at the adjacent cell

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

### Requirement: Wilderness minimap nodes are actionable
Every traversable adjacent wilderness node in the local map SHALL carry an `explore.move` action
descriptor with the canonical destination node, matching the grid/interior layers' behavior. Where a
direction is a registered gateway step, the node it renders IS the resolved `grid:` gate node — its
id, label (the gate room's canonical name), landmark flags, and action destination all identify that
gate node, and no geometric `wild:` cell stands in for it.

#### Scenario: Adjacent wilderness node can be moved to
- **WHEN** the player opens the local map while in wilderness terrain
- **THEN** each traversable adjacent node has a move action whose destination is the canonical node, and activating it moves the player there

#### Scenario: The gateway cell shows the gate, not terrain
- **WHEN** the player stands at a registered entry coordinate and opens the local map
- **THEN** the gateway direction's node is the gate room's `grid:` node labelled with the room's name, and activating it arrives in that room

#### Scenario: Non-traversable or unreachable nodes stay inert
- **WHEN** a wilderness node is outside the traversable set (e.g. out of bounds)
- **THEN** the node carries no move action

## ADDED Requirements

### Requirement: The minimap gate nodes match traversal in both directions
For every entry in the wilderness entry registry, the minimap SHALL present the gateway as a matched
pair of edges on both sides: standing at the entry coordinate, the gateway direction SHALL render the
gate's grid node (canonical `grid:` id, gate room label, resolver-derived visibility, move descriptor
with that id as destination); standing at the gate room, the grid layer SHALL render the entry cell's
`wild:` node (canonical `wild:` id for the registered coordinate, the region's display name,
knowledge-derived visibility, move descriptor whose `exit_ref` is the gate exit and whose destination
is that `wild:` id). The rendered destination SHALL always equal the node carrying it, SHALL always
equal what `resolve_wilderness_destination` derives from the same registration the traversal code
reads, and a pinning test SHALL move a character through the real gateway exit in both directions and
compare the committed node against the actual arrival. Node identity and direction deltas for these
nodes SHALL come from that same single resolver source, never from a duplicated table. The gate node
SHALL NEVER be silently omitted: registered-gate capacity SHALL be reserved before ordinary visible
nodes are collected (excess visible nodes trimmed farthest-first in deterministic order), and when
the gate's preferred renderer-local slot is occupied the gate node SHALL take the nearest free slot in
deterministic probe order instead of being dropped.

#### Scenario: Wilderness side shows the gate room
- **WHEN** the puppet stands at a registered entry coordinate and the `local_map` panel is built
- **THEN** the gateway direction carries the gate room's `grid:` node with the room's name as label,
  an action whose destination equals the node id, and the geometric wild cell for that direction is
  absent from the payload

#### Scenario: Gate side shows the wilderness entry
- **WHEN** the puppet stands at the gate room and the `local_map` panel is built
- **THEN** a `wild:` node for the registered entry coordinate exists with the region's display name,
  a move action whose `exit_ref` is the gate exit, and activating it enters the wilderness at that cell

#### Scenario: Both directions agree with real traversal
- **WHEN** a test walks a character through the gateway exit into the wilderness and back through the
  return exit, building the panel at each end
- **THEN** every rendered gateway node's id and action destination equal the actual arrival node the
  traversal produced, in both directions

#### Scenario: An unregistered direction stays ordinary terrain
- **WHEN** a wilderness direction at any coordinate is not a registered gateway step
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
