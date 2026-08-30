## MODIFIED Requirements

### Requirement: rest <duration> parses an explicit duration and advances the clock by that much, capped at the configured maximum
`commands/skip.py::CmdRest` SHALL parse an explicit duration argument (e.g., `"1h"`, `"30m"`)
into a concrete number of seconds, cap that value at `MAX_SKIP_SECONDS`
(`rulebook/clock.yaml`'s `max_sleep_seconds`), and, when `evaluate_skip_safety()` returns `None`,
call `WorldClock.advance(seconds, AdvanceSource.SKIP, entities=[caller])` with exactly the capped
value. The syntax SHALL accept the optional declared-practice clause
`rest <duration> practice <skill>` (the design's `skip <hours> [practice <skill>]` surface on the
mounted duration command): an accepted booking is recorded on the caller before the advance, and
the clock's `practice_settlement` stage is its sole writer (see `settlement-stage-order`). An
unlabeled duration and `rest` without the clause are explicit rest: clock advance with zero
growth. The clause SHALL be preflighted BEFORE any clock advance: the skill must be ACTIVE, be in
the caller's `owned_keys()`, and not be saturated at its derived tip cap, rejecting with the
stable reason codes `PRACTICE_SKILL_UNKNOWN` (unknown key, non-ACTIVE, or unowned) or
`PRACTICE_SKILL_CAPPED` with zero clock advance and no booking recorded — a skip never
half-applies.

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
- **THEN** `WorldClock.advance()` is called with `seconds == 28800` and the `practice_settlement` stage accrues `8 × PRACTICE_XP_PER_STUDY_HOUR` scaled by learning, affinity, and the growth buff onto `fire_arrow`, saturated at its tip cap

#### Scenario: A capped booking rejects with zero clock advance
- **WHEN** the actor's `fire_arrow` has saturated at its derived tip cap and they issue `rest 8h practice fire_arrow`
- **THEN** the command reports `PRACTICE_SKILL_CAPPED`, `WorldClock.advance()` is never called, and no practice state changes

#### Scenario: An unknown or unowned booking skill rejects with zero clock advance
- **WHEN** an actor issues `rest 1h practice not_a_skill`, or practices a PASSIVE skill, or a spell they do not own
- **THEN** the command reports `PRACTICE_SKILL_UNKNOWN`, `WorldClock.advance()` is never called, and no booking is recorded

#### Scenario: Plain rest grows nothing
- **WHEN** a safe actor issues `rest 8h` with no practice clause
- **THEN** the clock advances 28800 seconds and no `skill_proficiency` value changes

#### Scenario: rest is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `rest 1h`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called
