## MODIFIED Requirements

### Requirement: Long jumps settle in quanta, not per-second steps, with an early exit once nothing
remains to settle
`world/rules/clock.py` SHALL derive `SETTLEMENT_QUANTUM_SECONDS` as the greatest common divisor of
every currently-configured buff `tick_interval` (change 6's `buffs.yaml`) and sexual-decay
`interval_seconds` (change 7's `DECAY_CONFIG`), and SHALL invoke `tick_buffs()`/`decay_tick()` once per
quantum rather than once per second. Immediately after each `decay_tick()` call within this loop, the
settlement SHALL also call `world.rules.sexual_state.climax_settlement_action(entity)` and, when it
returns `"extend"` or `"end"`, SHALL emit the correspondingly named event through
`world.rules.sexual_transitions.apply_event()`. The settlement loop SHALL stop iterating quanta, for a
given `advance()` call, the moment no entity in scope has an active buff, a sexual field above its
configured floor, **or a `climax_phase` of `進行中`** — an entity mid-climax always counts as needing
further settlement regardless of every other field's floor state — and SHALL additionally stop at a
configured defensive cap (`MAX_SETTLEMENT_QUANTA`) regardless of remaining work.

Any final partial quantum from a command or combat-adjacent duration SHALL still be passed to the
per-entity accumulators once. It is never discarded merely because it is smaller than the quantum.

#### Scenario: An 8-hour skip with no active buffs or elevated sexual state exits before a quantum
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with no active buffs
  and every sexual field already at its vocabulary floor
- **THEN** neither `tick_buffs()` nor `decay_tick()` is called, because there is no work to settle and
  the loop exits before its first quantum

#### Scenario: A short-lived buff ticks correctly through its own duration, then the loop exits early
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with a `poisoned`
  buff (duration 300 seconds) active at the start
- **THEN** `tick_buffs()`/`decay_tick()` are called enough times to cover the buff's own 300-second
  duration at the derived quantum size, and no further quanta are processed once the buff has expired
  and every sexual field is at its floor

#### Scenario: A six-second command preserves partial elapsed time
- **WHEN** two command-sourced advances of six seconds each occur while settlement work is active
- **THEN** both six-second portions reach buff and sexual-state accumulators; no elapsed game seconds are
  lost because they are smaller than the ten-second quantum

#### Scenario: A non-positive configured interval fails loudly at startup
- **WHEN** a future `buffs.yaml` or `DECAY_CONFIG` entry declares a non-positive `tick_interval` or
  `interval_seconds`
- **THEN** a startup assertion raises, naming the offending interval rather than creating an invalid
  quantum loop

#### Scenario: An entity in 進行中 keeps the loop iterating even after every other field reaches its floor
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity whose `climax_phase`
  is `進行中` and whose every other `DECAY_CONFIG`-tracked field has already reached its floor
- **THEN** the settlement loop does not exit early on that account — it continues until
  `climax_settlement_action()` resolves the entity out of `進行中` (or the defensive quantum cap is
  reached)

#### Scenario: An entity in 進行中 with no other settlement work still receives climax settlement on the remainder branch
- **WHEN** `advance()` is called with an elapsed duration shorter than one quantum for an entity whose
  `climax_phase` is `進行中` and whose every other field is at its floor
- **THEN** the remainder branch still calls `decay_tick()` and `climax_settlement_action()` for that
  entity, because `climax_phase == 進行中` alone satisfies the settlement-work check gating that branch
