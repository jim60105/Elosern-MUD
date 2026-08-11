"""
Room

Rooms are simple containers that has no location of their own.

"""
from evennia.contrib.grid.wilderness.wilderness import WildernessRoom
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.objects.objects import DefaultRoom
from evennia.typeclasses.attributes import AttributeProperty

from world.quests.room_observation import QuestObservableRoomMixin

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


class GridRoom(SceneArchetypeMixin, QuestObservableRoomMixin, ObjectParent, XYZRoom):
    """A room on the xyzgrid layer (design doc D3's 'Grid' layer).

    Adopts ``QuestObservableRoomMixin`` so a ``PlayerCharacter`` entering a grid
    room advances matching REACH/ESCORT stages (quest-runtime D-5). Every
    ``AnchorRoom`` inherits the hook through this class. The onboarding
    room-entry observer does NOT live here: it runs from the shared
    movement-completion boundary ``after_successful_movement``
    (``typeclasses/exits.py``), so arrivals into plain ``Room``, ``GridRoom``,
    ``TerrainRoom``, and ``InstanceRoom`` all reach
    ``world.rules.onboarding.observe_room_entry`` the same way (onboarding-skip
    coverage design D1) — no per-room monkey-patching and no double
    observation.

    ``ObjectParent`` sits before ``XYZRoom`` in the MRO so the shared zh-tw
    frame and the scene-flavor paragraph hook apply to every grid room while
    ``XYZRoom``'s own overrides (``return_appearance`` map display, builder
    ``get_display_name``) are still reached first (scene-flavor-apply design D4
    correction; ``XYZRoom`` inherits ``DefaultRoom`` directly, so without this
    adoption a grid room would show evennia's stock English ``Exits:`` frame).
    """

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(obj, source_location, move_type=move_type, **kwargs)
        from typeclasses.characters import PlayerCharacter

        if isinstance(obj, PlayerCharacter):
            from world.art.service import ensure_scene_asset

            ensure_scene_asset(self.scene_archetype)


class AnchorRoom(GridRoom):
    """The one canonical room per anchor (design doc D3's 'Anchor' layer), still a
    real xyzgrid node -- 'Anchor' and 'Grid' are complementary, not mutually
    exclusive: an anchor's canonical room is a GridRoom with one extra fact
    (which ANCHOR_REGISTRY entry it represents).
    """

    anchor_key: str | None = AttributeProperty(default=None)


class TerrainRoom(SceneArchetypeMixin, ObjectParent, WildernessRoom):
    """A room on the wilderness/Virtual layer (design doc D3). Unlike GridRoom,
    TerrainRoom instances are pooled and reused across many different (x, y)
    coordinates over their lifetime (WildernessScript._create_room() recycles
    unused rooms) -- see map-wilderness design.md D-3 for why scene_archetype
    must be re-set on every at_prepare_room() call, not merely defaulted once.

    Deliberately does NOT adopt ``QuestObservableRoomMixin``: the installed
    wilderness contrib assigns ``.location`` directly on its ordinary entry and
    stepping path, so advertising an arrival hook here would create a silently
    unreachable objective (quest-runtime D-5).

    ``ObjectParent`` sits before ``WildernessRoom`` in the MRO: its
    ``get_display_desc`` chains ``super()`` into the contrib's ``ndb.active_desc``
    path before appending the scene-flavor paragraph, so the pooled-description
    behavior survives while every terrain room shares the zh-tw appearance
    frame and the flavor hook (scene-flavor-apply design D4 correction).
    """

    pass


class InstanceRoom(SceneArchetypeMixin, QuestObservableRoomMixin, ObjectParent, DefaultRoom):
    """A room on the Instance layer (design doc D3) -- ephemeral, TTL-bounded,
    spawned through core evennia.prototypes.spawner.spawn(), never through
    xyzgrid. Carries no (x, y, z) of any kind; reachability is a plain Evennia
    exit-graph fact, identical to how Limbo itself works (map-instance
    design.md D-1).

    ``ObjectParent`` is adopted so the flavor-bearing scene room renders the
    zh-tw appearance frame and the scene-flavor paragraph through the shared
    room appearance layer (scene-flavor-apply design D4 correction; without it
    an instance room would show evennia's stock English ``Exits:`` frame).
    """

    expire_tick: int | None = AttributeProperty(default=None)  # None = promoted
    named: bool = AttributeProperty(default=False)
    interacted: bool = AttributeProperty(default=False)
    pin_reasons: list[str] = AttributeProperty(default=list)
    owned_entities: list = AttributeProperty(default=list)  # despawned on reclaim
    origin_room = AttributeProperty(default=None)

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(obj, source_location, move_type=move_type, **kwargs)
        from typeclasses.characters import PlayerCharacter

        if isinstance(obj, PlayerCharacter):
            self.db.interacted = True
            from world.art.service import ensure_scene_asset

            ensure_scene_asset(self.scene_archetype)

    def at_object_delete(self):
        if not super().at_object_delete():
            return False
        if self.db.pin_reasons:
            return False
        from typeclasses.characters import PlayerCharacter

        if any(isinstance(occupant, PlayerCharacter) for occupant in self.contents):
            return False
        return True
