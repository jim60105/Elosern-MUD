## Purpose

Define the all-or-nothing movement settlement boundary: every project exit lineage settles relocation,
the clock cost, map knowledge, and companion following in one outer database transaction,
compensating every Evennia in-process cache surface when any step fails
(movement-settlement-atomicity).

## Requirements

### Requirement: Movement settles relocation, clock cost, map knowledge, and companion following as one coherent transaction

Every successful traversal through any project exit lineage SHALL run inside one outer movement-settlement transaction that covers the Evennia relocation, the clock charge (`charge_movement`), destination map-knowledge recording (`record_arrival`), and companion following (`follow_companions`) as a single all-or-nothing unit. The boundary SHALL be opened inside the exit's own `at_traverse`, so the Telnet `ExitCommand` path, the WebClient `_move_adapter` path, and the scene-door command path all pass through it. `WorldClock.advance`'s own transaction degrades to a savepoint inside the boundary.

#### Scenario: A successful plain-exit traversal commits every settlement step together

- **WHEN** a `PlayerCharacter` successfully traverses an exit whose class includes `MovementCostMixin`
- **THEN** the traverser's location is the destination, `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"][movement_cost_key]`, the destination node is recorded in the traverser's map-knowledge record, and co-located companions moved to the destination — all visible after the traversal returns

#### Scenario: The boundary wraps the wilderness gate entry and the wilderness return and step paths

- **WHEN** a `PlayerCharacter` enters the wilderness through `WildernessGateExit`, or leaves through `WildernessReturnExit`'s registered return branch, or takes an ordinary wilderness step through the fallback branch
- **THEN** each successful path runs relocation and the full settlement sequence inside the same movement-settlement transaction, with charging through `after_successful_movement(...)` exactly as before

#### Scenario: The boundary applies to non-PlayerCharacter traversers without charging

- **WHEN** an `NPC`-typeclassed object successfully traverses any project exit lineage
- **THEN** the traversal succeeds and passes through the movement-settlement transaction, while the settlement steps (charge, record, follow) remain internal no-ops for the non-player traverser

### Requirement: A failed movement compensates the persisted relocation and reconciles every Evennia cache surface

When any step inside the movement-settlement transaction raises, when the outer transaction fails at commit, or when a wilderness lineage traversal returns falsy after relocating the traverser, the boundary SHALL compensate before the failure surfaces: the traverser and every companion the settlement moved SHALL be returned to their pre-move locations (using hook-free Evennia relocations, or the wilderness coordinate API where applicable), the wilderness script's `itemcoordinates`, `rooms`, and `unused_rooms` bookkeeping SHALL be restored to its pre-move state, and every in-process Evennia cache the settlement touched SHALL be reconciled — in-memory `db_location` values, the source and destination rooms' `contents_cache`, and the attribute backend caches of touched entities (restored from pre-move snapshots, including map-knowledge and quest-observation surfaces) — because Django rollback alone reverts only durable rows. Compensation steps SHALL run in a fixed deterministic order, each step SHALL be best-effort with a logged diagnostic on failure, and a compensation failure SHALL NOT mask or replace the original failure.

#### Scenario: A clock-charge failure during a plain exit move returns the player to the source

- **WHEN** `WorldClock.advance` raises during `charge_movement` after the player's relocation through a plain `MovementCostMixin` exit, with a co-located companion present
- **THEN** after `at_traverse` re-raises, the player and the companion are both back in the source room, the source room's contents cache contains both, the destination room's contents cache contains neither, `get_world_clock().tick` is unchanged, and the player's map-knowledge record, quest log, and the destination room's pin and interaction state are all unchanged

#### Scenario: A clock-charge failure during wilderness gate entry returns the player to the grid room

- **WHEN** `WorldClock.advance` raises during the `WildernessGateExit` entry after `enter_wilderness` succeeded (including when the entry created a fresh wilderness room)
- **THEN** after `at_traverse` re-raises, the player is back in the grid source room, is no longer registered in the wilderness script's `itemcoordinates`, and the wilderness script's full bookkeeping (`itemcoordinates`, `rooms`, `unused_rooms`) matches its pre-move state with no rolled-back zombie rooms retained

#### Scenario: A clock-charge failure during an ordinary wilderness step returns the player to the source coordinates

- **WHEN** `WorldClock.advance` raises during a `WildernessReturnExit` fallback step after the contrib moved the player to new coordinates
- **THEN** after `at_traverse` re-raises, the player is at the source coordinates (location restored and re-registered in the wilderness script), the wilderness bookkeeping matches its pre-move state, and the clock is unchanged

#### Scenario: A falsy wilderness return after relocation is compensated as a failure

- **WHEN** `WildernessGateExit.at_traverse` or `WildernessReturnExit.at_traverse` returns a falsy value while the traverser's location changed (for example a `move_to` hook raised after relocation)
- **THEN** the boundary treats the traversal as failed and compensates exactly as for a raised settlement step: the traverser is returned to its pre-move location, wilderness bookkeeping is restored, and no clock charge or knowledge record remains

#### Scenario: A failure after companions moved returns every moved companion

- **WHEN** a settlement step after `follow_companions` raises, with companions already moved to the destination
- **THEN** after compensation every moved companion is back at its pre-move location and the player is back at the source, with source/destination contents caches and wilderness bookkeeping consistent

#### Scenario: A rolled-back commit reconciles durable rows and in-process caches to the pre-move state

- **WHEN** the outer movement-settlement transaction fails at commit
- **THEN** the durable rows (location, clock, attributes) revert to the pre-move state and a fresh read of the in-process objects shows the same pre-move state: `db_location`, contents caches, attribute values, and the world-clock tick (verified deterministically by invoking the compensation against a deliberately constructed divergent in-process state, since Django test cases wrap every transaction so commit failure cannot occur at the boundary level in tests)

### Requirement: A failed movement reports failure truthfully on every client path

A movement whose settlement failed SHALL report failure (WebClient `move_failed`, Telnet command error propagation) only after compensation restored the traverser's authoritative location, and no client path SHALL observe or act on a player relocated without time, knowledge, or companions. The one documented exception is the plain-exit lineage's `move_to` hook quirk (a hook raising after relocation makes `move_to` return `False` without an exception and `DefaultExit.at_traverse` return `None` on both branches), which the mixin lineage cannot detect; the wilderness lineages close this gap through their falsy-return trigger.

#### Scenario: WebClient explore.move reports move_failed with the player still at the source

- **WHEN** the WebClient `_move_adapter` traverses an exit and the clock charge raises
- **THEN** the adapter returns `outcome=rejected` with code `move_failed`, the player's location is the source room, the clock is unchanged, and no map-knowledge change occurred

#### Scenario: The Telnet exit command path leaves the player at the source after a failing charge

- **WHEN** `ExitCommand` traverses an exit and the clock charge raises
- **THEN** the traversal propagates the failure and the player remains in the source room with the clock unchanged
