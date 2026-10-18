"""Tests for the member item transfer rule (party-item-transfer).

Intended requirement IDs, recorded here until the capability is synced into
``openspec/specs/`` and ``tools.spec_traceability list`` can hand out the
canonical ones (``covers_requirement`` decorators are added then):

- ``party-item-transfer::transfers-happen-only-outside-combat``
- ``party-item-transfer::giver-and-receiver-are-distinct-authorized-members``
- ``party-item-transfer::equipped-and-locked-items-cannot-be-transferred``
- ``party-item-transfer::a-transfer-moves-both-bags-atomically-and-costs-nothing``
- ``party-item-transfer::transfer-rejections-are-stable-and-observable``
"""

from dataclasses import replace
from unittest.mock import patch

from django.db import transaction

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey
from world.quests import runtime as quest_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    accept_auto,
    acquire,
    quest,
    register,
    stage_active_record,
)
from world.quests.transitions import apply_quest_log_replacement, stage_pin_reason
from world.rules import party_inventory
from world.rules.affinity import seed_affinity
from world.rules.clock import get_world_clock
from world.rules.equipment import apply_inventory_plan as real_apply_inventory_plan
from world.rules.equipment import materialize_registry_object, toggle_equipment
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.party import join_party
from world.rules.party_inventory import (
    MAX_TRANSFER_QUANTITY,
    REASON_INVALID_QUANTITY,
    REASON_ITEM_EQUIPPED,
    REASON_ITEM_LOCKED,
    REASON_ITEM_NOT_HELD,
    REASON_TRANSFER_IN_COMBAT,
    REASON_TRANSFER_SAME_MEMBER,
    TRANSFER_MESSAGES,
    PartyTransferError,
    transfer_item,
)
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
)
from world.rules.possession import enter_possession
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import make_item, synthetic_registries

from ._combat_session_helpers import _race_key

_POTION = make_item("t_transfer_potion", display_name_zh="測試藥水", sellable=False)
_BLADE = make_item(
    "t_transfer_blade",
    display_name_zh="測試長劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_SEAL = make_item(
    "t_transfer_seal", display_name_zh="測試徽記", sellable=False, guild_property=True
)
_REWARD = make_item("t_transfer_reward", display_name_zh="測試獎勵", sellable=False)


class PartyTransferTestCase(EvenniaTestCase):
    """Builds a co-located commander and companions over the synthetic kit."""

    def setUp(self):
        super().setUp()
        scope = synthetic_registries(
            "races",
            "static_tiers",
            "subraces",
            "items",
            extra={
                "items": {
                    row.key: row for row in (_POTION, _BLADE, _SEAL, _REWARD)
                }
            },
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.room = create_object(Room, key="測試房間")
        self.commander = create_object(
            PlayerCharacter, key="指揮者", location=self.room
        )
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        join_party(npc, self.commander)
        return npc

    def outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def hold(self, entity, *keys):
        entity.db.inventory = list(keys)

    def mirror(self, entity, item_key):
        return materialize_registry_object(entity, item_key)

    def transfer(self, **overrides):
        fields = {
            "acting": self.commander,
            "giver_id": self.commander.pk,
            "receiver_id": self.aila.pk,
            "item_key": _POTION.key,
            "quantity": 1,
        }
        fields.update(overrides)
        return transfer_item(**fields)

    def _attribute_rows(self, entity):
        """The stored Attribute rows of an entity as detached, sortable tuples."""
        return sorted(
            (str(attribute.key), str(attribute.category or ""), repr(attribute.value))
            for attribute in entity.attributes.all()
        )

    def _bag_state(self, entity):
        """Key list, contained identities, locations and contents-cache keys."""
        objects = sorted(
            entity.contents_get(content_type="object"), key=lambda obj: obj.pk
        )
        return (
            list(entity.db.inventory or []),
            [obj.pk for obj in objects],
            [obj.db_location_id for obj in objects],
            sorted(entity.contents_cache._pkcache),
        )

    def _assert_rejected(self, reason, **overrides):
        members = (self.commander, self.aila, self.kahn)
        before = {entity.pk: self._attribute_rows(entity) for entity in members}
        bags = {entity.pk: self._bag_state(entity) for entity in members}
        with self.assertRaises(PartyTransferError) as context:
            self.transfer(**overrides)
        error = context.exception
        self.assertEqual(error.reason, reason)
        self.assertEqual(
            error.message, TRANSFER_MESSAGES.get(reason) or PARTY_SCOPE_MESSAGES[reason]
        )
        for entity in members:
            self.assertEqual(self._attribute_rows(entity), before[entity.pk])
            self.assertEqual(self._bag_state(entity), bags[entity.pk])
        return error


class TransferSuccessTests(PartyTransferTestCase):
    """A transfer moves both bags in both directions and costs nothing."""

    def test_commander_moves_items_to_a_present_companion(self):
        self.hold(self.commander, *([_POTION.key] * 3))
        first = self.mirror(self.commander, _POTION.key)
        second = self.mirror(self.commander, _POTION.key)
        third = self.mirror(self.commander, _POTION.key)

        outcome = self.transfer(quantity=2)

        self.assertEqual(outcome.giver, self.commander)
        self.assertEqual(outcome.receiver, self.aila)
        self.assertEqual(outcome.item_key, _POTION.key)
        self.assertEqual(outcome.quantity, 2)
        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertEqual(self.aila.db.inventory, [_POTION.key, _POTION.key])
        self.assertEqual(
            sorted(obj.pk for obj in self.commander.contents_get()),
            [third.pk],
        )
        self.assertEqual(
            sorted(obj.pk for obj in self.aila.contents_get()), [first.pk, second.pk]
        )

    def test_companion_moves_items_back_to_the_commander(self):
        self.hold(self.aila, _POTION.key)
        mirror = self.mirror(self.aila, _POTION.key)

        self.transfer(giver_id=self.aila.pk, receiver_id=self.commander.pk)

        self.assertEqual(self.aila.db.inventory, [])
        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertEqual(list(self.aila.contents_get()), [])
        self.assertEqual([obj.pk for obj in self.commander.contents_get()], [mirror.pk])

    def test_knocked_out_receiver_is_admitted(self):
        self.hold(self.commander, _POTION.key)
        self.aila.traits.hp.current = 1

        self.transfer()

        self.assertEqual(self.aila.db.inventory, [_POTION.key])

    def test_knocked_out_giver_is_admitted(self):
        self.hold(self.aila, _POTION.key)
        self.aila.traits.hp.current = 1

        self.transfer(giver_id=self.aila.pk, receiver_id=self.commander.pk)

        self.assertEqual(self.commander.db.inventory, [_POTION.key])

    def test_missing_mirrors_are_materialized_at_the_receiver(self):
        self.hold(self.commander, _POTION.key, _POTION.key)

        self.transfer(quantity=2)

        self.assertEqual(self.aila.db.inventory, [_POTION.key, _POTION.key])
        mirrors = list(self.aila.contents_get(content_type="object"))
        self.assertEqual(len(mirrors), 2)
        self.assertEqual(
            sorted(obj.db.registry_key for obj in mirrors), [_POTION.key, _POTION.key]
        )

    def test_free_copies_of_a_partly_equipped_stack_can_move(self):
        self.hold(self.commander, _BLADE.key, _BLADE.key)
        self.assertEqual(
            toggle_equipment(self.commander, _BLADE.key).outcome, "success"
        )

        self.transfer(item_key=_BLADE.key)

        self.assertEqual(self.commander.db.inventory, [_BLADE.key])
        self.assertEqual(self.aila.db.inventory, [_BLADE.key])

    def test_transfer_is_free_of_time_and_affinity(self):
        seed_affinity(self.aila, self.commander, 12)
        tick = get_world_clock().tick
        affinity = self.aila.relations.affinity_for(self.commander)
        self.hold(self.commander, _POTION.key)

        self.transfer()

        self.assertEqual(get_world_clock().tick, tick)
        self.assertEqual(self.aila.relations.affinity_for(self.commander), affinity)


class TransferRejectionTests(PartyTransferTestCase):
    """Every rejection carries its stable code and writes nothing."""

    def test_combat_rejects_the_transfer(self):
        self.hold(self.commander, _POTION.key)
        with patch(
            "world.rules.combat_session.is_in_active_session",
            side_effect=lambda actor: actor is self.aila,
        ):
            self._assert_rejected(REASON_TRANSFER_IN_COMBAT)

    def test_absent_receiver_is_refused(self):
        elsewhere = create_object(Room, key="別處")
        absent = create_object(NPC, key="遠方", location=self.room, home=elsewhere)
        absent.race = _race_key()
        absent.apply_race_baseline()
        join_party(absent, self.commander)
        absent.move_to(elsewhere, quiet=True)
        self.hold(self.commander, _POTION.key)

        self._assert_rejected(REASON_MEMBER_NOT_PRESENT, receiver_id=absent.pk)

    def test_non_member_is_refused_and_never_replaced(self):
        outsider = self.outsider()
        self.hold(self.commander, _POTION.key)

        self._assert_rejected(REASON_NOT_PARTY_MEMBER, receiver_id=outsider.pk)

        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertFalse(outsider.db.inventory)

    def test_same_member_is_refused(self):
        self._assert_rejected(
            REASON_TRANSFER_SAME_MEMBER,
            giver_id=self.aila.pk,
            receiver_id=self.aila.pk,
        )

    def test_invalid_quantities_are_refused(self):
        self.hold(self.commander, *([_POTION.key] * MAX_TRANSFER_QUANTITY))
        for quantity in (0, MAX_TRANSFER_QUANTITY + 1, True, "2", None):
            with self.subTest(quantity=quantity):
                self._assert_rejected(REASON_INVALID_QUANTITY, quantity=quantity)

    def test_unknown_item_is_refused(self):
        self._assert_rejected(REASON_ITEM_NOT_HELD, item_key="t_transfer_unknown")

    def test_guild_property_is_locked(self):
        self.hold(self.commander, _SEAL.key)

        self._assert_rejected(REASON_ITEM_LOCKED, item_key=_SEAL.key)

    def test_exam_restricted_member_locks_the_transfer(self):
        self.hold(self.commander, _POTION.key)
        for restricted in (self.commander, self.aila):
            with self.subTest(restricted=restricted.key):
                restricted.db.guild_exam_restriction = {
                    "host_id": restricted.pk,
                    "exam_id": "t_transfer_exam",
                    "allowed_skills": [],
                }
                try:
                    self._assert_rejected(REASON_ITEM_LOCKED)
                finally:
                    restricted.db.guild_exam_restriction = None

    def test_item_not_held_when_the_giver_holds_fewer(self):
        self.hold(self.commander, _POTION.key)

        self._assert_rejected(REASON_ITEM_NOT_HELD, quantity=2)

    def test_equipped_item_is_refused(self):
        self.hold(self.commander, _BLADE.key)
        self.assertEqual(
            toggle_equipment(self.commander, _BLADE.key).outcome, "success"
        )

        self._assert_rejected(REASON_ITEM_EQUIPPED, item_key=_BLADE.key)

        self.assertEqual(self.commander.db.inventory, [_BLADE.key])
        self.assertEqual(self.commander.db.equipment["weapon_main"], _BLADE.key)


class RejectionOrderTests(PartyTransferTestCase):
    """The design's rejection order is observable when several checks fail."""

    def test_combat_wins_over_an_invalid_quantity(self):
        self.hold(self.commander, _POTION.key)
        with patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            self._assert_rejected(REASON_TRANSFER_IN_COMBAT, quantity=0)

    def test_membership_wins_over_same_member(self):
        outsider = self.outsider()

        self._assert_rejected(
            REASON_NOT_PARTY_MEMBER,
            giver_id=outsider.pk,
            receiver_id=outsider.pk,
        )

    def test_same_member_wins_over_an_invalid_quantity(self):
        self._assert_rejected(
            REASON_TRANSFER_SAME_MEMBER,
            giver_id=self.aila.pk,
            receiver_id=self.aila.pk,
            quantity=0,
        )

    def test_locked_wins_over_an_insufficient_quantity(self):
        self.hold(self.commander, _SEAL.key)

        self._assert_rejected(
            REASON_ITEM_LOCKED, item_key=_SEAL.key, quantity=5
        )

    def test_insufficient_quantity_wins_over_an_equipped_conflict(self):
        self.hold(self.commander, _BLADE.key)
        self.assertEqual(
            toggle_equipment(self.commander, _BLADE.key).outcome, "success"
        )

        self._assert_rejected(
            REASON_ITEM_NOT_HELD, item_key=_BLADE.key, quantity=2
        )

    def test_unknown_item_wins_over_an_exam_restriction(self):
        self.commander.db.guild_exam_restriction = {
            "host_id": self.commander.pk,
            "exam_id": "t_transfer_exam",
            "allowed_skills": [],
        }
        try:
            self._assert_rejected(
                REASON_ITEM_NOT_HELD, item_key="t_transfer_unknown"
            )
        finally:
            self.commander.db.guild_exam_restriction = None


class TransferAtomicityTests(PartyTransferTestCase):
    """Any failure restores both bags, contained objects and their caches."""

    def _both_bags(self):
        return {
            entity.pk: self._bag_state(entity)
            for entity in (self.commander, self.aila)
        }

    def test_failure_after_the_giver_write_restores_both_bags(self):
        self.hold(self.commander, _POTION.key, _POTION.key)
        first = self.mirror(self.commander, _POTION.key)
        second = self.mirror(self.commander, _POTION.key)
        before = self._both_bags()
        calls = []

        def failing(plan):
            calls.append(plan.entity)
            if len(calls) == 2:
                raise RuntimeError("injected receiver write failure")
            real_apply_inventory_plan(plan)

        with patch.object(party_inventory, "apply_inventory_plan", failing):
            with self.assertRaises(RuntimeError):
                self.transfer(quantity=2)

        for entity in (self.commander, self.aila):
            self.assertEqual(self._bag_state(entity), before[entity.pk])
        self.assertEqual(
            sorted(obj.pk for obj in self.commander.contents_get()),
            sorted([first.pk, second.pk]),
        )

    def test_failure_after_the_receiver_write_restores_both_bags(self):
        self.hold(self.commander, _POTION.key)
        self.mirror(self.commander, _POTION.key)
        before = self._both_bags()
        calls = []

        def failing(plan):
            calls.append(plan.entity)
            real_apply_inventory_plan(plan)
            if len(calls) == 2:
                raise RuntimeError("injected failure after the receiver write")

        with patch.object(party_inventory, "apply_inventory_plan", failing):
            with self.assertRaises(RuntimeError):
                self.transfer()

        for entity in (self.commander, self.aila):
            self.assertEqual(self._bag_state(entity), before[entity.pk])

    def test_failure_during_materialization_leaves_no_cached_orphan(self):
        self.hold(self.commander, _POTION.key, _POTION.key)
        before = self._both_bags()
        created = []
        real_materialize = party_inventory.materialize_registry_object

        def failing(container, item_key):
            if created:
                raise RuntimeError("injected second materialization failure")
            mirror = real_materialize(container, item_key)
            created.append(mirror)
            return mirror

        with patch.object(
            party_inventory, "materialize_registry_object", failing
        ):
            with self.assertRaises(RuntimeError):
                self.transfer(quantity=2)

        orphan = created[0]
        self.assertFalse(ObjectDB.objects.filter(pk=orphan.pk).exists())
        self.assertNotIn(orphan.pk, ObjectDB.__instance_cache__)
        for entity in (self.commander, self.aila):
            self.assertEqual(self._bag_state(entity), before[entity.pk])

    def test_a_refused_move_restores_both_bags(self):
        self.hold(self.commander, _POTION.key, _POTION.key)
        first = self.mirror(self.commander, _POTION.key)
        second = self.mirror(self.commander, _POTION.key)
        before = self._both_bags()

        with patch.object(second, "move_to", return_value=False):
            with self.assertRaises(party_inventory._TransferRefused):
                self.transfer(quantity=2)

        for entity in (self.commander, self.aila):
            self.assertEqual(self._bag_state(entity), before[entity.pk])
        self.assertEqual(
            sorted(obj.db_location_id for obj in (first, second)),
            [self.commander.pk, self.commander.pk],
        )

    def test_failure_after_a_pin_release_restores_the_room_attribute(self):
        self.hold(self.commander, _POTION.key)
        self.room.db.pin_reasons = ["before"]
        real_plan = party_inventory.plan_inventory_delta

        def plan_with_pin(entity, additions=(), removals=()):
            plan = real_plan(entity, additions=additions, removals=removals)
            if entity is self.aila:
                return replace(plan, acquire=([], ((self.room, (), ("t_reason",)),)))
            return plan

        def failing(plan):
            if plan.entity is self.aila:
                self.room.db.pin_reasons = []
                raise RuntimeError("injected after the pin release")
            real_apply_inventory_plan(plan)

        with patch.object(party_inventory, "plan_inventory_delta", plan_with_pin):
            with patch.object(party_inventory, "apply_inventory_plan", failing):
                with self.assertRaises(RuntimeError):
                    self.transfer()

        self.assertEqual(self.room.db.pin_reasons, ["before"])

    def test_cleanup_failure_does_not_mask_the_transfer_failure(self):
        self.hold(self.commander, _POTION.key)
        self.mirror(self.commander, _POTION.key)
        before = self._both_bags()

        def failing(plan):
            raise RuntimeError("injected transfer failure")

        with patch.object(party_inventory, "apply_inventory_plan", failing):
            with patch.object(
                party_inventory,
                "_flush_rolled_back_instances",
                side_effect=RuntimeError("injected cleanup failure"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "injected transfer failure"
                ):
                    self.transfer()

        for entity in (self.commander, self.aila):
            self.assertEqual(self._bag_state(entity), before[entity.pk])


class TransferMessageTests(EvenniaTestCase):
    """Rejection messages are fixed and complete."""

    def test_rejection_messages_are_fixed_and_complete(self):
        self.assertEqual(
            TRANSFER_MESSAGES,
            {
                REASON_TRANSFER_IN_COMBAT: "戰鬥中無法交換物品。",
                REASON_TRANSFER_SAME_MEMBER: "不能交給同一個人。",
                REASON_ITEM_EQUIPPED: "已裝備的物品無法交換；請先卸下。",
                REASON_ITEM_LOCKED: "這件物品無法交換。",
                REASON_ITEM_NOT_HELD: "對方沒有足夠的這件物品。",
                REASON_INVALID_QUANTITY: "數量不正確。",
            },
        )


class TransferObservabilityTests(PartyTransferTestCase):
    """A committed transfer emits exactly one info event."""

    def test_successful_transfer_emits_one_info_event(self):
        self.hold(self.commander, _POTION.key)
        with patch.object(party_inventory, "log_info") as log_info:
            with self.captureOnCommitCallbacks(execute=True):
                self.transfer()
        log_info.assert_called_once_with(
            "party_transfer",
            context={
                "giver": self.commander.pk,
                "receiver": self.aila.pk,
                "item": _POTION.key,
                "quantity": 1,
            },
        )

    def test_a_rolled_back_transfer_emits_no_event(self):
        self.hold(self.commander, _POTION.key)

        def failing(plan):
            raise RuntimeError("injected")

        with patch.object(party_inventory, "log_info") as log_info:
            with patch.object(party_inventory, "apply_inventory_plan", failing):
                with self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaises(RuntimeError):
                        self.transfer()
        log_info.assert_not_called()


class TransferPlanObserverTests(QuestRegistryIsolation, PartyTransferTestCase):
    """Plans are built inside the transfer savepoint.

    A plan's ACQUIRE replacement dispatches quest-completion observers, whose
    contract is to defer through ``transaction.on_commit``. A rolled-back
    transfer must discard that deferred work.
    """

    def setUp(self):
        super().setUp()
        definition = register(
            quest(
                "transfer_acquire_quest",
                stages=(QuestStage(0, acquire(_POTION.key, quantity=1)),),
            )
        )
        self.record = accept(self.aila, definition)
        self.effects = []

    def _observer(self, entity, record, definition):
        transaction.on_commit(lambda: self.effects.append(record.quest_id))

    def test_a_committed_transfer_publishes_the_plan_completion(self):
        self.hold(self.commander, _POTION.key)
        with patch.object(
            quest_runtime, "_QUEST_COMPLETION_OBSERVERS", [self._observer]
        ):
            with self.captureOnCommitCallbacks(execute=True):
                self.transfer()
        self.assertEqual(self.effects, [self.record.quest_id])

    def test_a_rolled_back_transfer_discards_the_plan_completion(self):
        self.hold(self.commander, _POTION.key)

        def failing(plan):
            raise RuntimeError("injected")

        with patch.object(
            quest_runtime, "_QUEST_COMPLETION_OBSERVERS", [self._observer]
        ):
            with patch.object(party_inventory, "apply_inventory_plan", failing):
                with self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaises(RuntimeError):
                        self.transfer()
        self.assertEqual(self.effects, [])


class TransferChainPinTests(QuestRegistryIsolation, PartyTransferTestCase):
    """An AUTO reward chain's released pins join the outer rollback snapshot.

    Receiving the potion completes an AUTO quest whose paid item completes a
    second, room-bound ACQUIRE stage. That second room is absent from the
    receiver plan's own pin operations, so only the transfer's preflight can
    restore it when a later write fails.
    """

    def setUp(self):
        super().setUp()
        reward_definition = register(
            quest(
                "transfer_chain_reward",
                stages=(QuestStage(0, acquire(_REWARD.key, quantity=1)),),
            )
        )
        staged = stage_active_record(self.aila, reward_definition)
        apply_quest_log_replacement(
            self.aila,
            [
                replace(record, stage_room_id=self.room.pk)
                if record.quest_id == staged.quest_id
                else record
                for record in read_records(self.aila)
            ],
        )
        self.chain_reason = stage_pin_reason(
            self.aila.pk, staged.quest_id, staged.stage_index
        )
        self.room.db.pin_reasons = [self.chain_reason]
        trigger_definition = register(
            quest(
                "transfer_chain_trigger",
                stages=(QuestStage(0, acquire(_POTION.key, quantity=1)),),
            )
        )
        accept_auto(
            self.aila,
            trigger_definition,
            QuestReward(copper=0, items=(ItemQuantity(_REWARD.key, 1),), merit=0),
        )

    def test_a_late_failure_restores_a_chain_released_pin(self):
        self.hold(self.commander, _POTION.key)
        self.mirror(self.commander, _POTION.key)
        calls = []

        def failing(plan):
            calls.append(plan.entity)
            real_apply_inventory_plan(plan)
            if len(calls) == 2:
                raise RuntimeError("injected failure after the receiver write")

        with patch.object(party_inventory, "apply_inventory_plan", failing):
            with self.assertRaises(RuntimeError):
                self.transfer()

        self.assertEqual(self.room.db.pin_reasons, [self.chain_reason])
        self.assertNotIn(_REWARD.key, list(self.aila.db.inventory or []))


class PossessedTransferTests(EvenniaTest):
    """A possessed figure is only the anchor; the commander authorizes."""

    def setUp(self):
        super().setUp()
        scope = synthetic_registries(
            "races",
            "static_tiers",
            "subraces",
            "items",
            extra={"items": {_POTION.key: _POTION}},
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        enter_possession(self.char1, self.aila)

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.char1)
        return npc

    def test_a_possessed_figure_can_organize_another_pair(self):
        self.char1.db.inventory = [_POTION.key]

        outcome = transfer_item(
            self.aila, self.char1.pk, self.kahn.pk, _POTION.key, 1
        )

        self.assertEqual(outcome.giver, self.char1)
        self.assertEqual(self.kahn.db.inventory, [_POTION.key])

    def test_combat_on_the_possessed_figure_alone_bars_the_transfer(self):
        self.char1.db.inventory = [_POTION.key]
        with patch(
            "world.rules.combat_session.is_in_active_session",
            side_effect=lambda actor: actor is self.aila,
        ):
            with self.assertRaises(PartyTransferError) as context:
                transfer_item(
                    self.aila, self.char1.pk, self.kahn.pk, _POTION.key, 1
                )
        self.assertEqual(context.exception.reason, REASON_TRANSFER_IN_COMBAT)

    def test_a_possessed_figure_outside_the_commander_room_cannot_act(self):
        self.char1.db.inventory = [_POTION.key]
        elsewhere = create_object(Room, key="別處")
        self.aila.move_to(elsewhere, quiet=True)

        with self.assertRaises(PartyTransferError) as context:
            transfer_item(self.aila, self.char1.pk, self.kahn.pk, _POTION.key, 1)

        self.assertEqual(context.exception.reason, REASON_MEMBER_NOT_PRESENT)
