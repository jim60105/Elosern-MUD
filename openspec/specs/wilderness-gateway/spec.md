## Purpose

The concrete, bidirectional connection between the grid layer and the wilderness/Virtual layer: the
`WILDERNESS_ENTRY_REGISTRY` linking a grid-placed anchor to an authored wilderness footprint with
per-face gates, the two exit typeclasses (`WildernessGateExit` for grid→wilderness,
`WildernessReturnExit` for wilderness→grid and ordinary wilderness steps), the `wilderness_move`
clock cost that every successful wilderness step charges, and the idempotent `sync_wilderness()`
provisioning wired into server startup.

## Requirements


### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates
`world/lore/wilderness_entry.py` SHALL define frozen `WildernessGate` (`return_direction: str`,
`grid_xy: tuple[int, int]`, `z_map_key: str`) and `WildernessEntryPoint` (`anchor_key: str`,
`shape: tuple[str, ...]`, `origin_xy: tuple[int, int]`, `gates: tuple[WildernessGate, ...]`)
dataclasses and a module-level `WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint]`.
`shape` is an ASCII mask of `#` (anchor footprint cell) and `.` (outside), placed so that
`shape[0][0]` corresponds to wilderness cell `origin_xy`. An entry with exactly one `#` cell is a
point-shape anchor: it owns no footprint cells and every direction at its anchor cell is a
gateway to its single registered gate. An entry with more than one `#` cell owns every mask cell
as a footprint cell, and each of its gates is reachable only at that gate's exterior approach
cell, where `return_direction` names the direction a wilderness-side traveler takes to enter the
anchor. The registry SHALL expose derived pure helpers — `footprint_cells` (origin + mask
offsets, empty for point-shape), `anchor_cell` (integer-rounded centroid of the `#` cells), and
`approach_cell(gate)` (the anchor cell for point-shape entries; otherwise the first cell walking
from `anchor_cell` along the face opposite `return_direction` that lies outside the footprint) —
as the single geometry source for all consumers. Every entry's `anchor_key` SHALL exist as a key
in change 12's `ANCHOR_PLACEMENT_REGISTRY`. The registry SHALL NOT be required to contain an
entry for every `ANCHOR_PLACEMENT_REGISTRY` key. This change SHALL populate exactly one entry,
keyed `"capital_altoria"`: a 5×5 all-`#` mask at origin `(58, 98)` (anchor cell `(60, 100)`) with
gates `return_direction="n"` → `(2, 0, "capital_altoria")` (approach cell `(60, 97)`) and
`return_direction="s"` → `(2, 4, "capital_altoria")` (approach cell `(60, 103)`).
`anchor_cell` SHALL be the bounding-box midpoint `((min_x + max_x) // 2, (min_y + max_y) // 2)`
of the `#` cells under Python floor division, and no two gates in the whole registry SHALL share
the same `(approach_cell, return_direction)` pair.

#### Scenario: The registry has exactly one v2 entry after this change
- **WHEN** `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** it contains exactly one entry, keyed `"capital_altoria"`, whose `shape` is a 5×5 mask
  of `#`, whose `origin_xy` is `(58, 98)`, and whose gates are exactly `("n" → (2,0)),
  ("s" → (2,4))` on map `capital_altoria`, and no test in this change's own suite asserts that
  any other `ANCHOR_PLACEMENT_REGISTRY` key must also appear

#### Scenario: Derived geometry matches the authored mask
- **WHEN** `footprint_cells`, `anchor_cell`, and `approach_cell` are read for the
  `"capital_altoria"` entry
- **THEN** `footprint_cells` is the 25-cell set `58 <= x <= 62 and 98 <= y <= 102`, `anchor_cell`
  is `(60, 100)`, the `"n"` gate's approach cell is `(60, 97)`, and the `"s"` gate's approach
  cell is `(60, 103)`

#### Scenario: Gate identity is globally unique

- **WHEN** the derived `(approach_cell, return_direction)` pairs of all gates in the registry
  are collected
- **THEN** no pair occurs twice, and no footprint cell of any entry equals another entry's gate
  approach cell or point-shape anchor cell

#### Scenario: A point-shape entry expresses cave semantics with no footprint
- **WHEN** an entry is constructed with a single-`#` mask, one gate, and any origin
- **THEN** its `footprint_cells` is empty, its `anchor_cell` is the origin, and its
  `approach_cell(gate)` equals its `anchor_cell`

#### Scenario: Every entry's anchor_key resolves against ANCHOR_PLACEMENT_REGISTRY
- **WHEN** every entry in `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** each entry's `anchor_key` exists as a key in `world.lore.anchor_placement.
  ANCHOR_PLACEMENT_REGISTRY`

#### Scenario: WILDERNESS_ENTRY_REGISTRY is mirrored into LoreRecord Scripts idempotently
- **WHEN** `sync_all()` runs, and then runs a second time
- **THEN** a `LoreRecord` Script keyed `"lore:wilderness_entries:capital_altoria"` exists after
  both calls, and no duplicate exists after the second

### Requirement: WildernessGateExit moves a traversing object from a grid room into the wilderness
`typeclasses.exits.py::WildernessGateExit`, an ordinary `Exit`, SHALL fully override `at_traverse`
to call `evennia.contrib.grid.wilderness.wilderness.enter_wilderness(traversing_object,
coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
name=WILDERNESS_NAME)` instead of moving to a fixed `destination`, where `<its anchor_key>` is
read from `self.db.anchor_key` and `<its gate>` is the registered gate whose `return_direction`
equals `self.db.gate_direction` — both attributes this change's `sync_wilderness()` (the
`wilderness-gateway` capability's own provisioning requirement below) SHALL set at creation time.
For a footprint anchor the arrival cell is the exterior approach cell (never a footprint cell);
for a point-shape anchor `approach_cell` is the anchor cell itself, so the same formula lands
the traveler on the entry cell. Before attempting to move, it SHALL call the traversing object's
`at_pre_move(None)` hook and abort with no state change if it returns falsy, matching the veto
convention every other exit in the game (including the stock `WildernessExit`) honors. On a
successful traversal, it SHALL send departure/arrival room announcements, call
`at_post_move(None)` on the traversing object, and complete through the shared
movement-completion helper `typeclasses.exits.after_successful_movement(traversing_object,
source_location, cost_key="wilderness_move",
wilderness_coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
wilderness_name=WILDERNESS_NAME)` — the `onboarding-skip-coverage` change's shared boundary —
which SHALL call `world.rules.movement.charge_movement(traversing_object, cost_key)` (the
`movement-cost-charging` capability), `world.rules.map_knowledge.record_arrival(traversing_object)`
(the `map-knowledge` capability), and the onboarding room-entry observer, rather than calling
`world.rules.clock.get_world_clock().advance()` directly. The observable cost, success-only
condition, and `AdvanceSource.COMMAND` source are unchanged; only the call sites are now the
shared functions every movement lineage uses. The arrival recording SHALL NOT alter the charge.

#### Scenario: Traversing a gate exit places the object at that gate's approach cell
- **WHEN** a character traverses a `WildernessGateExit` configured for
  `("capital_altoria", gate facing 南門)`
- **THEN** the character's new location is a `TerrainRoom` whose `.coordinates` equals the `"n"`
  gate's `approach_cell` `(60, 97)` (the cell outside the footprint, never a footprint cell), and
  its map-knowledge record contains the corresponding `wild:elosern:<x>:<y>` node

#### Scenario: Traversing the other gate lands at the other gate's approach cell
- **WHEN** a character traverses the `WildernessGateExit` provisioned on the North Gate room
- **THEN** the arrival coordinates equal the `"s"` gate's `approach_cell` `(60, 103)`,
  independent of which gate was used before

#### Scenario: A successful traversal advances the world clock by the wilderness_move cost
- **WHEN** a character successfully traverses a `WildernessGateExit`
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal
  plus `CLOCK_YAML["command_defaults"]["wilderness_move"]`

#### Scenario: An unsuccessful traversal does not advance the clock and records nothing
- **WHEN** `enter_wilderness()` returns `False` (for example, the gate's landing cell is somehow
  invalid)
- **THEN** `get_world_clock().tick` is unchanged by the attempted traversal and no map-knowledge
  observation is recorded

#### Scenario: A vetoed at_pre_move blocks the traversal entirely
- **WHEN** the traversing object's `at_pre_move(None)` returns a falsy value
- **THEN** `WildernessGateExit.at_traverse` returns `False`, `enter_wilderness()` is never
  called, the traversing object's location is unchanged, `get_world_clock().tick` is unchanged,
  and no map-knowledge observation is recorded

#### Scenario: The clock charge and arrival recording go through the shared completion helper
- **WHEN** `typeclasses.exits.py::WildernessGateExit.at_traverse` is inspected
- **THEN** its successful branch calls `after_successful_movement(...)` with
  `cost_key="wilderness_move"`, the shared helper (not the exit) calls
  `world.rules.movement.charge_movement(traversing_object, cost_key)` and
  `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the exit nor the
  helper calls `world.rules.clock.get_world_clock().advance()` directly

### Requirement: WildernessReturnExit routes every registered approach-cell-and-direction pair back to the grid
`typeclasses.exits.py::WildernessReturnExit`, subclassing
`evennia.contrib.grid.wilderness.wilderness.WildernessExit`, SHALL be
`ElosernWildernessMapProvider.exit_typeclass`. It SHALL recognize a gateway step through one
shared registry helper — the same helper the canonical resolver uses — that returns the owning
entry and gate if and only if the traverser's current coordinates equal some entry's
`approach_cell(gate)` and the exit's direction equals that gate's `return_direction`. For a
recognized gateway step it SHALL move the traversing object to the `GridRoom` at the gate's
`grid_xy`/`z_map_key` (resolved via the grid model, not via a hardcoded coordinate or via the
exit object's stored anchor). For every other coordinate or direction, its **routing**
(destination room, coordinate movement) SHALL behave identically to the stock
`WildernessExit`. The hardcoded legacy rule (current coordinates equal to an entry's single
`wilderness_xy` and exit key `"south"`) SHALL NOT exist in any form. This requirement governs
routing only — every successful traversal's **clock cost** is governed by the separate "Every
successful WildernessReturnExit traversal advances the clock, not only the registered return
branch" requirement below, which applies uniformly regardless of which routing branch was taken.

#### Scenario: Traversing north from the south approach cell returns through the south gate
- **WHEN** a character at `(60, 97)` traverses the `"north"` exit
- **THEN** the character's new location is the `capital_altoria` 南門 `GridRoom` object at grid
  `(2, 0, "capital_altoria")`

#### Scenario: Traversing south from the north approach cell returns through the north gate
- **WHEN** a character at `(60, 103)` traverses the `"south"` exit
- **THEN** the character's new location is the `capital_altoria` North Gate `GridRoom` object at
  grid `(2, 4, "capital_altoria")` (the same object instance that existed before the character
  first entered the wilderness through it)

#### Scenario: The return direction at the wrong approach cell is not a gateway
- **WHEN** a character at `(60, 97)` traverses `"south"`, or a character at `(60, 103)` traverses
  `"north"`
- **THEN** the traversal routes like the stock `WildernessExit` (ordinary coordinate movement to
  the provider-valid neighbor), reaching no grid room

#### Scenario: A step toward the footprint is refused
- **WHEN** a character at any cell adjacent to the `capital_altoria` footprint on a non-gate face
  traverses the exit pointing into the footprint
- **THEN** the traversal fails like any step toward an invalid coordinate (the exit is hidden and
  blocked by the provider-invalid lock state and `at_traverse_coordinates` refuses it), the
  character's location is unchanged, `get_world_clock().tick` is unchanged, and no
  map-knowledge observation is recorded

#### Scenario: Every other coordinate and direction routes like a stock WildernessExit
- **WHEN** a character traverses any directional exit at a coordinate that is not any
  entry's `approach_cell`, or traverses a direction other than the matching gate's
  `return_direction` at an approach cell that is not covered by the previous scenario
- **THEN** the traversal's destination behaves identically to
  `evennia.contrib.grid.wilderness.wilderness.WildernessExit.at_traverse` (ordinary coordinate
  movement within the wilderness)

### Requirement: Every successful WildernessReturnExit traversal advances the clock, not only the registered return branch
Every successful traversal through `WildernessReturnExit` — both the special-cased branch that routes
back to a grid room, and the ordinary `super().at_traverse()` fallback that governs every other
coordinate and direction — SHALL complete through the shared movement-completion helper
`typeclasses.exits.after_successful_movement(...)` with `cost_key="wilderness_move"`, which SHALL call
`world.rules.movement.charge_movement(traversing_object, cost_key)` (the `movement-cost-charging`
capability) and `world.rules.map_knowledge.record_arrival(traversing_object)` (the `map-knowledge`
capability) on both branches, plus the onboarding room-entry observer — rather than calling
`world.rules.clock.get_world_clock().advance()` directly. No successful step through this exit SHALL
be free, and every successful step SHALL record its destination node. An unsuccessful traversal (the
underlying `at_traverse_coordinates`/`at_pre_move` check fails, per the stock `WildernessExit`'s own
logic) SHALL NOT advance the clock and SHALL NOT record an observation.

This is the concrete fix for a defect a rubber-duck review found in an earlier draft of this
capability: `ElosernWildernessMapProvider.exit_typeclass = WildernessReturnExit` installs this class on
all eight directional exits at every wilderness coordinate (the `wilderness-map-provider` capability),
so if only the registered return branch advanced the clock, every intermediate step of a continent
crossing would cost nothing — contradicting the whole point of wiring wilderness movement to
`WorldClock` at all. Folding both call sites onto the one shared completion helper (rather than each
duplicating `get_world_clock().advance()` independently) is this change's own contribution: the same
fix, now expressed once instead of twice, and consistent with how every other movement lineage in the
project charges (`movement-cost-charging` capability).

#### Scenario: Traversing south from the registered entry coordinate advances the clock and records the grid node
- **WHEN** a character successfully traverses the `"south"` exit at a registered entry coordinate
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`, and the character's map-knowledge record
  contains the returned grid room's `grid:` node

#### Scenario: An ordinary intermediate step advances the clock and records the wilderness node
- **WHEN** a character at a coordinate that is not any `WILDERNESS_ENTRY_REGISTRY` entry's
  `wilderness_xy` successfully traverses any directional exit (an ordinary wilderness step, taking
  neither special-cased branch)
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`, and the character's map-knowledge record
  contains the destination's `wild:` node

#### Scenario: An N-step round trip advances the clock by exactly N times wilderness_move
- **WHEN** a character enters the wilderness through `WildernessGateExit`, takes three consecutive
  intermediate steps in one direction, three consecutive steps back in the opposite direction, and
  finally traverses `"south"` from the registered entry coordinate back to the grid — eight successful
  traversals in total, only two of which (the entry and the final return) take a special-cased
  routing branch
- **THEN** `get_world_clock().tick` after the whole round trip equals its value before the trip plus
  exactly `8 * CLOCK_YAML["command_defaults"]["wilderness_move"]` — proving no step, including the six
  ordinary intermediate ones, is free

#### Scenario: A failed traversal does not advance the clock and records nothing
- **WHEN** a traversal through `WildernessReturnExit` fails its underlying validity/veto check (for
  example, the target coordinate is invalid, or the traverser's `at_pre_move` vetoes)
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded

#### Scenario: A return to a missing grid room does not advance the clock and records nothing
- **WHEN** the special-cased return branch resolves no grid room for the entry's anchor (e.g. the gate
  exit `sync_wilderness()` provisioned has been deleted, so `_grid_room_for_anchor` returns `None`) or
  the resulting `move_to()` fails its pre-move veto
- **THEN** `WildernessReturnExit.at_traverse` returns `False`, the traverser's location is unchanged,
  `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded — a failed
  return is never reported as a successful, clock-charged step

#### Scenario: Both branches complete through the shared completion helper
- **WHEN** `typeclasses/exits.py::WildernessReturnExit.at_traverse` is inspected
- **THEN** both its special-cased return branch and its `super().at_traverse()` fallback branch call
  `after_successful_movement(...)` with `cost_key="wilderness_move"`, the shared helper (not the
  exit) calls `world.rules.movement.charge_movement(traversing_object, cost_key)` and
  `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the exit nor the helper
  calls `world.rules.clock.get_world_clock().advance()` directly

### Requirement: Leaving the wilderness through WildernessReturnExit triggers ordinary cleanup
When a traversing object leaves a `TerrainRoom` through `WildernessReturnExit`'s grid-routing branch,
the wilderness's own per-object bookkeeping (`itemcoordinates` entry removal, room recycling into
`unused_rooms` when no one remains) SHALL fire exactly as it does for an ordinary
`move_to()`-driven departure, with no additional cleanup code in this change.

#### Scenario: The departing object is no longer tracked by the wilderness after returning
- **WHEN** a character returns to the grid via `WildernessReturnExit`
- **THEN** the character no longer appears as a key in the `WildernessScript`'s
  `itemcoordinates` mapping

#### Scenario: A vacated wilderness room is not leaked, and is reused on a later return
- **WHEN** a character who was alone in a `TerrainRoom` returns to the grid via `WildernessReturnExit`
- **THEN** the vacated room is not orphaned: it remains owned by the `WildernessScript` (either
  recycled into `unused_rooms` when the contrib's recycling condition is met, or retained in
  `db.rooms` keyed by its coordinates for an account-character `move_to()`-driven departure, which
  the contrib does not recycle because the departing account is still in the room's contents when
  `_destroy_room` runs), and re-entering the same coordinates later reuses that same room object
  rather than spawning a new one

### Requirement: sync_wilderness() idempotently provisions the wilderness map and one grid-side gate per registered gate
`world/maps/bootstrap.py::sync_wilderness()` SHALL call `create_wilderness(name=WILDERNESS_NAME,
mapprovider=ElosernWildernessMapProvider())` and, for every gate of every
`WILDERNESS_ENTRY_REGISTRY` entry whose destination `GridRoom` (at the gate's
`grid_xy`/`z_map_key`) exists, SHALL idempotently ensure exactly one `WildernessGateExit` exists
on that room **with `db.anchor_key` set to the entry's `anchor_key` and `db.gate_direction` set
to that gate's `return_direction`** — the gate exit is not usable without these attributes
(`WildernessGateExit.at_traverse` reads both and fails closed on lookup if either is unset), so a
`sync_wilderness()` that creates the exit without setting them is not a conforming implementation
of this requirement even though the exit object itself exists. When a gate's destination room does
not exist, `sync_wilderness()` SHALL log a warning and skip creating that gate's exit, and SHALL
NOT raise; other gates SHALL still be provisioned. `sync_wilderness()` SHALL be distinct in name
and module role from change 12's `sync_grid()`, and SHALL NOT modify `sync_grid()`'s own behavior.
Provisioned wilderness-side gate exits SHALL be keyed `荒野` (aliases `["wilderness",
<direction>, <direction-initial>]`) — the same key on multiple rooms is safe because gateway
resolution matches room and direction, never key aliases — and grid-side gate exits SHALL carry
the wilderness return wording with the entry's `display_name_zh` in aliases.

#### Scenario: sync_wilderness creates the wilderness map and both city gates
- **WHEN** `sync_wilderness()` runs after `sync_grid()` has already created the sample city
- **THEN** a `WildernessScript` keyed `WILDERNESS_NAME` exists; the 南門 `GridRoom` has exactly one
  `WildernessGateExit` with `db.anchor_key == "capital_altoria"` and
  `db.gate_direction == "n"`; and the North Gate `GridRoom` has exactly one `WildernessGateExit`
  with `db.anchor_key == "capital_altoria"` and `db.gate_direction == "s"`

#### Scenario: The created gate exits are immediately usable, not merely present
- **WHEN** a character traverses either `WildernessGateExit` that `sync_wilderness()` created,
  immediately after `sync_wilderness()` returns, with no further setup
- **THEN** the traversal succeeds and does not raise — the concrete regression check for the
  defect this requirement's attribute clause exists to prevent

#### Scenario: Repeated calls create no duplicates
- **WHEN** `sync_wilderness()` is called twice in succession
- **THEN** exactly one `WildernessScript` keyed `WILDERNESS_NAME` exists, and each gate room still
  has exactly one `WildernessGateExit`

#### Scenario: A restarted server restores deterministic room descriptions
- **WHEN** a wilderness room that was retained in `WildernessScript.db.rooms` (e.g. a player's
  current or vacated room) loses its non-persistent `ndb.active_desc`/`scene_archetype` across a
  server restart, and `sync_wilderness()` runs again
- **THEN** each room still registered in the script's `db.rooms` has `ndb.active_desc` and
  `scene_archetype` re-computed from its current coordinates via the provider's
  `at_prepare_room()` — the deterministic terrain description survives a restart

#### Scenario: A mis-provisioned gate is healed, a foreign same-key exit is left alone
- **WHEN** a provisioned `WildernessGateExit` has a wrong `db.anchor_key` or `db.gate_direction`,
  and `sync_wilderness()` runs again
- **THEN** the existing `WildernessGateExit`'s attributes are corrected in place with no new exit
  spawned; and if a non-`WildernessGateExit` with the same key exists on the room, it is left in
  place and no second gate is created atop it

#### Scenario: A missing destination room degrades gracefully per gate
- **WHEN** `sync_wilderness()` runs against a database where the 南門 room does not exist but the
  North Gate room does
- **THEN** the `WildernessScript` is still created, no exception is raised, no gate exit is
  created for the missing room, and the North Gate's gate exit is provisioned normally

#### Scenario: sync_wilderness runs automatically at server start, after sync_grid
- **WHEN** `server/conf/at_server_startstop.py::at_server_start()` is inspected
- **THEN** the call to `sync_wilderness()` appears after the call to `sync_grid()` in source
  order

### Requirement: wilderness_move is a new, distinct clock cost, not a reuse of the grid's move constant
`world/rules/rulebook/clock.yaml::command_defaults` SHALL include a new key, `wilderness_move: 9000`
(seconds), distinct from the existing `move: 30` entry. No code in this change SHALL read `move` for
wilderness traversal, and no code from change 12 (grid traversal) SHALL be modified to read
`wilderness_move`.

**Amended 2026-08-01 (change `map-movement-clock`):** the previous wording asserted that intra-city
grid traversal "remains unwired to the clock" — a statement `map-movement-clock` makes false, since it
wires every intra-city link to charge `command_defaults.move` through `CostedXYZExit` (the
`sample-city-altoria` capability). The distinctness claim that is this requirement's real subject is
unchanged: wilderness steps pay `wilderness_move`, grid steps pay `move`, and the two lineages never
read each other's constant. The amended scenario below asserts exactly that.

#### Scenario: wilderness_move is present and distinct from move
- **WHEN** `world/rules/rulebook/clock.yaml` is inspected after this change lands
- **THEN** `command_defaults.wilderness_move == 9000` and `command_defaults.move == 30` (unchanged
  from change 11)

#### Scenario: Grid traversal is unaffected
- **WHEN** a character traverses an intra-city `CostedXYZExit` created by change 12's `sync_grid()`
  with this change's `("*", "*", "*")` wildcard prototype override
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, and
  no grid-traversal code reads `wilderness_move` — grid traversal is unaffected by the wilderness
  cost, charging the ordinary `move` cost instead
### Requirement: WILDERNESS_ENTRY_REGISTRY authored data is validated before persistence
`world/lore/wilderness_entry.py` SHALL provide `validate_wilderness_entries()` — a pure,
DB-free check of the whole registry — and `world/lore/sync.py`'s wilderness mirror step SHALL
run it before mirroring, so malformed authored data fails at startup rather than producing an
unwalkable or contradictory world. It SHALL reject: an empty mask or one with no `#`; any `#`
cell outside the provider's valid rectangle; a footprint whose `#` cells are not 4-connected; a
`return_direction` that is not a canonical wilderness direction or is duplicated within one
entry; a footprint-entry gate whose approach-cell ray from `anchor_cell` crosses no footprint
cell or whose approach cell is not a provider-valid cell outside the footprint; a point-shape
entry with any number of gates other than exactly one; a `grid_xy` outside the extent of the map
named by its `z_map_key`; and an `anchor_key` absent from `ANCHOR_PLACEMENT_REGISTRY`. The
shipped registry SHALL pass validation.
The mask SHALL be a well-formed rectangle — every row the same non-empty length, containing only
`#` and `.` (the `altoria_capital.MAPSTR` loading expectation) — and the derived `anchor_cell`
SHALL itself be a `#` cell. Globally, two entries SHALL NOT have overlapping footprints; no
footprint SHALL contain another entry's gate approach cell or point-shape anchor cell; and two
gates SHALL NOT share the same `(approach_cell, return_direction)` pair; and two gates SHALL NOT
share the same destination `(grid_xy, z_map_key)` room — one grid room hosts exactly one
WildernessGateExit slot, so a second gate on that room would silently displace the first at
provisioning time. A point-shape entry's anchor cell SHALL have all eight wilderness neighbors
provider-valid, so a gateway is never advertised toward a cell the provider cannot honor.

#### Scenario: The shipped registry validates
- **WHEN** `validate_wilderness_entries()` is called against the shipped
  `WILDERNESS_ENTRY_REGISTRY`
- **THEN** it raises nothing

#### Scenario: Malformed authored entries are each rejected
- **WHEN** `validate_wilderness_entries()` is called with a registry patched to contain one
  malformed entry at a time — empty mask, out-of-bounds `#` cell, disconnected footprint,
  non-canonical or duplicated `return_direction`, gate face not crossing the footprint,
  point-shape entry with zero or two gates, `grid_xy` outside its map, or unknown `anchor_key`
- **THEN** each patch raises a validation error naming the offending entry and the rejected rule

#### Scenario: Malformed masks and colliding geometry are each rejected
- **WHEN** `validate_wilderness_entries()` is called with a registry patched to contain one
  malformed entry at a time — ragged mask rows, a character outside `#`/`.`, an all-`.` mask, a
  mask whose bounding-box midpoint falls on a `.` cell, two entries whose footprints overlap, a
  footprint containing another entry's gate approach cell, two gates sharing one destination
  `(grid_xy, z_map_key)` room, or a point anchor with a provider-invalid neighbor direction
- **THEN** each patch raises a validation error naming the offending entry and the rejected rule

#### Scenario: sync_all refuses to mirror a malformed registry
- **WHEN** `sync_all()` runs with the wilderness registry patched to a malformed entry
- **THEN** the run fails with the validation error before any `lore:wilderness_entries:*` Script
  is created or updated
