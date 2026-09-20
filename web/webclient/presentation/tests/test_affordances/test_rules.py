"""Affordance rule resolution over the synthetic cast."""
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from world.rules.party import PARTY_MAX_COMPANIONS, join_party
from typeclasses.rooms import Room
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.combat_session import engage
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
from world.tests.synthetic_data import synthetic_registries
import unittest
from web.webclient.actions.exploration_actions import validate_move_payload
from ._support import (
    T_DIALOGUE_KEY,
    VocabularyTestCase,
    _T_KEYWORDS,
    _monster,
    _player,
)


@synthetic_registries("dialogue", "guild_branches")
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
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
        entries = self._entries_for(host)
        self.assertEqual(len(entries), len(_T_KEYWORDS))
        self.assertTrue(all(entry.action_id == "explore.talk_scripted" for entry in entries))
        keyword_ids = [entry.params["keyword_id"] for entry in entries]
        self.assertEqual(keyword_ids, _T_KEYWORDS)
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
        host.components.add(ScriptedDialogue.create(host, dialogue_key=T_DIALOGUE_KEY))
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
            GuildStaff.create(staff, service_id="staff", branch_key=SYNTH_GUILD_BRANCH_KEY)
        )
        shop = create_object(NPC, key="合成商", location=self.room)
        shop.components.add(
            Merchant.create(shop, service_id="shop", branch_key=SYNTH_GUILD_BRANCH_KEY)
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

if __name__ == "__main__":
    unittest.main()
