"""Slice of ``test_item_use``: recovery-food profile mechanics.

The item and its profile are synthetic. Shipped food rows are balance data,
so this slice pins only the mechanics a recovery food reaches through the
ordinary item-use boundary: ordered multi-gauge recovery under the ordinary
caps, exactly one consumed serving, and a combat refusal that writes nothing.
"""

from tools.spec_traceability import covers_requirement

from world.lore.items import (
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
)
from world.rules.items import ItemUseReason, ItemUseRequest, resolve_item_use
from world.skills.equipment import list_items
from world.tests.synthetic_data import make_item

from ._support import _ItemUseTestCase

_RATION_KEY = "t_trail_ration"

# Fixed synthetic magnitudes (an HP/MP/SP triple that no shipped row declares),
# so every expected value below is independent of the game data.
_RATION_HP = 7
_RATION_MP = 9
_RATION_SP = 11

_RATION = make_item(
    _RATION_KEY,
    display_name_zh="合成旅糧",
    price_table_key="t_mossmeals",
    presentation=ItemPresentation(
        kind=ItemKind.FOOD,
        icon_key=ItemIconKey.FOOD,
        rarity=ItemRarity.COMMON,
        summary_zh="測試用的合成旅糧。",
    ),
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=False),
)

_RATION_PROFILE = ItemEffectProfile(
    effects=(
        GaugeAdjustEffect(stat=ItemStat.HP, amount=_RATION_HP),
        GaugeAdjustEffect(stat=ItemStat.MP, amount=_RATION_MP),
        GaugeAdjustEffect(stat=ItemStat.SP, amount=_RATION_SP),
    )
)


class FoodRecoveryUseTests(_ItemUseTestCase):
    """A committed out-of-combat serving feeds the profile; combat refuses it."""

    def setUp(self):
        super().setUp()
        self.register_fixture(_RATION, _RATION_PROFILE)

    def drain(self, gauge: str, missing: int) -> tuple[int, int]:
        """Lower one gauge by ``missing``; return (current, maximum)."""
        maximum = int(getattr(self.actor.traits, gauge).max)
        getattr(self.actor.traits, gauge).current = maximum - missing
        return maximum - missing, maximum

    @covers_requirement(
        "item-use-resolution::recovery-food-is-an-out-of-combat-consumable"
    )
    def test_committed_serving_restores_gauges_in_profile_order(self):
        hp_before, hp_max = self.drain("hp", 3)
        mp_before, _ = self.drain("mp", 40)
        sp_before, _ = self.drain("sp", 30)
        self.actor.db.inventory = [_RATION_KEY, _RATION_KEY]

        result = resolve_item_use(
            ItemUseRequest(self.actor, _RATION_KEY), in_combat=False
        )

        self.assertEqual(result.outcome, "success")
        # HP is already inside its last three points, so it stops at the cap;
        # MP and SP gain their full authored amounts below their caps.
        self.assertEqual(int(self.actor.traits.hp.current), hp_max)
        self.assertGreater(hp_before + _RATION_HP, hp_max)
        self.assertEqual(int(self.actor.traits.mp.current), mp_before + _RATION_MP)
        self.assertEqual(int(self.actor.traits.sp.current), sp_before + _RATION_SP)
        # Exactly one serving leaves the stack.
        self.assertEqual(list_items(self.actor), [_RATION_KEY])
        self.assertEqual(
            [(entry.data["stat"], entry.data["amount"]) for entry in result.event_log.entries],
            [("hp", 3), ("mp", _RATION_MP), ("sp", _RATION_SP)],
        )

    @covers_requirement(
        "item-use-resolution::recovery-food-is-an-out-of-combat-consumable"
    )
    def test_combat_attempt_refuses_without_consuming_or_restoring(self):
        self.drain("hp", 5)
        self.drain("mp", 5)
        self.drain("sp", 5)
        self.actor.db.inventory = [_RATION_KEY]
        before = self.canonical_state()

        result = resolve_item_use(
            ItemUseRequest(self.actor, _RATION_KEY), in_combat=True
        )

        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.COMBAT_NOT_ALLOWED)
        self.assertIsNone(result.event_log)
        self.assert_state_unchanged(before)
