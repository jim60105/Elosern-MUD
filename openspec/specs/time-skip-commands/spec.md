## Purpose

Define deterministic player commands that advance game time through the world clock.

## Requirements

### Requirement: rest <duration> parses an explicit duration and advances the clock by that much, capped at the configured maximum
`commands/skip.py::CmdRest` SHALL parse a duration into seconds, capped at `MAX_SKIP_SECONDS` (`max_sleep_seconds`). When `evaluate_skip_safety()` returns `None`, it SHALL call `WorldClock.advance(seconds, AdvanceSource.SKIP, entities)` for only the actual interval before the earliest interruption boundary, `entities` being the present party scope. Every positive-duration SKIP advance SHALL settle each eligible awake in-scope member's own booking; no skip path clears an unsettled booking.

#### Scenario: rest settles the present party
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake commander with no earlier relevant boundary standing with companion 艾拉 issues `rest 1h`
- **THEN** `WorldClock.advance()` is called once with `seconds == 3600` and entities exactly the
  commander followed by 艾拉

#### Scenario: A possessed companion rests for the same party scope
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake possessed companion with no earlier relevant boundary issues `rest 1h` while the commander and 艾拉 are present
- **THEN** `WorldClock.advance()` receives the same scope as the commander's own `rest`: the
  commander followed by 艾拉

#### Scenario: rest 1h advances the clock by exactly 3600 seconds
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake actor with no earlier relevant boundary issues `rest 1h`
- **THEN** `WorldClock.advance()` is called with `seconds == 3600`

#### Scenario: rest longer than the configured maximum is capped
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake actor with no earlier relevant boundary issues `rest 1000000000d` (or any duration exceeding `max_sleep_seconds`)
- **THEN** `WorldClock.advance()` is called with `seconds == MAX_SKIP_SECONDS`, never the uncapped
  parsed value

#### Scenario: An unparseable duration is rejected before any safety check or clock advance
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and `rest` is issued with an argument that does not match a valid duration shape
- **THEN** the command rejects with a parse error, calls neither `evaluate_skip_safety()` nor
  `WorldClock.advance()`

#### Scenario: A valid booking settles hourly practice with the advance
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake actor with no earlier relevant boundary owning `fire_arrow` issues `rest 8h practice fire_arrow`
- **THEN** the caller's booking is recorded, `WorldClock.advance()` is called with `seconds == 28800`, and the `practice_settlement` stage accrues `8 × PRACTICE_XP_PER_STUDY_HOUR` scaled by learning, affinity, and the growth buff onto `fire_arrow`, saturated at its tip cap

#### Scenario: A capped booking rejects with zero clock advance
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and the actor's `fire_arrow` has saturated at its derived tip cap and they issue `rest 8h practice fire_arrow`
- **THEN** the command reports `PRACTICE_SKILL_CAPPED`, `WorldClock.advance()` is never called, and no practice state changes

#### Scenario: An unknown or unowned booking skill rejects with zero clock advance
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and an actor issues `rest 1h practice not_a_skill`, or practices a PASSIVE skill, or a spell they do not own
- **THEN** the command reports `PRACTICE_SKILL_UNKNOWN`, `WorldClock.advance()` is never called,
  and the caller's previous booking (if any) is left unchanged

#### Scenario: A plain rest settles standing bookings
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and the commander booked 艾拉's `healing_light` earlier and then issues `rest 2h` with no practice clause while 艾拉 is present
- **THEN** the clock advances 7200 seconds, 艾拉's `healing_light` grows by two study hours, and 艾拉's booking is consumed

#### Scenario: Plain rest grows nothing
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe awake actor with no earlier relevant boundary with no standing booking in the present party issues `rest 8h` with no practice clause
- **THEN** the clock advances 28800 seconds and no `skill_proficiency` value changes

#### Scenario: rest is blocked by the safety gate
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a safe-check-failing actor issues `rest 1h`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called

#### Scenario: The syntax accepts the optional declared-practice clause
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and the `rest` syntax is parsed
- **THEN** it SHALL accept the optional declared-practice clause
  `rest <duration> practice <skill>`, which books the caller's practice before the advance, and the
  clock's `practice_settlement` stage is its sole writer (see `settlement-stage-order`)

#### Scenario: The practice clause is preflighted before any clock advance
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a `rest <duration> practice <skill>` clause is submitted
- **THEN** the skill must be ACTIVE, be in the caller's `owned_keys()`, and not be saturated at its
  derived tip cap, checked BEFORE any clock advance; rejection reports the stable reason codes
  `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED` with zero clock advance — a skip never
  half-applies

#### Scenario: A rolled-back skip restores every booking
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a SKIP advance raises after settlement started for a party with two standing bookings
- **THEN** both bookings and both skills' proficiency equal their pre-advance values and the tick is unchanged

#### Scenario: An unlabeled adapter skip clears a rolled-back booking before advancing
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a rolled-back advance has restored a standing `practice_booking` and the accepted
  `explore.wait` adapter (or `sleep`/`wait until`) performs its SKIP advance
- **THEN** the restored booking is still standing before the advance and is settled (consumed) by
  that advance for its eligible awake member, so no booking is cleared without being settled

#### Scenario: A plain rest clears a stale rolled-back booking
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a caller whose standing `practice_booking` was restored by an earlier rolled-back
  advance issues `rest 8h` with no practice clause
- **THEN** the clock advances 28800 seconds, the booking is settled by that advance (eight study
  hours on the booked skill) and no booking remains after the command

#### Scenario: An unlabeled duration or clause-less rest is explicit rest
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and a duration is unlabeled, or `rest` is issued without the practice clause
- **THEN** the result is a clock advance that records no new booking and settles only the present
  members' standing bookings

#### Scenario: After the safety gate passes, the command owns the booking state outright
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and the safety gate has passed for a `rest` invocation
- **THEN** an accepted clause records the caller's booking (replacing a previous one), a clause-less
  rest records nothing, and a rejected clause leaves the caller's previous booking unchanged

#### Scenario: Every accepted unlabeled skip clears stale bookings before advancing
- **WHEN** no earlier forced-sleep, wake or interactive-event boundary intervenes and `sleep`, `wait until`, or the `advance_skip()` helper behind the WebClient `explore.wait`
  adapter performs an accepted unlabeled SKIP advance
- **THEN** it clears no booking before the advance; every eligible awake in-scope member's standing booking is
  settled by the advance itself through the clock's practice stage

### Requirement: sleep computes its own duration from gauge regen, capped at a configured maximum
Voluntary sleep SHALL select only the named body (default acting body), take no duration argument, and target full HP/MP/SP and mental reserve under existing skip bounds. Safe sleep SHALL commit posture at zero elapsed time, offer control handoff, then advance only on explicit continuation up to the first relevant boundary.

#### Scenario: Full gauges with low reserve
- **WHEN** a safe actor has full HP/MP/SP and 180000 reserve units and explicitly continues sleep with no earlier boundary
- **THEN** its recovery interval is 15000 seconds, not zero

#### Scenario: Sleep duration matches the slowest-regenerating gauge, when under the cap
- **WHEN** a safe actor needs 1200, 600 and 900 gauge seconds and at most 1200 reserve recovery seconds
- **THEN** uninterrupted explicit continuation targets 1200 seconds

#### Scenario: Sleep duration is capped at MAX_SLEEP_SECONDS
- **WHEN** full recovery would exceed the configured maximum
- **THEN** requested continuation is capped by the existing maximum and may interrupt earlier

#### Scenario: No elapsed entry
- **WHEN** a possessed companion enters voluntary sleep and an awake owner is available
- **THEN** only companion posture commits; return-to-owner is offered before recovery, cancel advances zero and reports no completed sleep

#### Scenario: An actor already at full hp/mp/sp sleeps for zero seconds
- **WHEN** a safe body is full in every gauge and reserve
- **THEN** no elapsed recovery is invented; entry alone offers no dream

#### Scenario: sleep is blocked by the safety gate
- **WHEN** existing skip safety rejects the request
- **THEN** neither voluntary posture entry nor elapsed recovery commits

### Requirement: wait until <daypart> computes seconds to the next occurrence of a named daypart
`commands/skip.py::CmdWaitUntil` SHALL parse a named daypart (`midnight`, `dawn`, `noon`, `dusk`, from `rulebook/clock.yaml`'s `dayparts` mapping) and compute the seconds from the current `WorldClock.calendar` state to the next future occurrence of that daypart's hour, always strictly positive: a request matching the current hour resolves to the following day's occurrence. That interval SHALL be the request limit; only time to the earliest relevant boundary commits.

#### Scenario: Waiting for a future daypart today computes the same-day interval
- **WHEN** no earlier relevant boundary intervenes and the current calendar hour is `2` and a safe actor issues `wait until dawn` (`dawn == 6`)
- **THEN** `WorldClock.advance()` is called with `seconds` equal to the exact remaining time until
  hour `6` today

#### Scenario: Waiting for a daypart already passed today computes tomorrow's occurrence
- **WHEN** no earlier relevant boundary intervenes and the current calendar hour is `10` and a safe actor issues `wait until dawn` (`dawn == 6`)
- **THEN** `WorldClock.advance()` is called with `seconds` equal to the exact remaining time until
  hour `6` on the following day, not a negative or zero value

#### Scenario: An unrecognized daypart is rejected before any safety check or clock advance
- **WHEN** `wait until` is issued with a daypart name absent from `rulebook/clock.yaml`'s `dayparts`
  mapping
- **THEN** the command rejects with a named error, calling neither `evaluate_skip_safety()` nor
  `WorldClock.advance()`

#### Scenario: wait until is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `wait until dawn`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called

### Requirement: Every time-skip command reports the events that came due
`commands/skip.py`'s three commands SHALL render a summary of the `ScheduledEvent` list
`WorldClock.advance()` returns (including a daily-reset indication when a day boundary was crossed)
alongside the elapsed duration, using no LLM call.

#### Scenario: A skip crossing a day boundary reports the reset
- **WHEN** a safe actor's `rest`/`sleep`/`wait` call causes `advance()` to cross a midnight boundary
- **THEN** the command's rendered output reflects that a new day began, using only the returned
  `ScheduledEvent` list and plain text — no LLM call is made

#### Scenario: A skip with no due events reports the elapsed duration alone
- **WHEN** a safe actor's skip causes `advance()` to return an empty `ScheduledEvent` list
- **THEN** the command still reports how much time passed, with no error and no LLM call

sed: -e 表示式 #1，字元 2: 未預期的「,」

### Requirement: Interruptible skips stop at the earliest relevant boundary
Wait, sleep and eligible study SHALL stop at the earliest involved forced-sleep entry, natural wake target or registered interactive event. Only elapsed time SHALL commit; the unperformed remainder SHALL be discarded. Noninteractive fatigue-stage crossings SHALL preserve exact consumption without forcing an early return.

#### Scenario: First wake
- **WHEN** a forced sleeper at zero is involved in a requested 10000-second safe wait
- **THEN** exactly 6000 seconds commits, the undefeated sleeper wakes at 72000, control returns and 4000 seconds is discarded

#### Scenario: First collapse
- **WHEN** an awake companion has 2400 units during a requested 1200-second wait
- **THEN** exactly 600 seconds commits, that companion enters forced sleep and the remainder is discarded

#### Scenario: Registered event
- **WHEN** an actual registered interactive event is due in 37 seconds before any physiological boundary
- **THEN** exactly 37 seconds commits and the event is published without a random ambush roll

#### Scenario: No replay
- **WHEN** a completed interrupted result is retried with the same accepted operation identity
- **THEN** the committed interval is not replayed; any later advance requires a new explicit action

### Requirement: Recovery waiting preserves skip safety
An authenticated player with no awake candidate SHALL retain non-acting status and explicit outside-combat recovery waiting. Safe recovery SHALL stop at the first eligible wake. Active combat or a present hostile SHALL still block skips; forced-sleep entry itself SHALL grant no skip or safety.

#### Scenario: Unsafe collapse
- **WHEN** an accepted indivisible action collapses a body in a hostile room
- **THEN** posture commits with the action but a later recovery wait is refused with existing unsafe reason and zero extra time

#### Scenario: Safe all asleep
- **WHEN** the party has no awake eligible member in a safe room
- **THEN** the account can inspect and explicitly wait until the first eligible wake without background time or sleeper actions
