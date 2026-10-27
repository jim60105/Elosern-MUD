"""Synthetic privacy, precision and visited-ground contracts for world_map."""
import json
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch

from tools.spec_traceability import covers_requirement
from web.webclient.presentation import world_map as panel
from web.webclient.presentation.world_map_geometry import raster_rings
from elosern_map_core.references import wilderness_cell_ref
from world.rules.map_knowledge import encode_wild
from world.maps.wilderness_provider import WILDERNESS_NAME


RING=[[0,0],[10,0],[10,10],[0,10],[0,0]]
LANDMARK=encode_wild(WILDERNESS_NAME,12,13)
SECRET="SECRET_DISTRICT_781"
VILLAGE="SECRET_VILLAGE_913"
DUNGEON="SECRET_DUNGEON_361"
PUBLIC="VISIBLE_PORT_329"


def fixtures():
    stack=ExitStack()
    stack.enter_context(patch("world.lore.map_districts.MAP_DISTRICT_REGISTRY",{
        SECRET:NS(landmark=wilderness_cell_ref((12, 13)))}))
    stack.enter_context(patch.object(panel.geometry,"common_layer",return_value=dict(coastline=RING,borders=[],nations=[])))
    stack.enter_context(patch.object(panel.geometry,"district_geometry",return_value={SECRET:dict(
        name=SECRET,outline=[RING],landmark=dict(name="SECRET_LANDMARK_632",x=12.5,y=13.5),
        nations=[],terrain=[dict(region="secret_terrain",polygons=[RING])],rivers=[],ridge=[],roads=[])}))
    records=[]
    for name,hidden,x in ((PUBLIC,False,3),(VILLAGE,True,4),(DUNGEON,True,5)):
        records.append((SECRET,dict(id=name.lower(),name=name,kind="hidden" if hidden else "harbour",x=x,y=2),hidden,
                        frozenset((encode_wild(WILDERNESS_NAME,x,2),))))
    stack.enter_context(patch.object(panel.geometry,"place_geometry",return_value=records))
    return stack


class WorldMapPrivacyTests(TestCase):
    @covers_requirement("webclient-world-map::world-scope-reveals-only-common-geography-and-permitted-district-knowledge")
    def test_full_serialization_filters_unlit_and_hidden_and_separates_players(self):
        with fixtures():
            fresh=panel.assemble_world_map(visit_ids=set(),current=(1,2),markers=[])
            lit=panel.assemble_world_map(visit_ids={LANDMARK},current=(1,2),markers=[])
            other=panel.assemble_world_map(visit_ids=set(),current=(1,2),markers=[])
            self.assertEqual(fresh,other)
            serialized=json.dumps(fresh)
            for secret in (SECRET,VILLAGE,DUNGEON,PUBLIC,"SECRET_LANDMARK_632","secret_terrain"):
                self.assertNotIn(secret,serialized)
            self.assertEqual(set(fresh["districts"][0]),{"id","lit","outline"})
            self.assertEqual(fresh["districts"][0]["id"],lit["districts"][0]["id"])
            self.assertIn(PUBLIC,json.dumps(lit))
            self.assertNotIn(VILLAGE,json.dumps(lit))
            self.assertNotIn(DUNGEON,json.dumps(lit))
            lit["districts"][0]["outline"][0][0][0]=99
            again=panel.assemble_world_map(visit_ids=set(),current=(1,2),markers=[])
            self.assertEqual(again["districts"][0]["outline"][0][0],[0,0])

    @covers_requirement("webclient-world-map::world-scope-reveals-only-common-geography-and-permitted-district-knowledge")
    def test_visited_hidden_place_survives_unlit_district(self):
        with fixtures():
            body=panel.assemble_world_map(visit_ids={encode_wild(WILDERNESS_NAME,4,2)},current=(4.5,2.5),markers=[])
            self.assertEqual([row["name"] for row in body["visited_places"]],[VILLAGE])
            self.assertFalse(body["districts"][0]["lit"])
            self.assertNotIn(DUNGEON,json.dumps(body))
            self.assertEqual(body["current"],dict(x=4.5,y=2.5))

    @covers_requirement("webclient-world-map::unknown-world-commission-destinations-are-rounded-before-serialization")
    def test_marker_whitelist_removes_all_exact_alternate_metadata(self):
        destination=NS(world_cell=(123,178),definition_key="synthetic",quest_id="quest_synthetic",
                       node_id=encode_wild(WILDERNESS_NAME,123,178))
        with patch("web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
                   return_value=((destination,),frozenset((destination.quest_id,)))), \
             patch("world.maps.district_partition.district_at",return_value=SECRET), \
             patch("world.quests.definitions.QUEST_DEFINITION_REGISTRY",{"synthetic":NS(display_name="Synthetic commission")}):
            rough=panel.quest_markers(NS(),set())[0]
            exact=panel.quest_markers(NS(),{SECRET})[0]
        self.assertEqual((rough["x"],rough["y"]),(100,200))
        self.assertTrue(rough["approximate"])
        self.assertEqual(set(rough),{"id","title","tracked","x","y","approximate"})
        self.assertNotIn("123",json.dumps(rough))
        self.assertNotIn("178",json.dumps(rough))
        self.assertNotIn(destination.node_id,json.dumps(rough))
        self.assertEqual((exact["x"],exact["y"]),(123.5,178.5))
        self.assertFalse(exact["approximate"])

    def test_world_scope_is_on_demand_and_fresh_or_corrupt_knowledge_is_read_only(self):
        from web.webclient.actions.map_actions import validate_map_view_payload,map_view_adapter
        from web.webclient.presentation.registry import build_production_registry,PanelUnavailableError
        registry=build_production_registry()
        self.assertIn("world_map",registry.on_demand_panel_names)
        self.assertNotIn("world_map",registry.eager_panel_names)
        payload=validate_map_view_payload({"scope":"world"})
        self.assertEqual(map_view_adapter(None,payload)["affected_panels"],("world_map",))
        attrs=NS(get=lambda key,**kwargs:None)
        with fixtures(),patch.object(panel.geometry,"current_point",return_value=(4.5,7.5)), \
             patch.object(panel,"quest_markers",return_value=[]):
            result=panel.world_map_presenter(NS(actor=NS(attributes=attrs)))
            self.assertEqual(result["current"],dict(x=4.5,y=7.5))
            with patch.object(panel,"persisted_visits",side_effect=panel.KnowledgeError("corrupt")):
                with self.assertRaises(PanelUnavailableError):
                    panel.world_map_presenter(NS(actor=NS(attributes=NS(get=lambda key:{}))))

    def test_terrain_union_keeps_distinct_regions_and_holes(self):
        rings=raster_rings([(0,0),(5,0),(0,5),(5,5)])
        self.assertEqual(rings,[[[0,0],[10,0],[10,10],[0,10],[0,0]]])
        hole=raster_rings([(x,y) for y in range(0,15,5) for x in range(0,15,5) if (x,y)!=(5,5)])
        self.assertEqual(len(hole),2)
        with patch("world.lore.wilderness_regions.CONTINENT_FRAME_CELLS",10), \
             patch("world.maps.district_partition.district_at",return_value="t_district"), \
             patch("world.maps.wilderness_provider.region_for_coordinates",
                   side_effect=lambda x,y:"t_west" if x < 5 else "t_east"), \
             patch("world.maps.wilderness_provider.nominal_nation_for_coordinates",
                   side_effect=lambda x,y:"t_nation_w" if x < 5 else "t_nation_e"):
            terrain,nations=panel.geometry.terrain_layers.__wrapped__()
        regions={row["region"]:row["polygons"] for row in terrain["t_district"]}
        self.assertEqual(regions["t_west"],[[[0,0],[5,0],[5,10],[0,10],[0,0]]])
        self.assertEqual(regions["t_east"],[[[5,0],[10,0],[10,10],[5,10],[5,0]]])
        self.assertEqual(nations["t_district"],["t_nation_e","t_nation_w"])

    def test_coordinate_free_interior_uses_canonical_place_and_unknown_is_unavailable(self):
        from typeclasses.rooms import Room, InstanceRoom
        room=Mock(spec=Room)
        room.tags.all.return_value=["t_interior"]
        actor=NS(location=room)
        with patch("world.lore.settlements.places.PLACE_REGISTRY",{
                "t_interior":NS(settlement_key="t_anchor")}), \
             patch("web.webclient.presentation.map_quest_destinations.ANCHOR_GEOGRAPHY_REGISTRY",{
                "t_anchor":NS(cell=(123,456))}):
            self.assertEqual(panel.geometry.current_point(actor),(123.5,456.5))
            instance=Mock(spec=InstanceRoom)
            instance.attributes.get.return_value=room
            self.assertEqual(panel.geometry.current_point(NS(location=instance)),(123.5,456.5))
            room.tags.all.return_value=[]
            self.assertIsNone(panel.geometry.current_point(actor))
            with self.assertRaises(panel.PanelUnavailableError):
                panel.world_map_presenter(NS(actor=actor))

    @covers_requirement("webclient-world-map::unknown-world-commission-destinations-are-rounded-before-serialization")
    def test_registered_service_hunt_reaches_world_presenter_with_privacy(self):
        from typeclasses.rooms import Room, InstanceRoom
        from web.webclient.presentation.tests.test_map_quest_destinations import (
            _patch_geography, _record, _DEFINITIONS,
        )
        from world.quests.runtime import to_storage

        _patch_geography(self)
        room = Mock(spec=Room)
        room.tags.all.return_value = ["t_service"]
        instance = Mock(spec=InstanceRoom)
        instance.attributes.get.return_value = room
        log = [to_storage(_record(name)) for name in ("hunt", "grid", "site")]
        with fixtures(), \
             patch("world.lore.settlements.places.PLACE_REGISTRY", {"t_service": NS(settlement_key="town")}), \
             patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", _DEFINITIONS), \
             patch("world.maps.district_partition.district_at", return_value=SECRET):
            for location in (room, instance):
                actor = NS(location=location, db=NS(possessed_by=None, quest_log=log),
                           attributes=NS(get=lambda key, **kwargs: log if key == "quest_log" else None))
                body = panel.world_map_presenter(NS(actor=actor))
                self.assertEqual(body["current"], dict(x=300.5, y=400.5))
                markers = {row["id"]: row for row in body["quest_markers"]}
                self.assertEqual(set(markers), {"q_hunt", "q_grid", "q_site"})
                self.assertEqual((markers["q_hunt"]["x"], markers["q_hunt"]["y"]), (50, 0))
                self.assertTrue(all(m["approximate"] for m in markers.values()))
                self.assertNotIn(SECRET, json.dumps(body))

    def test_anchor_classification_keeps_villages_and_dungeons_visit_only(self):
        from world.lore.anchors import AnchorKind
        anchors={
            "t_village":NS(kind=AnchorKind.ELVEN_VILLAGE,display_name_zh=VILLAGE),
            "t_dungeon":NS(kind=AnchorKind.DUNGEON,display_name_zh=DUNGEON),
            "t_capital":NS(kind=AnchorKind.CAPITAL,display_name_zh=PUBLIC),
        }
        with patch("world.lore.anchors.ANCHOR_REGISTRY",anchors), \
             patch("world.lore.anchors.ANCHOR_GEOGRAPHY_REGISTRY",{
                key:NS(cell=(100+i,200)) for i,key in enumerate(anchors)}), \
             patch("world.lore.anchor_placement.ANCHOR_PLACEMENT_REGISTRY",{}), \
             patch("world.lore.wilderness_regions.HARBOR_SITE_REGISTRY",{}), \
             patch("world.maps.district_partition.district_at",return_value=SECRET):
            records=panel.geometry._place_geometry("uncached-probe")
        policy={row["name"]:hidden for _,row,hidden,_ in records}
        self.assertTrue(policy[VILLAGE])
        self.assertTrue(policy[DUNGEON])
        self.assertFalse(policy[PUBLIC])


class WorldMapTrailTests(TestCase):
    @covers_requirement("webclient-world-map::world-trails-retain-visited-ground-with-bounded-precision-reduction")
    def test_threshold_and_large_downsampling_preserve_coverage(self):
        cells={(x,y) for y in range(100) for x in range(200)}
        ids={encode_wild(WILDERNESS_NAME,x,y) for x,y in cells}
        initial=panel.trail_for_visits(ids)
        self.assertEqual(initial["resolution_km"],1)
        self.assertEqual(initial["rows"],[[y,[[0,200]]] for y in range(100)])
        ids.add(encode_wild(WILDERNESS_NAME,200,100))
        reduced=panel.trail_for_visits(ids)
        self.assertEqual(reduced["resolution_km"],5)
        self.assertEqual(reduced["rows"],[[y,[[0,40]]] for y in range(20)]+[[20,[[40,1]]]])
        large={encode_wild(WILDERNESS_NAME,x,y) for y in range(0,2700,5) for x in range(0,2700,5)}
        body=panel.trail_for_visits(large)
        self.assertEqual(body["rows"],[[y,[[0,540]]] for y in range(540)])
        self.assertEqual(body["resolution_km"],5)
        checker={encode_wild(WILDERNESS_NAME,x,y) for y in range(0,2700,5) for x in range(0,2700,10)}
        with fixtures():
            assembled=panel.assemble_world_map(visit_ids=checker,current=(1,2),markers=[])
        self.assertEqual(sum(len(runs) for _,runs in assembled["trail"]["rows"]),145_800)
        self.assertEqual(assembled["trail"]["rows"][-1][1][-1],[538,1])
