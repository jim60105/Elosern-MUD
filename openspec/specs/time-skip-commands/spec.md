## Purpose

Define deterministic player commands that advance game time through the world clock.

## Requirements


### Requirement: rest <duration> parses an explicit duration and advances the clock by exactly that
much
`commands/skip.py::CmdRest` SHALL parse an explicit duration argument (e.g., `"1h"`, `"30m"`) into a
concrete number of seconds and, when `evaluate_skip_safety()` returns `None`, call
`WorldClock.advance(seconds, AdvanceSource.SKIP, entities=[caller])` with exactly that parsed value —
never a computed or capped value.

#### Scenario: rest 1h advances the clock by exactly 3600 seconds
- **WHEN** a safe actor issues `rest 1h`
- **THEN** `WorldClock.advance()` is called with `seconds == 3600`

#### Scenario: An unparseable duration is rejected before any safety check or clock advance
- **WHEN** `rest` is issued with an argument that does not match a valid duration shape
- **THEN** the command rejects with a parse error, calls neither `evaluate_skip_safety()` nor
  `WorldClock.advance()`

#### Scenario: rest is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `rest 1h`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called

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
