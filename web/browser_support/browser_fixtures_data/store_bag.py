"""Store/bag fixture roles and the webclient display vocabulary.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every payload ships verbatim."""

from __future__ import annotations

from web.browser_support.browser_fixtures_data.combat_fixtures import (
    SYNTH_COMBAT_MONSTERS,
)
from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled

def store_fixture_values() -> dict:
    """The store fixture's two held-item roles for the current boot mode.

    - ``potion``: the held SELF_HEAL use-deal. At full HP the server refuses
      it with the stable ``hp_full`` reason, and the shop offers it below its
      stock cap (stock headroom), so selling the single held unit is accepted
      and its row disappears — the shipped shop's potion story mirrors here.
    - ``staple``: the other held pair; the shop stocks it AT its cap, so it
      never appears as sellable and its inventory row survives the sale.

    The ``*_display``/``*_rarity`` fields pin what the fixture's item rows
    must present (kit rows differ from shipped ones), so inventory journeys
    compare the committed panel against a mode-derived expectation instead
    of a shipped literal.
    """
    if synth_mode_enabled():
        return {
            "potion_key": "t_ember_spray",
            "staple_key": "t_huskapple",
            "potion_display": "熾焰噴射劑",
            "staple_display": "燼殼果",
            "potion_rarity": "common",
            "staple_rarity": "common",
            "potion_kind": "potion",
            "staple_kind": "material",
        }
    return {
        "potion_key": "healing_potion",
        "staple_key": "meal",
        "potion_display": "治療藥水",
        "staple_display": "普通餐食",
        "potion_rarity": "rare",
        "staple_rarity": "common",
        "potion_kind": "potion",
        "staple_kind": "food",
    }


#: The webclient's closed display vocabulary (mirrors
#: ``web/webclient-app/components/item-icons.js``): the bag inspector spells
#: every committed kind/rarity enum value with these words. Closed client UI
#: vocabulary, not catalog data — some words coincide with shipped catalog
#: tokens, so test paths resolve them through these helpers.
_ITEM_KIND_WORDS = {
    "food": "食物",
    "potion": "藥水",
    "weapon": "武器",
    "armor": "裝甲",
    "accessory": "飾品",
    "ammunition": "彈藥",
    "tool": "工具",
    "material": "素材",
    "misc": "雜項",
}
_ITEM_RARITY_WORDS = {
    "common": "普通",
    "uncommon": "罕見",
    "rare": "稀有",
    "epic": "史詩",
    "legendary": "傳說",
}


def kind_word(kind: str) -> str:
    """The inspector's Traditional-Chinese word for a committed kind value."""
    return _ITEM_KIND_WORDS[kind]


def bag_action_fixture_values() -> dict:
    """The inventory-actions fixture's roles for the current boot mode.

    The fixture seeds one INJURED holder of two potion units and one
    slotted weapon; the combat-bag journey engages the start room's first
    living combat monster. The kit rows differ from the shipped ones in
    every identifier, so the journeys resolve all four through here.
    """
    if synth_mode_enabled():
        return {
            "potion_key": "t_ember_spray",
            "potion_display": "熾焰噴射劑",
            "weapon_key": "t_thorn_knife",
            "engage_target": SYNTH_COMBAT_MONSTERS[0][0],
        }
    return {
        "potion_key": "healing_potion",
        "potion_display": "治療藥水",
        "weapon_key": "plain_sword",
        "engage_target": "goblin",
    }


def rarity_word(rarity: str) -> str:
    """The inspector's Traditional-Chinese word for a committed rarity."""
    return _ITEM_RARITY_WORDS[rarity]
