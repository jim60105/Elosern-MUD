"""
Room

Rooms are simple containers that has no location of their own.

"""
from evennia.contrib.grid.wilderness.wilderness import WildernessRoom
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


class SceneArchetypeMixin:
    """The design doc D10/§8 seam: which SceneArchetype (change 22, unbuilt) a
    room's scene art should use. Not validated against any registry here -- see
    change 12's own GridRoom docstring for why (no SceneArchetype registry
    exists yet)."""

    scene_archetype: str | None = AttributeProperty(default=None)


class GridRoom(SceneArchetypeMixin, XYZRoom):
    """A room on the xyzgrid layer (design doc D3's 'Grid' layer)."""

    pass


class AnchorRoom(GridRoom):
    """The one canonical room per anchor (design doc D3's 'Anchor' layer), still a
    real xyzgrid node -- 'Anchor' and 'Grid' are complementary, not mutually
    exclusive: an anchor's canonical room is a GridRoom with one extra fact
    (which ANCHOR_REGISTRY entry it represents).
    """

    anchor_key: str | None = AttributeProperty(default=None)


class TerrainRoom(SceneArchetypeMixin, WildernessRoom):
    """A room on the wilderness/Virtual layer (design doc D3). Unlike GridRoom,
    TerrainRoom instances are pooled and reused across many different (x, y)
    coordinates over their lifetime (WildernessScript._create_room() recycles
    unused rooms) -- see map-wilderness design.md D-3 for why scene_archetype
    must be re-set on every at_prepare_room() call, not merely defaulted once.
    """

    pass
