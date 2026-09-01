# Fix Wilderness Map Adjacency Truth

## Why

Standing in the wilderness entry cell (60,100) north of the capital's North
Gate, the minimap's southern node is a lie. `resolve_wilderness_destination`
correctly resolves the gateway `south` step to `grid:capital_altoria:2:4` and
the node's move action carries that destination — but the node's **identity,
label, and coordinates are fabricated from raw geometry** (`encode_wild` of the
adjacent cell + that cell's terrain name). So the map says "south is wilderness
plains" while clicking that node actually walks into the North Gate room, and
the visited North Gate `grid:` node — present in the player's own knowledge
record — never appears on the wilderness map at all. The same class of bug
exists mirrored on the grid side: standing at the North Gate, the
`WildernessGateExit` (a self-loop exit whose `destination` is the gate room
itself) is invisible to the grid minimap because `_grid_exit_action` matches
exits by `exit_obj.destination`, so the wilderness entrance is never listed
even though CLI/exploration show it.

Root cause is one architectural shortcut: the presenter derives node identity
from coordinate arithmetic, but the traversal truth lives in
`WildernessReturnExit.at_traverse` / `WildernessGateExit.at_traverse`, and the
contrib's self-loop exits make `exit_obj.destination` structurally unable to
name the real arrival node. The fix is that the presenter must derive **node
identity, label, and visibility from the same resolver traversal uses** —
identity follows resolution, geometry stays renderer-local.

## What Changes

- The wilderness layer builds each adjacent node from
  `resolve_wilderness_destination(location, direction)`: when the destination
  is a `grid:` node (a registered gateway), the node's `id`, label (the gate
  room's key from the knowledge record / room lookup), `anchor`/`landmark`
  flags, and visibility (`visible_visited` — the gateway grid node is in the
  player's visited knowledge by definition if they just came through it) come
  from the grid node, not from the wild cell's terrain. Its `x`/`y` stay the
  adjacent-cell position so the lattice keeps its clean 3×3 neighbourhood
  (the payload already declares node `x`/`y` as renderer-local presentation
  geometry; the delta makes the gateway case explicit).
- The grid layer gains gateway awareness: for each `WildernessGateExit` at the
  current room whose anchor resolves to a registered entry, the presenter adds
  a node for the resolved entry `wild:` cell — id `wild:elosern:<x>:<y>`,
  label = that region's display name, action = the gate exit's `move`
  descriptor with the `wild:` destination — positioned at the direction the
  gate exit's key/aliases name (North Gate's exit is keyed 荒野/`north`/`n`, so
  it draws to the north). The gate node is never silently dropped: capacity for
  registered gates is reserved before the ordinary in-range nodes are collected
  (overflow trims the in-range tail in deterministic order), and if the gate's
  preferred direction slot is already occupied by an in-range grid node — id
  disjointness does NOT prevent coordinate-slot collision — the gate node takes
  the nearest free renderer-local slot in deterministic probe order instead.
- Shared direction geometry: `local_map.py`'s private `_wild_neighbor` deltas
  are replaced by the single source in
  `world/maps/wilderness_destination.py` (exported `DIRECTION_DELTAS` + a
  bounds-checked neighbour helper), eliminating the duplicated 8-way delta
  table that can silently drift from traversal.
- Hygiene in the same file (same author, same lines touched): remove the dead
  `known_visited_ids` set and the no-op `anchor_coord` loop in `_grid_layer`
  (replace with the existing `get_node_from_coord` guard it re-derives);
  collapse `_grid_node_label`/`_grid_coord_label` (byte-identical bodies) into
  one helper. `_grid_exit_action`'s own per-node destination lookup is left as
  is (merging it with the label fetch is deferred: signature churn for a few ms
  on a ≤64-node panel).
- No payload schema change: gateway nodes use only the existing exact fields
  (`id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`,
  `action`); mixed-prefix neighbours on one layer are already schema-legal
  (only `current_node` is prefix-checked). No new validators, no JS parity
  changes, no Node-gate changes.

Out of scope: the grid-side locked/hidden gate exits beyond the registered
entry set (same `_grid_exit_action` matching semantics as today for ordinary
exits), the exploration menu (already correct via the resolver), knowledge
recording (already records `grid:` arrivals), and the CLI map.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`:
  - `local_map is a read-only version-1 presentation panel` — the node-`x`/`y`
    clause gains the explicit rule that a node's presentation geometry follows
    its map position (adjacency/range), never its identity's raw world
    coordinates, pinning the gateway-node case; the wilderness scenario gains
    the gateway statement.
  - `Visibility states are current, visible_unvisited, visible_visited, and remembered` —
    visibility is keyed on the node's canonical id (the resolved one), so a
    visited gateway grid node reads `visible_visited` on the wilderness layer.
  - `Only currently traversable Exits receive movement descriptors` — the
    association rule is amended to the resolver: a wilderness direction and a
    registered gate exit are associated with the node the step ACTUALLY
    reaches, not with the exit's (self-loop) destination.
  - `Wilderness minimap nodes are actionable` — "canonical destination" gains
    the gateway scenario (destination and node identity are both the gate's
    grid node).
  - ADDED `The minimap gate nodes match traversal in both directions` — the
    round-trip contract: wilderness→gate and gate→wilderness nodes exist,
    agree with `resolve_wilderness_destination` / the entry registry, and stay
    consistent with knowledge.

### Modified Capabilities (no spec delta)

None beyond the above — `world/maps/` traversal is unchanged; only presentation
catches up to it.

## Impact

- Affected code: `web/webclient/presentation/local_map.py`
  (`_wilderness_layer`, `_grid_layer`, `_grid_exit_action`, label helpers),
  `world/maps/wilderness_destination.py` (export the delta table + neighbour
  helper), plus tests:
  `web/webclient/presentation/tests/test_local_map.py` (gateway cell tests;
  update the tests pinning the current fabricated-identity behavior:
  `wilderness provider labels`, adjacent-node destination tests, grid gate
  tests), `world/maps/tests/` resolver pinning test if the helper moves.
- No new test modules (files unchanged → `.github/evennia-shards.json`
  untouched). No browser-suite change needed: the island DOM contract is
  unaffected (the new node renders through existing node machinery). No
  command surface change.
- Depends on no other active change; the sibling `slim-minimap-island` change
  touches only Vue/JS client files and the browser suite — no file conflicts,
  and both touch `openspec/specs/webclient-local-map/spec.md` on different
  requirements (OpenSpec deltas merge per requirement).
