## Purpose

Define deterministic player commands that advance game time through the world clock.

## Requirements

### Requirement: rest <duration> parses an explicit duration and advances the clock by that much, capped at the configured maximum
`commands/skip.py::CmdRest` SHALL parse an explicit duration argument into seconds, cap it at
`MAX_SKIP_SECONDS` (`rulebook/clock.yaml`'s `max_sleep_seconds`), and, when
`evaluate_skip_safety()` returns `None`, call
`WorldClock.advance(seconds, AdvanceSource.SKIP, entities)` with exactly that capped value,
where `entities` is the caller's present party scope. Every SKIP advance SHALL settle each
in-scope member's own standing practice booking; no skip path clears a booking it did not settle.

#### Scenario: rest settles the present party
- **WHEN** a safe commander standing with companion 艾拉 issues `rest 1h`
- **THEN** `WorldClock.advance()` is called once with `seconds == 3600` and entities exactly the
  commander followed by 艾拉

#### Scenario: A possessed companion rests for the same party scope
- **WHEN** a safe possessed companion issues `rest 1h` while the commander and 艾拉 are present
- **THEN** `WorldClock.advance()` receives the same scope as the commander's own `rest`: the
  commander followed by 艾拉

#### Scenario: rest 1h advances the clock by exactly 3600 seconds
- **WHEN** a safe actor issues `rest 1h`
- **THEN** `WorldClock.advance()` is called with `seconds == 3600`

#### Scenario: rest longer than the configured maximum is capped
- **WHEN** a safe actor issues `rest 1000000000d` (or any duration exceeding `max_sleep_seconds`)
- **THEN** `WorldClock.advance()` is called with `seconds == MAX_SKIP_SECONDS`, never the uncapped
  parsed value

#### Scenario: An unparseable duration is rejected before any safety check or clock advance
- **WHEN** `rest` is issued with an argument that does not match a valid duration shape
- **THEN** the command rejects with a parse error, calls neither `evaluate_skip_safety()` nor
  `WorldClock.advance()`

#### Scenario: A valid booking settles hourly practice with the advance
- **WHEN** a safe actor owning `fire_arrow` issues `rest 8h practice fire_arrow`
- **THEN** the caller's booking is recorded, `WorldClock.advance()` is called with `seconds == 28800`, and the `practice_settlement` stage accrues `8 × PRACTICE_XP_PER_STUDY_HOUR` scaled by learning, affinity, and the growth buff onto `fire_arrow`, saturated at its tip cap

#### Scenario: A capped booking rejects with zero clock advance
- **WHEN** the actor's `fire_arrow` has saturated at its derived tip cap and they issue `rest 8h practice fire_arrow`
- **THEN** the command reports `PRACTICE_SKILL_CAPPED`, `WorldClock.advance()` is never called, and no practice state changes

#### Scenario: An unknown or unowned booking skill rejects with zero clock advance
- **WHEN** an actor issues `rest 1h practice not_a_skill`, or practices a PASSIVE skill, or a spell they do not own
- **THEN** the command reports `PRACTICE_SKILL_UNKNOWN`, `WorldClock.advance()` is never called,
  and the caller's previous booking (if any) is left unchanged

#### Scenario: A plain rest settles standing bookings
- **WHEN** the commander booked 艾拉's `healing_light` earlier and then issues `rest 2h` with no practice clause while 艾拉 is present
- **THEN** the clock advances 7200 seconds, 艾拉's `healing_light` grows by two study hours, and 艾拉's booking is consumed

#### Scenario: Plain rest grows nothing
- **WHEN** a safe actor with no standing booking in the present party issues `rest 8h` with no practice clause
- **THEN** the clock advances 28800 seconds and no `skill_proficiency` value changes

#### Scenario: rest is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `rest 1h`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called

#### Scenario: The syntax accepts the optional declared-practice clause
- **WHEN** the `rest` syntax is parsed
- **THEN** it SHALL accept the optional declared-practice clause
  `rest <duration> practice <skill>`, which books the caller's practice before the advance, and the
  clock's `practice_settlement` stage is its sole writer (see `settlement-stage-order`)

#### Scenario: The practice clause is preflighted before any clock advance
- **WHEN** a `rest <duration> practice <skill>` clause is submitted
- **THEN** the skill must be ACTIVE, be in the caller's `owned_keys()`, and not be saturated at its
  derived tip cap, checked BEFORE any clock advance; rejection reports the stable reason codes
  `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED` with zero clock advance — a skip never
  half-applies

#### Scenario: A rolled-back skip restores every booking
- **WHEN** a SKIP advance raises after settlement started for a party with two standing bookings
- **THEN** both bookings and both skills' proficiency equal their pre-advance values and the tick is unchanged

#### Scenario: An unlabeled adapter skip clears a rolled-back booking before advancing
- **WHEN** a rolled-back advance has restored a standing `practice_booking` and the accepted
  `explore.wait` adapter (or `sleep`/`wait until`) performs its SKIP advance
- **THEN** the restored booking is still standing before the advance and is settled (consumed) by
  that advance for its member, so no booking is cleared without being settled

#### Scenario: A plain rest clears a stale rolled-back booking
- **WHEN** a caller whose standing `practice_booking` was restored by an earlier rolled-back
  advance issues `rest 8h` with no practice clause
- **THEN** the clock advances 28800 seconds, the booking is settled by that advance (eight study
  hours on the booked skill) and no booking remains after the command

#### Scenario: An unlabeled duration or clause-less rest is explicit rest
- **WHEN** a duration is unlabeled, or `rest` is issued without the practice clause
- **THEN** the result is a clock advance that records no new booking and settles only the present
  members' standing bookings

#### Scenario: After the safety gate passes, the command owns the booking state outright
- **WHEN** the safety gate has passed for a `rest` invocation
- **THEN** an accepted clause records the caller's booking (replacing a previous one), a clause-less
  rest records nothing, and a rejected clause leaves the caller's previous booking unchanged

#### Scenario: Every accepted unlabeled skip clears stale bookings before advancing
- **WHEN** `sleep`, `wait until`, or the `advance_skip()` helper behind the WebClient `explore.wait`
  adapter performs an accepted unlabeled SKIP advance
- **THEN** it clears no booking before the advance; every in-scope member's standing booking is
  settled by the advance itself through the clock's practice stage

### Requirement: sleep computes its own duration from gauge regen, capped at a configured maximum
`commands/skip.py::CmdSleep` SHALL take no duration argument. When `evaluate_skip_safety()` returns
`None`, it SHALL compute the number of seconds needed for every one of the actor's `hp`/`mp`/`sp`
gauges to reach its `max` at its own configured regen `rate`, take the maximum such value across the
three gauges, cap it at `MAX_SLEEP_SECONDS` (`rulebook/clock.yaml`), and advance the clock by that
computed value.

#### Scenario: Sleep duration matches the slowest-regenerating gauge, when under the cap
- **WHEN** a safe actor issues `sleep`, and computing time-to-full for `hp`/`mp`/`sp` yields `1200`,
  `600`, and `900` seconds respectively, all under `MAX_SLEEP_SECONDS`
- **THEN** `WorldClock.advance()` is called with `seconds == 1200` (the largest of the three)

#### Scenario: Sleep duration is capped at MAX_SLEEP_SECONDS
- **WHEN** a safe actor issues `sleep` and the largest computed time-to-full across `hp`/`mp`/`sp`
  exceeds `MAX_SLEEP_SECONDS`
- **THEN** `WorldClock.advance()` is called with `seconds == MAX_SLEEP_SECONDS`, not the larger
  uncapped value

#### Scenario: An actor already at full hp/mp/sp sleeps for zero seconds
- **WHEN** a safe actor issues `sleep` while every gauge is already at its `max`
- **THEN** `WorldClock.advance()` is called with `seconds == 0`

#### Scenario: sleep is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `sleep`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and no regen computation or
  `WorldClock.advance()` call occurs

### Requirement: wait until <daypart> computes seconds to the next occurrence of a named daypart
`commands/skip.py::CmdWaitUntil` SHALL parse a named daypart (`midnight`, `dawn`, `noon`, `dusk`, from
`rulebook/clock.yaml`'s `dayparts` mapping) and compute the number of seconds from the current
`WorldClock.calendar` state to the next future occurrence of that daypart's hour, always resolving to
a strictly positive value (a request matching the current hour resolves to the following day's
occurrence, not zero).

#### Scenario: Waiting for a future daypart today computes the same-day interval
- **WHEN** the current calendar hour is `2` and a safe actor issues `wait until dawn` (`dawn == 6`)
- **THEN** `WorldClock.advance()` is called with `seconds` equal to the exact remaining time until
  hour `6` today

#### Scenario: Waiting for a daypart already passed today computes tomorrow's occurrence
- **WHEN** the current calendar hour is `10` and a safe actor issues `wait until dawn` (`dawn == 6`)
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
