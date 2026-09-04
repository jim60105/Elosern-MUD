"""Rules-side home writer for the one-way city gates (limbo-one-way-gates D7).

The starting room (虛境) is every character's creation home (no
``DEFAULT_HOME`` override exists), and the capability's own hard gate refuses
every later character entry into it — a persisted 虛境 ``home`` would make the
``home`` command deliver the player into a room that rejects them. This module
is the capability's SOLE home writer (single-writer rule): the shared
movement-completion boundary calls it, and nothing else may write ``home``
for gate arrivals.
"""

from typing import Any

from world.observability import log_info


def reanchor_home_on_gate_arrival(character: Any, destination: Any | None) -> None:
    """Re-anchor a 虛境 ``home`` to the arrival gate room, exactly once.

    Mirrors the internally no-op discipline of ``record_arrival`` /
    ``follow_companions``: anything that is not a ``PlayerCharacter``, any
    destination without a grid coordinate, any coordinate that matches no
    ``CITY_GATE_REGISTRY`` row, and any character whose ``home`` is no longer
    the 虛境 starting room all return without touching state. The predicate is
    the destination COORDINATE, not the traversed exit's origin — a wilderness
    return that lands on a registry gate room re-anchors under the same rule
    (documented in the requirement; gate rooms are the city's threshold, and
    the policy is "cross the threshold, live in the city").
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(character, PlayerCharacter):
        return
    if destination is None:
        return
    gate_xyz = getattr(destination, "xyz", None)
    if gate_xyz is None:
        return

    from world.maps.city_gates import CITY_GATE_REGISTRY

    if not any(row.gate_xyz == gate_xyz for row in CITY_GATE_REGISTRY.values()):
        return

    from world.maps.bootstrap import find_starting_rooms
    from world.maps.limbo import LIMBO_KEY

    starting_rooms = find_starting_rooms(LIMBO_KEY)
    if not starting_rooms:
        return
    if character.home != starting_rooms[0]:
        return

    character.home = destination
    log_info(
        "city_gate_home_reanchored",
        context={
            "char": character.key,
            "char_dbref": character.dbref,
            "gate_map_id": next(
                row.map_id
                for row in CITY_GATE_REGISTRY.values()
                if row.gate_xyz == gate_xyz
            ),
            "action": "first_gate_traversal",
        },
    )
