## MODIFIED Requirements

### Requirement: The sample city connects to the rest of the world through exactly one bridging exit
The South Gate room, at `(2,0)`, SHALL be the sample city's sole connection point to non-grid space,
reached via the single forward bridging `Exit` from Limbo described by the `grid-room-sync`
capability — exactly one forward bridging exit per `CITY_GATE_REGISTRY` row, of which
`capital_altoria` is one. Other settlements have their own rows and their own entrances; this
requirement bounds the capital's connectivity only, and SHALL NOT be read as a claim about how
many settlements the registry describes. The bridge is one-way: no room of the sample city SHALL hold an exit whose
destination is the Limbo starting room, and `sync_grid()` prunes any such exit on every run (see
the `limbo-one-way-gates` capability). The North Gate room, at `(2,4)`, SHALL have no exit beyond the
one leading back into the city.

#### Scenario: The South Gate is the only room reachable from Limbo
- **WHEN** Limbo's exits are inspected after `sync_grid()` runs
- **THEN** they are exactly the registry's forward gate exits — one per `CITY_GATE_REGISTRY` row —
  and the `capital_altoria` row's exit leads into that map, at `(2,0)`

#### Scenario: No city room leads back to Limbo
- **WHEN** every exit of every spawned `capital_altoria` room is inspected after `sync_grid()` runs
- **THEN** none of them has the Limbo starting room as its destination

#### Scenario: The North Gate is a dead end, reserved for a future wilderness link
- **WHEN** the North Gate room's exits are inspected
- **THEN** its only exit is the one leading south back to `(2,3)`; it has no other exit, and no
  `WildernessMapProvider` or other non-grid destination is referenced anywhere in this change's map
  data
