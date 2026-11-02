## MODIFIED Requirements

### Requirement: The sample city connects to the rest of the world through exactly one bridging exit
The room of the capital's authored `city_gate` node SHALL be the sample city's entrance from Limbo,
reached via the single forward bridging `Exit` from Limbo described by the `grid-room-sync`
capability, exactly one forward bridging exit per `CITY_GATE_REGISTRY` row, of which
`capital_altoria` is one. Wilderness gates and service interiors SHALL remain separate
from that bridge. Every room a capital wilderness gate targets SHALL carry its declared
wilderness gate and SHALL NOT be a dead end.

#### Scenario: The South Gate is the only room reachable from Limbo
- **WHEN** Limbo's exits are inspected after `sync_grid()` runs
- **THEN** they are exactly the registry's forward gate exits, one per `CITY_GATE_REGISTRY` row,
  and the `capital_altoria` row's exit leads into that map, at the city-gate node's current authored coordinate

#### Scenario: No city room leads back to Limbo
- **WHEN** every exit of every spawned `capital_altoria` room is inspected after `sync_grid()` runs
- **THEN** none of them has the Limbo starting room as its destination

#### Scenario: The East Gate connects the city and wilderness
- **WHEN** the exits of each room a capital wilderness gate targets are inspected
- **THEN** it holds one city exit per authored road leaving that node and the wilderness gate exit its
  `WILDERNESS_ENTRY_REGISTRY` row authorises, and no other exit

#### Scenario: The bridge is one-way and pruned on every sync
- **WHEN** the capital's bridging connection is exercised and `sync_grid()` runs
- **THEN** the bridge is one-way: no room of the sample city SHALL hold an exit whose destination
  is the Limbo starting room, and `sync_grid()` prunes any such exit on every run (see the
  `limbo-one-way-gates` capability)

#### Scenario: Other settlements keep their own rows and entrances
- **WHEN** the `CITY_GATE_REGISTRY` is read alongside this requirement
- **THEN** other settlements have their own rows and their own entrances; this requirement bounds
  the capital's connectivity only, and SHALL NOT be read as a claim about how many settlements the
  registry describes
