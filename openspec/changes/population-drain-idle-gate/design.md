# Design

## Context

See `proposal.md` for the motivation.

Current code:

- `world/maps/population_drain.py`: `PopulationDrainScript.at_repeat` returns when `settings.POPULATION_DRAIN_ENABLED` is false and otherwise calls `drain_population_backlog(settings.POPULATION_DRAIN_SLICE_SECONDS)`.
- `server/conf/inputfuncs.py` defines the project's `text`, `ui_action` and `ui_sync` input functions. `text` returns early for `_IDLE_COMMAND` after `session.update_session_counters(idle=True)`. `ui_action` returns early for a non-WebClient session and for a session with no puppet; otherwise it calls `handle_ui_action(...)`.
- Evennia's `session.cmd_last` is updated only by `text`. `ui_action` never updates it, and a game played through the WebClient sends mostly UI actions, so `cmd_last` cannot be the signal.
- `server/conf/settings.py`: `_env_int(name, default)` accepts a positive integer only.

Constraints from the request: no thread or process; no wall-clock assertion in tests; the synchronous catch-up must stay correct.

## Goals / Non-Goals

**Goals:**

- One process-wide record of the last player input, written at the two ingress points.
- The periodic caller skips a repeat inside the idle window.

**Non-Goals:**

- No change to `drain_population_backlog`, `lagging_sets`, the settlement pass, the catch-up, or any owner.
- No per-session or per-account idle tracking, no persistence of the record across a reload.
- No new event and no log line for a skipped repeat.
- No change to `session.cmd_last`, the idle timeout, or `ui_sync`.

## Decisions

### D1. New module `world/rules/player_input.py`

Exact content contract:

```python
"""The process-wide time of the last player input.

Written at the two ingress points of ``server/conf/inputfuncs.py``. Read by a
background caller that must not run while a player is acting. The value is a
monotonic clock reading, held in memory only: a reload starts with no input
recorded, which reads as idle.
"""

from __future__ import annotations

import time

#: The monotonic reading of the last player input, or ``None`` before any.
_LAST_INPUT: float | None = None


def _now() -> float:
    """The monotonic clock; the one seam a test replaces."""
    return time.monotonic()


def note_player_input() -> None:
    """Record that a player sent input now."""
    global _LAST_INPUT
    _LAST_INPUT = _now()


def seconds_since_player_input() -> float | None:
    """Real seconds since the last player input; ``None`` when none was recorded."""
    if _LAST_INPUT is None:
        return None
    return _now() - _LAST_INPUT


def reset_player_input() -> None:
    """Forget the recorded input (process start state; used by tests)."""
    global _LAST_INPUT
    _LAST_INPUT = None


__all__ = ["note_player_input", "reset_player_input", "seconds_since_player_input"]
```

Why a module global: settlement and input both run on the one reactor thread, the same reason `monster_activity._ACTIVE_BATCH` and `surfaces._OUTER_ROLLBACK` are globals. Why `time.monotonic`: a wall-clock adjustment must not make the drain run early or stall.

Alternative rejected: scanning `SESSION_HANDLER` for the newest `cmd_last`. `ui_action` does not update it, and changing Evennia's counter semantics for UI actions would also change the visible idle time in `commands/localized/account.py`.

### D2. Record at ingress in `server/conf/inputfuncs.py`

Add `from world.rules.player_input import note_player_input`.

- In `text`: call `note_player_input()` on the line directly after the `_IDLE_COMMAND` early return (before `_maybe_strip_incoming_mxp`). The `txt is None` return and the idle return stay before it.
- In `ui_action`: call `note_player_input()` on the line directly before `handle_ui_action(`. The non-WebClient return and the whole `actor is None` branch stay before it.
- `ui_sync` is not edited.

### D3. The gate in `PopulationDrainScript.at_repeat`

```python
    def at_repeat(self) -> None:
        if not settings.POPULATION_DRAIN_ENABLED:
            return
        idle = player_input.seconds_since_player_input()
        if idle is not None and idle < settings.POPULATION_DRAIN_IDLE_SECONDS:
            return
        drain_population_backlog(settings.POPULATION_DRAIN_SLICE_SECONDS)
```

Import as `from world.rules import player_input` so a test can patch `player_input._now`. `drain_population_backlog` is not edited. Update the module docstring's last paragraph and the class docstring to say the caller also yields to recent input.

The comparison is `idle < window`: an input exactly one window old no longer blocks (spec scenario "Window passed").

### D4. Setting

In `server/conf/settings.py`, directly after the `POPULATION_DRAIN_SLICE_SECONDS` line:

```python
POPULATION_DRAIN_IDLE_SECONDS = _env_int("POPULATION_DRAIN_IDLE_SECONDS", 5)
```

Extend the comment block above the three existing lines with one sentence: "A repeat is skipped while a player sent input within the idle window (real seconds)."

Mirror every place the three existing names appear:

- `server/conf/test_settings.py`: add `"POPULATION_DRAIN_IDLE_SECONDS",` after `"POPULATION_DRAIN_SLICE_SECONDS",` in `_ENV_OVERRIDES`.
- `.env.example`: after `#POPULATION_DRAIN_SLICE_SECONDS=600` add a comment "Real seconds without player input before a repeat may drain. Type: positive integer. Default: 5." and the line `#POPULATION_DRAIN_IDLE_SECONDS=5`.
- `server/conf/tests/test_env_overrides/_support.py`: add the name beside each existing `POPULATION_DRAIN_SLICE_SECONDS` entry: the name map, the defaults map (`"5"`), the override cases (`("POPULATION_DRAIN_IDLE_SECONDS", "POPULATION_DRAIN_IDLE_SECONDS", "9", "9")`), the invalid values (`("POPULATION_DRAIN_IDLE_SECONDS", "0", "expected a positive integer")`) and the environment filter tuple. Find them with `grep -n POPULATION_DRAIN_SLICE_SECONDS server/conf/tests/test_env_overrides/_support.py` (five places).

Why 5 seconds: the repeat interval is 2 seconds and the observed gap between a player's actions is a few seconds, so 5 keeps a run from starting between two quick clicks while still draining during ordinary reading pauses. The value is a tuning knob; see Open Questions.

### D5. Documentation

- `docs/development/settings-and-environment.md`: add one table row after the `POPULATION_DRAIN_SLICE_SECONDS` row, same columns, written in zh-TW like its neighbours: name, env name, 整數, `5`, and the meaning (positive integer; real seconds without player input before a repeat may drain; the synchronous catch-up is unaffected).
- `docs/development/regional-monster-population.md`, section "The periodic caller": add the setting to the table (`POPULATION_DRAIN_IDLE_SECONDS` | `5` | Real seconds without player input before a repeat drains) and one paragraph: what counts as input (D2), that the record is in memory and a reload reads as idle, and that the catch-up and a direct `drain_population_backlog` call ignore it.

## Risks / Trade-offs

- [A player who acts more often than the window never lets the drain run, so the backlog grows while they play] → Intended: the debt is then paid in the next pause or by the synchronous catch-up. `population-drain-batched-runs` raises how much one idle repeat pays.
- [A run that starts just after the window can still collide with the next input] → The collision is bounded by one run's duration; the window only lowers how often it happens.
- [The record is shared process state, so one test can leak into another] → `reset_player_input()` in the `setUp` of every test class that calls `at_repeat` or the input functions (tasks 1.2, 2.2, 3.2).

## Open Questions

- The default of 5 seconds is a starting value. It can be tuned through the environment without a code change.
