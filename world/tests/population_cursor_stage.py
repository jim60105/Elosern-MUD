"""Test seam: keep settlement cursors with the world tick without settling.

Production's population lifecycle stage raises every unit cursor to an advance's
end tick before the clock tick is persisted. Fixtures that drive game time
outside the command seam, and that cannot run the real stage because it would
settle the authored placement (or would perturb the exact physiology a test
asserts), register this seam instead: it performs the stage's cursor step alone,
so the population writer guards see the same world production gives them.

The seam registers no advance-surface contract. A fixture that rolls an advance
back would need the cursor record's own surface contract, because the durable
value rolls back with the transaction while the attribute cache does not; no
fixture using this seam rolls an advance back.
"""

from __future__ import annotations

from typing import Any


def register_cursor_stage(testcase: Any, wilderness: Any) -> None:
    """Register the cursor step for one test and pop it on cleanup."""
    from world.maps import population_lifecycle, population_units
    from world.rules import clock as clock_module

    def settle(start_tick: int, end_tick: int):
        population_units.advance_unit_cursors(wilderness, None, int(end_tick))
        return []

    clock_module.register_event_source(population_lifecycle.STAGE_KIND, settle, None)
    testcase.addCleanup(
        clock_module._EVENT_SOURCES.pop,
        population_lifecycle.STAGE_KIND,
        None,
    )


__all__ = ["register_cursor_stage"]