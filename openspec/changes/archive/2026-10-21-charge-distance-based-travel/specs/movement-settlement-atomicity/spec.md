# Spec Delta

## MODIFIED Requirements

### Requirement: Movement settles relocation, clock cost, map knowledge, and companion following as one coherent transaction

Every successful traversal through any project exit lineage SHALL run inside one outer movement-settlement transaction that covers the Evennia relocation, the clock charge (`charge_movement`), destination map-knowledge recording (`record_arrival`), and companion following (`follow_companions`) as a single all-or-nothing unit.

#### Scenario: A successful plain-exit traversal commits every settlement step together

- **WHEN** a `PlayerCharacter` successfully traverses an exit whose class includes `MovementCostMixin`
- **THEN** the traverser's location is the destination, `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"][movement_cost_key]`, the destination node is recorded in the traverser's map-knowledge record, and co-located companions moved to the destination — all visible after the traversal returns

#### Scenario: The boundary wraps the wilderness gate entry and the wilderness return and step paths

- **WHEN** a `PlayerCharacter` enters the wilderness through `WildernessGateExit`, or leaves through `WildernessReturnExit`'s registered return branch, or takes an ordinary wilderness step through the fallback branch
- **THEN** each successful path runs relocation and the full settlement sequence inside the same movement-settlement transaction, with charging through `after_successful_movement(...)` exactly as before

#### Scenario: The boundary applies to non-PlayerCharacter traversers without charging

- **WHEN** an `NPC`-typeclassed object successfully traverses any project exit lineage
- **THEN** the traversal succeeds and passes through the movement-settlement transaction, while the settlement steps (charge, record, follow) remain internal no-ops for the non-player traverser

#### Scenario: The boundary is opened inside the exit's own at_traverse for every client path

- **WHEN** a traversal arrives via the Telnet `ExitCommand` path, the WebClient `_move_adapter` path, or the scene-door command path
- **THEN** each passes through the movement-settlement transaction, because the boundary is opened inside the exit's own `at_traverse`

#### Scenario: The clock's own transaction degrades to a savepoint inside the boundary

- **WHEN** the settlement's clock charge runs `WorldClock.advance` inside the movement-settlement boundary
- **THEN** `WorldClock.advance`'s own transaction degrades to a savepoint inside the boundary
