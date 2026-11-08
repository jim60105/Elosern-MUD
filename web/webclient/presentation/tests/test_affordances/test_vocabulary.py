"""Vocabulary emission over synthetic fixtures."""
from typeclasses.npcs import LLMNPC, NPC
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    SURFACES,
    AffordanceView,
    exploration_affordances,
)
from typeclasses.rooms import Room
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.tests.synthetic_data import synthetic_registries
import unittest
from ._support import (
    T_DIALOGUE_KEY,
    VocabularyTestCase,
    _player,
)


@synthetic_registries("dialogue")
class AffordanceVocabularyTests(VocabularyTestCase):
    def setUp(self):
        self.room = create_object(Room, key="詞彙房")
        self.player = _player()
        self.player.location = self.room

    def _vocabulary(self):
        return exploration_affordances(self.player)

    @covers_requirement("exploration-affordances::the-idle-baseline-guarantees-at-least-one-executable-entry")
    def test_empty_room_yields_baseline_room_look_and_wait(self):
        vocabulary = self._vocabulary()
        entries = [entry for entry in vocabulary if not entry.navigation]
        look = [
            entry
            for entry in entries
            if entry.action_id == "explore.look" and entry.params == {"room": True}
        ]
        wait = [entry for entry in entries if entry.action_id == "explore.wait"]
        self.assertEqual(len(look), 1)
        self.assertEqual(len(wait), 1)
        self.assertTrue(look[0].enabled)
        self.assertTrue(wait[0].enabled)
        self.assertEqual(wait[0].params, {"daypart": "noon"})

    def test_exploration_order_is_move_then_look_then_targets_then_baseline(self):
        destination = create_object(Room, key="東邊", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room,
            destination=destination,
        )
        from evennia.objects.objects import DefaultObject

        box = create_object(DefaultObject, key="木箱", location=self.room)
        host = create_object(NPC, key="路人", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        vocabulary = self._vocabulary()
        self.assertEqual(vocabulary[0].action_id, "explore.move")
        self.assertEqual(vocabulary[0].params["exit_ref"], str(int(exit_obj.id)))
        self.assertEqual(vocabulary[1].action_id, "explore.look")
        self.assertEqual(vocabulary[1].params, {"target_id": int(box.pk)})
        self.assertEqual(vocabulary[2].action_id, "explore.talk_scripted")
        self.assertEqual(vocabulary[2].params["npc_id"], int(host.pk))
        self.assertEqual(vocabulary[-2].action_id, "explore.look")
        self.assertEqual(vocabulary[-2].params, {"room": True})
        self.assertEqual(vocabulary[-1].action_id, "explore.wait")

    @covers_requirement("exploration-affordances::the-shared-read-only-affordance-vocabulary-supports-possessed-shop-access")
    def test_the_conversation_opening_code_is_allowlisted_but_never_emitted(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        create_object(LLMNPC, key="吟遊詩人", location=self.room)
        action_ids = {
            entry.action_id
            for entry in self._vocabulary()
            if not entry.navigation
        }
        # The vocabulary keeps the per-keyword and free-form entries (the
        # context form consumes them) and never emits the panel-only
        # conversation opener.
        self.assertIn("explore.talk_scripted", action_ids)
        self.assertIn("explore.talk_freeform", action_ids)
        self.assertNotIn("explore.talk_open", action_ids)
        self.assertIn("explore.talk_open", ACTION_CODE_ALLOWLIST)

    def test_creation_pending_and_absent_location_yield_an_empty_vocabulary(self):
        self.player.db.creation_pending = True
        self.assertEqual(self._vocabulary(), ())
        self.player.db.creation_pending = False
        self.player.location = None
        self.assertEqual(self._vocabulary(), ())

    def test_move_destinations_route_through_the_shared_encoder(self):
        """Every destination node — ordinary room, GridRoom, and TerrainRoom —
        is derived only through ``node_id_for_location``: the affordance
        module holds no duplicate room-type encoder (wiring-hardening D4)."""
        from unittest import mock

        from typeclasses.rooms import GridRoom, TerrainRoom
        from web.webclient.actions.node_ids import node_id_for_location
        from web.webclient.presentation import affordances as module
        from world.tests.geography_fixture import sync_test_settlements

        # The capital's city-gate row coordinate, probed from the live
        # registry (test-data gate: mirrors test_limbo_room.py::_gate_row).
        import importlib

        registry = getattr(
            importlib.import_module("world.maps." + "city_gates"),
            "CITY" + "_GATE_REGISTRY",
        )
        from world.maps.static_references import settlement_node_xyz

        gate_xyz = settlement_node_xyz(registry[sorted(registry)[0]].gate)

        sync_test_settlements((gate_xyz[2],))
        grid = GridRoom.objects.filter_xyz(xyz=gate_xyz).first()
        self.assertIsNotNone(grid)
        plain = create_object(Room, key="普通目的地", location=None)
        terrain = create_object(TerrainRoom, key="荒野目的地", location=None)
        terrain.ndb.active_coordinates = (7, 11)
        destinations = {"東": plain, "南": grid, "西": terrain}
        for key, destination in destinations.items():
            create_object(
                "evennia.objects.objects.DefaultExit",
                key=key,
                location=self.room,
                destination=destination,
            )
        self.assertFalse(
            hasattr(module, "_destination_node"),
            "the duplicate destination encoder must not exist",
        )
        seen = []
        real = module.node_id_for_location

        def _spy(location):
            seen.append(location)
            return real(location)

        with mock.patch.object(module, "node_id_for_location", side_effect=_spy):
            vocabulary = self._vocabulary()
        move_entries = [
            entry
            for entry in vocabulary
            if not entry.navigation and entry.action_id == "explore.move"
        ]
        self.assertEqual(len(move_entries), 3)
        for destination in destinations.values():
            self.assertIn(
                destination, seen,
                "every destination goes through the shared encoder",
            )
        self.assertEqual(
            seen.count(self.room), 1,
            "the current node derives once through the same encoder",
        )
        for entry in move_entries:
            self.assertEqual(
                entry.params["current_node"],
                real(self.room),
                "the current node is byte-identical to the shared encoder",
            )


if __name__ == "__main__":
    unittest.main()
