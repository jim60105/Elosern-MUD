## ADDED Requirements

### Requirement: advance() persists the tick and entity state atomically

`WorldClock.advance()` SHALL settle all per-entity stages and the final `tick` increment inside a single durable transaction with snapshot/restore of the touched entity attributes, so a process termination during the call can never leave character state advanced without the matching tick (or the reverse).

#### Scenario: Terminated advance leaves no partial save

- **WHEN** a process is terminated while `advance()` is running after entity writes but before the tick persist
- **THEN** after restart both the entity state and `world_clock.db.tick` reflect the same pre-advance values

#### Scenario: Successful advance commits entity state and tick together

- **WHEN** `advance()` completes normally for a caller-supplied entity
- **THEN** the entity's gauge/daily-counter changes and the increased `tick` are both durably visible after restart

### Requirement: advance() has a bounded settlement budget per call

`WorldClock.advance()` SHALL reject or reject-and-degrade any call whose elapsed seconds would exceed a configured maximum advance duration (`MAX_ADVANCE_SECONDS`, equal to one full game day — `seconds_per_hour * hours_per_day` from `rulebook/clock.yaml`), so the per-day boundary loop and event accumulation are bounded per call. One full day keeps `wait until`'s worst case (a day-long wait) legal while still bounding the loop at one day crossing per call.

#### Scenario: Oversized advance is refused without writes

- **WHEN** `advance()` is called with seconds above `MAX_ADVANCE_SECONDS`
- **THEN** the call raises a named error before any entity or tick write occurs
