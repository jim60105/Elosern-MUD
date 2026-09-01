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
