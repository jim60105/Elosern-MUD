# Design

## Context

See proposal.md - Why. Facts verified in the tree:

- `world/observability/api.py`: `log_debug` writes nothing unless `settings.VERBOSE` is true. The caller segment is taken from the frame that calls `log_*`, so a wrapper function around the facade would report the wrapper as caller.
- `tools/observability_lint.py` recognises facade calls by the names `log_debug`/`log_info`/`log_warn`/`log_error` and requires `context=`. `world/observability/` is on its whitelist.
- Emit sites, all scheduled with `transaction.on_commit`:
  - `world/maps/monster_activity.py::_emit_decided` → `monster_activity_decided`
  - `world/maps/monster_activity.py::_begin_group_journey` → `monster_departed` (and `monster_escape_resolved` when `emit_escape`)
  - `world/maps/monster_activity.py::_arrive` → `monster_arrived`
  - `world/maps/monster_activity.py::_settle_due_journeys` → `monster_arrival_deferred`
  - `world/rules/fatigue.py::settle_fatigue_intervals` → `fatigue_transition`
- `world/maps/population_lifecycle.py::settle_population_lifecycle` is the one pass. Inside it, `_settle_population_at` runs the field contact block under `monster_activity.unbatched_state_writes()`.
- `on_commit` callbacks run after the outermost transaction commits, when the pass is over. The level must therefore be chosen when the callback is scheduled, not when it runs.
- Tests assert events by patching the caller module's binding (`patch.object(activity_owner, "log_info")`, `patch("world.rules.fatigue.log_info")`).

## Goals / Non-Goals

**Goals:**

- One counting scope, opened only by the lifecycle pass.
- No change to event names or context keys of the five events.

**Non-Goals:**

- No new facade function and no change to `world/observability/api.py`, `render.py`, `recent.py`.
- No change to `ScheduledEvent` lists returned by settlement.
- No change to `monster_population_wave`, `monster_population_recovery_blocked`, `monster_site_*`, `monster_escape_resolved`, `field_contact_*`, `clock_advance`.
- No log rotation or log-size setting.

## Decisions

### D1. Tally module

Create `world/observability/tally.py` (standard library only):

```python
"""Counting scope for per-entity world-maintenance events."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

MAINTENANCE_EVENTS: frozenset[str] = frozenset(
    {
        "fatigue_transition",
        "monster_activity_decided",
        "monster_departed",
        "monster_arrived",
        "monster_arrival_deferred",
    }
)

_ACTIVE: dict[str, int] | None = None


@contextmanager
def maintenance_tally() -> Iterator[dict[str, int]]:
    """Open the counting scope; a nested call reuses the open scope."""


@contextmanager
def suspended_maintenance_tally() -> Iterator[None]:
    """Run the enclosed work with no scope, then resume the same scope."""


def note_maintenance(event: str) -> bool:
    """Count ``event`` in the open scope and return True; return False with no scope."""
```

`note_maintenance` raises `ValueError` for a name outside `MAINTENANCE_EVENTS`. `maintenance_tally` always clears `_ACTIVE` in `finally` when it opened the scope. The module state is a plain module global, the same pattern as `monster_activity._ACTIVE_BATCH`: settlement is synchronous on the reactor thread.

Alternative rejected: a `log_maintenance()` facade function. It would break the caller-segment frame contract and the lint's call recognition.

### D2. Emit sites choose the level when scheduling

Each of the five sites replaces its single `transaction.on_commit(lambda ...: log_info(EVENT, context=context))` with two literal branches:

```python
if note_maintenance("monster_arrived"):
    transaction.on_commit(
        lambda context=context: log_debug("monster_arrived", context=context)
    )
else:
    transaction.on_commit(
        lambda context=context: log_info("monster_arrived", context=context)
    )
```

Import `log_debug` by name next to the existing `log_info` import, and `from world.observability.tally import note_maintenance`. Keep the context dictionaries unchanged. In `_begin_group_journey`, when `emit_escape` is true do not call `note_maintenance`: schedule `monster_departed` and `monster_escape_resolved` at info exactly as today (an escape is a combat outcome). In `settle_fatigue_intervals` the wake-observer `on_commit` is unchanged.

### D3. The pass opens the scope and schedules the summary

In `settle_population_lifecycle`, wrap the existing `with (monster_activity.batched_state_writes(...), regional_population.reused_living_presence()):` block:

```python
with maintenance_tally() as counts:
    with (...existing two managers...):
        ...existing body...
    if counts:
        context = {"tick_from": int(start_tick), "tick_to": int(end_tick), **dict(sorted(counts.items()))}
        transaction.on_commit(
            lambda context=context: log_info("population_maintenance_settled", context=context)
        )
```

`population_lifecycle.py` gains `from django.db import transaction` and `from world.observability import log_info`. The summary is scheduled inside the advance's transaction, so a rolled-back advance discards it together with the counted events.

In `_settle_population_at`, the contact block becomes:

```python
with monster_activity.unbatched_state_writes(), suspended_maintenance_tally():
    events.extend(settle_population_contact_at(wilderness, tick, int(contact_tick)))
```

### D4. Tests

`world/observability/tests/test_tally.py` (`unittest.TestCase`): no scope returns False and counts nothing; a scope counts per name; nested open reuses the scope; suspension stops counting and resumes; an exception inside the scope closes it; an unknown name raises.

`world/maps/tests/test_population_maintenance_log.py` (`EvenniaTest`, importing `ActivityFixture` from `world.maps.tests.test_monster_activity`): the scenarios of the two requirements in `specs/observability-logging/spec.md`. Use the fixture's `_group`, `_register_lifecycle` and `_departure_seed` helpers, `self.captureOnCommitCallbacks(execute=True)`, and patch `log_info`/`log_debug` on `world.maps.monster_activity`, `world.rules.fatigue` and `world.maps.population_lifecycle`. Expected counts come from the fixture's own group count, never from calling the code under test. The rolled-back scenario raises inside `transaction.atomic()` after the pass and asserts no patched call.

Existing tests: run `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.rules.tests.test_fatigue` and `world.rules.tests.test_world_escape`. Where a test asserts an info call for one of the five events emitted through a lifecycle pass, change the patched binding to `log_debug`; do not delete the assertion and do not change any other assertion.

### D5. Documentation

- `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2: add a row for `population_maintenance_settled` (`tick_from`, `tick_to`, one count per maintenance event name) in the file's own language, and one sentence under the table stating the level rule of D2.
- `docs/development/monster-field-behaviour.md`: in the two event tables that list `monster_departed`, `monster_arrived`, `monster_arrival_deferred` and `monster_activity_decided`, add the level rule.
- `docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md` §11: append a blockquote `> **Amended 2026-11-14 (change population-maintenance-log-tally).**` stating that departure and arrival events committed by unobserved lifecycle settlement are debug-level and summarised by one info event per pass.

## Risks / Trade-offs

- [A single maintenance event can no longer be found in a default-level log] → set `VERBOSE = True` to get every line; the summary gives the counts and tick range to look for.
- [A future emit site forgets the two-branch form and logs at info inside the pass] → the scenario "Many groups, one info line" fails for the five listed events; other events are intentionally out of scope.
