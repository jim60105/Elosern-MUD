## MODIFIED Requirements

### Requirement: Settlement stages run in the fixed order regen, buffs, sexual decay, practice settlement,
daily resets, then the five declared world-event seams
`world/rules/clock.py` SHALL define a single, ordered stage sequence — `gauge_regen`, `buff_ticks`,
`sexual_decay`, `practice_settlement`, `daily_resets`, `caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`npc_schedules`, `instance_reclamation` — matching design doc §6.5's four built stages plus
`practice_settlement` (the declared-practice writer owned directly by
`world/rules/clock.py`, inserted between `sexual_decay` and
`daily_resets`) plus `instance_reclamation` (change 14's `reclaim_due_instances()`, appended after
`npc_schedules` as the final stage), and SHALL execute every `advance()` call's stages in this order
with no configuration or call-site override capable of changing it.

#### Scenario: The stage order is exactly the fixed sequence, including practice_settlement and instance_reclamation
- **WHEN** the settlement stage sequence is inspected
- **THEN** it is exactly `("gauge_regen", "buff_ticks", "sexual_decay", "practice_settlement", "daily_resets",
  "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules", "instance_reclamation")`, in
  that order, with no duplicate or missing entry

#### Scenario: Transposing any of the four ordered stages is mechanically detected
- **WHEN** a test asserts `"buff_ticks"` appears strictly before `"sexual_decay"` and strictly after
  `"gauge_regen"` in the stage sequence, and `"practice_settlement"` appears strictly between `"sexual_decay"`
  and `"daily_resets"`
- **THEN** the assertion fails immediately if the stage sequence is ever edited to place any of these
  stages out of that relative order

#### Scenario: A transposed regen/buff order produces a different, incorrect final hp value
- **WHEN** a fixture entity starts with `hp` within one regen-step of its gauge `max`, an active
  `poisoned` buff, and a fixed elapsed time is settled once under the correct order (`gauge_regen`
  before `buff_ticks`) and once under a deliberately transposed order (`buff_ticks` before
  `gauge_regen`) constructed in the same test
- **THEN** the two resulting final `hp` values differ, because the regen-first order clamps against
  `max` on a step the buff-first order does not, proving the order has an observable, not merely
  documented, consequence

#### Scenario: No arithmetic transposition proof exists for practice settlement, because it shares no
resource with its neighbors
- **WHEN** `practice_settlement`'s data dependencies are inspected (it reads the caller's
  declared-practice booking and race/buff state, and writes only `skill_proficiency`) against `sexual_decay`'s (`entity.sexual`'s ordered-level fields) and
  `daily_resets`'s (`entity.sexual.climax_today` only)
- **THEN** no field is written by both `practice_settlement` and either neighbor, so the
  structural check above
  is `practice_settlement`'s only mechanical safeguard against transposition — this is a verified property, not
  an unexamined gap

#### Scenario: instance_reclamation running after quest_deadlines and npc_schedules reclaims within
one advance() call; running before either leaves the room existing for one extra call
- **WHEN** a test registers a synthetic `quest_deadlines` source that, when its deadline comes due
  within `(start_tick, end_tick]`, calls `unpin_instance_room()` on a target `InstanceRoom`, and that
  room is simultaneously due for TTL reclamation, unoccupied, unnamed, and pinned by exactly the
  reason the synthetic source releases
- **THEN** under the declared order (`quest_deadlines` before `instance_reclamation`), a single
  `advance()` call across both boundaries results in the room no longer existing; a test that
  constructs the transposed order (`instance_reclamation` before `quest_deadlines`) in isolation shows
  the same single `advance()` call leaves the room still existing, deferred, requiring a second call —
  an existence-differs proof, not merely a differently-ordered but equivalent outcome

#### Scenario: instance_reclamation position is not itself proof against every possible transposition,
and this is a stated, not silent, limitation
- **WHEN** `instance_reclamation`'s data dependencies are inspected (reads/writes `InstanceRoom.db.
  expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`, none of which any other stage reads
  or writes) against `caravan_arrivals`/`shop_hours`/`npc_schedules`, none of which has a registered
  source in this project's shipped codebase as of this change (and `npc_schedules`, once
  `instance_reclamation`'s own occupancy check was corrected during rubber-duck review to gate on
  `PlayerCharacter` rather than any `LivingEntity`, no longer has any concrete releasing mechanism this
  design depends on either — see design.md D-3's own correction note)
- **THEN** the transposition proof above is the sole mechanical safeguard for `instance_reclamation`'s
  position relative to `quest_deadlines` specifically; its position relative to `caravan_arrivals`/
  `shop_hours`/`npc_schedules` (all three still unregistered, no-op seams, and none with a concrete
  releasing story this design leans on) has no equivalent proof and is justified by "last, so nothing
  after it could still need the room" reasoning alone (design.md D-3), not by an arithmetic
  counter-example against any of the three

### Requirement: buff_ticks, sexual_decay, and practice settlement are skipped for combat-sourced advances
`world/rules/clock.py`'s settlement stage runner SHALL skip the `buff_ticks`, `sexual_decay`, and
`practice_settlement` stages entirely when `advance()` is called with `AdvanceSource.COMBAT`: `buff_ticks` and
`sexual_decay` because change 9's `run_round()` already applies both once per round as part of combat's
own per-round upkeep; `practice_settlement` because declared practice is a downtime concept that must
never settle during a fight. Every other stage (`gauge_regen`, `daily_resets`, and the four declared world-event
stages) SHALL run regardless of `AdvanceSource`.

#### Scenario: A combat-sourced advance does not double-tick an active buff
- **WHEN** a `poisoned` combatant's fight is resolved via `run_round()` for `N` rounds (each round
  already calling `tick_buffs()` once per change 9's own upkeep), and the resulting `total_seconds` is
  then passed to `WorldClock.advance(total_seconds, AdvanceSource.COMBAT, entities)`
- **THEN** the combatant's `hp` reflects exactly `N` poison ticks' worth of damage, not `2N`

#### Scenario: A combat-sourced advance still applies gauge regen
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called
- **THEN** every entity in `entities`' `hp`/`mp`/`sp` gauges reflect regen for the full `seconds`
  elapsed, unaffected by the `AdvanceSource.COMBAT` gate

#### Scenario: A combat-sourced advance performs no practice settlement
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called for an entity carrying
  a declared-practice booking that would settle under `AdvanceSource.SKIP`
- **THEN** no `skill_proficiency` or other practice state changes as a result of the call, and the
  booking survives untouched for the actor's next SKIP-sourced advance

#### Scenario: A command- or skip-sourced advance runs the full stage list
- **WHEN** `advance(seconds, AdvanceSource.COMMAND, entities)` or `advance(seconds,
  AdvanceSource.SKIP, entities)` is called
- **THEN** `buff_ticks` and `sexual_decay` both run for every entity in `entities`, unlike the
  `AdvanceSource.COMBAT` case

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
  only production SKIP callers supply a single-entity scope, and every unlabeled skip path
  clears stale bookings before advancing (see `time-skip-commands`)

## REMOVED Requirements
