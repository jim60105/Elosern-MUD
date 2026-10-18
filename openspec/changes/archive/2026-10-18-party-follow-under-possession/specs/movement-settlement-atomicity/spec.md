# Spec Delta

## MODIFIED Requirements

### Requirement: A failed movement compensates the persisted relocation and reconciles every Evennia cache surface

When any step inside the movement-settlement transaction raises, when the outer transaction fails at commit, or when a wilderness lineage traversal returns falsy after relocating the traverser, the boundary SHALL compensate before the failure surfaces: the traverser and every party member the settlement moved (companions, and the commander's body when the traverser is a possessed companion) SHALL be returned to their pre-move locations via hook-free Evennia relocations, or the wilderness coordinate API where applicable.

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

#### Scenario: Compensation restores wilderness script bookkeeping to its pre-move state

- **WHEN** compensation runs after a wilderness lineage movement failed
- **THEN** the wilderness script's `itemcoordinates`, `rooms`, and `unused_rooms` bookkeeping is restored to its pre-move state

#### Scenario: Compensation reconciles every in-process Evennia cache the settlement touched

- **WHEN** compensation runs after a failed movement settlement
- **THEN** every in-process Evennia cache the settlement touched is reconciled — in-memory `db_location` values, the source and destination rooms' `contents_cache`, and the attribute backend caches of touched entities (restored from pre-move snapshots, including map-knowledge and quest-observation surfaces)
- **AND** this reconciliation is required because Django rollback alone reverts only durable rows

#### Scenario: Compensation steps are ordered, best-effort, and non-masking

- **WHEN** the boundary's compensation sequence runs
- **THEN** the steps run in a fixed deterministic order and each step is best-effort with a logged diagnostic on failure
- **AND** a compensation failure does not mask or replace the original failure

#### Scenario: A failed possessed traversal returns the whole party
- **WHEN** the clock charge raises after a possessed 艾拉 relocated and the follow step had not yet run, or a later settlement step raises after the player's body and 卡恩 followed
- **THEN** 艾拉, the player's body and 卡恩 are all back in the source room with contents caches, wilderness bookkeeping and the possession mirror unchanged
