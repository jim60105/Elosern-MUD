# Spec Delta

## MODIFIED Requirements

### Requirement: Gauge and buff elapsed time is deterministic
The clock change SHALL disable the stock GaugeTrait wall-clock timer and SHALL make rulebook buff
expiration and tick accumulation consume explicit elapsed game seconds. Reading a gauge or buff outside
an `advance()` or combat round SHALL NOT advance it.

Timed rulebook buffs SHALL use an indefinitely-lived Evennia handler entry and persist their remaining
game seconds separately, so the handler cannot schedule real-time cleanup.

#### Scenario: Real time passing does not regenerate or expire game state
- **WHEN** a gauge has a positive regen rate or a timed buff is active, and no deterministic settlement
  receives elapsed seconds
- **THEN** reading the gauge or active-buff query leaves its state unchanged

#### Scenario: A permanently active fixture is bounded by the defensive quantum cap
- **WHEN** every entity in scope has continuously active settlement work for longer than
  `MAX_SETTLEMENT_QUANTA` quanta
- **THEN** the settlement loop stops at exactly `MAX_SETTLEMENT_QUANTA` iterations, and `advance()`
  still completes (calendar advance, gauge regen, practice settlement, and boundary stages are
  unaffected by this cap)

#### Scenario: Practice settlement never participates in the quantum loop
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called
- **THEN** the `practice_settlement` stage is called exactly once with the full elapsed value
  regardless of `SETTLEMENT_QUANTUM_SECONDS` — it is never chunked into quanta the way
  `tick_buffs()`/`decay_tick()` are — and accrues `completed_whole_hours ×
PRACTICE_XP_PER_STUDY_HOUR` scaled by learning, affinity, and `growth_rate_multiplier`, once per
  entity per advance, SKIP-source only, saturating at the skill's derived tip cap and writing
  nothing when the actor's booking has been consumed or never existed. A successful SKIP advance
  of fewer than 3600 seconds consumes any booking while growing nothing (whole-hour closed form),
  and a COMMAND-source advance leaves the booking unconsumed for the actor's next SKIP advance.
  Settlement is per-entity against each entity's OWN booking — the design §11 batch note's
  contract that every member's growth comes only from that member's own declared command; the
  production SKIP callers supply the caller's present party scope, each member settled against
  its own standing booking, and no skip path clears a booking it did not settle (see
  `time-skip-commands`)
