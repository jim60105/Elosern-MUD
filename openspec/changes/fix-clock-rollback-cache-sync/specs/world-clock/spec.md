## ADDED Requirements

### Requirement: Every registered boundary-stage source declares the durable surfaces it may write
`register_event_source(kind, source, surfaces)` SHALL accept an optional advance-surface contract: a pure, read-only callable `(start_tick, end_tick) -> mapping[id(obj), SurfaceSnapshot]` that re-discovers, with the same deterministic queries its settlement uses, every object the source may write and snapshots each durable surface and any location state through the shared attribute-snapshot helper. A source that writes durable state SHALL ship a contract; a source with no contract (`None`) SHALL be treated as a read-only seam and SHALL not write durable state during settlement. `WorldClock.advance` SHALL run every registered contract before opening its transaction, SHALL merge the results with its caller-entity snapshot set by object identity, and SHALL restore every declared surface on failure. The two-argument registration form SHALL remain valid for read-only and test sources.

#### Scenario: A writing source without a contract is a completeness violation
- **WHEN** the registered boundary-stage sources are inspected (`caravan_arrivals`, `quest_deadlines`, `npc_schedules`, `instance_reclamation`)
- **THEN** each one declares a contract that snapshots the durable surfaces its settlement writes, and a test fails if any of these four registrations loses its contract

#### Scenario: A read-only source declares no contract and still runs
- **WHEN** `register_event_source("shop_hours", settle_shop_hours)` is registered with no contract and `advance()` crosses a shop-hours boundary
- **THEN** settlement still emits its events, the call succeeds, and no snapshot or restore is performed for shop state

#### Scenario: A synthetic two-argument source registered by a test still works
- **WHEN** a test registers `register_event_source(kind, source)` with a lambda and calls `advance()` across a boundary
- **THEN** the source's events are returned in the correct stage position exactly as before, with no contract required

#### Scenario: A contract is a pure read that never mutates state
- **WHEN** a contract snapshot function is invoked
- **THEN** it only reads attributes and locations — no attribute, trait, location, or tag value changes as a side effect of the snapshot

### Requirement: A rolled-back advance restores every callback-owned surface, not just caller entities
When any stage or the final clock persistence fails inside `WorldClock.advance`, the in-memory values of every durable surface written by any registered boundary-stage source SHALL be restored to their pre-advance values in addition to the caller-entity surfaces and the clock tick, so the process never serves or repersists state that the rolled-back transaction never committed.

#### Scenario: A failed advance restores a discovered quest log and room pins
- **WHEN** a player has an in-progress quest whose deadline falls inside the advance window, and a later registered stage raises
- **THEN** after the exception the player's `db.quest_log` in the in-process object, the raw `quest_log` Attribute row, and every affected room's `db.pin_reasons` are all unchanged from before the advance, and the clock tick is unchanged

#### Scenario: A failed advance restores merchant stock and last restock day
- **WHEN** an advance crosses a merchant's restock day and a later stage or the final persist raises
- **THEN** the merchant host's cached `merchant_stock` and `last_restock_day` values and their raw Attribute rows both equal their pre-advance values

#### Scenario: A failed advance restores NPC schedule state and location
- **WHEN** an advance settles a due schedule occurrence that writes `schedule_state` or relocates the NPC, and a later stage or the final persist raises
- **THEN** the NPC's cached and stored `schedule_state` equal the pre-advance value, the NPC's in-memory `db_location` points back at the pre-advance room, and the source and destination rooms' contents caches re-read from the rolled-back database

#### Scenario: A failed advance restores instance-room state, pruned map knowledge, and relocated occupants
- **WHEN** an advance promotes or reclaims a due `InstanceRoom` (including pruning `map_knowledge` records and relocating unowned occupants), and a later stage or the final persist raises
- **THEN** every touched room's `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities` values and every pruned player's `map_knowledge` value, in cache and in raw Attribute rows, equal their pre-advance values; every relocated occupant's in-memory location points back into the re-fetched (rolled-back) reclaimed room rather than at a deleted object or `None`; and a room deleted during the failed advance is re-fetched fresh from the rolled-back database on the next access

## MODIFIED Requirements

### Requirement: advance() persists the tick and entity state atomically
`WorldClock.advance()` SHALL settle all per-entity stages, every registered boundary stage, and the final `tick` increment inside a single durable transaction with snapshot/restore of the touched entity attributes **and of every durable surface any registered boundary-stage source may write (through its declared advance-surface contract, including quest logs and room pins, merchant components, NPC schedule state and location, instance-room state, and pruned map knowledge)**, so a process termination or a failure inside the call can never leave character state advanced without the matching tick (or the reverse), and no observer can see or persist an uncommitted settlement.

#### Scenario: Terminated advance leaves no partial save
- **WHEN** a process is terminated while `advance()` is running after entity writes but before the tick persist
- **THEN** after restart both the entity state and `world_clock.db.tick` reflect the same pre-advance values

#### Scenario: Successful advance commits entity state and tick together
- **WHEN** `advance()` completes normally for a caller-supplied entity
- **THEN** the entity's gauge/daily-counter changes and the increased `tick` are both durably visible after restart

#### Scenario: A successful advance with a due quest deadline commits the failure together with the tick
- **WHEN** `advance()` completes normally while a player's in-progress quest deadline falls inside the window and all writing sources ship their contracts
- **THEN** the failed quest record is durably visible in `quest_log` after restart and the tick increased by the full `seconds`, with no divergence between cache and storage

#### Scenario: The fixed stage order and one-day bound survive the snapshot extension
- **WHEN** the stage sequence and `MAX_ADVANCE_SECONDS` are inspected after this change
- **THEN** the stage sequence is still exactly `("gauge_regen", "buff_ticks", "sexual_decay", "magic_study", "daily_resets", "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules", "instance_reclamation")`, an oversized call still raises before any write, and contracts run before any stage write
