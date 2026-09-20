"""The ``explore.deliver`` vocabulary: bound-recipient emission rules."""
from typeclasses.npcs import LLMNPC, NPC
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    deliver,
    quest,
    register,
)
from world.quests.definitions import QuestStage
from typeclasses.rooms import Room
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS
from world.quests.binding import bind_stage_runtime
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
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
from world.rules.tests._combat_session_helpers import open_synthetic_scope
import unittest
from ._support import VocabularyTestCase, _T_SPRAY, _player


class DeliveryAffordanceTests(QuestRegistryIsolation, VocabularyTestCase):
    """The ``explore.deliver`` vocabulary: bound-recipient emission rules.

    One enabled entry for a held item, one disabled entry with the shared
    rule's stable reason for an unheld item, no entry without an active bound
    stage, and validator-normalized params (delta scenarios + task 6.5).
    """

    def setUp(self):
        open_synthetic_scope(self, "items")
        super().setUp()
        self.room = create_object(Room, key="交付詞彙房")
        self.player = _player(key="交付持有者")
        self.player.location = self.room
        self.recipient = create_object(NPC, key="灰婆婆", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        self.bystander = create_object(NPC, key="旁觀村民", location=self.room)
        self.bystander.race = "human"
        self.bystander.apply_race_baseline()

        definition = register(
            quest(
                "deliver_affordance_quest",
                stages=(QuestStage(0, deliver(_T_SPRAY, quantity=2)),),
            )
        )
        self.record = accept(self.player, definition)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    def _deliver_entries(self, actor=None):
        vocabulary = exploration_affordances(actor or self.player)
        return [
            entry
            for entry in vocabulary
            if not entry.navigation and entry.action_id == "explore.deliver"
        ]

    @covers_requirement(
        "exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only"
    )
    def test_held_item_offers_one_enabled_normalized_entry(self):
        self.player.db.inventory = [_T_SPRAY, _T_SPRAY]
        (entry,) = self._deliver_entries()
        self.assertTrue(entry.enabled)
        self.assertIsNone(entry.disabled_reason)
        self.assertEqual(
            entry.params, {"npc_id": int(self.recipient.pk), "item_key": _T_SPRAY}
        )
        self.assertEqual(
            entry.label,
            f"交付 {SYNTH_ITEMS['t_ember_spray'].display_name_zh} 給 灰婆婆",
        )
        self.assertFalse(entry.freeform)
        self.assertIsNone(entry.surface)

    @covers_requirement(
        "exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only"
    )
    def test_unheld_item_keeps_a_disabled_entry_with_the_rule_reason(self):
        self.player.db.inventory = []
        (entry,) = self._deliver_entries()
        self.assertFalse(entry.enabled)
        self.assertEqual(
            entry.disabled_reason,
            ("item_not_held", "你沒有帶著足夠的任務物品。"),
        )

    @covers_requirement(
        "exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only"
    )
    def test_no_entry_without_an_active_bound_stage(self):
        self.player.db.inventory = [_T_SPRAY, _T_SPRAY]
        # The bystander is co-located but bound to nothing.
        vocabulary = exploration_affordances(self.player)
        bystander_entries = [
            entry
            for entry in vocabulary
            if not entry.navigation
            and entry.action_id == "explore.deliver"
            and entry.params["npc_id"] == int(self.bystander.pk)
        ]
        self.assertEqual(bystander_entries, [])

        # Dropping the record removes the recipient's entry entirely.
        self.player.db.quest_log = []
        self.assertEqual(self._deliver_entries(), [])

    @covers_requirement(
        "exploration-affordances::affordance-params-are-validator-normalized"
    )
    def test_entry_params_survive_the_registered_validator_round_trip(self):
        from web.webclient.actions.exploration_actions import validate_deliver_payload

        self.player.db.inventory = [_T_SPRAY, _T_SPRAY]
        (entry,) = self._deliver_entries()
        self.assertEqual(
            validate_deliver_payload(entry.params),
            {"npc_id": int(self.recipient.pk), "item_key": _T_SPRAY},
        )

    @covers_requirement(
        "exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only"
    )
    def test_delivery_entry_serializes_into_the_panel_target_with_params(self):
        from web.webclient.presentation.exploration import (
            _interact_targets,
            validate_exploration,
        )
        from web.webclient.actions.exploration_actions import validate_deliver_payload

        self.player.db.inventory = [_T_SPRAY, _T_SPRAY]
        payload = validate_exploration(
            {
                "schema_version": 2,
                "available": True,
                "kind": "exploration",
                "move": [],
                "look": {
                    "room": {
                        "identity": int(self.room.pk),
                        "display_name": "交付詞彙房",
                        "room": True,
                    },
                    "entities": [],
                    "objects": [],
                },
                "interact": _interact_targets(self.player),
                "character": {"available": True},
                "quests": {"available": True},
                "inventory": {"available": True},
            }
        )
        targets = payload["interact"]
        recipient_target = next(
            t for t in targets if t["identity"] == int(self.recipient.pk)
        )
        deliver_rows = [
            a
            for a in recipient_target["affordances"]
            if a["kind"] == "action" and a["action_id"] == "explore.deliver"
        ]
        self.assertEqual(len(deliver_rows), 1)
        self.assertTrue(deliver_rows[0]["enabled"])
        # The serialized row carries the validator-normalized dispatch payload
        # (schema version 2): the dock forwards it byte-for-byte.
        self.assertEqual(
            deliver_rows[0]["params"],
            {"npc_id": int(self.recipient.pk), "item_key": _T_SPRAY},
        )
        self.assertEqual(
            validate_deliver_payload(deliver_rows[0]["params"]),
            {"npc_id": int(self.recipient.pk), "item_key": _T_SPRAY},
        )

if __name__ == "__main__":
    unittest.main()
