"""Command tests for 使用/use and 裝備/equip (add-inventory-item-actions 7.2).

Both commands delegate to the deterministic item-use, combat-session, and
equipment-toggle APIs, so these tests assert the command surface (usage
hints, stable refusal semantics, accepted prose) plus the round/time/cost
boundary each mode owns: exploration use spends world time, combat use
occupies exactly one initiative-ordered round, and an equipment toggle is a
free action in both modes.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from commands.items import CmdToggleEquip, CmdUseItem
from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.rules.combat_session import engage, read_session
from world.rules.equipment import EquipmentToggleReason
from world.rules.items import ItemUseReason
from world.rules.service_messages import rejection_message
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.equipment import EquipmentSlot, list_items

from world.rules.tests._combat_session_helpers import _monster, _player

def _weapon_fixture(key: str, display_name_zh: str) -> ItemDefinition:
    return ItemDefinition(
        key=key,
        display_name_zh=display_name_zh,
        price_table_key="plain_sword",
        sellable=False,
        presentation=ItemPresentation(
            kind=ItemKind.WEAPON,
            icon_key=ItemIconKey.WEAPON,
            rarity=ItemRarity.COMMON,
            summary_zh="測試用武器。",
        ),
        equipment_slot=EquipmentSlot.WEAPON_MAIN,
    )


def _accessory_fixture(key: str) -> ItemDefinition:
    return ItemDefinition(
        key=key,
        display_name_zh=f"測試戒指 {key}",
        price_table_key="potion",
        sellable=False,
        presentation=ItemPresentation(
            kind=ItemKind.ACCESSORY,
            icon_key=ItemIconKey.ACCESSORY,
            rarity=ItemRarity.COMMON,
            summary_zh="測試用飾品。",
        ),
        equipment_slot=EquipmentSlot.ACCESSORY,
    )


class _ItemsCommandBase(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        registry_snapshot = dict(ITEM_REGISTRY)

        def restore_registry():
            ITEM_REGISTRY.clear()
            ITEM_REGISTRY.update(registry_snapshot)

        self.addCleanup(restore_registry)
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.db.inventory = []
        self.player.db.equipment = None

    def hurt(self, missing: int) -> None:
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum - missing


class ExplorationUseTests(_ItemsCommandBase):
    def test_usage_hints_without_arguments(self):
        self.call(CmdUseItem(), "", "用法：使用 <item_key>")
        self.call(CmdToggleEquip(), "", "用法：裝備 <item_key>")

    def test_exploration_use_heals_and_consumes_one_of_two(self):
        self.hurt(20)
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        before = int(self.player.traits.hp.current)
        self.call(
            CmdUseItem(),
            "healing_potion",
            "你使用了「治療藥水」，恢復了 20 點生命值。",
            caller=self.player,
        )
        # The restored amount is clamped to the missing HP: min(40, 20) == 20.
        self.assertEqual(int(self.player.traits.hp.current), before + 20)
        self.assertEqual(list_items(self.player), ["healing_potion"])

    def test_full_hp_refusal_is_stable_and_touches_nothing(self):
        self.player.db.inventory = ["healing_potion"]
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum
        self.call(
            CmdUseItem(),
            "healing_potion",
            rejection_message(ItemUseReason.HP_FULL),
            caller=self.player,
        )
        self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(list_items(self.player), ["healing_potion"])

    def test_not_held_and_not_usable_refusals_are_stable(self):
        self.hurt(10)
        self.player.db.inventory = []
        self.call(
            CmdUseItem(),
            "healing_potion",
            rejection_message(ItemUseReason.ITEM_NOT_HELD),
            caller=self.player,
        )
        self.player.db.inventory = ["meal"]
        self.call(
            CmdUseItem(),
            "meal",
            rejection_message(ItemUseReason.NOT_USABLE),
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), ["meal"])


class EquipmentToggleCommandTests(_ItemsCommandBase):
    def test_singleton_equip_then_replace_states_the_returned_item(self):
        ITEM_REGISTRY["test_second_blade"] = _weapon_fixture(
            "test_second_blade", "測試匕首"
        )
        self.player.db.inventory = ["plain_sword", "test_second_blade"]
        self.call(
            CmdToggleEquip(),
            "plain_sword",
            "你裝備了 普通劍。",
            caller=self.player,
        )
        self.call(
            CmdToggleEquip(),
            "test_second_blade",
            "你裝備了 測試匕首，原本的 普通劍 已收回背包。",
            caller=self.player,
        )
        # Toggling the now-equipped item unequips it (ownership-aware).
        self.call(
            CmdToggleEquip(),
            "test_second_blade",
            "你卸下了 測試匕首。",
            caller=self.player,
        )

    def test_unequip_singleton_prose(self):
        self.player.db.inventory = ["plain_sword"]
        self.call(CmdToggleEquip(), "plain_sword", "你裝備了 普通劍。", caller=self.player)
        self.call(CmdToggleEquip(), "plain_sword", "你卸下了 普通劍。", caller=self.player)

    def test_five_accessories_equip_and_the_sixth_is_refused(self):
        keys = [f"test_cap_ring_{i}" for i in range(1, 7)]
        for key in keys:
            ITEM_REGISTRY[key] = _accessory_fixture(key)
        self.player.db.inventory = list(keys)
        for key in keys[:5]:
            self.call(
                CmdToggleEquip(),
                key,
                f"你佩戴了 測試戒指 {key}。",
                caller=self.player,
            )
        self.call(
            CmdToggleEquip(),
            keys[5],
            rejection_message(EquipmentToggleReason.ACCESSORY_SLOTS_FULL),
            caller=self.player,
        )

    def test_not_equipment_refusal_is_stable(self):
        self.player.db.inventory = ["healing_potion"]
        self.call(
            CmdToggleEquip(),
            "healing_potion",
            rejection_message(EquipmentToggleReason.NOT_EQUIPMENT),
            caller=self.player,
        )
        self.assertIsNone(self.player.db.equipment)


class CombatItemCommandTests(BattlefieldIsolation, EvenniaTest):
    """In-session routing: one round per accepted use, none per toggle."""

    def setUp(self):
        super().setUp()
        from typeclasses.rooms import Room

        self.room = create_object(Room, key="item command arena")
        self.player = _player("item commander")
        self.player.location = self.room
        self.player.db.inventory = []
        self.player.db.equipment = None
        self.monster = _monster("goblin commander", hp=100, atk=0)
        self.monster.location = self.room

    def _run(self, command, args: str) -> list[str]:
        command.caller = self.player
        command.args = args
        command.cmdstring = command.key
        messages: list[str] = []
        with patch.object(self.player, "msg", side_effect=messages.append):
            command.func()
        return messages

    def test_combat_use_consumes_exactly_one_round(self):
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum - 20
        self.player.db.inventory = ["healing_potion"]
        engage(self.player, self.monster)
        messages = self._run(CmdUseItem(), "healing_potion")
        self.assertTrue(any("使用了「治療藥水」" in line for line in messages))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(list_items(self.player), [])

    def test_combat_full_hp_refusal_consumes_no_round(self):
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum
        self.player.db.inventory = ["healing_potion"]
        engage(self.player, self.monster)
        messages = self._run(CmdUseItem(), "healing_potion")
        self.assertEqual(messages, [rejection_message(ItemUseReason.HP_FULL)])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(list_items(self.player), ["healing_potion"])

    def test_combat_equipment_toggle_consumes_no_round(self):
        self.player.db.inventory = ["plain_sword"]
        engage(self.player, self.monster)
        messages = self._run(CmdToggleEquip(), "plain_sword")
        self.assertEqual(messages, ["你裝備了 普通劍。"])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
