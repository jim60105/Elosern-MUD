## MODIFIED Requirements

### Requirement: The sample city has exactly thirteen rooms in a fixed, connected topology
<!-- Requirement name retained verbatim: a MODIFIED block may not rename a requirement, so the
     historical "thirteen" in this title is stale. The text below is the current contract. -->
`world/maps/altoria_capital.py` SHALL declare `XYMAP_DATA` for `zcoord="capital_altoria"` describing
exactly twenty-one rooms at the coordinates: `(3,0)`, `(1,1)`, `(2,1)`, `(3,1)`, `(4,1)`, `(5,1)`,
`(2,2)`, `(3,2)`, `(1,3)`, `(2,3)`, `(3,3)`, `(4,3)`, `(5,3)`, `(6,3)`, `(2,4)`, `(3,4)`, `(4,4)`,
`(3,5)`, `(4,5)`, `(5,5)`, `(4,6)`, connected by exactly twenty-six links such that every room is
reachable from every other room.

The topology SHALL NOT be a tree. It SHALL contain exactly six independent cycles, and it SHALL
include at least two diagonal links. Both are load-bearing world-building, not incidental: a city
in which every route between two points is the only route is a corridor. The cycles are the ring
of the old wall the city outgrew and the blocks the pilgrim road divides; the diagonals are the
shortcuts foot traffic wears into a city that grew rather than one that was laid out.

The map's declared `options` SHALL contain exactly `map_visual_range`, a positive integer at most 8,
and `map_mode`, one of the closed tokens `nodes` or `scan` — the same closed values the xyzgrid
contrib's own `get_visual_range` accepts. The `webclient-local-map` capability's grid adapter reads
these as the configured grid visual range; an absent, malformed, or out-of-range `options` value SHALL
fail closed to the stable unavailable reason rather than guessing a default. Adding this `options`
entry SHALL NOT change the room or exit topology, count, or connectivity required by this capability.

#### Scenario: The map parses to exactly thirteen nodes
<!-- Scenario name retained verbatim; the count it asserts is the one in the text above. -->
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA["map"]` string is parsed with
  `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()`
- **THEN** exactly twenty-one nodes exist, at exactly the coordinates listed above

#### Scenario: Every room is reachable from every other room
- **WHEN** `XYMap.calculate_path_matrix()` is run against the parsed map
- **THEN** a shortest path exists between every pair of the twenty-one coordinates

#### Scenario: The topology has no cycle
<!-- Scenario name retained verbatim: the contract inverted, and a MODIFIED block may not rename
     a scenario. The body states the current rule. -->
- **WHEN** the twenty-six links in the parsed map are inspected
- **THEN** they connect the twenty-one nodes with exactly twenty-six edges, six more than a tree
  would need, and at least one pair of rooms has two distinct routes between them

#### Scenario: The map declares bounded visual-range options
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA` is inspected
- **THEN** its `options` contains a `map_visual_range` positive integer of at most 8 and a `map_mode`
  equal to `nodes` or `scan`, and parsing the map still yields exactly twenty-one nodes and
  twenty-six links

#### Scenario: The grid adapter reads the declared options and fails closed on invalid values
- **WHEN** the grid layer adapter runs against the declared `options` and against a malformed or
  out-of-range `options` value
- **THEN** the valid value is used as the visual range, and the invalid value produces the stable
  unavailable reason instead of a guessed default

### Requirement: Exactly one room is the AnchorRoom, at the central plaza
Of the twenty-one rooms, exactly one, at coordinate `(3,3)`, SHALL spawn as an `AnchorRoom` with
`anchor_key="capital_altoria"`. The remaining twenty SHALL spawn as plain `GridRoom`.

#### Scenario: Only the plaza is an AnchorRoom
- **WHEN** all twenty-one spawned rooms are inspected by typeclass
- **THEN** exactly one, at `(3,3)`, is an `AnchorRoom` instance, and the others are `GridRoom`
  instances that are not `AnchorRoom` instances

### Requirement: The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached
<!-- Requirement name retained verbatim; the count it names is stale, the text is current. -->
Every notable building referenced by the xyzgrid SHALL remain represented by one exterior
GridRoom in that map. Guild economy SHALL additionally create one ordinary permanent room outside the
xyzgrid node count for each place the settlement's place registry declares, linked bidirectionally from
that place's declared exterior. The number and identity of those interiors SHALL follow the registry
rather than being fixed by this requirement.

One exterior MAY carry more than one interior, distinguished by their authored doorway names: a
craft alley with a forge and a tailor on it is one street with two doors. Some exteriors SHALL
carry none at all — a capital contains squares, steps, ruins and quaysides that exist to be walked
through rather than entered.

The twenty-one grid coordinates, twenty-six grid links, cycle count and sole AnchorRoom SHALL
remain unchanged by interior attachment.

#### Scenario: Grid topology is unchanged
- **WHEN** `XYMAP_DATA` is parsed after guild economy lands
- **THEN** it still contains exactly the twenty-one grid nodes and twenty-six links

#### Scenario: Both interiors are reachable and permanent
<!-- Scenario name retained verbatim; it now covers every registered interior. -->
- **WHEN** map and guild-economy synchronization complete
- **THEN** each interior exists once, has no expiry tick, and can be reached from and exited back to its
  documented exterior

#### Scenario: Interiors do not become xyzgrid nodes
- **WHEN** the XYZGrid map is queried by coordinate
- **THEN** no service interior appears as an additional coordinate or changes shortest paths among
  the grid rooms

#### Scenario: Adding a trading place needs no map edit
- **WHEN** a place is declared against an exterior that already exists in the grid
- **THEN** its interior and doorways appear after synchronization with no change to `XYMAP_DATA`

#### Scenario: Specialist shops do not narrow what the capital sells
- **WHEN** the goods offered across every capital place are collected
- **THEN** the set equals the set the single general store offered before the split, with no key
  offered by two places

#### Scenario: One exterior carries two doors
- **WHEN** two places declare the same exterior with different doorway names
- **THEN** both interiors exist, that exterior holds one doorway exit per place, and each interior
  leads back to it

### Requirement: The sample city connects to the rest of the world through exactly one bridging exit
The South Gate room, at `(3,0)`, SHALL be the sample city's sole connection point to non-grid space,
reached via the single forward bridging `Exit` from Limbo described by the `grid-room-sync`
capability — exactly one forward bridging exit per `CITY_GATE_REGISTRY` row, of which
`capital_altoria` is one. Other settlements have their own rows and their own entrances; this
requirement bounds the capital's connectivity only, and SHALL NOT be read as a claim about how
many settlements the registry describes. The bridge is one-way: no room of the sample city SHALL hold an exit whose
destination is the Limbo starting room, and `sync_grid()` prunes any such exit on every run (see
the `limbo-one-way-gates` capability). The East Gate room, at `(6,3)`, SHALL carry the capital's
second wilderness gate and SHALL NOT be a dead end.

#### Scenario: The South Gate is the only room reachable from Limbo
- **WHEN** Limbo's exits are inspected after `sync_grid()` runs
- **THEN** they are exactly the registry's forward gate exits — one per `CITY_GATE_REGISTRY` row —
  and the `capital_altoria` row's exit leads into that map, at `(3,0)`

#### Scenario: No city room leads back to Limbo
- **WHEN** every exit of every spawned `capital_altoria` room is inspected after `sync_grid()` runs
- **THEN** none of them has the Limbo starting room as its destination

#### Scenario: The North Gate is a dead end, reserved for a future wilderness link
<!-- Scenario name retained verbatim: the reserved dead end is now the East Gate and is no longer
     reserved. The body states the current rule. -->
- **WHEN** the East Gate room's exits are inspected
- **THEN** it holds its link west back into the city and the wilderness gate exit its
  `WILDERNESS_ENTRY_REGISTRY` row authorises, and no other exit

### Requirement: The sample city's twelve intra-city exits spawn as CostedXYZExit, not the bare contrib XYZExit
<!-- Requirement name retained verbatim; the count it names is stale, the text is current. -->
`world/maps/altoria_capital.py::XYMAP_DATA["prototypes"]` SHALL include exactly one
wildcard link-prototype override, `("*", "*", "*"): {"prototype_parent": "xyz_exit", "typeclass":
"typeclasses.exits.CostedXYZExit"}`, so that every one of the sample city's intra-city links
spawns as `typeclasses.exits.CostedXYZExit` (the `movement-cost-charging` capability) instead of the
contrib's own bare `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`. This SHALL NOT change the room or
exit topology, count, or connectivity already required by this capability's other requirements — it
changes only which typeclass each link spawns as. The override SHALL cover diagonal links exactly
as it covers cardinal ones.

#### Scenario: Every intra-city exit is a CostedXYZExit instance
- **WHEN** `sync_grid()` runs and the sample city's intra-city exits are inspected by typeclass
- **THEN** every one of them is a `typeclasses.exits.CostedXYZExit` instance, diagonals included

#### Scenario: The topology and count required by this capability are unaffected
- **WHEN** the sample city's rooms and exits are inspected after this change lands
- **THEN** exactly twenty-one rooms and twenty-six intra-city links still exist, in the identical
  topology this capability's other requirements already describe — only the exits' typeclass has
  changed

#### Scenario: A successful traversal of an intra-city exit advances the clock
- **WHEN** a `PlayerCharacter` successfully traverses any of the sample city's intra-city exits
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`
