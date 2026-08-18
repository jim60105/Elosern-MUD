"""Canonical affordance vocabulary tests (action-options-affordance-contract).

Covers the frozen discriminated ``AffordanceView`` contract, the
``ACTION_CODE_ALLOWLIST`` / ``SUGGESTIBLE_ACTION_IDS`` / ``MAX_CARDS``
constants, the per-rule candidate builders with their version-1 identical
eligibility and disabled semantics, validator-normalized params (including the
freeform binding-only exception), the idle baseline, the vocabulary collector
order, and the suggestion-eligibility filtering.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
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
from web.webclient.actions.exploration_actions import validate_move_payload
from world.rules.combat_session import engage
from world.rules.party import PARTY_MAX_COMPANIONS, join_party
from world.rules.time_skip import DAYPARTS, unsafe_rejection


def _player(key="詞彙測試"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="哥布林", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class VocabularyTestCase(EvenniaTestCase):
    """Base fixture class that isolates the module-level battlefield registry.

    The skip-safety registry is keyed by actor pk; a retained test database
    can reuse pks across tests, so any engaged combat must be cleared in both
    directions to keep every test deterministic.
    """

    def setUp(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()

    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        super().tearDown()


class AffordanceContractTests(unittest.TestCase):
    def test_action_code_allowlist_is_exactly_the_eight_actions(self):
        self.assertEqual(
            ACTION_CODE_ALLOWLIST,
            (
                "explore.move",
                "explore.look",
                "explore.talk_scripted",
                "explore.talk_freeform",
                "explore.party_invite",
                "explore.party_leave",
                "explore.engage",
                "explore.wait",
            ),
        )
        self.assertNotIn("explore.interact", ACTION_CODE_ALLOWLIST)

    def test_suggestible_set_excludes_party_actions(self):
        self.assertEqual(
            SUGGESTIBLE_ACTION_IDS,
            set(ACTION_CODE_ALLOWLIST) - {"explore.party_invite", "explore.party_leave"},
        )

    def test_max_cards_is_five(self):
        self.assertEqual(MAX_CARDS, 5)

    def test_action_entry_shape_is_exact(self):
        entry = AffordanceView(
            action_id="explore.look",
            label="木箱",
            params={"target_id": 5},
            freeform=False,
            navigation=False,
            enabled=True,
            disabled_reason=None,
        )
        self.assertEqual(
            entry.as_dict(),
            {
                "action_id": "explore.look",
                "label": "木箱",
                "params": {"target_id": 5},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
        )

    def test_navigation_entry_shape_is_exact(self):
        entry = AffordanceView(
            surface="guild",
            label="公會服務",
            navigation=True,
            enabled=True,
            disabled_reason=None,
        )
        self.assertEqual(
            entry.as_dict(),
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
        )
        self.assertIsNone(entry.action_id)
        self.assertIsNone(entry.params)
        self.assertIsNone(entry.freeform)

    def test_discriminated_shapes_reject_mixed_fields(self):
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
                surface="guild",
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                surface="guild",
                label="公會服務",
                navigation=True,
                enabled=True,
                disabled_reason=None,
                action_id="explore.look",
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.take",
                label="拾取",
                params={},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                surface="bank",
                label="公會",
                navigation=True,
                enabled=True,
                disabled_reason=None,
            )

    def test_enabled_reason_exclusion_is_enforced(self):
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=False,
                disabled_reason=None,
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=("locked", "此出口目前無法通行。"),
            )

    def test_disabled_reason_serializes_as_an_exact_object(self):
        entry = AffordanceView(
            action_id="explore.engage",
            label="戰鬥",
            params={"monster_id": 7},
            freeform=False,
            navigation=False,
            enabled=False,
            disabled_reason=("target_dead", "目標已經死亡。"),
        )
        self.assertEqual(
            entry.as_dict()["disabled_reason"],
            {"code": "target_dead", "message": "目標已經死亡。"},
        )

    def test_wait_baseline_daypart_is_a_stable_value(self):
        from web.webclient.presentation.affordances import BASELINE_WAIT_DAYPART

        self.assertIn(BASELINE_WAIT_DAYPART, DAYPARTS)


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
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
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
        from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid

        sync_grid()
        grid = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
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


class AffordanceRuleTests(VocabularyTestCase):
    def setUp(self):
        self.room = create_object(Room, key="規則房")
        self.player = _player()
        self.player.location = self.room

    def _vocabulary(self):
        return exploration_affordances(self.player)

    def _entries_for(self, obj):
        return [
            entry
            for entry in self._vocabulary()
            if not entry.navigation
            and isinstance(entry.params, dict)
            and entry.params.get("npc_id") == int(obj.pk)
        ]

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_scripted_host_emits_one_entry_per_authored_keyword(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        entries = self._entries_for(host)
        self.assertEqual(len(entries), 6)
        self.assertTrue(all(entry.action_id == "explore.talk_scripted" for entry in entries))
        keyword_ids = [entry.params["keyword_id"] for entry in entries]
        self.assertEqual(keyword_ids, ["註冊", "任務", "公會", "工會", "回報", "再見"])
        self.assertTrue(all(entry.enabled for entry in entries))
        self.assertFalse(any(entry.freeform for entry in entries))

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_generative_npc_emits_freeform_with_binding_only_params(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        freeform = next(
            entry
            for entry in self._entries_for(npc)
            if entry.action_id == "explore.talk_freeform"
        )
        self.assertTrue(freeform.enabled)
        self.assertTrue(freeform.freeform)
        self.assertEqual(freeform.params, {"npc_id": int(npc.pk)})

    def test_party_invite_and_leave_params_are_validator_normalized(self):
        from world.rules.party import NOT_COMPANION_MESSAGE

        npc = create_object(LLMNPC, key="對話精靈", location=self.room)
        invite = next(
            entry
            for entry in self._entries_for(npc)
            if entry.action_id == "explore.party_invite"
        )
        self.assertEqual(invite.params, {"npc_id": int(npc.pk), "message": ""})
        self.assertTrue(invite.enabled)
        join_party(npc, self.player)
        leave = next(
            entry
            for entry in self._entries_for(npc)
            if entry.action_id == "explore.party_leave"
        )
        self.assertEqual(leave.params, {"npc_id": int(npc.pk)})
        self.assertTrue(leave.enabled)
        self.assertNotIn(
            "explore.party_invite", {entry.action_id for entry in self._entries_for(npc)}
        )
        self.assertIn("explore.talk_freeform", {entry.action_id for entry in self._entries_for(npc)})

    @covers_requirement("exploration-affordances::affordance-params-are-validator-normalized")
    def test_every_entry_params_are_validator_normalized(self):
        from web.webclient.actions.exploration_actions import (
            validate_engage_payload,
            validate_look_payload,
            validate_move_payload,
            validate_party_invite_payload,
            validate_party_leave_payload,
            validate_talk_scripted_payload,
            validate_wait_payload,
        )

        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        monster = _monster()
        monster.location = self.room
        destination = create_object(Room, key="東邊", location=None)
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room,
            destination=destination,
        )
        from evennia.objects.objects import DefaultObject

        create_object(DefaultObject, key="木箱", location=self.room)
        validators = {
            "explore.move": validate_move_payload,
            "explore.look": validate_look_payload,
            "explore.talk_scripted": validate_talk_scripted_payload,
            "explore.party_invite": validate_party_invite_payload,
            "explore.party_leave": validate_party_leave_payload,
            "explore.engage": validate_engage_payload,
            "explore.wait": validate_wait_payload,
        }
        for entry in self._vocabulary():
            if entry.navigation:
                continue
            if entry.action_id == "explore.talk_freeform":
                # The single documented exception: the binding-only shape is
                # never produced by a registered validator (which requires
                # speech); it is exactly {"npc_id": int}.
                self.assertEqual(entry.params, {"npc_id": int(npc.pk)})
                self.assertTrue(entry.freeform)
                continue
            validator = validators[entry.action_id]
            self.assertEqual(validator(entry.params), entry.params, entry.action_id)
            self.assertFalse(entry.freeform)

    def test_full_party_disables_the_invite_entry_with_the_reason(self):
        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.room),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.room)
        invite = next(
            entry
            for entry in self._entries_for(npc)
            if entry.action_id == "explore.party_invite"
        )
        self.assertFalse(invite.enabled)
        self.assertEqual(invite.disabled_reason, ("party_full", "你的隊伍已經滿了（最多 4 人）。"))
        self.assertEqual(invite.params, {"npc_id": int(npc.pk), "message": ""})

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_dead_monster_stays_a_disabled_engage_entry(self):
        monster = _monster()
        monster.location = self.room
        entry = next(
            entry
            for entry in self._vocabulary()
            if not entry.navigation
            and entry.action_id == "explore.engage"
            and entry.params["monster_id"] == int(monster.pk)
        )
        self.assertTrue(entry.enabled)
        monster.traits.hp.current = 0
        monster.save()
        entry = next(
            entry
            for entry in self._vocabulary()
            if not entry.navigation
            and entry.action_id == "explore.engage"
            and entry.params["monster_id"] == int(monster.pk)
        )
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason, ("target_dead", "目標已經死亡。"))

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_locked_exit_is_a_disabled_move_entry_with_normalized_params(self):
        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.room,
            destination=destination,
        )
        exit_obj.locks.add("traverse:false()")
        entry = next(
            entry
            for entry in self._vocabulary()
            if not entry.navigation and entry.action_id == "explore.move"
        )
        self.assertFalse(entry.enabled)
        self.assertEqual(entry.disabled_reason, ("locked", "此出口目前無法通行。"))
        self.assertEqual(
            entry.params,
            validate_move_payload(
                {"exit_ref": str(int(exit_obj.id)), "current_node": entry.params["current_node"]}
            ),
        )
        self.assertIsNotNone(entry.params["current_node"])

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_corrupt_dialogue_table_host_has_no_vocabulary_entries(self):
        # A host whose authored table cannot be resolved has no talk entries
        # in the vocabulary (no validator-normalized params exist for a
        # keywordless host); the version-1 panel's disabled
        # dialogue_unavailable affordance is a panel serialization
        # degradation, not a vocabulary entry.
        host = create_object(NPC, key="壞掉的NPC", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="unknown_table"))
        entries = self._entries_for(host)
        self.assertEqual(entries, [])
        self.assertFalse(
            any(
                not entry.navigation and entry.action_id == "explore.talk_scripted"
                for entry in self._vocabulary()
            )
        )

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_service_entries_attach_to_the_exact_local_host(self):
        staff = create_object(NPC, key="公會職員", location=self.room)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        shop = create_object(NPC, key="商人", location=self.room)
        shop.components.add(
            Merchant.create(shop, service_id="shop", branch_key="guild_branch_altoria")
        )
        monster = _monster()
        monster.location = self.room
        vocabulary = self._vocabulary()
        navigation = [entry for entry in vocabulary if entry.navigation]
        self.assertEqual(
            {(entry.surface, entry.label) for entry in navigation},
            {("guild", "公會服務"), ("shop", "商店")},
        )
        self.assertTrue(all(entry.enabled for entry in navigation))
        for entry in navigation:
            self.assertIsNone(entry.action_id)
            self.assertIsNone(entry.params)
            self.assertIsNone(entry.freeform)
        self.assertEqual(
            [entry.surface for entry in navigation], ["guild", "shop"]
        )
        # Navigation entries are dock openers, never suggestions.
        self.assertNotIn(
            "guild",
            [entry.action_id for entry in suggestible_candidates(vocabulary)],
        )
        self.assertNotIn(
            "shop",
            [entry.action_id for entry in suggestible_candidates(vocabulary)],
        )

    @covers_requirement("exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only")
    def test_combat_mode_yields_an_empty_vocabulary(self):
        monster = _monster()
        monster.location = self.room
        engage(self.player, monster)
        self.assertEqual(self._vocabulary(), ())


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
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
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
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
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


class DefaultCardsTests(VocabularyTestCase):
    def setUp(self):
        self.room = create_object(Room, key="卡片房")
        self.player = _player()
        self.player.location = self.room

    def _vocabulary(self):
        return exploration_affordances(self.player)

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_cards_are_a_strict_subset_of_the_vocabulary(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        monster = _monster()
        monster.location = self.room
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        self.assertGreaterEqual(len(cards), 1)
        self.assertLessEqual(len(cards), MAX_CARDS)
        union = {
            (entry.action_id, repr(entry.params), entry.label)
            for entry in vocabulary
            if not entry.navigation
        }
        for card in cards:
            self.assertIn((card.action_id, repr(card.params), card.label), union)
            self.assertTrue(card.enabled)
            self.assertIn(card.action_id, SUGGESTIBLE_ACTION_IDS)

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_objective_relevant_actions_rank_first(self):
        host = create_object(NPC, key="目標NPC", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        destination = create_object(Room, key="東邊", location=None)
        create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room,
            destination=destination,
        )
        vocabulary = self._vocabulary()
        cards = default_cards(
            vocabulary, objective_npc_ids=frozenset({int(host.pk)}), actor=self.player
        )
        first = cards[0]
        self.assertEqual(first.action_id, "explore.talk_scripted")
        self.assertEqual(first.params["npc_id"], int(host.pk))
        self.assertEqual(
            [entry.action_id for entry in cards[:3]],
            ["explore.talk_scripted", "explore.talk_scripted", "explore.talk_scripted"],
        )
        # Every objective-relevant talk entry precedes any move or baseline.
        seen_talk = 0
        for entry in cards:
            if entry.action_id == "explore.talk_scripted":
                seen_talk += 1
        self.assertEqual(seen_talk, len(cards))

    @covers_requirement("exploration-affordances::the-deterministic-degradation-fallback-derives-rule-cards")
    def test_talk_and_engage_precede_the_baseline_within_the_cap(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room)
        monster = _monster()
        monster.location = self.room
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        # The living monster makes the room unsafe, so wait is absent; the
        # talk and engage entries still precede the room-look baseline.
        self.assertEqual(
            [entry.action_id for entry in cards],
            ["explore.talk_freeform", "explore.engage", "explore.look"],
        )
        self.assertLessEqual(len(cards), MAX_CARDS)

    def test_cards_preserve_vocabulary_order_within_a_rank(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        vocabulary = self._vocabulary()
        cards = default_cards(vocabulary, actor=self.player)
        keyword_ids = [entry.params["keyword_id"] for entry in cards]
        self.assertEqual(
            keyword_ids,
            ["註冊", "任務", "公會", "工會", "回報"],
        )
        self.assertEqual(len(cards), 5)

    def test_default_cards_are_pure(self):
        vocabulary = self._vocabulary()
        before = [entry.as_dict() for entry in vocabulary]
        default_cards(vocabulary, actor=self.player)
        after = [entry.as_dict() for entry in self._vocabulary()]
        self.assertEqual(before, after)

    def test_cap_is_respected_even_with_many_objectives(self):
        host = create_object(NPC, key="公會職員", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        vocabulary = self._vocabulary()
        cards = default_cards(
            vocabulary, objective_npc_ids=frozenset({int(host.pk)}), actor=self.player
        )
        self.assertLessEqual(len(cards), MAX_CARDS)


if __name__ == "__main__":
    unittest.main()
