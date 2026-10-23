"""Synthetic landmark discovery through real committed traversal seams."""
from contextlib import contextmanager
from types import SimpleNamespace as NS
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.map_knowledge import _derive_node_id, parse_knowledge
from world.tests.synthetic_grid_map import load_synthetic_grid, synthetic_rooms


class LandmarkArrivalTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        load_synthetic_grid()
        self.source,self.landmark,self.end=synthetic_rooms()
        self.char1.location=self.source
        self.district=NS(key="t_district",landmark_node=_derive_node_id(self.landmark),district_name_zh="測試丘陵")
        self.registry=patch("world.lore.map_districts.MAP_DISTRICT_REGISTRY",{"t_district":self.district})
        self.registry.start()
        self.addCleanup(self.registry.stop)
        self.exit=next(exit for exit in self.source.exits if exit.destination == self.landmark)
        # Discovery owns no clock semantics; keep these tests on the arrival
        # writer/transaction seam rather than every clock event consumer.
        charge=patch("world.rules.movement.charge_movement")
        charge.start()
        self.addCleanup(charge.stop)

    def move(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.exit.at_traverse(self.char1,self.landmark)

    def narratives(self,msg):
        return [call.args[0] for call in msg.call_args_list if call.args and isinstance(call.args[0],str)
                and call.args[0].startswith("你移動到了")]

    @covers_requirement("map-district-discovery::first-committed-landmark-arrival-adds-one-discovery-narrative")
    def test_grid_first_and_repeat_arrivals_emit_one_committed_narrative(self):
        with patch.object(self.char1,"msg") as msg,patch("world.rules.map_discovery.log_info") as info:
            self.move()
            self.assertEqual(self.narratives(msg),[f"你移動到了{self.landmark.key}。\n已探明：測試丘陵"])
            self.assertIn(self.district.landmark_node,{visit.node_id for visit in parse_knowledge(self.char1)})
            info.assert_called_once_with("map_district_discovered",context={"char":self.char1.pk,"district":"t_district"})
            self.char1.location=self.source
            msg.reset_mock()
            self.move()
            self.assertEqual(self.narratives(msg),[f"你移動到了{self.landmark.key}。"])
            self.assertEqual(info.call_count,1)

    @covers_requirement("map-district-discovery::first-committed-landmark-arrival-adds-one-discovery-narrative")
    def test_veto_and_late_settlement_failure_have_no_discovery_or_record(self):
        with patch.object(self.char1,"msg") as msg:
            with patch.object(self.char1,"at_pre_move",return_value=False):
                self.move()
            self.assertEqual(self.narratives(msg),[])
            self.assertIs(self.char1.location,self.source)
            with patch("world.rules.party.follow_companions",side_effect=RuntimeError("late failure")):
                with self.assertRaises(RuntimeError):
                    self.move()
            self.assertIs(self.char1.location,self.source)
            self.assertIsNone(self.char1.attributes.get("map_knowledge"))
            self.assertEqual(self.narratives(msg),[])

    def test_outer_rollback_discards_discovery_callback(self):
        with patch.object(self.char1,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.exit.at_traverse(self.char1,self.landmark)
                    raise RuntimeError("outer rollback")
        self.assertEqual(self.narratives(msg),[])

    @covers_requirement("map-district-discovery::first-committed-landmark-arrival-adds-one-discovery-narrative")
    def test_corrupt_knowledge_and_swallowed_writer_failure_do_not_announce(self):
        corrupt={"schema_version":99,"visited":{}}
        self.char1.attributes.add("map_knowledge",corrupt)
        with patch.object(self.char1,"msg") as msg,patch("world.rules.map_discovery.log_warn") as warning, \
             patch("world.rules.map_knowledge.log_warn") as writer_warning:
            self.move()
            self.assertEqual(self.char1.attributes.get("map_knowledge"),corrupt)
            self.assertNotIn("已探明",str(self.narratives(msg)))
            warning.assert_called()
            writer_warning.assert_called()
        self.char1.attributes.remove("map_knowledge")
        self.char1.location=self.source
        original=self.char1.attributes.add
        def failed_write(key,value,*args,**kwargs):
            if key == "map_knowledge":
                raise RuntimeError("knowledge write failed")
            return original(key,value,*args,**kwargs)
        with patch.object(self.char1,"msg") as msg,patch.object(self.char1.attributes,"add",side_effect=failed_write), \
             patch("world.rules.map_knowledge.log_warn") as warning,patch("world.rules.map_discovery.log_warn"):
            self.move()
            self.assertNotIn("已探明",str(self.narratives(msg)))
            self.assertIsNone(self.char1.attributes.get("map_knowledge"))
            self.assertEqual(warning.call_args.args[0],"map_knowledge_record_arrival_failed")

    def test_delivery_failure_does_not_compensate_committed_move(self):
        with patch.object(self.char1,"msg",side_effect=RuntimeError("offline")), \
             patch("world.rules.map_discovery.log_warn") as warning:
            # Quiet relocation removes unrelated look output; only the commit
            # callback fails, after all deterministic writes have settled.
            from world.rules.map_discovery import publish_traversal_narrative
            from world.rules.map_knowledge import record_arrival
            self.char1.location=self.landmark
            record_arrival(self.char1)
            with self.captureOnCommitCallbacks(execute=True):
                publish_traversal_narrative(self.char1,set())
            self.assertIs(self.char1.location,self.landmark)
            self.assertEqual(warning.call_args.args[0],"map_discovery_delivery_failed")

    def test_possessed_npc_nested_settlement_narrates_once_and_direct_move_never_discovers(self):
        npc=create_object(NPC,key="t_puppet",location=self.room1)
        npc.db.possessed_by=self.char1.pk
        exit=create_object(Exit,key="t_door",location=self.room1,destination=self.room2)
        with patch.object(npc,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            exit.at_traverse(npc,self.room2)
        self.assertEqual(len(self.narratives(msg)),1)
        with patch.object(npc,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            npc.move_to(self.room1,quiet=True,move_type="teleport")
        self.assertEqual(self.narratives(msg),[])
        with patch.object(self.char1,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            self.char1.move_to(self.landmark,quiet=True,move_type="teleport")
        self.assertEqual(self.narratives(msg),[])

    @covers_requirement("map-district-discovery::first-committed-landmark-arrival-adds-one-discovery-narrative")
    def test_gateway_and_wilderness_arrival_use_canonical_landmarks(self):
        from world.lore.wilderness_entry import WildernessEntryPoint,WildernessGate
        from world.maps.bootstrap import sync_wilderness
        from world.rules.travel_cost import TraversalStatus
        from world.rules.map_knowledge import encode_wild
        from world.maps.wilderness_provider import WILDERNESS_NAME
        # Import production-derived population constants before replacing the
        # entry registry. Population itself is unrelated to this seam test.
        import world.maps.wilderness_population
        sync_wilderness()
        entry=WildernessEntryPoint(anchor_key="t_gate",shape=("#",),origin_xy=(500,500),
                                  gates=(WildernessGate("w",(0,0),"t_probe_grid"),))
        cell=entry.approach_cell(entry.gates[0])
        gate=create_object(WildernessGateExit,key="t_out",location=self.source,destination=self.source)
        gate.db.anchor_key="t_gate"
        gate.db.gate_direction="w"
        @contextmanager
        def preflight(*args,**kwargs):
            yield NS(status=TraversalStatus.RESOLVED,cost=None)
        self.district.landmark_node=encode_wild(WILDERNESS_NAME,*cell)
        with patch("world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",{"t_gate":entry}), \
             patch("typeclasses.exits.WILDERNESS_ENTRY_REGISTRY",{"t_gate":entry}), \
             patch("world.rules.travel_cost.preflight_movement_cost",preflight), \
             patch("world.maps.wilderness_population.ensure_population"), \
             patch.object(self.char1,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            gate.at_traverse(self.char1,self.source)
        self.assertEqual(self.char1.location.coordinates,cell)
        self.assertEqual(len(self.narratives(msg)),1)
        self.assertIn("已探明：測試丘陵",self.narratives(msg)[0])
        destination=(cell[0]+1,cell[1])
        self.district.landmark_node=encode_wild(WILDERNESS_NAME,*destination)
        step=next(exit for exit in self.char1.location.exits if exit.key == "east")
        with patch("world.rules.travel_cost.preflight_movement_cost",preflight), \
             patch("world.maps.wilderness_population.ensure_population"), \
             patch.object(self.char1,"msg") as msg,self.captureOnCommitCallbacks(execute=True):
            step.at_traverse(self.char1,self.char1.location)
        self.assertEqual(self.char1.location.coordinates,destination)
        self.assertEqual(len(self.narratives(msg)),1)
        self.assertIn("已探明：測試丘陵",self.narratives(msg)[0])
