## MODIFIED Requirements

### Requirement: rest <duration> parses an explicit duration and advances the clock by that much, capped at the configured maximum
`commands/skip.py::CmdRest` SHALL parse an explicit duration argument (e.g., `"1h"`, `"30m"`) into a
concrete number of seconds, cap that value at `MAX_SKIP_SECONDS` (`rulebook/clock.yaml`'s
`max_sleep_seconds`), and, when `evaluate_skip_safety()` returns `None`, call
`WorldClock.advance(seconds, AdvanceSource.SKIP, entities=[caller])` with exactly the capped value.

#### Scenario: rest 1h advances the clock by exactly 3600 seconds
- **WHEN** a safe actor issues `rest 1h`
- **THEN** `WorldClock.advance()` is called with `seconds == 3600`

#### Scenario: rest longer than the configured maximum is capped
- **WHEN** a safe actor issues `rest 1000000000d` (or any duration exceeding `max_sleep_seconds`)
- **THEN** `WorldClock.advance()` is called with `seconds == MAX_SKIP_SECONDS`, never the uncapped parsed value

#### Scenario: An unparseable duration is rejected before any safety check or clock advance
- **WHEN** `rest` is issued with an argument that does not match a valid duration shape
- **THEN** the command rejects with a parse error, calls neither `evaluate_skip_safety()` nor
  `WorldClock.advance()`

#### Scenario: rest is blocked by the safety gate
- **WHEN** a safe-check-failing actor issues `rest 1h`
- **THEN** `evaluate_skip_safety()`'s reason is reported to the player and `WorldClock.advance()` is
  never called
