## ADDED Requirements

### Requirement: The sample city's twelve intra-city exits spawn as CostedXYZExit, not the bare contrib XYZExit
`world/maps/altoria_capital.py::ALTORIA_CAPITAL_MAP_DATA["prototypes"]` SHALL include exactly one
wildcard link-prototype override, `("*", "*", "*"): {"prototype_parent": "xyz_exit", "typeclass":
"typeclasses.exits.CostedXYZExit"}`, so that every one of the sample city's twelve intra-city links
spawns as `typeclasses.exits.CostedXYZExit` (the `movement-cost-charging` capability) instead of the
contrib's own bare `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`. This SHALL NOT change the room or
exit topology, count, or connectivity already required by this capability's other requirements — it
changes only which typeclass each of the twelve links spawns as.

#### Scenario: Every intra-city exit is a CostedXYZExit instance
- **WHEN** `sync_grid()` runs and the sample city's twelve intra-city exits are inspected by typeclass
- **THEN** every one of them is a `typeclasses.exits.CostedXYZExit` instance

#### Scenario: The topology and count required by this capability are unaffected
- **WHEN** the sample city's rooms and exits are inspected after this change lands
- **THEN** exactly thirteen rooms and twelve intra-city exits still exist, in the identical topology
  this capability's other requirements already describe — only the exits' typeclass has changed

#### Scenario: A successful traversal of an intra-city exit advances the clock
- **WHEN** a `PlayerCharacter` successfully traverses any of the sample city's twelve intra-city exits
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`
