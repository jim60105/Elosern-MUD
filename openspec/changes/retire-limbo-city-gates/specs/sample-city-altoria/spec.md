# Spec Delta

## ADDED Requirements

### Requirement: The sample city connects to the world only through its wilderness gates
Apart from service interiors, the sample city's rooms SHALL connect outward only through the wilderness gate exits its wilderness entry authorizes. Every room a capital wilderness gate targets SHALL hold one city exit per authored road leaving that node plus that wilderness gate exit, and SHALL NOT be a dead end. No sample-city room SHALL hold an exit into the starting room or receive one from it.

#### Scenario: A wilderness gate room connects the city and the wilderness
- **WHEN** the exits of each room a capital wilderness gate targets are inspected after `sync_grid()` and `sync_wilderness()` run
- **THEN** it holds one city exit per authored road leaving that node and the wilderness gate exit its entry row authorizes, and no other exit

#### Scenario: No city room is joined to 虛境
- **WHEN** every exit located in or leading into a spawned sample-city room is inspected after `sync_grid()` runs with a starting room present
- **THEN** none of them is located in the starting room or leads into it

## REMOVED Requirements

### Requirement: The sample city connects to the rest of the world through exactly one bridging exit
**Reason**: 虛境 has no bridging exits any more. Characters start in their subrace's
settlement (`subrace-start-settlements`).
**Migration**: The wilderness-gate connectivity is kept as "The sample city connects to
the world only through its wilderness gates".
