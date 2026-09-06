"""Tests for the shared deterministic quest-item delivery rule.

One rule, two surfaces: every test exercises
``world.rules.quest_delivery.deliver_quest_item`` — the entry point both the
``explore.deliver`` action adapter and the ``交付`` command call — so the
refusals, the transferred quantity, and the observability boundary are pinned
at the seam where the surfaces cannot diverge.
"""

import unittest
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.ai.profiles import default_profiles
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    deliver,
    quest,
    register,
)
from world.rules.combat_session import engage
from world.rules.quest_delivery import (
    REASON_IN_COMBAT,
    REASON_ITEM_NOT_HELD,
    REASON_NO_ACTIVE_DELIVERY,
    REASON_NOT_COLOCATED,
    REASON_TRANSFER_FAILED,
    DeliveryStageView,
    active_deliveries_for_recipient,
    deliver_quest_item,
)
from world.rules.tests._combat_session_helpers import _monster
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def _all_profiles_disabled() -> dict:
    """Every ``LLM_PROFILES`` entry switched off: the offline configuration."""
    raw = default_profiles()
    for values in raw.values():
        if isinstance(values, dict) and "enabled" in values:
            values["enabled"] = False
    return raw


class _DeliveryWorldBase(QuestRegistryIsolation, EvenniaTest):
    """One room, one holder with a bound quantity-2 delivery, one bystander."""

    quantity = 2

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="delivery rule room")
        self.player = create_object(PlayerCharacter, key="delivery holder")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(NPC, key="灰婆婆", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        self.bystander = create_object(NPC, key="旁觀者", location=self.room)
        self.bystander.race = "human"
        self.bystander.apply_race_baseline()

        self.definition = register(
            quest(
                "deliver_rule_quest",
                stages=(QuestStage(0, deliver("healing_potion", quantity=self.quantity)),),
            )
        )
        self.record = accept(self.player, self.definition)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    # -- snapshot helpers ---------------------------------------------------

    def _world_snapshot(self):
        return (
            list(self.player.db.inventory or []),
            list(self.recipient.db.inventory or []),
            [dict(entry) for entry in (self.player.db.quest_log or [])],
        )


class OfflineDeliveryTests(_DeliveryWorldBase):
    """The delivery completes with every generative profile disabled (task 6.1)."""

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_delivery_completes_end_to_end_with_all_profiles_disabled(self):
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []

        with override_settings(LLM_PROFILES=_all_profiles_disabled()):
            outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertTrue(outcome.applied)
        self.assertIsNone(outcome.code)
        self.assertEqual(list(self.player.db.inventory), [])
        self.assertEqual(list(self.recipient.db.inventory), ["healing_potion", "healing_potion"])
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(outcome.message, "你把 2 個治療藥水交給了灰婆婆。")

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_partially_advanced_stage_is_completed_by_one_hand_over(self):
        self.player.db.inventory = ["healing_potion"] * 3
        self.recipient.db.inventory = []
        from world.rules.npc_intents import _transfer_items

        # Advance the stage halfway through the LLM-driven transfer path:
        # 1 of 2 potions moved, progress 1, 2 potions left held.
        _transfer_items(self.player, self.recipient, "healing_potion", 1)
        record = read_records(self.player)[0]
        self.assertEqual(record.stage_progress, 1)

        self.assertEqual(list(self.player.db.inventory), ["healing_potion", "healing_potion"])
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertTrue(outcome.applied)
        self.assertEqual(list(self.player.db.inventory), ["healing_potion"])
        self.assertEqual(
            list(self.recipient.db.inventory), ["healing_potion"] * 2
        )
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 2)

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_partially_advanced_stage_refuses_without_the_exact_remainder(self):
        self.player.db.inventory = ["healing_potion"]
        self.recipient.db.inventory = []
        from world.rules.npc_intents import _transfer_items

        _transfer_items(self.player, self.recipient, "healing_potion", 1)

        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_ITEM_NOT_HELD)
        self.assertEqual(self._world_snapshot(), before)


class DeliveryParityTests(_DeliveryWorldBase):
    """Both surfaces funnel into the identical rule with identical outcomes."""

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_action_adapter_and_rule_produce_identical_outcomes(self):
        from web.webclient.actions.exploration_actions import _deliver_adapter

        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []

        result = _deliver_adapter(
            self.player,
            {"npc_id": int(self.recipient.pk), "item_key": "healing_potion"},
        )
        self.assertEqual(result["outcome"], "success")
        # The adapter's success message is the rule's success message.
        self.assertEqual(result["message"], "你把 2 個治療藥水交給了灰婆婆。")

        # Reset to the identical fixture and run the rule directly: identical
        # outcome, identical final state.
        self.player.db.quest_log = []
        record = accept(self.player, self.definition)
        bind_stage_runtime(
            self.player, record.quest_id, objective_targets=(self.recipient,)
        )
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []
        direct = deliver_quest_item(self.player, self.recipient, "healing_potion")
        self.assertTrue(direct.applied)
        self.assertEqual(direct.message, result["message"])
        self.assertEqual(read_records(self.player)[0].state, QuestState.COMPLETED)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_adapter_rejection_carries_the_rule_reason_unchanged(self):
        from web.webclient.actions.exploration_actions import _deliver_adapter

        self.player.db.inventory = []
        result = _deliver_adapter(
            self.player,
            {"npc_id": int(self.recipient.pk), "item_key": "healing_potion"},
        )
        direct = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], direct.code)
        self.assertEqual(result["message"], direct.message)
        self.assertEqual(direct.code, REASON_ITEM_NOT_HELD)


class DeliveryRefusalTests(_DeliveryWorldBase):
    """One test per refusal branch; each asserts a byte-identical world (task 6.4)."""

    def setUp(self):
        super().setUp()
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_distant_recipient_is_refused(self):
        other_room = create_object(Room, key="far room")
        self.recipient.location = other_room

        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_NOT_COLOCATED)
        self.assertEqual(outcome.message, "對方不在這裡。")
        self.assertEqual(self._world_snapshot(), before)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_unbound_recipient_is_refused(self):
        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.bystander, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_NO_ACTIVE_DELIVERY)
        self.assertEqual(self._world_snapshot(), before)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_unheld_item_is_refused(self):
        self.player.db.inventory = []
        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_ITEM_NOT_HELD)
        self.assertEqual(self._world_snapshot(), before)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_insufficient_holdings_are_refused(self):
        self.player.db.inventory = ["healing_potion"]
        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_ITEM_NOT_HELD)
        self.assertEqual(self._world_snapshot(), before)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_rolled_back_transfer_refuses_and_restores_the_world(self):
        def failing_apply(plan):
            if plan.entity == self.recipient:
                raise RuntimeError("simulated recipient failure")
            from world.rules.npc_intents import _apply_plan

            return _apply_plan(plan)

        before = self._world_snapshot()
        with patch("world.rules.npc_intents._apply_plan", side_effect=failing_apply):
            outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_TRANSFER_FAILED)
        self.assertEqual(self._world_snapshot(), before)


class DeliveryCombatGateTests(BattlefieldIsolation, _DeliveryWorldBase):
    """The combat gate precedes every other rule-level check (design D6)."""

    def setUp(self):
        super().setUp()
        self.monster = _monster(key="delivery goblin")
        self.monster.location = self.room

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_active_combat_refuses_a_valid_delivery(self):
        engage(self.player, self.monster)
        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_IN_COMBAT)
        self.assertEqual(outcome.message, "戰鬥中無法交付物品。")
        self.assertEqual(self._world_snapshot(), before)

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_combat_refusal_precedes_the_other_checks(self):
        # Unbound recipient and empty inventory would each refuse on their own;
        # under active combat the combat code wins.
        engage(self.player, self.monster)
        self.player.db.inventory = []
        outcome = deliver_quest_item(self.player, self.bystander, "healing_potion")

        self.assertEqual(outcome.code, REASON_IN_COMBAT)


class DeliverySelectionTests(_DeliveryWorldBase):
    """The shared lowest-remaining selection (delta: quantity semantics)."""

    def _accept_second_quest(self, quantity: int):
        second = register(
            quest(
                "deliver_rule_quest_second",
                stages=(QuestStage(0, deliver("healing_potion", quantity=quantity)),),
            )
        )
        record = accept(self.player, second)
        bind_stage_runtime(
            self.player, record.quest_id, objective_targets=(self.recipient,)
        )
        return record

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_lowest_remaining_stage_is_selected_for_both_surfaces(self):
        # Bound quest: remaining 2 (quantity 2). Second quest: remaining 1.
        self._accept_second_quest(quantity=1)
        self.player.db.inventory = ["healing_potion"]
        self.recipient.db.inventory = []

        views = active_deliveries_for_recipient(self.player, self.recipient)
        self.assertEqual(len(views), 1)
        view = views[0]
        self.assertIsInstance(view, DeliveryStageView)
        self.assertEqual(view.remaining, 1)
        self.assertTrue(view.deliverable)

        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.message, "你把治療藥水交給了灰婆婆。")

        states = {r.definition_key: r for r in read_records(self.player)}
        self.assertEqual(
            states["deliver_rule_quest_second"].state, QuestState.COMPLETED
        )
        # The observer advanced every matching record by min(transferred, own
        # remaining): the quantity-2 quest gained 1 of 2.
        self.assertEqual(states["deliver_rule_quest"].stage_progress, 1)
        self.assertEqual(states["deliver_rule_quest"].state, QuestState.IN_PROGRESS)

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_unequal_remaining_pairs_refuse_when_the_lowest_is_unsatisfiable(self):
        self._accept_second_quest(quantity=1)
        self.player.db.inventory = []

        views = active_deliveries_for_recipient(self.player, self.recipient)
        self.assertEqual(len(views), 1)
        self.assertFalse(views[0].deliverable)
        self.assertEqual(views[0].reason[0], REASON_ITEM_NOT_HELD)

        before = self._world_snapshot()
        outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.code, REASON_ITEM_NOT_HELD)
        self.assertEqual(self._world_snapshot(), before)


class DeliveryObservabilityTests(_DeliveryWorldBase):
    """The ``delivery_handover`` boundary event (task 1.3)."""

    @covers_requirement(
        "quest-delivery::a-delivery-is-completable-with-every-generative-service-offline"
    )
    def test_successful_hand_over_schedules_boundary_event(self):
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []
        with (
            patch("world.rules.quest_delivery.log_info") as mock_log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertTrue(outcome.applied)
        mock_log.assert_called_once_with(
            "delivery_handover",
            context={
                "char": str(self.player.pk),
                "quest": self.definition.key,
                "npc": str(self.recipient.pk),
                "item": "healing_potion",
            },
        )

    @covers_requirement(
        "quest-delivery::a-delivery-is-refused-honestly-and-changes-nothing-when-refused"
    )
    def test_refused_hand_over_emits_no_boundary_event(self):
        self.player.db.inventory = []
        with (
            patch("world.rules.quest_delivery.log_info") as mock_log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = deliver_quest_item(self.player, self.recipient, "healing_potion")

        self.assertFalse(outcome.applied)
        mock_log.assert_not_called()
