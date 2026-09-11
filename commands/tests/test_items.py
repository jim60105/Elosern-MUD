"""Command tests for 使用/use and 裝備/equip (add-inventory-item-actions 7.2).

Both commands delegate to the deterministic item-use, combat-session, and
equipment-toggle APIs, so these tests assert the command surface (usage
hints, stable refusal semantics, accepted prose) plus the round/time/cost
boundary each mode owns: exploration use spends world time, combat use
occupies exactly one initiative-ordered round, and an equipment toggle is a
free action in both modes.

Every item row is invented (test-data-independence): the whole catalog is
swapped for the kit + locally authored rows, the expected adjustment prose is
computed from the locally authored effect table, and the expected restoration
amount is read from the live effect rulebook — no shipped item key, name, or
number is restated.
"""

from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest

from commands.items import CmdToggleEquip, CmdUseItem
from world.lore.items import (
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.rules.combat_session import engage, read_session
from world.rules.equipment import EquipmentToggleReason
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.items import ItemEffectKey, ItemUseReason
from world.rules.service_messages import rejection_message
from world.rules.tests._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.equipment import EquipmentSlot, list_items
from world.tests.synthetic_data import make_item

# Preimport the import-time-validated rulebooks (item effects + equipment
# effects) before the kit is ever scoped, so their shipped-row validation
# runs against the live catalogs at import time.
import world.rules.items  # noqa: F401
import world.rules.equipment_effects  # noqa: F401

from world.rules import items as _items_rules
from world.rules import equipment_effects as _equipment_rules

# Locally authored gear vocabulary. The closed shipped modifier enum cannot
# gain members, so rows borrow members positionally at runtime (never named
# as literals); the invented effect table below is the only source their
# prose resolves through while the scope is open. Index 0 is the kit blade's
# own borrowed member, so local gear takes the next three.
_BLADE_KEY, _RING_KEY = tuple(EquipmentModifierKey)[1:3]

_SCOPE_LOGICALS = (
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
)

# Invention rows: one usable potion (the kit row), one equip/replace pair,
# six accessories for the slot-cap overflow, and one inert non-usable item.
_BLADE = make_item(
    "t_test_blade",
    display_name_zh="測試鐵牙劍",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_BLADE_KEY,
)
_BLADE_B = make_item(
    "t_test_blade_b",
    display_name_zh="測試匕首",
    price_table_key="t_ironbite_steel",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_BLADE_KEY,
)
_RING_RULE = EquipmentEffectRule(
    adjustments={"defense": 6},
    gauge_caps={"hp": 10},
    immune=(),
    attached_buffs=(),
    exposure_bias=0,
)
_MEAL = make_item(
    "t_test_meal",
    display_name_zh="測試飯糰",
    price_table_key="t_mossmeals",
    sellable=False,
    presentation=ItemPresentation(
        kind=ItemKind.MISC,
        icon_key=ItemIconKey.MISC,
        rarity=ItemRarity.COMMON,
        summary_zh="測試用的飯糰。",
    ),
)
_POTION = "t_ember_spray"


def _scope_extra() -> dict[str, dict[str, object]]:
    items = {
        _BLADE.key: _BLADE,
        _BLADE_B.key: _BLADE_B,
        _MEAL.key: _MEAL,
    }
    for index in range(1, 7):
        key = f"t_test_ring_{index}"
        items[key] = make_item(
            key,
            display_name_zh=f"測試戒指 {key}",
            price_table_key="t_ironbite_steel",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.COMMON,
                summary_zh="測試用飾品。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=_RING_KEY,
        )
    return {"items": items}


def _equip_prose(item: ItemDefinition) -> str:
    """The adjustment segment the command renders for one locally authored row."""
    rule = _EQUIPMENT_RULES[item.modifier_key]
    rendered = []
    value = rule.adjustments.get("atk_phys")
    if value:
        rendered.append(f"攻擊 +{value}")
    defense = rule.adjustments.get("defense")
    if defense:
        rendered.append(f"防禦 +{defense}")
    hp_cap = rule.gauge_caps.get("hp")
    if hp_cap:
        rendered.append(f"生命上限 +{hp_cap}")
    return "（" + "｜".join(rendered) + "）" if rendered else ""


# Locally authored equipment-effect table swapped in while the scope is open:
# both blades attack +2, the rings defend +6 with a +10 hp cap.
_EQUIPMENT_RULES = {
    _BLADE_KEY: EquipmentEffectRule(
        adjustments={"atk_phys": 2},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    _RING_KEY: _RING_RULE,
}

# The bounded restoration the live item-effect rulebook grants for the
# potion's effect key (read, never restated).
_HEAL_AMOUNT = int(_items_rules.ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount)
assert _HEAL_AMOUNT > 20, "the clamped-restore scenario needs a rule above the 20 HP gap"


class _ItemsCommandBase(EvenniaCommandTest):
    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        patcher = patch(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
            new=dict(_EQUIPMENT_RULES),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.player = self.char1
        self.player.race = _race_key()
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
        # The restored amount is clamped to the missing HP: missing 20 is
        # below the rulebook amount, so the full 20 is restored.
        self.hurt(20)
        self.player.db.inventory = [_POTION, _POTION]
        before = int(self.player.traits.hp.current)
        self.call(
            CmdUseItem(),
            _POTION,
            f"你使用了「熾焰噴射劑」，恢復了 20 點生命值。",
            caller=self.player,
        )
        self.assertEqual(int(self.player.traits.hp.current), before + 20)
        self.assertEqual(list_items(self.player), [_POTION])

    def test_full_hp_refusal_is_stable_and_touches_nothing(self):
        self.player.db.inventory = [_POTION]
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum
        self.call(
            CmdUseItem(),
            _POTION,
            rejection_message(ItemUseReason.HP_FULL),
            caller=self.player,
        )
        self.assertEqual(int(self.player.traits.hp.current), maximum)
        self.assertEqual(list_items(self.player), [_POTION])

    def test_not_held_and_not_usable_refusals_are_stable(self):
        self.hurt(10)
        self.player.db.inventory = []
        self.call(
            CmdUseItem(),
            _POTION,
            rejection_message(ItemUseReason.ITEM_NOT_HELD),
            caller=self.player,
        )
        self.player.db.inventory = [_MEAL.key]
        self.call(
            CmdUseItem(),
            _MEAL.key,
            rejection_message(ItemUseReason.NOT_USABLE),
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), [_MEAL.key])


class EquipmentToggleCommandTests(_ItemsCommandBase):
    def test_singleton_equip_then_replace_states_the_returned_item(self):
        self.player.db.inventory = [_BLADE.key, _BLADE_B.key]
        self.call(
            CmdToggleEquip(),
            _BLADE.key,
            f"你裝備了 {_BLADE.display_name_zh}{_equip_prose(_BLADE)}。",
            caller=self.player,
        )
        self.call(
            CmdToggleEquip(),
            _BLADE_B.key,
            f"你裝備了 {_BLADE_B.display_name_zh}{_equip_prose(_BLADE_B)}，"
            f"原本的 {_BLADE.display_name_zh} 已收回背包。",
            caller=self.player,
        )
        # Toggling the now-equipped item unequips it (ownership-aware).
        self.call(
            CmdToggleEquip(),
            _BLADE_B.key,
            f"你卸下了 {_BLADE_B.display_name_zh}。",
            caller=self.player,
        )

    def test_unequip_singleton_prose(self):
        self.player.db.inventory = [_BLADE.key]
        self.call(
            CmdToggleEquip(),
            _BLADE.key,
            f"你裝備了 {_BLADE.display_name_zh}{_equip_prose(_BLADE)}。",
            caller=self.player,
        )
        self.call(
            CmdToggleEquip(),
            _BLADE.key,
            f"你卸下了 {_BLADE.display_name_zh}。",
            caller=self.player,
        )

    def test_five_accessories_equip_and_the_sixth_is_refused(self):
        keys = [f"t_test_ring_{i}" for i in range(1, 7)]
        self.player.db.inventory = list(keys)
        for key in keys[:5]:
            self.call(
                CmdToggleEquip(),
                key,
                f"你佩戴了 測試戒指 {key}（防禦 +6｜生命上限 +10）。",
                caller=self.player,
            )
        self.call(
            CmdToggleEquip(),
            keys[5],
            rejection_message(EquipmentToggleReason.ACCESSORY_SLOTS_FULL),
            caller=self.player,
        )

    def test_not_equipment_refusal_is_stable(self):
        self.player.db.inventory = [_POTION]
        self.call(
            CmdToggleEquip(),
            _POTION,
            rejection_message(EquipmentToggleReason.NOT_EQUIPMENT),
            caller=self.player,
        )
        self.assertIsNone(self.player.db.equipment)


class CombatItemCommandTests(BattlefieldIsolation, EvenniaTest):
    """In-session routing: one round per accepted use, none per toggle."""

    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        patcher = patch(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
            new=dict(_EQUIPMENT_RULES),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
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

    @covers_requirement(
        "inventory-item-actions::text-clients-expose-the-same-deterministic-item-operations"
    )
    def test_combat_use_consumes_exactly_one_round(self):
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum - _HEAL_AMOUNT
        self.player.db.inventory = [_POTION]
        engage(self.player, self.monster)
        messages = self._run(CmdUseItem(), _POTION)
        self.assertTrue(any("使用了「熾焰噴射劑」" in line for line in messages))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(list_items(self.player), [])

    @covers_requirement(
        "inventory-item-actions::text-clients-expose-the-same-deterministic-item-operations"
    )
    def test_combat_full_hp_refusal_consumes_no_round(self):
        maximum = int(self.player.traits.hp.max)
        self.player.traits.hp.current = maximum
        self.player.db.inventory = [_POTION]
        engage(self.player, self.monster)
        messages = self._run(CmdUseItem(), _POTION)
        self.assertEqual(messages, [rejection_message(ItemUseReason.HP_FULL)])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(list_items(self.player), [_POTION])

    def test_combat_equipment_toggle_consumes_no_round(self):
        self.player.db.inventory = [_BLADE.key]
        engage(self.player, self.monster)
        messages = self._run(CmdToggleEquip(), _BLADE.key)
        self.assertEqual(
            messages,
            [f"你裝備了 {_BLADE.display_name_zh}{_equip_prose(_BLADE)}。"],
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
