## MODIFIED Requirements

### Requirement: advance() persists the tick and entity state atomically
`WorldClock.advance()` SHALL settle all per-entity stages, every registered boundary stage, and the
final `tick` increment inside a single durable transaction with snapshot/restore of the touched
entity attributes **and of every durable surface any registered boundary-stage source may write
(through its declared advance-surface contract, including quest logs and room pins, merchant
components, NPC schedule state and location, instance-room state, pruned map knowledge, narrative letter rows, and durable delivery projection progress)**, so a
process termination or a failure inside the call can never leave character state advanced without
the matching tick (or the reverse), and no observer can see or persist an uncommitted settlement.

#### Scenario: Terminated advance leaves no partial save
- **WHEN** a process is terminated while `advance()` is running after entity writes but before the
  tick persist
- **THEN** after restart both the entity state and `world_clock.db.tick` reflect the same pre-advance
  values

#### Scenario: Successful advance commits entity state and tick together
- **WHEN** `advance()` completes normally for a caller-supplied entity
- **THEN** the entity's gauge/daily-counter changes and the increased `tick` are both durably visible
  after restart

#### Scenario: A successful advance with a due quest deadline commits the failure together with the tick
- **WHEN** `advance()` completes normally while a player's in-progress quest deadline falls inside
  the window and all writing sources ship their contracts
- **THEN** the failed quest record is durably visible in `quest_log` after restart and the tick
  increased by the full `seconds`, with no divergence between cache and storage

#### Scenario: The fixed stage order and one-day bound survive the snapshot extension
- **WHEN** the stage sequence and `MAX_ADVANCE_SECONDS` are inspected after this change
- **THEN** the stage sequence is still exactly `("gauge_regen", "buff_ticks", "sexual_decay",
  "practice_settlement", "daily_resets", "caravan_arrivals", "shop_hours", "quest_deadlines",
  "npc_schedules", "correspondence_delivery", "instance_reclamation")`, an oversized call still raises before any write, and
  contracts run before any stage write

## ADDED Requirements

### Requirement: Delivery table changes participate in clock rollback

Letter and durable derived-work table changes SHALL share the clock transaction. Cached row instances SHALL be discarded or refreshed after rollback; delivery SHALL NOT cause mutations of recipient live traits or quest state.

#### Scenario: Rollback after due transition
- **WHEN** a later clock stage fails after a due letter changes state
- **THEN** letter/progress tables and any cached read models equal pre-advance state

