"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.contrib.grid.wilderness.wilderness import WildernessExit, enter_wilderness
from evennia.objects.objects import DefaultExit

from .objects import ObjectParent
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock

WILDERNESS_MOVE_SECONDS = CLOCK_YAML["command_defaults"]["wilderness_move"]


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

    """

    pass


def _grid_room_for_anchor(anchor_key: str):
    """Return the grid room this anchor's wilderness gate is attached to.

    Looked up through the gate exit itself (rather than from a coordinate) so
    the return target is exactly the room the character left from, wherever
    ``sync_wilderness()`` placed the gate.
    """

    for gate in WildernessGateExit.objects.all():
        if gate.db.anchor_key == anchor_key:
            return gate.location
    return None


class WildernessGateExit(Exit):
    """Ordinary Exit at a grid room (e.g. capital_altoria's North Gate) whose
    at_traverse is fully overridden -- mirrors WildernessExit's own pattern of
    ignoring target_location entirely. db.anchor_key is set by sync_wilderness()
    at creation time -- it is NOT optional, and a gate exit created without it
    will KeyError on first use (map-wilderness design.md D-7).
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        # Honor the same at_pre_move veto every other exit in the game honors,
        # so entering the wilderness never silently bypasses a future
        # movement-blocking convention (combat lock, restraint, quest gating).
        if not traversing_object.at_pre_move(None):
            return False

        entry = WILDERNESS_ENTRY_REGISTRY[self.db.anchor_key]
        source_location = traversing_object.location
        ok = enter_wilderness(
            traversing_object, coordinates=entry.wilderness_xy, name=WILDERNESS_NAME
        )
        if not ok:
            return False

        if source_location:
            source_location.msg_contents(
                f"{traversing_object.key} leaves into the wilderness.",
                exclude=[traversing_object],
            )
        traversing_object.location.msg_contents(
            f"{traversing_object.key} arrives from {source_location}.",
            exclude=[traversing_object],
        )
        traversing_object.at_post_move(None)
        get_world_clock().advance(
            WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
        )
        return True


class WildernessReturnExit(WildernessExit):
    """The wilderness's own exit typeclass: routes exactly one registered
    coordinate-and-direction pair (the entry coordinate, direction ``"south"``)
    back into the grid room, and routes everything else like a stock
    WildernessExit. The clock cost is charged on EVERY successful traversal --
    special-cased return branch and ordinary fallback alike -- so no wilderness
    step is free (map-wilderness design.md D-6's correction note).
    """

    def at_traverse(self, traversing_object, target_location):
        itemcoordinates = self.location.wilderness.db.itemcoordinates
        current = itemcoordinates[traversing_object]
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            if current == entry.wilderness_xy and self.key == "south":
                grid_room = _grid_room_for_anchor(entry.anchor_key)
                if grid_room is None:
                    # Misconfiguration (gate exit missing or wrong anchor_key):
                    # do not report success or charge time for a move that
                    # cannot happen -- the spec's "failed traversal does not
                    # advance the clock" applies here too.
                    return False
                if not traversing_object.move_to(grid_room, quiet=False):
                    return False
                get_world_clock().advance(
                    WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
                )
                return True
        # ORDINARY wilderness movement -- every coordinate/direction that is not
        # a registered gateway. Not free: a successful step still pays
        # wilderness_move; only the routing decision is gated.
        result = super().at_traverse(traversing_object, target_location)
        if result:
            get_world_clock().advance(
                WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object]
            )
        return result
