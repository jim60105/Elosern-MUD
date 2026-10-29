"""Read-only canonical resolution of accepted commission destinations.

Synthetic mechanism tests: every anchor, settlement graph, monster site,
terrain region and quest definition below is a fixture of this module, never
production lore. Nearest-cell outcomes are known independently, either by
construction or from a brute-force oracle over the same synthetic region.
"""

import importlib
import random
import unittest
from types import SimpleNamespace
from unittest import mock

from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import GridRoom, InstanceRoom, TerrainRoom
from web.webclient.presentation import map_quest_destinations as resolver
from web.webclient.presentation.map_quest_destinations import (
    DestinationFamily,
    QuestDestination,
    accepted_destinations_for,
    accepted_destinations_with_tracking,
    actor_world_cell,
    clear_search_memo,
    nearest_region_cell,
    resolve_accepted_destinations,
    resolve_record_destination,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.quests.tests._fixtures import TEST_ISSUER_KEY, RegistryIsolationMixin
from world.rules.map_knowledge import encode_room
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()

# --- Synthetic geography -------------------------------------------------------

#: Two synthetic settlements: ``town`` is built on map ``town_map`` (whose
#: entrance node sits at (10, 20)) and anchored at wilderness cell (300, 400);
#: ``ruin`` is a known anchor with no built settlement.
_GEOGRAPHY = {
    "town": SimpleNamespace(anchor_key="town", cell=(300, 400)),
    "ruin": SimpleNamespace(anchor_key="ruin", cell=(700, 50)),
}
_PLACEMENTS = {
    "town": SimpleNamespace(anchor_key="town", zcoord="town_map", node=object()),
    # The same anchor's settlement-space identity: a permanent interior's
    # authored exterior names the settlement map its rooms open onto, and a
    # place's authored display name joins that room. A settlement and its map
    # are two published facts, so both rows exist here.
    "town_settlement": SimpleNamespace(anchor_key="town", zcoord="town", node=object()),
    "service_settlement": SimpleNamespace(
        anchor_key="service", zcoord="service", node=object()
    ),
}
_TOWN_NODES = {(10, 20), (35, 60)}
_SITES = {
    "den": SimpleNamespace(key="den", coordinates=(120, 130)),
    "sunken": SimpleNamespace(key="sunken", coordinates=(5, 5)),
}


def _settlement_graph(map_key):
    if map_key != "town_map":
        return None
    return SimpleNamespace(
        node_at=lambda coordinate: object() if coordinate in _TOWN_NODES else None
    )


def _classify(x, y):
    """Region ``fen`` is the square x 40..49, y 0..9; everything else ``moor``."""
    return "fen" if 40 <= x <= 49 and 0 <= y <= 9 else "moor"


#: The fen's flooded cell (40, 4) is illegal; (5, 5) is the sunken site's
#: illegal cell. Every other in-frame cell is legal.
def _is_legal(cell):
    return cell not in {(40, 4), (5, 5)}


_BOXES = {"fen": (30, 59, 0, 19)}


def _patch_geography(test):
    for name, value in (
        ("anchor_geography", lambda: _GEOGRAPHY),
        ("ANCHOR_PLACEMENT_REGISTRY", _PLACEMENTS),
        ("MONSTER_SITE_REGISTRY", _SITES),
        ("region_search_boxes", lambda: _BOXES),
        ("settlement_graph", _settlement_graph),
        ("region_for_coordinates", _classify),
        ("is_valid_wilderness_cell", _is_legal),
    ):
        patcher = mock.patch.object(resolver, name, value)
        patcher.start()
        test.addCleanup(patcher.stop)
    node_xy = mock.patch(
        "world.maps.static_references.settlement_node_xy",
        side_effect=lambda reference, **kwargs: (10, 20),
    )
    node_xy.start()
    test.addCleanup(node_xy.stop)


# --- Synthetic quests ----------------------------------------------------------


def _definition(key, objective):
    return QuestDefinition(
        key=key,
        display_name=f"測試委託{key}",
        quest_type=QuestType.EXPLORE,
        rank="F",
        stages=(QuestStage(index=0, objective=objective),),
    )


def _reach(locator):
    return QuestObjective(kind=ObjectiveKind.REACH, destination=locator)


_OBJECTIVES = {
    "anchor": _reach(RoomLocator(DestinationKind.ANCHOR, anchor_key="town")),
    "anchor_unbuilt": _reach(RoomLocator(DestinationKind.ANCHOR, anchor_key="ruin")),
    "anchor_unknown": _reach(RoomLocator(DestinationKind.ANCHOR, anchor_key="lost")),
    "grid": _reach(RoomLocator(DestinationKind.GRID, xyz=(35, 60, "town_map"))),
    "grid_unbuilt_node": _reach(RoomLocator(DestinationKind.GRID, xyz=(36, 60, "town_map"))),
    "grid_unknown_map": _reach(RoomLocator(DestinationKind.GRID, xyz=(35, 60, "nowhere"))),
    "escort_grid": QuestObjective(
        kind=ObjectiveKind.ESCORT,
        destination=RoomLocator(DestinationKind.GRID, xyz=(35, 60, "town_map")),
    ),
    "bound": _reach(RoomLocator(DestinationKind.BOUND_INSTANCE)),
    "hunt": QuestObjective(
        kind=ObjectiveKind.DEFEAT,
        quantity=2,
        region_key="fen",
        species_key="synthetic_species",
        countable_variant_keys=("synthetic_variant",),
    ),
    "hunt_unknown_region": QuestObjective(
        kind=ObjectiveKind.DEFEAT, region_key="nowhere", species_key="s",
        countable_variant_keys=("v",),
    ),
    "site": QuestObjective(
        kind=ObjectiveKind.DEFEAT, requires_bound_targets=True, site_key="den"
    ),
    "site_illegal": QuestObjective(
        kind=ObjectiveKind.DEFEAT, requires_bound_targets=True, site_key="sunken"
    ),
    "site_unknown": QuestObjective(
        kind=ObjectiveKind.DEFEAT, requires_bound_targets=True, site_key="gone"
    ),
    "tier": QuestObjective(kind=ObjectiveKind.DEFEAT, quantity=3, monster_tier="low"),
    "acquire": QuestObjective(kind=ObjectiveKind.ACQUIRE, item_key="herb"),
    "deliver": QuestObjective(kind=ObjectiveKind.DELIVER, item_key="herb"),
}
_DEFINITIONS = {
    f"map_dest_{name}": _definition(f"map_dest_{name}", objective)
    for name, objective in _OBJECTIVES.items()
}


def _record(name, state=QuestState.IN_PROGRESS, **overrides):
    fields = dict(
        quest_id=f"q_{name}",
        definition_key=f"map_dest_{name}",
        issuer_key=TEST_ISSUER_KEY,
        state=state,
        stage_index=0,
        stage_progress=0,
        deadline_tick=None,
        accepted_tick=10,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason="timeout" if state is QuestState.FAILED else None,
    )
    fields.update(overrides)
    return QuestRecord(**fields)


def _resolve(name, origin=(0, 0), **record_overrides):
    record = _record(name, **record_overrides)
    return resolve_record_destination(
        record, _DEFINITIONS[record.definition_key], origin_cell=origin
    )


# --- Nearest legal region cell -------------------------------------------------


class NearestRegionCellTests(unittest.TestCase):
    def _nearest(self, origin, *, classify=_classify, is_legal=_is_legal, bounds=None, block=4):
        return nearest_region_cell(
            origin,
            "fen",
            classify=classify,
            is_legal=is_legal,
            bounds=_BOXES["fen"] if bounds is None else bounds,
            block=block,
        )

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_nearest_cell_is_the_closest_legal_region_cell(self):
        # Straight west of the square: the nearest column is x=40.
        self.assertEqual(self._nearest((10, 7)), (40, 7))
        # The flooded (40, 4) is illegal, so its two equal neighbours tie
        # and the smaller y wins.
        self.assertEqual(self._nearest((10, 4)), (40, 3))
        # North-east of the square: its corner.
        self.assertEqual(self._nearest((70, 30)), (49, 9))
        # Inside the region the origin itself is nearest.
        self.assertEqual(self._nearest((45, 5)), (45, 5))

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_equal_distance_ties_take_the_smaller_x_then_y_across_tiles(self):
        # Two one-cell regions at distance 3 from (5, 5), in different tiles.
        region = {(5, 8), (8, 5)}

        def classify(x, y):
            return "fen" if (x, y) in region else "moor"

        for block in (1, 2, 3, 4, 16):
            self.assertEqual(
                self._nearest((5, 5), classify=classify, bounds=(0, 15, 0, 15), block=block),
                (5, 8),
            )
        # An x tie falls through to the smaller y.
        region = {(9, 2), (9, 8)}
        self.assertEqual(
            self._nearest((9, 5), classify=classify, bounds=(0, 15, 0, 15)), (9, 2)
        )

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_no_legal_region_cell_resolves_to_nothing(self):
        self.assertIsNone(self._nearest((0, 0), is_legal=lambda cell: False))
        self.assertIsNone(self._nearest((0, 0), classify=lambda x, y: "moor"))
        self.assertIsNone(self._nearest((0, 0), bounds=(5, 4, 0, 0)))

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_search_matches_a_brute_force_oracle(self):
        rng = random.Random(4242)
        cells = {(rng.randrange(0, 60), rng.randrange(0, 60)) for _ in range(40)}
        illegal = set(rng.sample(sorted(cells), 10))

        def classify(x, y):
            return "fen" if (x, y) in cells else "moor"

        def is_legal(cell):
            return cell not in illegal

        legal = cells - illegal
        for _ in range(60):
            origin = (rng.randrange(-20, 80), rng.randrange(-20, 80))
            expected = min(
                legal,
                key=lambda c: ((c[0] - origin[0]) ** 2 + (c[1] - origin[1]) ** 2, c[0], c[1]),
            )
            for block in (1, 5, 16):
                self.assertEqual(
                    self._nearest(
                        origin, classify=classify, is_legal=is_legal,
                        bounds=(0, 59, 0, 59), block=block,
                    ),
                    expected,
                )

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_repeated_reads_are_stable_and_follow_the_origin(self):
        first = self._nearest((10, 7))
        self.assertEqual([self._nearest((10, 7)) for _ in range(3)], [first] * 3)
        self.assertEqual(self._nearest((45, 30)), (45, 9))

    def test_only_the_production_classifier_is_memoized(self):
        clear_search_memo()
        self.addCleanup(clear_search_memo)
        self._nearest((10, 7))
        self.assertEqual(resolver._OCCUPANCY, {})
        production = resolver.wilderness_provider.region_for_coordinates
        nearest_region_cell(
            (0, 0), "fen", classify=production, is_legal=lambda cell: True,
            bounds=(0, 3, 0, 3), block=2,
        )
        self.assertEqual(len(resolver._OCCUPANCY), 1)


# --- Per-record resolution -----------------------------------------------------


class ResolveRecordDestinationTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        _patch_geography(self)

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_locator_families_use_their_canonical_source(self):
        self.assertEqual(
            _resolve("anchor"),
            QuestDestination(
                "q_anchor", "map_dest_anchor", DestinationFamily.ANCHOR,
                (300, 400), "town_map", "grid:town_map:10:20",
            ),
        )
        # The GRID world position is the settlement's anchor cell, not a local
        # offset; its local identity is the actual node, not the anchor node.
        self.assertEqual(
            _resolve("grid"),
            QuestDestination(
                "q_grid", "map_dest_grid", DestinationFamily.GRID,
                (300, 400), "town_map", "grid:town_map:35:60",
            ),
        )
        escort = _resolve("escort_grid")
        self.assertEqual((escort.family, escort.node_id), (DestinationFamily.GRID, "grid:town_map:35:60"))
        self.assertEqual(
            _resolve("site"),
            QuestDestination(
                "q_site", "map_dest_site", DestinationFamily.MONSTER_SITE,
                (120, 130), "elosern", "wild:elosern:120:130",
            ),
        )
        self.assertEqual(
            _resolve("hunt", origin=(10, 4)),
            QuestDestination(
                "q_hunt", "map_dest_hunt", DestinationFamily.SPECIES_HUNT,
                (40, 3), "elosern", "wild:elosern:40:3",
            ),
        )

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_settlement_anchor_cells_survive_a_missing_local_node(self):
        unbuilt = _resolve("anchor_unbuilt")
        self.assertEqual((unbuilt.world_cell, unbuilt.map_key, unbuilt.node_id), ((700, 50), None, None))
        grid = _resolve("grid_unbuilt_node")
        self.assertEqual((grid.world_cell, grid.map_key, grid.node_id), ((300, 400), None, None))

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_unlocatable_destinations_are_not_fabricated(self):
        for name in (
            "anchor_unknown", "grid_unknown_map", "bound", "hunt_unknown_region",
            "site_illegal", "site_unknown", "tier", "acquire", "deliver",
        ):
            with self.subTest(name=name):
                self.assertIsNone(_resolve(name))
        # A hunt needs the player's position; the other families do not.
        self.assertIsNone(_resolve("hunt", origin=None))
        self.assertEqual(_resolve("site", origin=None).world_cell, (120, 130))
        self.assertEqual(_resolve("grid", origin=None).world_cell, (300, 400))
        # Only accepted, in-progress commissions resolve.
        self.assertIsNone(_resolve("grid", state=QuestState.COMPLETED))
        self.assertIsNone(_resolve("grid", state=QuestState.FAILED))


# --- Quest-log consumer --------------------------------------------------------


class AcceptedDestinationsConsumerTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        _patch_geography(self)
        QUEST_DEFINITION_REGISTRY.update(_DEFINITIONS)

    def _snapshot(self):
        """Every object, script, attribute and tag row plus object locations."""
        return {
            "attributes": sorted(
                (a.id, a.db_key, a.db_category, repr(a.value))
                for a in Attribute.objects.all()
            ),
            "tags": sorted(Tag.objects.values_list("id", "db_key", "db_category")),
            "scripts": sorted(ScriptDB.objects.values_list("id", "db_key")),
            "objects": sorted(ObjectDB.objects.values_list("id", "db_location_id")),
        }

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_grid_keeps_local_identity_and_unsupported_entries_add_no_marker(self):
        self.char1.db.quest_log = [
            to_storage(_record("bound")),
            {"quest_id": "q_corrupt", "definition_key": "map_dest_grid"},
            to_storage(_record("grid")),
            to_storage(_record("tier")),
            to_storage(_record("site")),
            to_storage(_record("hunt")),
            to_storage(_record("anchor", state=QuestState.COMPLETED)),
        ]
        before = self._snapshot()
        with mock.patch.object(resolver, "log_warn") as warn:
            first = resolve_accepted_destinations(self.char1, origin_cell=(45, 30))
            second = resolve_accepted_destinations(self.char1, origin_cell=(45, 30))

        self.assertEqual(first, second)
        by_quest = {destination.quest_id: destination for destination in first}
        self.assertEqual(sorted(by_quest), ["q_grid", "q_hunt", "q_site"])
        grid = by_quest["q_grid"]
        self.assertEqual(grid.node_id, "grid:town_map:35:60")
        self.assertEqual(grid.world_cell, (300, 400))
        self.assertNotEqual(grid.node_id, "grid:town_map:10:20")
        self.assertEqual(by_quest["q_hunt"].world_cell, (45, 9))
        # The corrupt entry is isolated and reported; the others still resolve.
        self.assertEqual(warn.call_count, 2)
        event, = {call.args[0] for call in warn.call_args_list}
        self.assertEqual(event, "map_quest_destination_unresolved")
        self.assertEqual(warn.call_args.kwargs["context"]["quest"], "q_corrupt")
        self.assertIsNotNone(warn.call_args.kwargs["exc"])
        # Resolution is read-only: no quest, knowledge, room or object write.
        self.assertEqual(self._snapshot(), before)

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_possessed_puppet_reads_its_owner_log_from_its_own_position(self):
        self.char2.db.quest_log = [to_storage(_record("hunt")), to_storage(_record("grid"))]
        puppet = SimpleNamespace(
            location=mock.MagicMock(spec=TerrainRoom, coordinates=(10, 4)),
            db=SimpleNamespace(possessed_by=self.char2.id),
        )
        before = self._snapshot()
        by_quest = {d.quest_id: d for d in accepted_destinations_for(puppet)}
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(by_quest["q_hunt"].node_id, "wild:elosern:40:3")
        self.assertEqual(by_quest["q_grid"].node_id, "grid:town_map:35:60")

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_bound_instance_keeps_its_canonical_room_identity(self):
        room = create_object(InstanceRoom, key="合成地城")
        room.db.origin_room = self.room1
        destination = resolve_record_destination(
            _record("bound", stage_room_id=int(room.id)),
            _DEFINITIONS["map_dest_bound"],
            origin_cell=(0, 0),
        )
        self.assertEqual(destination.family, DestinationFamily.BOUND_INSTANCE)
        self.assertEqual(destination.node_id, encode_room(int(room.id)))
        self.assertIsNone(destination.map_key)
        # A plain Room origin has no continental cell; the marker may still
        # carry the room identity and must not invent a bearing.
        self.assertIsNone(destination.world_cell)

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_bound_instance_without_a_live_instance_room_is_not_fabricated(self):
        missing = resolve_record_destination(
            _record("bound", stage_room_id=999_999),
            _DEFINITIONS["map_dest_bound"],
            origin_cell=(0, 0),
        )
        self.assertIsNone(missing)
        self.assertIsNone(_resolve("bound"))

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_tracking_ids_come_from_the_same_quest_log_read(self):
        self.char1.db.quest_log = [
            to_storage(_record("grid", tracked=True)),
            to_storage(_record("site")),
        ]
        destinations, tracked = accepted_destinations_with_tracking(self.char1)
        self.assertEqual(tracked, frozenset({"q_grid"}))
        self.assertEqual({d.quest_id for d in destinations}, {"q_grid", "q_site"})

    def test_actor_world_cell_follows_the_room_layer(self):
        terrain = mock.MagicMock(spec=TerrainRoom, coordinates=(12, 34))
        grid = mock.MagicMock(spec=GridRoom, xyz=(35, 60, "town_map"))
        unanchored = mock.MagicMock(spec=GridRoom, xyz=(1, 1, "nowhere"))
        instance = mock.MagicMock(spec=InstanceRoom)
        instance.attributes.get.return_value = grid
        orphan = mock.MagicMock(spec=InstanceRoom)
        orphan.attributes.get.return_value = None
        cases = (
            (terrain, (12, 34)),
            (grid, (300, 400)),
            (unanchored, None),
            (instance, (300, 400)),
            (orphan, None),
            (self.room1, None),
            (None, None),
        )
        for location, expected in cases:
            with self.subTest(location=location):
                self.assertEqual(actor_world_cell(SimpleNamespace(location=location)), expected)

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_registered_interior_and_instance_origins_are_read_only(self):
        from typeclasses.rooms import Room

        from world.tests.interior_fixture import (
            interior_document,
            interior_exterior,
            interior_room,
            published_interiors,
        )

        interior = create_object(Room, key="Synthetic service")
        interior.tags.add("t_service")
        interior.tags.add("t_second")
        instance = create_object(InstanceRoom, key="Synthetic instance")
        instance.attributes.add("origin_room", interior)
        orphan = create_object(InstanceRoom, key="Synthetic orphan")
        orphan.attributes.remove("origin_room")
        nested = create_object(InstanceRoom, key="Synthetic nested")
        nested.attributes.add("origin_room", instance)
        self.char1.db.quest_log = [to_storage(_record(name)) for name in ("anchor", "grid", "site", "hunt")]

        def _interiors(second_settlement: str | None):
            """Publish one authored room per tag: `t_second` may move or vanish."""

            documents = [
                interior_document(
                    "t_service",
                    {"t_service": interior_room("合成服務室", "A synthetic service room.")},
                    exterior=interior_exterior(
                        "town_map", "town_node", "t_service", "合成服務門"
                    ),
                )
            ]
            if second_settlement is not None:
                documents.append(
                    interior_document(
                        "t_second",
                        {"t_second": interior_room("合成第二室", "A second synthetic room.")},
                        exterior=interior_exterior(
                            second_settlement,
                            "town_node",
                            "t_second",
                            "合成第二門",
                        ),
                    )
                )
            return documents

        with published_interiors(*_interiors("town")):
            for room in (interior, instance):
                self.char1.location = room
                before = self._snapshot()
                destinations = {d.quest_id: d for d in accepted_destinations_for(self.char1)}
                self.assertEqual(destinations["q_hunt"].world_cell, (49, 9))
                self.assertEqual(set(destinations), {"q_anchor", "q_grid", "q_site", "q_hunt"})
                self.assertEqual(self._snapshot(), before)
                self.assertFalse(interior.attributes.has("coordinates"))
                self.assertFalse(interior.attributes.has("xyz"))
            bound = _resolve("bound", stage_room_id=int(instance.id))
            self.assertEqual((bound.world_cell, bound.node_id), ((300, 400), encode_room(int(instance.id))))
            for room in (orphan, nested):
                before = self._snapshot()
                self.assertIsNone(actor_world_cell(SimpleNamespace(location=room)))
                bound = _resolve("bound", stage_room_id=int(room.id))
                self.assertEqual(bound.node_id, encode_room(int(room.id)))
                self.assertIsNone(bound.world_cell)
                self.assertEqual(self._snapshot(), before)
            # A second authored enclosing anchor makes the room ambiguous: an
            # arbitrary one is never chosen.
            second_placement = SimpleNamespace(
                anchor_key="ruin", zcoord="ruin_map", node=object()
            )
            # A second authored enclosure in a different place is ambiguous.
            with published_interiors(
                *_interiors("ruin_map"), replace_existing=True
            ), mock.patch.object(
                resolver,
                "ANCHOR_PLACEMENT_REGISTRY",
                {**_PLACEMENTS, "ruin": second_placement},
            ):
                self.assertIsNone(
                    actor_world_cell(SimpleNamespace(location=interior))
                )
            # A second room naming an unplaced settlement adds no enclosure, so
            # the one resolvable document still locates the room.
            with published_interiors(*_interiors("missing"), replace_existing=True):
                self.assertEqual(
                    actor_world_cell(SimpleNamespace(location=interior)),
                    (300, 400),
                )
            # A room whose only tag names no authored interior is
            # unlocatable: no arbitrary enclosure is invented for it.
            unregistered = create_object(Room, key="Synthetic unregistered")
            unregistered.tags.add("t_second")
            with published_interiors(*_interiors(None), replace_existing=True):
                self.assertIsNone(
                    actor_world_cell(SimpleNamespace(location=unregistered))
                )
            # Restoring the authored room locates it again.
            with published_interiors(*_interiors("town_map"), replace_existing=True):
                self.assertEqual(
                    actor_world_cell(SimpleNamespace(location=unregistered)),
                    (300, 400),
                )

    @covers_requirement("map-quest-destinations::accepted-commission-destinations-resolve-on-the-server")
    def test_an_inner_room_locates_its_document_without_a_service_record(self):
        from typeclasses.rooms import Room

        from world.tests.interior_fixture import (
            interior_document,
            interior_exterior,
            interior_room,
            published_interiors,
        )

        _patch_geography(self)
        inner_room = create_object(Room, key="Synthetic inner")
        inner_room.tags.add("t_inner_room")
        house = interior_document(
            "t_two_room_house",
            {
                "t_entrance": interior_room("合成門廳", "A synthetic hall."),
                "t_inner_room": interior_room("合成內室", "A synthetic inner room."),
            },
            exterior=interior_exterior("town_map", "town_node", "t_entrance", "合成門"),
        )
        with published_interiors(house, replace_existing=True):
            # The inner room has no service record and no exterior of its own:
            # it is located through the document that authors it.
            self.assertEqual(
                actor_world_cell(SimpleNamespace(location=inner_room)), (300, 400)
            )

    def test_empty_or_missing_quest_log_resolves_to_nothing(self):
        self.char1.db.quest_log = None
        self.assertEqual(resolve_accepted_destinations(self.char1, origin_cell=(0, 0)), ())
        self.char1.db.quest_log = []
        self.assertEqual(resolve_accepted_destinations(self.char1, origin_cell=(0, 0)), ())
