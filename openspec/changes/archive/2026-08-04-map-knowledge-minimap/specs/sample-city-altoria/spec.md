## MODIFIED Requirements

### Requirement: The sample city has exactly thirteen rooms in a fixed, connected topology
`world/maps/altoria_capital.py` SHALL declare `XYMAP_DATA` for `zcoord="capital_altoria"` describing
exactly thirteen rooms at the coordinates: `(2,0)`, `(1,1)`, `(2,1)`, `(3,1)`, `(0,2)`, `(1,2)`,
`(2,2)`, `(3,2)`, `(4,2)`, `(1,3)`, `(2,3)`, `(3,3)`, `(2,4)`, connected by exactly twelve exits with
no cycle (a tree), such that every room is reachable from every other room. The map's declared `options` SHALL contain exactly `map_visual_range`, a positive integer at most 8,
and `map_mode`, one of the closed tokens `nodes` or `scan` — the same closed values the xyzgrid
contrib's own `get_visual_range` accepts. The `webclient-local-map` capability's grid adapter reads
these as the configured grid visual range; an absent, malformed, or out-of-range `options` value SHALL
fail closed to the stable unavailable reason rather than guessing a default. Adding this `options`
entry SHALL NOT change the room or exit topology, count, or connectivity required by this capability.

#### Scenario: The map parses to exactly thirteen nodes
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA["map"]` string is parsed with
  `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()`
- **THEN** exactly thirteen nodes exist, at exactly the coordinates listed above

#### Scenario: Every room is reachable from every other room
- **WHEN** `XYMap.calculate_path_matrix()` is run against the parsed map
- **THEN** a shortest path exists between every pair of the thirteen coordinates

#### Scenario: The topology has no cycle
- **WHEN** the twelve links in the parsed map are inspected
- **THEN** they connect the thirteen nodes with exactly twelve edges, and removing any one edge
  disconnects the graph (a tree, not a graph with a cycle)

#### Scenario: The map declares bounded visual-range options
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA` is inspected
- **THEN** its `options` contains a `map_visual_range` positive integer of at most 8 and a `map_mode`
  equal to `nodes` or `scan`, and parsing the map still yields exactly thirteen nodes and twelve links

#### Scenario: The grid adapter reads the declared options and fails closed on invalid values
- **WHEN** the grid layer adapter runs against the declared `options` and against a malformed or
  out-of-range `options` value
- **THEN** the valid value is used as the visual range, and the invalid value produces the stable
  unavailable reason instead of a guessed default
