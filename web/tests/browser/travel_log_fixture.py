"""Test-only placement for the travel log journey (wilderness-travel-log-ui).

Invoked through the superuser ``@py`` route from
``web.tests.browser.test_wilderness_travel.TravelLogTests``. It places the
logged-in character on one open wilderness cell through the wilderness
contrib's own entry API, so every later step, look and refusal of the journey
runs the production producers unchanged. The cell is chosen from the published
geography at run time (an open cell whose four orthogonal neighbours are open
and outside every settlement footprint, searched outward from the first
registered gate's approach cell), so this module names no shipped content.
"""

from __future__ import annotations

from typing import Any

_RESULT = "TRAVEL_LOG_FIXTURE"
_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _open_cell() -> tuple[int, int] | None:
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps.wilderness_provider import is_footprint_cell, is_valid_wilderness_cell

    def open_cell(cell: tuple[int, int]) -> bool:
        return is_valid_wilderness_cell(cell) and not is_footprint_cell(cell)

    for key in sorted(WILDERNESS_ENTRY_REGISTRY):
        entry = WILDERNESS_ENTRY_REGISTRY[key]
        for gate in entry.gates:
            try:
                start = tuple(entry.approach_cell(gate))
            except Exception:  # observability: ignore R2: a test fixture skips an unusable gate and tries the next one
                continue
            for radius in range(3, 12):
                for dx in range(-radius, radius + 1):
                    for dy in (-radius, radius):
                        cell = (start[0] + dx, start[1] + dy)
                        if open_cell(cell) and all(
                            open_cell((cell[0] + sx, cell[1] + sy)) for sx, sy in _STEPS
                        ):
                            return cell
    return None


def run(me: Any) -> None:
    """Place ``me`` on an open wilderness cell and report it on one line."""
    from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
    from world.maps.wilderness_provider import WILDERNESS_NAME

    origin = getattr(me.location, "pk", 0) or 0
    cell = _open_cell()
    moved = cell is not None and enter_wilderness(me, coordinates=cell, name=WILDERNESS_NAME)
    if not moved:
        me.msg(f"{_RESULT} failed")
        return
    from world.rules.map_knowledge import record_arrival

    # The arrival record an ordinary entry writes, so the local map and the
    # travel stage disclose the cell as they would after a real gate entry.
    record_arrival(me)
    me.msg(f"{_RESULT} ok {cell[0]} {cell[1]} {origin}")


def restore(me: Any, origin: int) -> None:
    """Return ``me`` to the room the journey started in (shared test account)."""
    from evennia.objects.models import ObjectDB

    room = ObjectDB.objects.filter(pk=int(origin)).first()
    if room is not None:
        me.move_to(room, quiet=True, move_type="teleport")
    me.msg(f"{_RESULT} restored")
