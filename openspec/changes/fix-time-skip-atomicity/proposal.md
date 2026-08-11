## Why

Telnet `rest` accepts any parseable duration with no cap, and `WorldClock.advance` writes character gauges/daily counters before running an unbounded per-day loop and only then persists the world tick. A forced termination leaves character state advanced while the tick stands still (audit finding F04); without termination the same input blocks the reactor for an unbounded period.

## What Changes

- Bound Telnet `rest` at the configured skip maximum (`max_sleep_seconds` in `rulebook/clock.yaml`), matching `sleep` and the Web bound.
- Make `WorldClock.advance` all-or-nothing: character/entity writes and the world-tick persist commit together (or the tick persists first with bounded, chunked settlement), so no partial save can survive a restart.

## Capabilities

### Modified Capabilities

- `time-skip-commands`: `rest` duration is capped at the configured maximum instead of "never a capped value".
- `world-clock`: `advance()` persists atomically and is bounded per call.

## Impact

- `commands/skip.py::CmdRest`, `world/rules/time_skip.py` (cap), `world/rules/clock.py` (atomic advance), `world/rules/sexual_state.py`/trait writes (within the transaction), tests for skip commands and clock settlement.
