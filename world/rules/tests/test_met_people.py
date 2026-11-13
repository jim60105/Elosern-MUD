"""Behavior tests for the per-character met-person record.

Every identifier and prose value is invented with the reserved ``t_`` prefix, so
no test names shipped content. The settlement place is the synthetic xyzgrid map
(``world/tests/synthetic_grid_map.py``) registered as one synthetic settlement
graph, and the wilderness place is one synthetic region published through
``world/tests/geography_fixture.py``; the region classifier is replaced with a
fixed synthetic answer because the shipped classifier can only derive its own
region keys, and an expectation must never be read out of the code under test.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from evennia.utils.create import create_object, create_script
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTest

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.sparse import SparseNode, SparseSettlementGraph
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, TerrainRoom
from world.lore.anchors import Anchor, AnchorKind
from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
from world.lore.wilderness_regions import WildernessRegion
from world.maps import geography as geography_module
from world.maps import map_data, wilderness_provider
from world.maps.map_data import SettlementSnapshot
from world.rules.clock import WorldClockScript, read_world_clock
from world.rules.met_people import (
    MET_PEOPLE_ATTRIBUTE,
    PLACE_REGION,
    PLACE_SETTLEMENT,
    interaction_place,
    met_people,
    place_label,
    record_person_interaction,
)
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.tests.geography_fixture import (
    publish_geography,
    publish_settlements,
    publish_shipped_settlements,
)
from world.tests.synthetic_grid_map import Z_MAP_KEY, load_synthetic_grid, synthetic_rooms

publish_shipped_settlements()

#: The synthetic named NPC's portrait stable key.
NAMED_KEY = "t_npc_a"
#: A second synthetic named NPC's portrait stable key.
OTHER_NAMED_KEY = "t_npc_b"
#: The synthetic anchor whose wilderness gateway targets the synthetic map.
SETTLEMENT_ANCHOR = "t_anchor"
#: The synthetic wilderness region key.
REGION_KEY = "t_region"


def _synthetic_graph() -> SparseSettlementGraph:
    """One three-node graph under the synthetic map's own identity."""

    return SparseSettlementGraph(
        Z_MAP_KEY,
        (
            SparseNode("t_node_start", 0, 0, {"prototype_parent": "grid_room", "key": "測試街口"}),
            SparseNode("t_node_anchor", 1, 0, {"prototype_parent": "anchor_room", "key": "測試廣場"}),
            SparseNode("t_node_end", 2, 0, {"prototype_parent": "grid_room", "key": "測試鐘樓"}),
        ),
        (),
    )


def _settlements(entries: dict[str, WildernessEntryPoint]) -> SettlementSnapshot:
    """One synthetic settlement world: the synthetic map and its gateway."""

    return SettlementSnapshot(
        settlements=MappingProxyType({}),
        graphs=MappingProxyType({Z_MAP_KEY: _synthetic_graph()}),
        anchor_placements=MappingProxyType({}),
        local_frame_anchors=MappingProxyType({}),
        city_gates=MappingProxyType({}),
        wilderness_entries=MappingProxyType(entries),
        grid_node_scene_archetypes=MappingProxyType({}),
    )


def _gateway() -> WildernessEntryPoint:
    """The synthetic anchor's gateway onto the synthetic map."""

    return WildernessEntryPoint(
        anchor_key=SETTLEMENT_ANCHOR,
        shape=("#",),
        origin_xy=(0, 0),
        gates=(
            WildernessGate(
                "n",
                QualifiedRef("settlement", map_id=Z_MAP_KEY, object_id="t_node_anchor"),
            ),
        ),
    )


def _synthetic_geography(previous):
    """Add one synthetic anchor and region to the published geography views."""

    return replace(
        previous,
        regions=MappingProxyType(
            {**previous.regions, REGION_KEY: WildernessRegion(REGION_KEY, "測試地域", None, ())}
        ),
        anchors=MappingProxyType(
            {
                **previous.anchors,
                SETTLEMENT_ANCHOR: Anchor(
                    key=SETTLEMENT_ANCHOR,
                    kind=AnchorKind.DUNGEON,
                    display_name_zh="測試錨地",
                    nation_key=None,
                    population=None,
                    floors=None,
                    description="",
                ),
            }
        ),
    )


class MetPersonRecordTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.previous_settlements = map_data.current()
        self.previous_geography = geography_module.current()
        publish_settlements(_settlements({SETTLEMENT_ANCHOR: _gateway()}))
        publish_geography(_synthetic_geography(self.previous_geography))
        scripts = search_script("world_clock")
        self.clock_script = (
            scripts[0]
            if scripts
            else create_script(
                WorldClockScript, key="world_clock", persistent=True, interval=0, repeats=0
            )
        )
        self._initial_tick = self.clock_script.db.tick
        load_synthetic_grid()
        self.start, self.anchor, self.end = synthetic_rooms()
        self.char1.location = self.start

    def tearDown(self):
        self.clock_script.db.tick = self._initial_tick
        publish_geography(self.previous_geography)
        publish_settlements(self.previous_settlements)
        super().tearDown()

    def _set_tick(self, tick):
        self.clock_script.db.tick = tick
        self.assertEqual(read_world_clock().tick, tick)

    def _npc(self, location, *, stable_key=NAMED_KEY, key=None):
        npc = create_object(NPC, key=key or stable_key, location=location)
        npc.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        return npc

    def _generic_npc(self, location):
        npc = create_object(NPC, key="t_npc_generic", location=location)
        npc.db.portrait_policy = {"mode": "generic"}
        return npc

    @covers_requirement(
        "met-person-record::each-character-owns-one-met-person-record-keyed-by-portrait-stable-key"
    )
    def test_a_named_npc_is_recorded_once(self):
        npc = self._npc(self.start)
        self._set_tick(10)
        with patch("world.rules.met_people.log_info") as info:
            record_person_interaction(self.char1, npc)
        info.assert_called_once()
        self.assertEqual(info.call_args.args[0], "met_person_recorded")

        self._set_tick(25)
        record_person_interaction(self.char1, npc)

        people = met_people(self.char1)
        self.assertEqual(len(people), 1)
        person = people[0]
        self.assertEqual(person.stable_key, NAMED_KEY)
        self.assertEqual(person.npc.pk, npc.pk)
        self.assertEqual((person.tick, person.seq), (25, 2))
        stored = self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE)
        self.assertEqual(set(stored["entries"]), {NAMED_KEY})
        self.assertEqual((stored["seq"], stored["entries"][NAMED_KEY]["tick"]), (2, 25))

    @covers_requirement(
        "met-person-record::each-character-owns-one-met-person-record-keyed-by-portrait-stable-key"
    )
    def test_a_generic_npc_is_not_recorded(self):
        npc = self._generic_npc(self.start)
        record_person_interaction(self.char1, npc)
        self.assertIsNone(self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE))
        self.assertEqual(met_people(self.char1), ())

    @covers_requirement(
        "met-person-record::each-character-owns-one-met-person-record-keyed-by-portrait-stable-key"
    )
    def test_records_belong_to_their_character(self):
        other = create_object(PlayerCharacter, key="t_other_char", location=self.start)
        other.account = self.char1.account
        record_person_interaction(self.char1, self._npc(self.start))

        self.assertEqual([person.stable_key for person in met_people(self.char1)], [NAMED_KEY])
        self.assertEqual(met_people(other), ())
        self.assertIsNone(other.attributes.get(MET_PEOPLE_ATTRIBUTE))

    @covers_requirement(
        "met-person-record::the-place-is-the-settlement-else-the-wilderness-region"
    )
    def test_moving_inside_a_settlement_keeps_the_place(self):
        npc = self._npc(self.start)
        self._set_tick(10)
        record_person_interaction(self.char1, npc)
        self._set_tick(40)
        self.char1.location = self.anchor
        record_person_interaction(self.char1, npc)

        person = met_people(self.char1)[0]
        self.assertEqual(person.place, f"{PLACE_SETTLEMENT}:{Z_MAP_KEY}")
        self.assertEqual((person.tick, person.seq), (40, 2))

    @covers_requirement(
        "met-person-record::the-place-is-the-settlement-else-the-wilderness-region"
    )
    def test_a_wilderness_interaction_records_the_region(self):
        terrain = create_object(TerrainRoom, key="t_terrain", location=None)
        terrain.ndb.active_coordinates = (7, 9)
        npc = self._npc(self.start)
        self.char1.location = terrain
        with patch.object(
            wilderness_provider, "region_for_coordinates", return_value=REGION_KEY
        ):
            record_person_interaction(self.char1, npc)

        self.assertEqual(met_people(self.char1)[0].place, f"{PLACE_REGION}:{REGION_KEY}")

    @covers_requirement(
        "met-person-record::the-place-is-the-settlement-else-the-wilderness-region"
    )
    def test_an_unknown_place_keeps_the_stored_place(self):
        npc = self._npc(self.start)
        self._set_tick(10)
        record_person_interaction(self.char1, npc)
        self._set_tick(30)
        self.char1.location = self.room1
        record_person_interaction(self.char1, npc)

        person = met_people(self.char1)[0]
        self.assertEqual(person.place, f"{PLACE_SETTLEMENT}:{Z_MAP_KEY}")
        self.assertEqual((person.tick, person.seq), (30, 2))

    def test_a_placeless_room_records_no_new_person(self):
        self.char1.location = self.room1
        record_person_interaction(self.char1, self._npc(self.room1))
        self.assertIsNone(self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE))
        self.assertEqual(met_people(self.char1), ())

    @covers_requirement(
        "met-person-record::possessed-interactions-are-recorded-for-the-owning-character"
    )
    def test_the_owner_receives_a_possessed_interaction(self):
        companion = create_object(NPC, key="t_companion", location=self.start)
        join_party(companion, self.char1)
        enter_possession(self.char1, companion)
        self.assertEqual(companion.db.possessed_by, self.char1.pk)

        record_person_interaction(companion, self._npc(self.start))

        self.assertEqual([person.stable_key for person in met_people(self.char1)], [NAMED_KEY])
        self.assertIsNone(companion.attributes.get(MET_PEOPLE_ATTRIBUTE))

    def test_a_mismatched_possession_binding_records_nothing(self):
        companion = create_object(NPC, key="t_companion", location=self.start)
        join_party(companion, self.char1)
        # A stale mirror naming a character the companion is not bound to: the
        # interaction must not be attributed to either character.
        companion.db.possessed_by = self.char2.pk

        record_person_interaction(companion, self._npc(self.start))

        self.assertIsNone(self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE))
        self.assertIsNone(self.char2.attributes.get(MET_PEOPLE_ATTRIBUTE))
        self.assertIsNone(companion.attributes.get(MET_PEOPLE_ATTRIBUTE))

    @covers_requirement(
        "met-person-record::vanished-npcs-are-skipped-on-read-and-dropped-on-write"
    )
    def test_a_deleted_npc_disappears_from_reads_and_the_next_write(self):
        npc = self._npc(self.start)
        record_person_interaction(self.char1, npc)
        self.assertEqual(len(met_people(self.char1)), 1)

        npc.delete()
        self.assertEqual(met_people(self.char1), ())

        record_person_interaction(
            self.char1, self._npc(self.start, stable_key=OTHER_NAMED_KEY)
        )
        stored = self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE)
        self.assertEqual(set(stored["entries"]), {OTHER_NAMED_KEY})

    @covers_requirement(
        "met-person-record::vanished-npcs-are-skipped-on-read-and-dropped-on-write"
    )
    def test_an_npc_that_loses_its_named_policy_is_dropped(self):
        npc = self._npc(self.start)
        record_person_interaction(self.char1, npc)
        self.assertEqual(len(met_people(self.char1)), 1)

        npc.db.portrait_policy = {"mode": "generic"}
        self.assertEqual(met_people(self.char1), ())

        record_person_interaction(
            self.char1, self._npc(self.start, stable_key=OTHER_NAMED_KEY)
        )
        stored = self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE)
        self.assertEqual(set(stored["entries"]), {OTHER_NAMED_KEY})

    @covers_requirement(
        "met-person-record::the-place-is-the-settlement-else-the-wilderness-region"
    )
    def test_an_instance_room_resolves_one_level_through_its_origin(self):
        instance = create_object(InstanceRoom, key="t_instance", location=None)
        self.assertIsNone(interaction_place(instance))
        instance.origin_room = self.start
        self.assertEqual(interaction_place(instance), f"{PLACE_SETTLEMENT}:{Z_MAP_KEY}")
        terrain = create_object(TerrainRoom, key="t_origin_terrain", location=None)
        terrain.ndb.active_coordinates = (3, 4)
        wilderness_instance = create_object(InstanceRoom, key="t_wild_instance", location=None)
        wilderness_instance.origin_room = terrain
        with patch.object(
            wilderness_provider, "region_for_coordinates", return_value=REGION_KEY
        ):
            self.assertEqual(
                interaction_place(wilderness_instance), f"{PLACE_REGION}:{REGION_KEY}"
            )
        nested = create_object(InstanceRoom, key="t_nested_instance", location=None)
        nested.origin_room = instance
        self.assertIsNone(interaction_place(nested))

    def test_place_labels_resolve_through_the_published_registries(self):
        self.assertEqual(place_label(f"{PLACE_SETTLEMENT}:{Z_MAP_KEY}"), "測試錨地")
        self.assertEqual(place_label(f"{PLACE_SETTLEMENT}:t_absent_map"), "t_absent_map")
        self.assertEqual(place_label(f"{PLACE_REGION}:{REGION_KEY}"), "測試地域")
        self.assertEqual(place_label(f"{PLACE_REGION}:t_absent_region"), "t_absent_region")
        self.assertEqual(place_label("t_unknown_prefix"), "t_unknown_prefix")
        self.assertEqual(place_label(None), "")

    def test_a_corrupt_record_is_logged_and_never_overwritten(self):
        corrupt = {"schema_version": 1, "seq": "not-a-count", "entries": {}}
        self.char1.attributes.add(MET_PEOPLE_ATTRIBUTE, corrupt)
        with patch("world.rules.met_people.log_warn") as warn:
            record_person_interaction(self.char1, self._npc(self.start))
            self.assertEqual(met_people(self.char1), ())
        self.assertEqual(
            [call.args[0] for call in warn.call_args_list],
            ["met_people_record_corrupt", "met_people_record_corrupt"],
        )
        self.assertEqual(self.char1.attributes.get(MET_PEOPLE_ATTRIBUTE), corrupt)
