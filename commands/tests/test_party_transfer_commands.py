"""Command tests for the member transfer text surface (party-transfer-text-commands).

``給`` routes a target that names a party member through the party item
transfer rule, while every other target keeps the legacy give path (including
quest delivery advancement). ``取回`` moves an item from a present member back
into the commander's bag. Both surfaces share the rule's fixed refusals with
the ``party.transfer`` action.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.items import CmdRetrieve
from commands.localized import CmdGive

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import read_records
from world.quests.tests._fixtures import (
    RegistryIsolationMixin,
    accept,
    deliver,
    quest,
    register,
)
from world.rules.clock import get_world_clock
from world.rules.combat_session import engage
from world.rules.equipment import materialize_registry_object, toggle_equipment
from world.rules.party import join_party
from world.rules.party_inventory import (
    REASON_INVALID_QUANTITY,
    REASON_ITEM_EQUIPPED,
    REASON_ITEM_LOCKED,
    REASON_ITEM_NOT_HELD,
    REASON_TRANSFER_IN_COMBAT,
    REASON_TRANSFER_SAME_MEMBER,
    TRANSFER_MESSAGES,
)
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
)
from world.rules.possession import enter_possession
from world.rules.tests._combat_session_helpers import _monster, _race_key
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import make_item, synthetic_registries

_POTION = make_item("t_cmd_transfer_potion", display_name_zh="測試藥水", sellable=False)
_BLADE = make_item(
    "t_cmd_transfer_blade",
    display_name_zh="測試長劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_SEAL = make_item(
    "t_cmd_transfer_seal", display_name_zh="測試徽記", sellable=False, guild_property=True
)


def _scope_extra():
    """The locally authored item rows this module exercises."""
    return {"items": {row.key: row for row in (_POTION, _BLADE, _SEAL)}}


class _TransferCommandBase(BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """A commander with two present companions over locally authored rows."""

    def setUp(self):
        scope = synthetic_registries(
            "races", "static_tiers", "subraces", "items", extra=_scope_extra()
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.room = create_object(Room, key="測試房間")
        self.commander = create_object(
            PlayerCharacter, key="指揮者", location=self.room
        )
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.commander)
        return npc

    def _outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def _hold(self, entity, *keys):
        entity.db.inventory = list(keys)

    def _mirror(self, entity, item_key):
        return materialize_registry_object(entity, item_key)

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

    def _bags(self, *entities):
        return {entity.pk: self._bag_state(entity) for entity in entities}

    def _assert_unchanged(self, before, *entities):
        for entity in entities:
            self.assertEqual(self._bag_state(entity), before[entity.pk])

    def _give(self, args, caller=None):
        return self.call(CmdGive(), args, caller=caller or self.commander)

    def _retrieve(self, args, caller=None):
        return self.call(CmdRetrieve(), args, caller=caller or self.commander)


class MemberGiveCommandTests(_TransferCommandBase):
    """A member target routes through the rule; other targets stay legacy."""

    @covers_requirement(
        "equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list"
    )
    @covers_requirement(
        "party-item-transfer::text-clients-move-items-between-members"
    )
    def test_member_give_with_a_count_moves_both_bags_through_the_rule(self):
        self._hold(self.commander, *([_POTION.key] * 3))
        first = self._mirror(self.commander, _POTION.key)
        second = self._mirror(self.commander, _POTION.key)
        third = self._mirror(self.commander, _POTION.key)

        output = self._give(f"2 個 {_POTION.key} = 艾拉")

        self.assertIn(f"你把 2 個{_POTION.display_name_zh}交給了艾拉。", output)
        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertEqual(self.aila.db.inventory, [_POTION.key, _POTION.key])
        self.assertEqual(
            sorted(obj.pk for obj in self.aila.contents_get()), [first.pk, second.pk]
        )
        self.assertEqual([obj.pk for obj in self.commander.contents_get()], [third.pk])

    def test_member_give_resolves_the_display_name_without_a_mirror(self):
        self._hold(self.commander, _POTION.key)
        self.aila.attributes.add("npc_title", "合成稱號")

        output = self._give(f"{_POTION.display_name_zh} = 艾拉")

        self.assertIn(f"你把 1 個{_POTION.display_name_zh}交給了艾拉。", output)
        self.assertNotIn("合成稱號", output)
        self.assertEqual(self.commander.db.inventory, [])
        self.assertEqual(self.aila.db.inventory, [_POTION.key])

    def test_member_give_moves_one_copy_when_no_count_is_given(self):
        self._hold(self.commander, _POTION.key, _POTION.key)
        self._mirror(self.commander, _POTION.key)
        self._mirror(self.commander, _POTION.key)

        self._give(f"{_POTION.key} = 艾拉")

        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertEqual(self.aila.db.inventory, [_POTION.key])

    def test_explicit_zero_or_over_limit_count_is_the_invalid_quantity_refusal(self):
        self._hold(self.commander, _POTION.key)
        before = self._bags(self.commander, self.aila)

        for count in ("0", "0 個", "100"):
            with self.subTest(count=count):
                output = self._give(f"{count} {_POTION.key} = 艾拉")
                self.assertIn(TRANSFER_MESSAGES[REASON_INVALID_QUANTITY], output)
                self._assert_unchanged(before, self.commander, self.aila)

    def test_missing_item_reports_the_rule_refusal_and_writes_nothing(self):
        before = self._bags(self.commander, self.aila)

        output = self._give(f"{_POTION.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_ITEM_NOT_HELD], output)
        self._assert_unchanged(before, self.commander, self.aila)

    def test_combat_wins_over_a_missing_item(self):
        monster = _monster("測試魔物")
        monster.location = self.room
        engage(self.commander, monster)
        before = self._bags(self.commander, self.aila)

        output = self._give(f"{_POTION.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_TRANSFER_IN_COMBAT], output)
        self._assert_unchanged(before, self.commander, self.aila)

    def test_giving_to_self_is_the_same_member_refusal(self):
        self._hold(self.commander, _POTION.key)
        before = self._bags(self.commander, self.aila)

        output = self._give(f"{_POTION.key} = 指揮者")

        self.assertIn(TRANSFER_MESSAGES[REASON_TRANSFER_SAME_MEMBER], output)
        self._assert_unchanged(before, self.commander, self.aila)

    def test_absent_companion_is_refused_without_a_legacy_fallback(self):
        elsewhere = create_object(Room, key="別處")
        self.aila.move_to(elsewhere, quiet=True)
        self._hold(self.commander, _POTION.key)
        before = self._bags(self.commander, self.aila)

        output = self._give(f"{_POTION.key} = 艾拉")

        self.assertIn(PARTY_SCOPE_MESSAGES[REASON_MEMBER_NOT_PRESENT], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list"
    )
    def test_non_member_npc_keeps_the_legacy_give_path(self):
        outsider = self._outsider()
        self._hold(self.commander, _POTION.key)
        self._mirror(self.commander, _POTION.key)

        output = self._give(f"{_POTION.key} = {outsider.key}")

        self.assertIn(f"你把{_POTION.key}交給了 {outsider.key}。", output)
        self.assertEqual(self.commander.db.inventory, [])
        self.assertEqual(outsider.db.inventory, [_POTION.key])

    def test_another_player_keeps_the_legacy_give_path(self):
        other = create_object(PlayerCharacter, key="另一位玩家", location=self.room)
        other.race = _race_key()
        other.apply_race_baseline()
        self._hold(self.commander, _POTION.key)
        self._mirror(self.commander, _POTION.key)

        output = self._give(f"{_POTION.key} = 另一位玩家")

        self.assertIn(f"你把{_POTION.key}交給了 另一位玩家。", output)
        self.assertEqual(other.db.inventory, [_POTION.key])


class NonMemberDeliveryGiveTests(RegistryIsolationMixin, _TransferCommandBase):
    """A quest-bound non-member recipient still advances the delivery."""

    def setUp(self):
        super().setUp()
        self.recipient = self._outsider("灰婆婆")
        self.definition = register(
            quest(
                "cmd_give_delivery_quest",
                stages=(QuestStage(0, deliver(_POTION.key, quantity=2)),),
            )
        )
        self.record = accept(self.commander, self.definition.key)
        bind_stage_runtime(
            self.commander,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    @covers_requirement("quest-delivery::the-general-give-advances-the-delivery")
    def test_delivery_to_a_non_member_still_advances(self):
        self._hold(self.commander, _POTION.key)

        output = self._give(f"{_POTION.key} = 灰婆婆")

        self.assertIn("交給了", output)
        self.assertEqual(self.recipient.db.inventory, [_POTION.key])
        self.assertEqual(read_records(self.commander)[0].stage_progress, 1)


class RetrieveCommandTests(_TransferCommandBase):
    """取回 moves a member's copy into the commander's bag, or refuses fixedly."""

    @covers_requirement(
        "party-item-transfer::a-transfer-moves-both-bags-atomically-and-costs-nothing"
    )
    @covers_requirement(
        "party-item-transfer::text-clients-move-items-between-members"
    )
    def test_retrieve_moves_a_copy_to_the_commander_without_advancing_time(self):
        self._hold(self.aila, _POTION.key, _POTION.key)
        self.aila.attributes.add("npc_title", "合成稱號")
        first = self._mirror(self.aila, _POTION.key)
        second = self._mirror(self.aila, _POTION.key)
        tick = get_world_clock().tick

        output = self._retrieve(f"{_POTION.key} = 艾拉")

        self.assertIn(f"你從艾拉那裡取回了 1 個{_POTION.display_name_zh}。", output)
        self.assertNotIn("合成稱號", output)
        self.assertEqual(self.aila.db.inventory, [_POTION.key])
        self.assertEqual(self.commander.db.inventory, [_POTION.key])
        self.assertEqual([obj.pk for obj in self.commander.contents_get()], [first.pk])
        self.assertEqual([obj.pk for obj in self.aila.contents_get()], [second.pk])
        self.assertEqual(get_world_clock().tick, tick)

    def test_retrieve_accepts_the_display_name_and_a_count(self):
        self._hold(self.aila, *([_POTION.key] * 2))

        output = self._retrieve(f"2 個 {_POTION.display_name_zh} = 艾拉")

        self.assertIn(f"你從艾拉那裡取回了 2 個{_POTION.display_name_zh}。", output)
        self.assertEqual(self.commander.db.inventory, [_POTION.key, _POTION.key])

    def test_explicit_zero_or_over_limit_count_is_the_invalid_quantity_refusal(self):
        self._hold(self.aila, _POTION.key)
        before = self._bags(self.commander, self.aila)

        for count in ("0", "0 個", "100"):
            with self.subTest(count=count):
                output = self._retrieve(f"{count} {_POTION.key} = 艾拉")
                self.assertIn(TRANSFER_MESSAGES[REASON_INVALID_QUANTITY], output)
                self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement("party-item-transfer::transfers-happen-only-outside-combat")
    def test_retrieve_in_combat_is_refused(self):
        self._hold(self.aila, _POTION.key)
        monster = _monster("測試魔物")
        monster.location = self.room
        engage(self.commander, monster)
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_POTION.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_TRANSFER_IN_COMBAT], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "party-item-transfer::transfer-rejections-are-stable-and-observable"
    )
    @covers_requirement(
        "party-item-transfer::text-clients-move-items-between-members"
    )
    def test_unknown_member_token_is_refused(self):
        self._hold(self.aila, _POTION.key)
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_POTION.key} = 不存在的人")

        self.assertIn(PARTY_SCOPE_MESSAGES[REASON_NOT_PARTY_MEMBER], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "party-item-transfer::giver-and-receiver-are-distinct-authorized-members"
    )
    def test_absent_member_is_refused(self):
        elsewhere = create_object(Room, key="別處")
        self.aila.move_to(elsewhere, quiet=True)
        self._hold(self.aila, _POTION.key)
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_POTION.key} = 艾拉")

        self.assertIn(PARTY_SCOPE_MESSAGES[REASON_MEMBER_NOT_PRESENT], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "party-item-transfer::transfer-rejections-are-stable-and-observable"
    )
    @covers_requirement(
        "party-item-transfer::text-clients-move-items-between-members"
    )
    def test_equipped_item_is_refused(self):
        self._hold(self.aila, _BLADE.key)
        self.assertEqual(toggle_equipment(self.aila, _BLADE.key).outcome, "success")
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_BLADE.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_ITEM_EQUIPPED], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "party-item-transfer::transfer-rejections-are-stable-and-observable"
    )
    def test_locked_item_is_refused(self):
        self._hold(self.aila, _SEAL.key)
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_SEAL.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_ITEM_LOCKED], output)
        self._assert_unchanged(before, self.commander, self.aila)

    @covers_requirement(
        "party-item-transfer::transfer-rejections-are-stable-and-observable"
    )
    def test_item_the_member_does_not_hold_is_refused(self):
        before = self._bags(self.commander, self.aila)

        output = self._retrieve(f"{_POTION.key} = 艾拉")

        self.assertIn(TRANSFER_MESSAGES[REASON_ITEM_NOT_HELD], output)
        self._assert_unchanged(before, self.commander, self.aila)


class PossessedRetrieveTests(EvenniaCommandTestMixin, EvenniaTest):
    """A possessed figure is only the anchor; the commander receives."""

    def setUp(self):
        scope = synthetic_registries(
            "races", "static_tiers", "subraces", "items", extra=_scope_extra()
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        enter_possession(self.char1, self.aila)

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.char1)
        return npc

    @covers_requirement(
        "party-item-transfer::giver-and-receiver-are-distinct-authorized-members"
    )
    @covers_requirement(
        "party-item-transfer::text-clients-move-items-between-members"
    )
    def test_retrieve_while_possessing_a_member_fills_the_commander_bag(self):
        self.char1.db.inventory = []
        self.aila.db.inventory = []
        self.kahn.db.inventory = [_POTION.key]
        mirror = materialize_registry_object(self.kahn, _POTION.key)

        output = self.call(CmdRetrieve(), f"{_POTION.key} = 卡恩", caller=self.aila)

        self.assertIn(f"你從卡恩那裡取回了 1 個{_POTION.display_name_zh}。", output)
        self.assertEqual(self.char1.db.inventory, [_POTION.key])
        self.assertEqual(self.kahn.db.inventory, [])
        self.assertEqual(self.aila.db.inventory, [])
        self.assertEqual([obj.pk for obj in self.char1.contents_get()], [mirror.pk])
        self.assertEqual(list(self.aila.contents_get()), [])
