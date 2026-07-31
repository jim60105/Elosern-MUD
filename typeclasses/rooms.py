"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.objects.objects import DefaultRoom
from evennia.typeclasses.attributes import AttributeProperty

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    pass


class GridRoom(XYZRoom):
    """A room on the xyzgrid layer (design doc D3's 'Grid' layer)."""

    # Forward-declared seam for design doc D10/§8 (change 22, art-queue).
    # Unresolved against any registry here -- no SceneArchetype registry exists
    # yet. Mirrors the treatment already given to NPC.schedule and
    # Monster.behaviour_tree (change 3): the attribute exists so change 22 has
    # somewhere to read from and write validation against; nothing here
    # enforces a value.
    scene_archetype: str | None = AttributeProperty(default=None)


class AnchorRoom(GridRoom):
    """The one canonical room per anchor (design doc D3's 'Anchor' layer), still a
    real xyzgrid node -- 'Anchor' and 'Grid' are complementary, not mutually
    exclusive: an anchor's canonical room is a GridRoom with one extra fact
    (which ANCHOR_REGISTRY entry it represents).
    """

    anchor_key: str | None = AttributeProperty(default=None)
