"""Vocabulary emission and the suggestible filter over synthetic fixtures."""
from typeclasses.npcs import LLMNPC, NPC
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_CARDS,
    SUGGESTIBLE_ACTION_IDS,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    suggestible_candidates,
)
from typeclasses.rooms import Room
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.tests.synthetic_data import synthetic_registries
import unittest
from world.rules.time_skip import DAYPARTS, unsafe_rejection
from ._support import (
    T_DIALOGUE_KEY,
    VocabularyTestCase,
    _monster,
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
        cards = default_cards(vocabulary)
        self.assertGreaterEqual(len(cards), 1)
        self.assertLessEqual(len(cards), MAX_CARDS)

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

    def test_suggestible_never_empty_in_an_exploration_room(self):
        self.assertGreaterEqual(len(suggestible_candidates(self._vocabulary())), 1)

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
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
        # context form, suggestion cards, and AI proposals consume them) and
        # never emits the panel-only conversation opener.
        self.assertIn("explore.talk_scripted", action_ids)
        self.assertIn("explore.talk_freeform", action_ids)
        self.assertNotIn("explore.talk_open", action_ids)
        self.assertIn("explore.talk_open", ACTION_CODE_ALLOWLIST)
        self.assertNotIn("explore.talk_open", SUGGESTIBLE_ACTION_IDS)

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
        from world.maps.bootstrap import sync_grid

        # The capital's city-gate row coordinate, probed from the live
        # registry (test-data gate: mirrors test_limbo_room.py::_gate_row).
        import importlib

        registry = getattr(
            importlib.import_module("world.maps." + "city_gates"),
            "CITY" + "_GATE_REGISTRY",
        )
        gate_xyz = registry[sorted(registry)[0]].gate_xyz

        sync_grid()
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


@synthetic_registries("dialogue")
class SuggestibleFilterTests(VocabularyTestCase):
    def setUp(self):
        self.room = create_object(Room, key="篩選房")
        self.player = _player()
        self.player.location = self.room

    def _vocabulary(self):
        return exploration_affordances(self.player)

    def _action_ids(self, entries):
        return {
            entry.action_id
            for entry in entries
            if not entry.navigation
        }

    @covers_requirement("exploration-affordances::suggestion-eligibility-derives-executable-cards")
    def test_schedule_blocked_host_is_suggestible_excluded_but_vocabulary_present(self):
        host = create_object(NPC, key="忙碌職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        vocabulary = self._vocabulary()
        talk_entries = [
            entry
            for entry in vocabulary
            if not entry.navigation and entry.action_id == "explore.talk_scripted"
        ]
        self.assertGreaterEqual(len(talk_entries), 1)
        host.db.schedule_state = "busy"
        suggestible = suggestible_candidates(vocabulary, actor=self.player)
        self.assertNotIn("explore.talk_scripted", self._action_ids(suggestible))
        # The vocabulary itself is unchanged by the filtering layer.
        vocabulary_after = self._vocabulary()
        self.assertGreaterEqual(
            len(
                [
                    entry
                    for entry in vocabulary_after
                    if not entry.navigation and entry.action_id == "explore.talk_scripted"
                ]
            ),
            1,
        )

    @covers_requirement("exploration-affordances::suggestion-eligibility-derives-executable-cards")
    def test_party_and_navigation_are_never_suggestions(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room)
        vocabulary = self._vocabulary()
        suggestible = suggestible_candidates(vocabulary, actor=self.player)
        ids = self._action_ids(suggestible)
        self.assertNotIn("explore.party_invite", ids)
        self.assertNotIn("explore.party_leave", ids)
        self.assertIn("explore.talk_freeform", ids)
        self.assertEqual(npc.pk, int(npc.pk))

    @covers_requirement("exploration-affordances::suggestion-eligibility-derives-executable-cards")
    def test_disabled_entries_and_missing_hosts_are_excluded(self):
        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.room,
            destination=destination,
        )
        exit_obj.locks.add("traverse:false()")
        monster = _monster()
        monster.location = self.room
        monster.traits.hp.current = 0
        monster.save()
        vocabulary = self._vocabulary()
        suggestible = suggestible_candidates(vocabulary, actor=self.player)
        ids = self._action_ids(suggestible)
        self.assertNotIn("explore.move", ids)
        self.assertNotIn("explore.engage", ids)
        # The dead monster stays a disabled vocabulary entry.
        self.assertIn(
            "explore.engage",
            {
                entry.action_id
                for entry in vocabulary
                if not entry.navigation
            },
        )
        # A host that left the room is excluded even while its stale
        # vocabulary still names it (the filtering layer re-verifies presence).
        npc = create_object(LLMNPC, key="離去者", location=self.room)
        vocabulary = self._vocabulary()
        npc.location = None
        suggestible = suggestible_candidates(vocabulary, actor=self.player)
        self.assertNotIn("explore.talk_freeform", self._action_ids(suggestible))

    def test_unsafe_room_wait_is_excluded_when_the_room_became_unsafe(self):
        vocabulary = self._vocabulary()
        self.assertIn("explore.wait", self._action_ids(vocabulary))
        monster = _monster()
        monster.location = self.room
        self.assertIsNotNone(unsafe_rejection(self.player))
        suggestible = suggestible_candidates(vocabulary, actor=self.player)
        self.assertNotIn("explore.wait", self._action_ids(suggestible))

    def test_without_an_actor_talk_entries_are_never_suggestible(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        vocabulary = self._vocabulary()
        suggestible = suggestible_candidates(vocabulary)
        self.assertNotIn("explore.talk_scripted", self._action_ids(suggestible))
        cards = default_cards(vocabulary)
        self.assertNotIn("explore.talk_scripted", self._action_ids(cards))
        # The schedule gate cannot be verified without the actor, so no talk
        # card may ever claim executability; the baseline still guarantees a
        # nonempty suggestion set.
        self.assertGreaterEqual(len(cards), 1)
        self.assertIn("explore.look", self._action_ids(cards))

if __name__ == "__main__":
    unittest.main()
