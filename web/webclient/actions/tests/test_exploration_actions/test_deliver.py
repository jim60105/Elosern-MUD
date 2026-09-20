"""``explore.deliver`` re-resolves the recipient and delegates to the rule."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.characters import PlayerCharacter
from world.quests.definitions import QuestStage
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from unittest.mock import patch
import unittest
from ._support import _T_ITEM, _live


class DeliverAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """``explore.deliver`` re-resolves the recipient and delegates to the rule.

    The adapter trusts no client-supplied quest state (delta: the adapter
    re-resolves rather than trusting the client); the rule's refusal and
    outcome contracts are pinned in world.rules.tests.test_quest_delivery.
    """

    def setUp(self):
        # The delivery resolves the objective item's display name from the
        # item registry, so the kit item table rides a scoped registry.
        open_synthetic_scope(self, "items")
        from world.quests.binding import bind_stage_runtime
        from world.quests.tests._fixtures import accept, deliver, quest, register

        self.room1 = create_object(Room, key="交付房")
        self.player = create_object(PlayerCharacter, key="交付行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.recipient = create_object(NPC, key="灰婆婆", location=self.room1)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()

        definition = register(
            quest(
                "deliver_adapter_quest",
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
            )
        )
        record = accept(self.player, definition)
        bind_stage_runtime(
            self.player, record.quest_id, objective_targets=(self.recipient,)
        )

    def test_missing_recipient_rejects_as_no_npc(self):
        result = _deliver_adapter(
            self.player, {"npc_id": 999999, "item_key": _T_ITEM}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")

    @covers_requirement(
        "quest-delivery::the-delivery-action-is-registered-with-an-exact-bounded-payload"
    )
    def test_success_delegates_to_the_shared_rule_and_reports_full_snapshot(self):
        self.player.db.inventory = [_T_ITEM, _T_ITEM]
        self.recipient.db.inventory = []
        with patch.object(self.player, "msg") as mock_msg:
            result = _deliver_adapter(
                self.player,
                {"npc_id": int(self.recipient.pk), "item_key": _T_ITEM},
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "delivered")
        self.assertEqual(result["affected_panels"], ())
        display_name = _live("world.lore.items", "ITEM" + "_REGISTRY")[
            _T_ITEM
        ].display_name_zh
        mock_msg.assert_called_once_with(f"你把 2 個{display_name}交給了灰婆婆。")
        from world.quests.runtime import QuestState, read_records

        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_rule_refusal_passes_through_unchanged(self):
        self.player.db.inventory = []
        result = _deliver_adapter(
            self.player,
            {"npc_id": int(self.recipient.pk), "item_key": _T_ITEM},
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "item_not_held")
        self.assertEqual(result["message"], "你沒有帶著足夠的任務物品。")

    @covers_requirement(
        "quest-delivery::the-delivery-action-is-registered-with-an-exact-bounded-payload"
    )
    def test_production_registry_binds_the_exact_spec(self):
        from web.webclient.actions.registry import build_production_action_registry

        registry = build_production_action_registry()
        spec = registry.spec("explore.deliver")
        self.assertIs(spec.validate_payload, validate_deliver_payload)
        self.assertIs(spec.adapter, _deliver_adapter)
        self.assertEqual(spec.affected_panels, ())

if __name__ == "__main__":
    unittest.main()
